"""
Rate limiting for CoreLogic API client.
"""

import asyncio
import time
import logging
from typing import Dict, Any
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CostTrackingData:
    """Data structure for tracking API costs."""
    daily_cost: float = 0.0
    monthly_cost: float = 0.0
    request_count: int = 0
    valuation_count: int = 0
    last_reset_day: int = 0
    last_reset_month: int = 0
    cost_history: deque = field(default_factory=lambda: deque(maxlen=1000))


class CoreLogicRateLimitManager:
    """
    Rate limiting and cost management for CoreLogic API.
    
    CoreLogic has different rate limiting patterns:
    - Hourly limits instead of per-minute
    - Cost-based throttling
    - Different limits for different operation types
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Rate limiting
        self._request_times: deque = deque()
        self._hourly_request_count = 0
        self._last_hour_reset = time.time()
        
        # Cost tracking
        self._cost_data = CostTrackingData()
        
        # Operation-specific tracking
        self._operation_counts: Dict[str, int] = {}
        self._operation_costs: Dict[str, float] = {}
        
        # Locks for thread safety
        self._rate_limit_lock = asyncio.Lock()
        self._cost_lock = asyncio.Lock()
        
        # Circuit breaker state
        self._circuit_open = False
        self._circuit_failures = 0
        self._circuit_last_failure = 0
    
    async def acquire_request_slot(self, operation: str = "general", 
                                 estimated_cost: float = 0.0) -> bool:
        """
        Acquire a request slot with rate limiting and cost checking.
        
        Args:
            operation: Type of operation being performed
            estimated_cost: Estimated cost of the operation
            
        Returns:
            bool: True if request can proceed, False if should be throttled
        """
        async with self._rate_limit_lock:
            current_time = time.time()
            
            # Check circuit breaker
            if self._circuit_open:
                if current_time - self._circuit_last_failure > self.config.circuit_timeout:
                    self._circuit_open = False
                    self._circuit_failures = 0
                    self.logger.info("Circuit breaker reset - allowing requests")
                else:
                    self.logger.warning("Circuit breaker open - blocking request")
                    return False
            
            # Reset hourly counter if needed
            if current_time - self._last_hour_reset >= 3600:  # 1 hour
                self._hourly_request_count = 0
                self._last_hour_reset = current_time
                self.logger.debug("Hourly rate limit counter reset")
            
            # Check hourly rate limit
            max_hourly = self.config.get_tier_setting("max_requests_per_hour", 1000)
            if self._hourly_request_count >= max_hourly:
                self.logger.warning(f"Hourly rate limit reached: {self._hourly_request_count}/{max_hourly}")
                return False
            
            # Check per-second rate limit
            self._cleanup_old_requests(current_time)
            if len(self._request_times) >= self.config.requests_per_second:
                self.logger.debug("Per-second rate limit reached")
                return False
            
            # Check cost limits
            if not await self._check_cost_limits(estimated_cost):
                return False
            
            # All checks passed - allow request
            self._request_times.append(current_time)
            self._hourly_request_count += 1
            
            # Track operation
            self._operation_counts[operation] = self._operation_counts.get(operation, 0) + 1
            
            self.logger.debug(f"Request slot acquired for {operation}")
            return True
    
    async def record_request_cost(self, operation: str, actual_cost: float) -> None:
        """Record the actual cost of a completed request."""
        async with self._cost_lock:
            current_time = time.time()
            
            # Reset daily/monthly counters if needed
            self._reset_cost_counters()
            
            # Update cost tracking
            self._cost_data.daily_cost += actual_cost
            self._cost_data.monthly_cost += actual_cost
            self._cost_data.request_count += 1
            
            if "valuation" in operation:
                self._cost_data.valuation_count += 1
            
            # Update operation-specific costs
            self._operation_costs[operation] = self._operation_costs.get(operation, 0.0) + actual_cost
            
            # Record in history
            self._cost_data.cost_history.append({
                "timestamp": current_time,
                "operation": operation,
                "cost": actual_cost
            })
            
            # Check for budget alerts
            await self._check_budget_alerts()
            
            self.logger.debug(f"Recorded cost ${actual_cost:.2f} for {operation}")
    
    async def record_request_failure(self, operation: str, error: Exception) -> None:
        """Record a failed request for circuit breaker logic."""
        self._circuit_failures += 1
        self._circuit_last_failure = time.time()
        
        if self._circuit_failures >= self.config.failure_threshold:
            self._circuit_open = True
            self.logger.error(f"Circuit breaker opened after {self._circuit_failures} failures")
        
        self.logger.warning(f"Request failure recorded for {operation}: {error}")
    
    async def get_current_limits(self) -> Dict[str, Any]:
        """Get current rate limiting and cost status."""
        current_time = time.time()
        
        # Calculate requests in current window
        self._cleanup_old_requests(current_time)
        
        # Reset counters if needed
        if current_time - self._last_hour_reset >= 3600:
            self._hourly_request_count = 0
            self._last_hour_reset = current_time
        
        self._reset_cost_counters()
        
        max_hourly = self.config.get_tier_setting("max_requests_per_hour", 1000)
        
        return {
            "requests_per_second_used": len(self._request_times),
            "requests_per_second_limit": self.config.requests_per_second,
            "hourly_requests_used": self._hourly_request_count,
            "hourly_requests_limit": max_hourly,
            "daily_cost": self._cost_data.daily_cost,
            "monthly_cost": self._cost_data.monthly_cost,
            "daily_budget_limit": self.config.cost_management["daily_budget_limit"],
            "monthly_budget_limit": self.config.cost_management["monthly_budget_limit"],
            "circuit_breaker_open": self._circuit_open,
            "circuit_failures": self._circuit_failures,
            "operation_counts": self._operation_counts.copy(),
            "operation_costs": self._operation_costs.copy()
        }
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove request timestamps older than 1 second."""
        cutoff = current_time - 1.0
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()
    
    async def _check_cost_limits(self, estimated_cost: float) -> bool:
        """Check if adding estimated cost would exceed budget limits."""
        if not self.config.cost_management.get("enable_cost_tracking", False):
            return True
        
        self._reset_cost_counters()
        
        daily_limit = self.config.cost_management["daily_budget_limit"]
        monthly_limit = self.config.cost_management["monthly_budget_limit"]
        
        # Check daily limit
        if self._cost_data.daily_cost + estimated_cost > daily_limit:
            if self.config.cost_management.get("auto_suspend_on_budget_exceeded", False):
                self.logger.error(f"Daily budget limit would be exceeded: "
                                f"${self._cost_data.daily_cost + estimated_cost:.2f} > ${daily_limit:.2f}")
                return False
        
        # Check monthly limit
        if self._cost_data.monthly_cost + estimated_cost > monthly_limit:
            if self.config.cost_management.get("auto_suspend_on_budget_exceeded", False):
                self.logger.error(f"Monthly budget limit would be exceeded: "
                                f"${self._cost_data.monthly_cost + estimated_cost:.2f} > ${monthly_limit:.2f}")
                return False
        
        return True
    
    def _reset_cost_counters(self) -> None:
        """Reset daily/monthly cost counters if time period has passed."""
        import datetime
        
        now = datetime.datetime.now()
        current_day = now.timetuple().tm_yday
        current_month = now.month
        
        # Reset daily counter
        if self._cost_data.last_reset_day != current_day:
            self._cost_data.daily_cost = 0.0
            self._cost_data.last_reset_day = current_day
            self.logger.debug("Daily cost counter reset")
        
        # Reset monthly counter
        if self._cost_data.last_reset_month != current_month:
            self._cost_data.monthly_cost = 0.0
            self._cost_data.last_reset_month = current_month
            self.logger.debug("Monthly cost counter reset")
    
    async def _check_budget_alerts(self) -> None:
        """Check if budget alert thresholds have been reached."""
        if not self.config.cost_management.get("enable_cost_tracking", False):
            return
        
        alert_threshold = self.config.cost_management.get("alert_threshold_percentage", 80.0) / 100.0
        
        daily_limit = self.config.cost_management["daily_budget_limit"]
        monthly_limit = self.config.cost_management["monthly_budget_limit"]
        
        # Check daily alert
        if self._cost_data.daily_cost >= daily_limit * alert_threshold:
            self.logger.warning(f"Daily budget alert: ${self._cost_data.daily_cost:.2f} "
                               f"(${daily_limit * alert_threshold:.2f} threshold)")
        
        # Check monthly alert
        if self._cost_data.monthly_cost >= monthly_limit * alert_threshold:
            self.logger.warning(f"Monthly budget alert: ${self._cost_data.monthly_cost:.2f} "
                               f"(${monthly_limit * alert_threshold:.2f} threshold)")
    
    async def wait_for_rate_limit_reset(self) -> float:
        """
        Calculate wait time until rate limit resets.
        
        Returns:
            float: Seconds to wait
        """
        current_time = time.time()
        
        # Check per-second limit
        self._cleanup_old_requests(current_time)
        if len(self._request_times) > 0:
            oldest_request = self._request_times[0]
            wait_time = 1.0 - (current_time - oldest_request)
            if wait_time > 0:
                return wait_time
        
        # Check hourly limit
        if self._hourly_request_count >= self.config.get_tier_setting("max_requests_per_hour", 1000):
            seconds_until_hour_reset = 3600 - (current_time - self._last_hour_reset)
            if seconds_until_hour_reset > 0:
                return seconds_until_hour_reset
        
        return 0.0
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get a summary of API costs and usage."""
        self._reset_cost_counters()
        
        return {
            "daily_cost": self._cost_data.daily_cost,
            "monthly_cost": self._cost_data.monthly_cost,
            "total_requests": self._cost_data.request_count,
            "valuation_count": self._cost_data.valuation_count,
            "average_cost_per_request": (
                self._cost_data.daily_cost / max(self._cost_data.request_count, 1)
            ),
            "operation_breakdown": {
                "counts": self._operation_counts.copy(),
                "costs": self._operation_costs.copy()
            },
            "budget_utilization": {
                "daily_percentage": (
                    self._cost_data.daily_cost / 
                    self.config.cost_management["daily_budget_limit"] * 100
                ),
                "monthly_percentage": (
                    self._cost_data.monthly_cost / 
                    self.config.cost_management["monthly_budget_limit"] * 100
                )
            }
        }
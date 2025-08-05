"""
Rate limiter for Domain API client with adaptive backoff.
"""

import asyncio
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """State tracking for rate limiting."""
    
    requests_made: int = 0
    window_start: float = field(default_factory=time.time)
    last_request_time: float = field(default_factory=time.time)
    consecutive_rate_limits: int = 0
    backoff_until: Optional[float] = None
    
    def reset_window(self, current_time: float) -> None:
        """Reset the rate limit window."""
        self.requests_made = 0
        self.window_start = current_time
    
    def is_in_backoff(self, current_time: float) -> bool:
        """Check if we're currently in a backoff period."""
        return self.backoff_until is not None and current_time < self.backoff_until
    
    def apply_backoff(self, backoff_seconds: float) -> None:
        """Apply adaptive backoff."""
        self.consecutive_rate_limits += 1
        self.backoff_until = time.time() + backoff_seconds
        logger.warning(f"Rate limit hit {self.consecutive_rate_limits} times, backing off for {backoff_seconds}s")
    
    def clear_backoff(self) -> None:
        """Clear backoff state after successful request."""
        if self.consecutive_rate_limits > 0:
            logger.info("Rate limit backoff cleared after successful request")
        self.consecutive_rate_limits = 0
        self.backoff_until = None


class AdaptiveRateLimiter:
    """Adaptive rate limiter with exponential backoff for API requests."""
    
    def __init__(
        self,
        requests_per_minute: int = 500,
        requests_per_second: float = 8.0,
        burst_allowance: int = 20,
        adaptive_backoff: bool = True
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_second
        self.burst_allowance = burst_allowance
        self.adaptive_backoff = adaptive_backoff
        
        # Rate limiting state
        self._state = RateLimitState()
        self._lock = asyncio.Lock()
        
        # Burst control
        self._burst_tokens = burst_allowance
        self._last_token_refill = time.time()
        
        # Adaptive parameters
        self._base_backoff = 1.0  # Base backoff in seconds
        self._max_backoff = 300.0  # Max backoff of 5 minutes
        
        logger.info(
            f"Rate limiter initialized: {requests_per_minute} RPM, "
            f"{requests_per_second} RPS, burst={burst_allowance}"
        )
    
    async def acquire(self, priority: str = "normal") -> None:
        """
        Acquire permission to make a request.
        
        Args:
            priority: Request priority ("low", "normal", "high")
        """
        async with self._lock:
            current_time = time.time()
            
            # Check if we're in a backoff period
            if self._state.is_in_backoff(current_time):
                wait_time = self._state.backoff_until - current_time
                logger.debug(f"In backoff period, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                current_time = time.time()
            
            # Refill burst tokens
            self._refill_burst_tokens(current_time)
            
            # Check rate limits
            await self._enforce_rate_limits(current_time, priority)
            
            # Record the request
            self._state.requests_made += 1
            self._state.last_request_time = current_time
            
            # Use a burst token if available
            if self._burst_tokens > 0:
                self._burst_tokens -= 1
    
    def _refill_burst_tokens(self, current_time: float) -> None:
        """Refill burst tokens based on elapsed time."""
        time_since_refill = current_time - self._last_token_refill
        tokens_to_add = int(time_since_refill * self.requests_per_second)
        
        if tokens_to_add > 0:
            self._burst_tokens = min(
                self.burst_allowance,
                self._burst_tokens + tokens_to_add
            )
            self._last_token_refill = current_time
    
    async def _enforce_rate_limits(self, current_time: float, priority: str) -> None:
        """Enforce rate limits with priority handling."""
        # Reset window if needed (1-minute window)
        if current_time - self._state.window_start >= 60.0:
            self._state.reset_window(current_time)
        
        # Check per-minute limit
        if self._state.requests_made >= self.requests_per_minute:
            wait_time = 60.0 - (current_time - self._state.window_start)
            if wait_time > 0:
                logger.warning(f"Per-minute rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self._state.reset_window(time.time())
        
        # Check per-second limit (if no burst tokens available)
        if self._burst_tokens == 0:
            time_since_last = current_time - self._state.last_request_time
            min_interval = 1.0 / self.requests_per_second
            
            # Apply priority-based adjustments
            if priority == "high":
                min_interval *= 0.8  # 20% faster for high priority
            elif priority == "low":
                min_interval *= 1.2  # 20% slower for low priority
            
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.debug(f"Per-second rate limit, waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)
    
    def report_rate_limit_error(self, retry_after: Optional[int] = None) -> None:
        """Report that a rate limit error occurred."""
        if not self.adaptive_backoff:
            return
        
        # Calculate adaptive backoff
        backoff_multiplier = min(2 ** self._state.consecutive_rate_limits, 16)
        backoff_time = min(self._base_backoff * backoff_multiplier, self._max_backoff)
        
        # Use server's retry-after if provided and reasonable
        if retry_after and 1 <= retry_after <= 300:
            backoff_time = max(backoff_time, retry_after)
        
        self._state.apply_backoff(backoff_time)
    
    def report_success(self) -> None:
        """Report a successful request to clear backoff state."""
        self._state.clear_backoff()
    
    def get_status(self) -> Dict[str, any]:
        """Get current rate limiter status."""
        current_time = time.time()
        window_progress = (current_time - self._state.window_start) / 60.0
        
        return {
            "requests_in_window": self._state.requests_made,
            "requests_per_minute_limit": self.requests_per_minute,
            "window_progress": min(window_progress, 1.0),
            "burst_tokens": self._burst_tokens,
            "burst_allowance": self.burst_allowance,
            "in_backoff": self._state.is_in_backoff(current_time),
            "consecutive_rate_limits": self._state.consecutive_rate_limits,
            "backoff_until": self._state.backoff_until,
            "time_until_window_reset": max(0, 60.0 - (current_time - self._state.window_start))
        }
    
    async def wait_for_capacity(self, required_requests: int = 1) -> float:
        """
        Wait until there's capacity for the required number of requests.
        
        Returns:
            Estimated wait time in seconds
        """
        current_time = time.time()
        
        # Calculate time until window reset if needed
        if self._state.requests_made + required_requests > self.requests_per_minute:
            wait_time = 60.0 - (current_time - self._state.window_start)
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.2f}s for rate limit window reset")
                await asyncio.sleep(wait_time)
                return wait_time
        
        return 0.0
    
    def adjust_limits(self, requests_per_minute: int, requests_per_second: float) -> None:
        """Dynamically adjust rate limits."""
        logger.info(
            f"Adjusting rate limits: {self.requests_per_minute} -> {requests_per_minute} RPM, "
            f"{self.requests_per_second} -> {requests_per_second} RPS"
        )
        
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_second
        
        # Reset state if limits were reduced significantly
        current_time = time.time()
        if self._state.requests_made > requests_per_minute * 0.8:
            self._state.reset_window(current_time)
            logger.info("Rate limit window reset due to reduced limits")


class RateLimitManager:
    """Manages multiple rate limiters for different API endpoints."""
    
    def __init__(self, default_config: Dict[str, any]):
        self.default_config = default_config
        self._limiters: Dict[str, AdaptiveRateLimiter] = {}
        self._global_limiter = AdaptiveRateLimiter(**default_config)
    
    def get_limiter(self, endpoint: str) -> AdaptiveRateLimiter:
        """Get or create rate limiter for specific endpoint."""
        if endpoint not in self._limiters:
            # Create endpoint-specific limiter with same config as global
            self._limiters[endpoint] = AdaptiveRateLimiter(**self.default_config)
        
        return self._limiters[endpoint]
    
    async def acquire(self, endpoint: str = "global", priority: str = "normal") -> None:
        """Acquire permission from both global and endpoint-specific limiters."""
        # Always check global limiter
        await self._global_limiter.acquire(priority)
        
        # Check endpoint-specific limiter if different from global
        if endpoint != "global":
            endpoint_limiter = self.get_limiter(endpoint)
            await endpoint_limiter.acquire(priority)
    
    def report_rate_limit_error(self, endpoint: str = "global", retry_after: Optional[int] = None) -> None:
        """Report rate limit error to appropriate limiters."""
        self._global_limiter.report_rate_limit_error(retry_after)
        
        if endpoint != "global" and endpoint in self._limiters:
            self._limiters[endpoint].report_rate_limit_error(retry_after)
    
    def report_success(self, endpoint: str = "global") -> None:
        """Report success to appropriate limiters."""
        self._global_limiter.report_success()
        
        if endpoint != "global" and endpoint in self._limiters:
            self._limiters[endpoint].report_success()
    
    def get_status(self) -> Dict[str, any]:
        """Get status of all rate limiters."""
        status = {
            "global": self._global_limiter.get_status(),
            "endpoints": {}
        }
        
        for endpoint, limiter in self._limiters.items():
            status["endpoints"][endpoint] = limiter.get_status()
        
        return status
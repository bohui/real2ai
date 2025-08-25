"""
Retry Manager for Real2.AI
Provides intelligent retry mechanisms with exponential backoff and jitter
"""

import asyncio
import random
import time
import logging
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass
from enum import Enum
from functools import wraps

from app.core.error_handler import ErrorCategory

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """Different retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_factor: float = 1.0


class RetryManager:
    """Manages retry logic for various operations"""
    
    def __init__(self):
        self.default_configs = self._initialize_default_configs()
        self.operation_stats = {}  # Track retry statistics
    
    def _initialize_default_configs(self) -> Dict[ErrorCategory, RetryConfig]:
        """Initialize default retry configurations for different error categories"""
        return {
            ErrorCategory.DATABASE: RetryConfig(
                max_attempts=3,
                initial_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF
            ),
            ErrorCategory.EXTERNAL_API: RetryConfig(
                max_attempts=3,
                initial_delay=5.0,
                max_delay=300.0,
                exponential_base=2.0,
                jitter=True,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF
            ),
            ErrorCategory.NETWORK: RetryConfig(
                max_attempts=4,
                initial_delay=2.0,
                max_delay=60.0,
                exponential_base=2.0,
                jitter=True,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF
            ),
            ErrorCategory.CONTRACT_ANALYSIS: RetryConfig(
                max_attempts=2,
                initial_delay=10.0,
                max_delay=180.0,
                exponential_base=1.5,
                jitter=True,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF
            ),
            ErrorCategory.FILE_PROCESSING: RetryConfig(
                max_attempts=2,
                initial_delay=3.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=False,
                strategy=RetryStrategy.LINEAR_BACKOFF
            ),
            ErrorCategory.RATE_LIMIT: RetryConfig(
                max_attempts=2,
                initial_delay=60.0,
                max_delay=300.0,
                exponential_base=1.0,
                jitter=True,
                strategy=RetryStrategy.FIXED_DELAY
            )
        }
    
    def calculate_delay(
        self, 
        attempt: int, 
        config: RetryConfig, 
        last_exception: Optional[Exception] = None
    ) -> float:
        """Calculate delay for next retry attempt"""
        
        if config.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.initial_delay
        
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.initial_delay * attempt * config.backoff_factor
        
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.initial_delay * (config.exponential_base ** (attempt - 1))
        
        else:
            delay = config.initial_delay
        
        # Apply maximum delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        # Handle special cases based on exception type
        if last_exception:
            delay = self._adjust_delay_for_exception(delay, last_exception)
        
        return max(0.0, delay)
    
    def _adjust_delay_for_exception(self, delay: float, exception: Exception) -> float:
        """Adjust delay based on specific exception characteristics"""
        
        error_str = str(exception).lower()
        
        # Rate limit errors need longer delays
        if "rate limit" in error_str or "too many requests" in error_str:
            # Extract rate limit reset time if available
            if "retry-after" in error_str:
                try:
                    # Try to extract retry-after value
                    import re
                    match = re.search(r'retry-after[:\s]+(\d+)', error_str)
                    if match:
                        return float(match.group(1))
                except:
                    pass
            return max(delay, 60.0)  # Minimum 60 seconds for rate limits
        
        # Database connection errors might need longer delays
        elif "connection" in error_str and "database" in error_str:
            return max(delay, 5.0)
        
        # Network timeouts might benefit from longer delays
        elif "timeout" in error_str and "network" in error_str:
            return max(delay, 10.0)
        
        return delay
    
    def should_retry(
        self, 
        exception: Exception, 
        attempt: int, 
        config: RetryConfig
    ) -> bool:
        """Determine if operation should be retried"""
        
        # Check if we've exceeded max attempts
        if attempt >= config.max_attempts:
            return False
        
        # Check if exception type is retryable
        if not self._is_retryable_exception(exception):
            return False
        
        return True
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Determine if an exception type is eligible for retry"""
        
        error_str = str(exception).lower()
        error_type = type(exception).__name__
        
        # Never retry these types of errors
        non_retryable_keywords = [
            "authentication",
            "authorization", 
            "permission",
            "invalid credentials",
            "forbidden",
            "not found",
            "bad request",  # Usually indicates client error
            "validation error",
            "malformed",
            "unsupported format"
        ]
        
        for keyword in non_retryable_keywords:
            if keyword in error_str:
                return False
        
        # Always retry these types of errors
        retryable_keywords = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "service unavailable",
            "internal server error",
            "rate limit",
            "too many requests",
            "busy",
            "overloaded"
        ]
        
        for keyword in retryable_keywords:
            if keyword in error_str:
                return True
        
        # Specific exception types that are retryable
        retryable_exceptions = [
            "ConnectionError",
            "TimeoutError",
            "HTTPException",  # Depending on status code
            "RequestException"
        ]
        
        if error_type in retryable_exceptions:
            return True
        
        # Default to not retryable for unknown errors
        return False
    
    async def retry_async(
        self,
        func: Callable,
        *args,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        config: Optional[RetryConfig] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Retry an async function with intelligent backoff
        """
        if config is None:
            config = self.default_configs.get(category, RetryConfig())
        
        last_exception = None
        operation_name = func.__name__
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                # Record attempt
                self._record_attempt(operation_name, attempt)
                
                # Log retry attempt (except for first attempt)
                if attempt > 1:
                    logger.info(
                        f"Retrying {operation_name} (attempt {attempt}/{config.max_attempts})",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt,
                            "max_attempts": config.max_attempts,
                            "context": context
                        }
                    )
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Record success
                self._record_success(operation_name, attempt)
                
                if attempt > 1:
                    logger.info(
                        f"Retry successful for {operation_name} on attempt {attempt}",
                        extra={
                            "operation": operation_name,
                            "successful_attempt": attempt,
                            "context": context
                        }
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self.should_retry(e, attempt, config):
                    logger.error(
                        f"Not retrying {operation_name} after attempt {attempt}: {str(e)}",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt,
                            "error": str(e),
                            "context": context
                        }
                    )
                    break
                
                # Calculate delay for next attempt
                if attempt < config.max_attempts:
                    delay = self.calculate_delay(attempt, config, e)
                    
                    logger.warning(
                        f"Attempt {attempt} failed for {operation_name}, retrying in {delay:.2f}s: {str(e)}",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt,
                            "delay": delay,
                            "error": str(e),
                            "context": context
                        }
                    )
                    
                    await asyncio.sleep(delay)
        
        # Record final failure
        self._record_failure(operation_name, config.max_attempts)
        
        # All retry attempts exhausted
        logger.error(
            f"All {config.max_attempts} retry attempts failed for {operation_name}",
            extra={
                "operation": operation_name,
                "max_attempts": config.max_attempts,
                "final_error": str(last_exception),
                "context": context
            }
        )
        
        raise last_exception
    
    def retry_sync(
        self,
        func: Callable,
        *args,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        config: Optional[RetryConfig] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Retry a synchronous function with intelligent backoff
        """
        if config is None:
            config = self.default_configs.get(category, RetryConfig())
        
        last_exception = None
        operation_name = func.__name__
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                # Record attempt
                self._record_attempt(operation_name, attempt)
                
                # Log retry attempt (except for first attempt)
                if attempt > 1:
                    logger.info(
                        f"Retrying {operation_name} (attempt {attempt}/{config.max_attempts})",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt,
                            "max_attempts": config.max_attempts,
                            "context": context
                        }
                    )
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Record success
                self._record_success(operation_name, attempt)
                
                if attempt > 1:
                    logger.info(
                        f"Retry successful for {operation_name} on attempt {attempt}",
                        extra={
                            "operation": operation_name,
                            "successful_attempt": attempt,
                            "context": context
                        }
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self.should_retry(e, attempt, config):
                    logger.error(
                        f"Not retrying {operation_name} after attempt {attempt}: {str(e)}",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt,
                            "error": str(e),
                            "context": context
                        }
                    )
                    break
                
                # Calculate delay for next attempt
                if attempt < config.max_attempts:
                    delay = self.calculate_delay(attempt, config, e)
                    
                    logger.warning(
                        f"Attempt {attempt} failed for {operation_name}, retrying in {delay:.2f}s: {str(e)}",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt,
                            "delay": delay,
                            "error": str(e),
                            "context": context
                        }
                    )
                    
                    time.sleep(delay)
        
        # Record final failure
        self._record_failure(operation_name, config.max_attempts)
        
        # All retry attempts exhausted
        logger.error(
            f"All {config.max_attempts} retry attempts failed for {operation_name}",
            extra={
                "operation": operation_name,
                "max_attempts": config.max_attempts,
                "final_error": str(last_exception),
                "context": context
            }
        )
        
        raise last_exception
    
    def _record_attempt(self, operation_name: str, attempt: int):
        """Record retry attempt for statistics"""
        if operation_name not in self.operation_stats:
            self.operation_stats[operation_name] = {
                "total_attempts": 0,
                "total_successes": 0,
                "total_failures": 0,
                "success_rate": 0.0
            }
        
        self.operation_stats[operation_name]["total_attempts"] += 1
    
    def _record_success(self, operation_name: str, attempt: int):
        """Record successful operation"""
        if operation_name in self.operation_stats:
            self.operation_stats[operation_name]["total_successes"] += 1
            self._update_success_rate(operation_name)
    
    def _record_failure(self, operation_name: str, attempts: int):
        """Record failed operation"""
        if operation_name in self.operation_stats:
            self.operation_stats[operation_name]["total_failures"] += 1
            self._update_success_rate(operation_name)
    
    def _update_success_rate(self, operation_name: str):
        """Update success rate for operation"""
        stats = self.operation_stats[operation_name]
        total_operations = stats["total_successes"] + stats["total_failures"]
        if total_operations > 0:
            stats["success_rate"] = stats["total_successes"] / total_operations
    
    def get_operation_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get retry statistics for operations"""
        if operation_name:
            return self.operation_stats.get(operation_name, {})
        return self.operation_stats.copy()


# Global retry manager instance
retry_manager = RetryManager()


def retry_on_failure(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    config: Optional[RetryConfig] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for automatic retry with intelligent backoff
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_manager.retry_async(
                    func, *args, 
                    category=category, 
                    config=config, 
                    context=context, 
                    **kwargs
                )
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_manager.retry_sync(
                    func, *args, 
                    category=category, 
                    config=config, 
                    context=context, 
                    **kwargs
                )
            return sync_wrapper
    
    return decorator


# Convenience decorators for common retry scenarios
def retry_database_operation(max_attempts: int = 3):
    """Decorator specifically for database operations"""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True
    )
    return retry_on_failure(ErrorCategory.DATABASE, config)


def retry_api_call(max_attempts: int = 3):
    """Decorator specifically for external API calls"""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=5.0,
        max_delay=300.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True
    )
    return retry_on_failure(ErrorCategory.EXTERNAL_API, config)


def retry_file_operation(max_attempts: int = 2):
    """Decorator specifically for file processing operations"""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=3.0,
        max_delay=30.0,
        strategy=RetryStrategy.LINEAR_BACKOFF,
        jitter=False
    )
    return retry_on_failure(ErrorCategory.FILE_PROCESSING, config)
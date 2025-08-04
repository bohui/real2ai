"""
Base client implementation for external service integrations.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable
from functools import wraps

from .exceptions import ClientError, ClientConnectionError, ClientTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class ClientConfig:
    """Base configuration for all external service clients."""
    
    # Connection settings
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.0
    
    # Monitoring settings
    enable_metrics: bool = True
    enable_logging: bool = True
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    circuit_timeout: int = 60
    
    # Health check settings
    health_check_interval: int = 300  # 5 minutes
    
    # Rate limiting
    rate_limit_rpm: Optional[int] = None
    
    # Additional client-specific settings
    extra_config: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Simple circuit breaker implementation for client resilience."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == "OPEN":
                if time.time() - (self.last_failure_time or 0) < self.timeout:
                    raise ClientConnectionError(
                        f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}"
                    )
                else:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker moving to HALF_OPEN state")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        """Handle successful operation."""
        async with self._lock:
            self.failure_count = 0
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                logger.info("Circuit breaker moving to CLOSED state")
    
    async def _on_failure(self):
        """Handle failed operation."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker moving to OPEN state after {self.failure_count} failures")


def with_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator for automatic retries with exponential backoff."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (ClientConnectionError, ClientTimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                except Exception:
                    # Don't retry on non-retryable errors
                    raise
            
            logger.error(f"All retry attempts failed. Last error: {last_exception}")
            raise last_exception
        
        return wrapper
    return decorator


class BaseClient(ABC):
    """Abstract base class for all external service clients."""
    
    def __init__(self, config: ClientConfig, client_name: str = None):
        self.config = config
        self.client_name = client_name or self.__class__.__name__
        self._client: Optional[Any] = None
        self._initialized = False
        self._circuit_breaker = None
        self._last_health_check = 0
        self._health_status = {"status": "unknown", "last_check": None}
        
        # Set up circuit breaker if enabled
        if config.circuit_breaker_enabled:
            self._circuit_breaker = CircuitBreaker(
                failure_threshold=config.failure_threshold,
                timeout=config.circuit_timeout
            )
        
        # Set up logging
        self.logger = logging.getLogger(f"{__name__}.{self.client_name}")
        if not config.enable_logging:
            self.logger.setLevel(logging.CRITICAL)
    
    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._initialized
    
    @property
    def client(self) -> Any:
        """Get the underlying client instance."""
        if not self._initialized:
            raise ClientError(f"Client {self.client_name} not initialized")
        return self._client
    
    async def _execute_with_circuit_breaker(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker if enabled."""
        if self._circuit_breaker:
            return await self._circuit_breaker.call(func, *args, **kwargs)
        else:
            return await func(*args, **kwargs)
    
    def _log_request(self, operation: str, **kwargs):
        """Log client request if logging is enabled."""
        if self.config.enable_logging:
            self.logger.debug(f"[{operation}] Request: {kwargs}")
    
    def _log_response(self, operation: str, success: bool, duration: float, **kwargs):
        """Log client response if logging is enabled."""
        if self.config.enable_logging:
            level = logging.DEBUG if success else logging.WARNING
            status = "SUCCESS" if success else "FAILED"
            self.logger.log(
                level,
                f"[{operation}] {status} in {duration:.3f}s: {kwargs}"
            )
    
    async def _check_health_if_needed(self) -> None:
        """Check health if interval has passed."""
        current_time = time.time()
        if (current_time - self._last_health_check) > self.config.health_check_interval:
            try:
                health_result = await self.health_check()
                self._health_status = health_result
                self._last_health_check = current_time
            except Exception as e:
                self.logger.warning(f"Health check failed: {e}")
                self._health_status = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": current_time
                }
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client connection.
        
        This method should:
        1. Create the underlying client instance
        2. Test the connection
        3. Set up any required authentication
        4. Set _initialized = True on success
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check client health and connectivity.
        
        Returns:
            Dict containing health status information
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up client resources.
        
        This method should:
        1. Close any open connections
        2. Clean up resources
        3. Set _initialized = False
        """
        pass
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get current health status with automatic check if needed."""
        await self._check_health_if_needed()
        return self._health_status.copy()
    
    async def force_health_check(self) -> Dict[str, Any]:
        """Force an immediate health check."""
        try:
            self._health_status = await self.health_check()
            self._last_health_check = time.time()
        except Exception as e:
            self.logger.warning(f"Forced health check failed: {e}")
            self._health_status = {
                "status": "unhealthy", 
                "error": str(e),
                "last_check": time.time()
            }
        return self._health_status.copy()
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get client information and configuration."""
        return {
            "client_name": self.client_name,
            "initialized": self._initialized,
            "config": {
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
                "circuit_breaker_enabled": self.config.circuit_breaker_enabled,
                "health_check_interval": self.config.health_check_interval,
            },
            "circuit_breaker_state": getattr(self._circuit_breaker, 'state', None) if self._circuit_breaker else None,
            "last_health_check": self._last_health_check,
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
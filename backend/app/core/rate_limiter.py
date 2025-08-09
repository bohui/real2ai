"""Rate limiting utilities for file uploads and API calls."""

import time
from typing import Dict, Optional
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter for file uploads."""
    
    def __init__(self):
        # Track requests per user and per IP
        self.user_requests: Dict[str, deque] = defaultdict(deque)
        self.ip_requests: Dict[str, deque] = defaultdict(deque)
        
        # Rate limits
        self.max_requests_per_minute = 10
        self.max_requests_per_hour = 100
        
    def is_rate_limited(
        self, 
        user_id: Optional[str] = None, 
        client_ip: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Check if user or IP is rate limited.
        
        Returns:
            Tuple of (is_limited, reason)
        """
        current_time = time.time()
        
        # Check user rate limit
        if user_id:
            user_queue = self.user_requests[user_id]
            
            # Remove old requests (older than 1 hour)
            while user_queue and current_time - user_queue[0] > 3600:
                user_queue.popleft()
            
            # Check hourly limit
            if len(user_queue) >= self.max_requests_per_hour:
                return True, f"User rate limit exceeded: {self.max_requests_per_hour} requests per hour"
            
            # Check minute limit (last 60 seconds)
            recent_requests = sum(1 for req_time in user_queue if current_time - req_time <= 60)
            if recent_requests >= self.max_requests_per_minute:
                return True, f"User rate limit exceeded: {self.max_requests_per_minute} requests per minute"
            
            # Record this request
            user_queue.append(current_time)
        
        # Check IP rate limit (more permissive)
        if client_ip:
            ip_queue = self.ip_requests[client_ip]
            
            # Remove old requests (older than 1 hour)
            while ip_queue and current_time - ip_queue[0] > 3600:
                ip_queue.popleft()
            
            # Check hourly limit (higher for IP)
            if len(ip_queue) >= self.max_requests_per_hour * 2:
                return True, f"IP rate limit exceeded: {self.max_requests_per_hour * 2} requests per hour"
            
            # Record this request
            ip_queue.append(current_time)
        
        return False, ""
    
    def get_rate_limit_info(
        self, 
        user_id: Optional[str] = None, 
        client_ip: Optional[str] = None
    ) -> Dict:
        """Get current rate limit status."""
        current_time = time.time()
        info = {}
        
        if user_id:
            user_queue = self.user_requests[user_id]
            # Count requests in last hour and minute
            hourly_requests = sum(1 for req_time in user_queue if current_time - req_time <= 3600)
            minute_requests = sum(1 for req_time in user_queue if current_time - req_time <= 60)
            
            info["user"] = {
                "requests_last_hour": hourly_requests,
                "requests_last_minute": minute_requests,
                "hourly_limit": self.max_requests_per_hour,
                "minute_limit": self.max_requests_per_minute,
                "hourly_remaining": max(0, self.max_requests_per_hour - hourly_requests),
                "minute_remaining": max(0, self.max_requests_per_minute - minute_requests)
            }
        
        if client_ip:
            ip_queue = self.ip_requests[client_ip]
            hourly_requests = sum(1 for req_time in ip_queue if current_time - req_time <= 3600)
            
            info["ip"] = {
                "requests_last_hour": hourly_requests,
                "hourly_limit": self.max_requests_per_hour * 2,
                "hourly_remaining": max(0, self.max_requests_per_hour * 2 - hourly_requests)
            }
        
        return info


# Global rate limiter instance
upload_rate_limiter = RateLimiter()
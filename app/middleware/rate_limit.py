from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

from app.core.redis import get_redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis with sliding window algorithm
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        
        # Get client identifier (IP address)
        client_ip = request.client.host
        
        # Get path
        path = request.url.path
        
        # Determine rate limit based on endpoint
        rate_limit_key, max_requests, window_seconds = self._get_rate_limit_config(path)
        
        if rate_limit_key:
            # Check rate limit
            is_allowed = await self._check_rate_limit(
                client_ip,
                rate_limit_key,
                max_requests,
                window_seconds
            )
            
            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded",
                    client_ip=client_ip,
                    path=path,
                    rate_limit=f"{max_requests}/{window_seconds}s"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
                )
        
        # Process request
        response = await call_next(request)
        return response
    
    def _get_rate_limit_config(self, path: str) -> tuple:
        """
        Get rate limit configuration based on endpoint
        
        Returns:
            Tuple of (rate_limit_key, max_requests, window_seconds)
        """
        # Login endpoints - 5 requests per minute
        if "/auth/login" in path or "/auth/password-reset" in path:
            return "login", settings.RATE_LIMIT_LOGIN, 60
        
        # OTP endpoints - 3 requests per 5 minutes
        if "/otp" in path or "/resend-otp" in path:
            return "otp", settings.RATE_LIMIT_OTP, 300
        
        # General API endpoints - 10 requests per second
        if path.startswith("/api/"):
            return "api", settings.RATE_LIMIT_API, 1
        
        # No rate limit for other endpoints
        return None, None, None
    
    async def _check_rate_limit(
        self,
        client_ip: str,
        rate_limit_key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Check if request is within rate limit using sliding window
        
        Returns:
            True if allowed, False if rate limit exceeded
        """
        try:
            redis = await get_redis()
            
            # Create unique key for this client and endpoint
            key = f"rate_limit:{rate_limit_key}:{client_ip}"
            
            # Current timestamp
            now = time.time()
            window_start = now - window_seconds
            
            # Remove old entries outside the window
            await redis.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            request_count = await redis.zcard(key)
            
            if request_count >= max_requests:
                return False
            
            # Add current request
            await redis.zadd(key, {str(now): now})
            
            # Set expiration on key
            await redis.expire(key, window_seconds)
            
            return True
            
        except Exception as e:
            logger.error("Rate limit check error", error=str(e))
            # Allow request on error to avoid blocking legitimate traffic
            return True

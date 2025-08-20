"""
Security middleware for Cloud Explorer API
"""
import time
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings


# Rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_REQUESTS}/minute"] if settings.RATE_LIMITING_ENABLED else []
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """
    
    def __init__(self, app: ASGIApp, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        if not self.enabled:
            return response
        
        # Security headers
        security_headers = {
            # HSTS - Force HTTPS for specified time
            "Strict-Transport-Security": f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains; preload",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent content type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # XSS Protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy
            "Content-Security-Policy": settings.CSP_POLICY,
            
            # Permissions Policy (formerly Feature Policy)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            
            # Remove server information
            "Server": "Cloud Explorer API",
            
            # Cache control for API responses
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        # Apply security headers
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log requests for security monitoring
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Get client information
        client_ip = get_remote_address(request)
        user_agent = request.headers.get("user-agent", "Unknown")
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log request information (in production, this would go to a security log)
        if settings.is_development:
            print(f"Security Log: {request.method} {request.url.path} - "
                  f"IP: {client_ip} - Status: {response.status_code} - "
                  f"Time: {process_time:.3f}s - UA: {user_agent[:50]}")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


def setup_rate_limiting(app):
    """
    Setup rate limiting for the FastAPI application
    """
    if settings.RATE_LIMITING_ENABLED:
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
    
    return limiter if settings.RATE_LIMITING_ENABLED else None


def get_rate_limit_string(requests: int, window: int = 60) -> str:
    """
    Generate rate limit string for slowapi
    
    Args:
        requests: Number of requests
        window: Time window in seconds (default: 60)
    
    Returns:
        Rate limit string (e.g., "10/minute")
    """
    if window == 60:
        return f"{requests}/minute"
    elif window == 3600:
        return f"{requests}/hour"
    elif window == 86400:
        return f"{requests}/day"
    else:
        return f"{requests}/{window}second"


# Rate limit decorators for different endpoint types
def rate_limit_config():
    """Rate limit decorator for configuration endpoints"""
    if settings.RATE_LIMITING_ENABLED:
        return limiter.limit(get_rate_limit_string(settings.API_RATE_LIMIT_CONFIG))
    return lambda f: f


def rate_limit_health():
    """Rate limit decorator for health endpoints"""
    if settings.RATE_LIMITING_ENABLED:
        return limiter.limit(get_rate_limit_string(settings.API_RATE_LIMIT_HEALTH))
    return lambda f: f


def rate_limit_default():
    """Rate limit decorator for default endpoints"""
    if settings.RATE_LIMITING_ENABLED:
        return limiter.limit(get_rate_limit_string(settings.API_RATE_LIMIT_DEFAULT))
    return lambda f: f

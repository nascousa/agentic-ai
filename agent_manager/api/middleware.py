"""
Monitoring Middleware for FastAPI

Automatic metrics collection for all API requests.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging

from agent_manager.monitoring import (
    api_request_duration_seconds,
    api_requests_total,
    system_errors_total
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect metrics for all API requests
    
    Tracks:
    - Request duration
    - Request count by method, endpoint, and status code
    - Error rates
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and collect metrics
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
        
        Returns:
            Response: API response
        """
        # Start timing
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        
        # Process request
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        
        except Exception as e:
            # Record error
            system_errors_total.labels(
                component='api',
                error_type=type(e).__name__
            ).inc()
            logger.error(f"Request failed: {method} {path} - {e}")
            raise
        
        finally:
            # Record metrics
            duration = time.time() - start_time
            
            api_request_duration_seconds.labels(
                method=method,
                endpoint=path,
                status_code=status_code
            ).observe(duration)
            
            api_requests_total.labels(
                method=method,
                endpoint=path,
                status_code=status_code
            ).inc()
            
            # Log slow requests
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {method} {path} took {duration:.2f}s"
                )


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track and log errors
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Track errors and exceptions
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
        
        Returns:
            Response: API response
        """
        try:
            response = await call_next(request)
            
            # Track 4xx and 5xx responses
            if response.status_code >= 400:
                error_type = 'client_error' if response.status_code < 500 else 'server_error'
                system_errors_total.labels(
                    component='api',
                    error_type=error_type
                ).inc()
            
            return response
        
        except Exception as e:
            # Track exceptions
            system_errors_total.labels(
                component='api',
                error_type=type(e).__name__
            ).inc()
            
            logger.error(
                f"Unhandled exception: {request.method} {request.url.path}",
                exc_info=True
            )
            raise

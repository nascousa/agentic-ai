"""
FastAPI application setup and middleware configuration.

This module initializes the main FastAPI application with proper
middleware, CORS configuration, and error handling for the MCP server.
"""

import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import uvicorn

from agent_manager.core.models import ErrorResponse


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager for startup and shutdown tasks.
    
    Handles database initialization, connection setup, and cleanup.
    """
    # Startup tasks
    print("🚀 Starting AM (AgentManager) MCP Server...")
    
    # Initialize database
    from agent_manager.db import create_database_tables, check_database_connection
    
    # Check database connection
    if await check_database_connection():
        print("✅ Database connection successful")
        # Create tables if they don't exist
        await create_database_tables()
    else:
        print("❌ Database connection failed")
        raise RuntimeError("Failed to connect to database")
    
    # TODO: Initialize LLM client connections
    
    yield
    
    # Shutdown tasks
    print("🔄 Shutting down AM (AgentManager) MCP Server...")
    
    # Clean up database connections
    from agent_manager.db import cleanup_database
    await cleanup_database()


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="AM (AgentManager) - MCP Server",
        description="Multi-Agent Coordination/Planning Server using FastAPI and SQLAlchemy ORM",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Add CORS middleware for external client coordination
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Global exception handler for consistent error responses
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with standardized error format."""
        error_response = ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.detail,
            details={"status_code": exc.status_code}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(error_response.model_dump())
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle general exceptions with standardized error format."""
        error_response = ErrorResponse(
            error=exc.__class__.__name__,
            message="Internal server error occurred",
            details={"exception": str(exc)}
        )
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(error_response.model_dump())
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Basic health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "service": "AM MCP Server",
            "version": "0.1.0"
        }
    
    # Include API routers
    from agent_manager.api.endpoints import router as api_router
    app.include_router(api_router, prefix="/v1")
    
    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    """Run the server directly for development."""
    uvicorn.run(
        "agent_manager.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
"""
Database configuration and session management for MCP Server.

This module provides async SQLAlchemy engine setup, session factory,
and database initialization with support for both SQLite (development)
and PostgreSQL (production) backends.
"""

import os
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """Database configuration with environment-based settings."""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agent_manager.db")
        self.echo = os.getenv("DEBUG", "false").lower() == "true"
        self.pool_pre_ping = True
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")
    
    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database."""
        return self.database_url.startswith("postgresql")


def create_database_engine(config: Optional[DatabaseConfig] = None) -> AsyncEngine:
    """
    Create async database engine with proper configuration.
    
    Supports both SQLite (development) and PostgreSQL (production) with
    appropriate connection pooling and configuration for each backend.
    
    Args:
        config: Database configuration (uses default if None)
        
    Returns:
        AsyncEngine: Configured async database engine
        
    Go/No-Go Checkpoint: Engine can be switched between SQLite and PostgreSQL
    """
    if config is None:
        config = DatabaseConfig()
    
    engine_kwargs = {
        "echo": config.echo,
        "pool_pre_ping": config.pool_pre_ping,
    }
    
    # SQLite-specific configuration
    if config.is_sqlite:
        engine_kwargs.update({
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 30,
            },
        })
    
    # PostgreSQL-specific configuration
    elif config.is_postgresql:
        engine_kwargs.update({
            "pool_recycle": config.pool_recycle,
            "pool_size": 10,
            "max_overflow": 20,
        })
    
    return create_async_engine(config.database_url, **engine_kwargs)


# Global database engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Get the global database engine, creating it if necessary."""
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the global session factory, creating it if necessary."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
    return _session_factory


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session injection.
    
    Provides proper session lifecycle management with automatic
    commit/rollback and cleanup for request handling.
    
    Yields:
        AsyncSession: Database session for the request
        
    Go/No-Go Checkpoint: Session management with proper cleanup
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_database_tables():
    """
    Create all database tables if they don't exist.
    
    Should be called during application startup to ensure
    database schema is properly initialized.
    
    Go/No-Go Checkpoint: Database tables created successfully
    """
    from agent_manager.orm import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database tables created successfully")


async def drop_database_tables():
    """
    Drop all database tables (for testing/development).
    
    WARNING: This will delete all data in the database.
    Use with caution and only in development/testing environments.
    """
    from agent_manager.orm import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("🗑️ Database tables dropped successfully")


async def check_database_connection() -> bool:
    """
    Check if database connection is working properly.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        from sqlalchemy import text
        engine = get_engine()
        async with engine.begin() as conn:
            # Simple connection test
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def cleanup_database():
    """
    Clean up database connections and resources.
    
    Should be called during application shutdown to properly
    close all database connections and clean up resources.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    
    _session_factory = None
    print("Database cleanup completed")


# Database health check utilities
async def get_database_info() -> dict:
    """
    Get database connection information for monitoring.
    
    Returns:
        dict: Database connection details and status
    """
    config = DatabaseConfig()
    engine = get_engine()
    
    return {
        "database_url": config.database_url.split("://")[0] + "://[REDACTED]",
        "backend": "sqlite" if config.is_sqlite else "postgresql",
        "echo": config.echo,
        "pool_size": getattr(engine.pool, "size", "N/A"),
        "checked_out": getattr(engine.pool, "checkedout", "N/A"),
        "overflow": getattr(engine.pool, "overflow", "N/A"),
        "is_connected": await check_database_connection(),
    }
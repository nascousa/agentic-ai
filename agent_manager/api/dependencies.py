"""
FastAPI dependency injection providers.

This module provides dependency injection functions for database sessions,
authentication, and other shared resources used across API endpoints.
"""

import os
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

# TODO: Import database session factory when db.py is created
# from agent_manager.db import AsyncSessionLocal


async def verify_auth_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify client authentication token.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        str: Validated token
        
    Raises:
        HTTPException: If authentication fails
        
    Go/No-Go Checkpoint: Auth token validation working across all endpoints
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    
    token = authorization.split(" ")[1]
    expected_token = os.getenv("SERVER_API_TOKEN")
    
    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="Server authentication not properly configured"
        )
    
    if token != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    
    return token


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide async database session for request handling.
    
    This dependency ensures proper session lifecycle management
    with automatic commit/rollback and cleanup.
    
    Yields:
        AsyncSession: Database session for the request
        
    Go/No-Go Checkpoint: All database operations handle transactions properly
    """
    from agent_manager.db import get_session_factory
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            print(f"[DEPENDENCY] Session created: {id(session)}")
            yield session
            print(f"[DEPENDENCY] Committing session: {id(session)}")
            await session.commit()
            print(f"[DEPENDENCY] ✅ Session committed successfully!")
        except Exception as e:
            print(f"[DEPENDENCY] ❌ Error during session handling: {e}")
            await session.rollback()
            raise
        finally:
            print(f"[DEPENDENCY] Closing session: {id(session)}")
            await session.close()


def get_current_user(token: str = Depends(verify_auth_token)) -> str:
    """
    Get current authenticated user/client ID from token.
    
    Args:
        token: Validated authentication token
        
    Returns:
        str: Client/user identifier
    """
    # For now, return a simple identifier
    # In production, this would decode the JWT or lookup the client
    return "authenticated_client"
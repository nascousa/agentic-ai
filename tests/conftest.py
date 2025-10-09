"""
Pytest configuration and fixtures for AM (AgentManager) test suite.

Provides shared fixtures for database testing, HTTP clients, and
mock configurations used across all test modules.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from agent_manager.api.main import create_application
from agent_manager.core.models import ClientConfiguration
from agent_manager.orm import Base
from agent_manager.db import DatabaseConfig
from agent_manager.service import DatabaseService


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_engine():
    """Create test database engine with in-memory SQLite."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for tests."""
    async with AsyncSession(test_db_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest.fixture
async def db_service(test_db_session) -> DatabaseService:
    """Provide database service for tests."""
    return DatabaseService(test_db_session)


@pytest.fixture
def test_app():
    """Create FastAPI test application."""
    app = create_application()
    return app


@pytest.fixture
def test_client(test_app) -> TestClient:
    """Provide test client for API endpoints."""
    return TestClient(test_app)


@pytest.fixture
async def async_test_client(test_app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide async test client for API endpoints."""
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("agent_manager.core.llm_client.AsyncOpenAI") as mock:
        mock_client = AsyncMock()
        mock.return_value = mock_client
        
        # Mock chat completion response
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(message=AsyncMock(content='{"result": "test response"}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        
        yield mock_client


@pytest.fixture
def test_config() -> ClientConfiguration:
    """Provide test client configuration."""
    return ClientConfiguration(
        client_id="test_client_001",
        server_url="http://test:8000",
        poll_interval_sec=1,
        max_retries=2,
        timeout_sec=10,
        agent_capabilities=["researcher", "analyst", "coder"],
        log_level="DEBUG"
    )


@pytest.fixture
def sample_user_request() -> str:
    """Provide sample user request for testing."""
    return "Research the latest developments in artificial intelligence and summarize the key findings."


@pytest.fixture
def sample_task_graph_data():
    """Provide sample task graph data for testing."""
    return {
        "workflow_id": "test_workflow_123",
        "tasks": [
            {
                "step_id": "task_1",
                "workflow_id": "test_workflow_123", 
                "task_description": "Research AI developments",
                "assigned_agent": "researcher",
                "dependencies": [],
                "status": "READY"
            },
            {
                "step_id": "task_2",
                "workflow_id": "test_workflow_123",
                "task_description": "Analyze research findings",
                "assigned_agent": "analyst", 
                "dependencies": ["task_1"],
                "status": "PENDING"
            }
        ]
    }


@pytest.fixture
def sample_ra_history():
    """Provide sample RAHistory for testing."""
    return {
        "iterations": [
            {
                "thought": "I need to research AI developments",
                "action": "Search for recent AI papers and news",
                "observation": "Found several relevant sources",
                "iteration_number": 1
            },
            {
                "thought": "Now I should analyze the findings",
                "action": "Summarize key points from sources",
                "observation": "Created comprehensive summary",
                "iteration_number": 2
            }
        ],
        "final_result": "Recent AI developments include advances in LLMs, multimodal AI, and AI safety research.",
        "source_agent": "researcher",
        "execution_time": 45.2,
        "client_id": "test_client_001"
    }


@pytest.fixture
def temp_config_file(test_config) -> Generator[str, None, None]:
    """Create temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        import json
        json.dump(test_config.model_dump(), f, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    # Set test environment variables
    test_env = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "OPENAI_API_KEY": "test_key_123",
        "SERVER_API_TOKEN": "test_token_123",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "testing"
    }
    
    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# Test markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
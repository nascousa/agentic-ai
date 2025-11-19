"""
Combined API endpoint testing - includes both direct HTTP tests and pytest unit tests.

Direct API Tests: Test actual HTTP endpoints with real requests
Pytest Unit Tests: Test endpoints with mocked dependencies
"""

# ============================================================
# PART 1: DIRECT API HTTP TESTS (for manual/integration testing)
# ============================================================

import asyncio
import httpx
import json


async def test_api_endpoints_direct():
    """Test all AgentManager API endpoints with direct HTTP requests"""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing AgentManager API Endpoints (Direct HTTP)...")
    print(f"Base URL: {base_url}")
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Health check
        print("\n1. Testing health check endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: OpenAPI docs endpoint
        print("\n2. Testing OpenAPI docs...")
        try:
            response = await client.get(f"{base_url}/docs")
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 3: Submit task endpoint
        print("\n3. Testing task submission...")
        try:
            task_request = {
                "user_request": "Test workflow: create a simple Python script that prints hello world",
                "metadata": {"priority": "high", "test": True}
            }
            response = await client.post(
                f"{base_url}/v1/submit_task",
                json=task_request
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                task_response = response.json()
                print(f"   Workflow ID: {task_response.get('workflow_id')}")
                print(f"   Number of tasks: {len(task_response.get('tasks', []))}")
                
                # Store workflow_id for further tests
                workflow_id = task_response.get('workflow_id')
                
                # Test 4: Check workflow status
                print("\n4. Testing workflow status...")
                status_response = await client.get(f"{base_url}/v1/workflows/{workflow_id}/status")
                print(f"   Status: {status_response.status_code}")
                print(f"   Response: {status_response.json()}")
                
                # Test 5: Poll for ready tasks
                print("\n5. Testing task polling...")
                poll_response = await client.get(f"{base_url}/v1/tasks/developer/ready")
                print(f"   Status: {poll_response.status_code}")
                if poll_response.status_code == 200:
                    task = poll_response.json()
                    print(f"   Task ID: {task.get('step_id')}")
                    print(f"   Description: {task.get('task_description', '')[:100]}...")
                elif poll_response.status_code == 204:
                    print("   No ready tasks available (expected)")
                else:
                    print(f"   Response: {poll_response.json()}")
                    
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 6: Report result endpoint (with dummy data)
        print("\n6. Testing result reporting...")
        try:
            result_data = {
                "step_id": "test-step-1",
                "workflow_id": "test-workflow",
                "iterations": [
                    {
                        "thought": "I need to create a hello world script",
                        "action": "CREATE_FILE",
                        "action_input": {"filename": "hello.py", "content": "print('Hello, World!')"}
                    }
                ],
                "final_result": "Created hello.py with greeting message",
                "source_agent": "developer",
                "client_id": "test-client",
                "execution_time": 1.5
            }
            response = await client.post(
                f"{base_url}/v1/report_result",
                json=result_data
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\nAPI endpoint testing completed!")


# ============================================================
# PART 2: PYTEST UNIT TESTS (for automated testing with mocks)
# ============================================================

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from agent_manager.core.models import (
    TaskGraphRequest,
    ClientPollRequest,
    TaskResult,
    RAHistory,
    ThoughtAction,
)


class TestSubmitTaskEndpoint:
    """Test suite for POST /v1/submit_task endpoint."""
    
    @pytest.mark.asyncio
    async def test_submit_task_success(self, async_test_client, mock_openai_client):
        """Test successful task submission."""
        # Mock the manager and database service
        with patch("agent_manager.api.endpoints.AgentManager") as mock_manager, \
             patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            
            # Setup mocks
            mock_manager_instance = AsyncMock()
            mock_manager.return_value = mock_manager_instance
            mock_manager_instance.plan_and_save_task.return_value = "test_workflow_123"
            
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            mock_db_instance.get_task_graph.return_value = AsyncMock(
                workflow_id="test_workflow_123",
                tasks=[],
                created_at=datetime.utcnow()
            )
            
            # Make request
            response = await async_test_client.post(
                "/v1/submit_task",
                json={
                    "user_request": "Test task submission",
                    "metadata": {"priority": "high"}
                }
            )
            
            # Assertions
            assert response.status_code == 201
            data = response.json()
            assert data["workflow_id"] == "test_workflow_123"
            assert data["status"] == "IN_PROGRESS"
    
    @pytest.mark.asyncio
    async def test_submit_task_invalid_request(self, async_test_client):
        """Test task submission with invalid request data."""
        response = await async_test_client.post(
            "/v1/submit_task",
            json={}  # Missing required user_request field
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_submit_task_planning_failure(self, async_test_client):
        """Test task submission when planning fails."""
        with patch("agent_manager.api.endpoints.AgentManager") as mock_manager:
            mock_manager_instance = AsyncMock()
            mock_manager.return_value = mock_manager_instance
            mock_manager_instance.plan_and_save_task.side_effect = ValueError("Planning failed")
            
            response = await async_test_client.post(
                "/v1/submit_task",
                json={"user_request": "Test task"}
            )
            
            assert response.status_code == 422
            data = response.json()
            assert "Planning failed" in data["detail"]


class TestPollForTasksEndpoint:
    """Test suite for POST /v1/tasks/poll endpoint."""
    
    @pytest.mark.asyncio
    async def test_poll_task_success(self, async_test_client):
        """Test successful task polling."""
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            
            # Mock returning a task
            mock_task = AsyncMock()
            mock_task.model_dump.return_value = {
                "step_id": "task_1",
                "workflow_id": "workflow_123",
                "task_description": "Test task",
                "assigned_agent": "researcher",
                "status": "IN_PROGRESS"
            }
            mock_db_instance.get_and_claim_ready_task.return_value = mock_task
            
            response = await async_test_client.post(
                "/v1/tasks/poll",
                json={
                    "client_id": "test_client_001",
                    "agent_capabilities": ["researcher", "analyst"]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["step_id"] == "task_1"
    
    @pytest.mark.asyncio
    async def test_poll_no_tasks_available(self, async_test_client):
        """Test polling when no tasks are available."""
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            mock_db_instance.get_and_claim_ready_task.return_value = None
            
            response = await async_test_client.post(
                "/v1/tasks/poll",
                json={
                    "client_id": "test_client_001",
                    "agent_capabilities": ["researcher"]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data is None


class TestReportResultEndpoint:
    """Test suite for POST /v1/report_result endpoint."""
    
    @pytest.mark.asyncio
    async def test_report_result_success(self, async_test_client, sample_ra_history):
        """Test successful result reporting."""
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service, \
             patch("agent_manager.api.endpoints.AgentManager") as mock_manager:
            
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            mock_db_instance.save_task_result.return_value = True
            mock_db_instance.check_and_dispatch_ready_tasks.return_value = 2
            mock_db_instance.is_workflow_complete.return_value = True
            
            mock_manager_instance = AsyncMock()
            mock_manager.return_value = mock_manager_instance
            
            task_result = {
                "workflow_id": "workflow_123",
                "task_id": "task_1",
                "ra_history": sample_ra_history,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            response = await async_test_client.post(
                "/v1/report_result",
                json=task_result
            )
            
            assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_report_result_task_not_found(self, async_test_client, sample_ra_history):
        """Test result reporting for non-existent task."""
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            mock_db_instance.save_task_result.return_value = False
            
            task_result = {
                "workflow_id": "workflow_123", 
                "task_id": "nonexistent_task",
                "ra_history": sample_ra_history,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            response = await async_test_client.post(
                "/v1/report_result",
                json=task_result
            )
            
            assert response.status_code == 404


class TestWorkflowStatusEndpoint:
    """Test suite for GET /v1/workflows/{workflow_id}/status endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_workflow_status_success(self, async_test_client):
        """Test successful workflow status retrieval."""
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            mock_db_instance.get_workflow_status.return_value = {
                "workflow_id": "workflow_123",
                "total_tasks": 5,
                "status_counts": {"COMPLETED": 3, "IN_PROGRESS": 1, "PENDING": 1},
                "is_complete": False
            }
            
            response = await async_test_client.get("/v1/workflows/workflow_123/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["workflow_id"] == "workflow_123"
            assert data["total_tasks"] == 5
    
    @pytest.mark.asyncio
    async def test_get_workflow_status_not_found(self, async_test_client):
        """Test workflow status for non-existent workflow."""
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            mock_db_instance.get_workflow_status.return_value = None
            
            response = await async_test_client.get("/v1/workflows/nonexistent/status")
            
            assert response.status_code == 404


class TestHealthCheckEndpoint:
    """Test suite for GET /v1/health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_test_client):
        """Test health check endpoint."""
        response = await async_test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "AM MCP Server"
        assert "version" in data


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Run direct HTTP tests
    asyncio.run(test_api_endpoints_direct())

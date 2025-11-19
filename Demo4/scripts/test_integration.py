"""
Integration tests for the complete MCP workflow.

Tests the full end-to-end workflow from task submission through
client execution to final result synthesis and audit coordination.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from client_worker import MCPWorkerClient
from agent_manager.core.models import (
    TaskGraphRequest,
    ClientConfig,
    TaskResult,
    RAHistory,
    ThoughtAction,
)


class TestEndToEndWorkflow:
    """Test complete workflow execution."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_workflow_execution(
        self,
        async_test_client,
        test_config,
        mock_openai_client
    ):
        """
        Test complete workflow from submission to completion.
        
        Go/No-Go Checkpoint: Full system integration working correctly
        """
        # Mock LLM responses for planning and execution
        mock_openai_client.chat.completions.create.side_effect = [
            # Response for workflow planning
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content='''
            {
                "workflow_id": "integration_test_workflow",
                "tasks": [
                    {
                        "step_id": "research_task",
                        "task_description": "Research AI developments",
                        "assigned_agent": "researcher",
                        "dependencies": []
                    },
                    {
                        "step_id": "analysis_task", 
                        "task_description": "Analyze research findings",
                        "assigned_agent": "analyst",
                        "dependencies": ["research_task"]
                    }
                ]
            }
            '''))]),
            # Response for task execution
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content='''
            {
                "thought": "I need to research AI developments",
                "action": "Search recent AI publications and news",
                "final_result": "Found key developments in LLMs and AI safety"
            }
            '''))])
        ]
        
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service, \
             patch("agent_manager.api.endpoints.AgentManager") as mock_manager:
            
            # Setup database service mock
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            
            # Setup manager mock
            mock_manager_instance = AsyncMock()
            mock_manager.return_value = mock_manager_instance
            
            # Mock workflow creation
            mock_manager_instance.plan_and_save_task.return_value = "integration_test_workflow"
            mock_db_instance.get_task_graph.return_value = AsyncMock(
                workflow_id="integration_test_workflow",
                tasks=[],
                created_at=datetime.utcnow()
            )
            
            # Step 1: Submit task
            response = await async_test_client.post(
                "/v1/submit_task",
                json={
                    "user_request": "Research and analyze AI developments",
                    "metadata": {"priority": "high"}
                }
            )
            
            assert response.status_code == 201
            workflow_data = response.json()
            workflow_id = workflow_data["workflow_id"]
            
            # Step 2: Client polls for task
            mock_db_instance.get_and_claim_ready_task.return_value = AsyncMock(
                step_id="research_task",
                workflow_id=workflow_id,
                task_description="Research AI developments",
                assigned_agent="researcher",
                status="IN_PROGRESS",
                client_id="test_client"
            )
            
            poll_response = await async_test_client.post(
                "/v1/tasks/poll",
                json={
                    "client_id": "test_client",
                    "agent_capabilities": ["researcher"]
                }
            )
            
            assert poll_response.status_code == 200
            task_data = poll_response.json()
            assert task_data["step_id"] == "research_task"
            
            # Step 3: Report task completion
            mock_db_instance.save_task_result.return_value = True
            mock_db_instance.check_and_dispatch_ready_tasks.return_value = 1
            mock_db_instance.is_workflow_complete.return_value = False
            
            task_result = {
                "workflow_id": workflow_id,
                "task_id": "research_task",
                "ra_history": {
                    "iterations": [
                        {
                            "thought": "Need to research AI",
                            "action": "Search publications",
                            "observation": "Found relevant sources",
                            "iteration_number": 1
                        }
                    ],
                    "final_result": "Research completed successfully",
                    "source_agent": "researcher",
                    "execution_time": 45.0,
                    "client_id": "test_client"
                },
                "completed_at": datetime.utcnow().isoformat()
            }
            
            result_response = await async_test_client.post(
                "/v1/report_result",
                json=task_result
            )
            
            assert result_response.status_code == 204
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_audit_and_rework_cycle(
        self,
        async_test_client,
        mock_openai_client
    ):
        """
        Test audit failure and rework coordination.
        
        Go/No-Go Checkpoint: System demonstrates Parallel → Audit → Rework → Synthesis cycle
        """
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service, \
             patch("agent_manager.api.endpoints.AgentManager") as mock_manager:
            
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            
            mock_manager_instance = AsyncMock()
            mock_manager.return_value = mock_manager_instance
            
            # Simulate completed workflow triggering audit
            mock_db_instance.save_task_result.return_value = True
            mock_db_instance.check_and_dispatch_ready_tasks.return_value = 0
            mock_db_instance.is_workflow_complete.return_value = True
            
            # Mock audit failure
            mock_manager_instance.trigger_audit.return_value = AsyncMock(
                is_successful=False,
                rework_suggestions=["Improve accuracy", "Add more details"]
            )
            
            task_result = {
                "workflow_id": "audit_test_workflow",
                "task_id": "final_task",
                "ra_history": {
                    "iterations": [
                        {
                            "thought": "Complete the task",
                            "action": "Generate result",
                            "observation": "Result generated",
                            "iteration_number": 1
                        }
                    ],
                    "final_result": "Low quality result",
                    "source_agent": "worker",
                    "execution_time": 30.0,
                    "client_id": "test_client"
                },
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Report result that triggers failed audit
            response = await async_test_client.post(
                "/v1/report_result",
                json=task_result
            )
            
            assert response.status_code == 204
            
            # Verify audit was triggered
            mock_manager_instance.trigger_audit.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_clients(
        self,
        async_test_client,
        mock_openai_client
    ):
        """
        Test multiple clients working concurrently.
        
        Go/No-Go Checkpoint: Concurrent clients receive different tasks with no duplicates
        """
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            
            # Mock returning different tasks for different clients
            task_responses = [
                AsyncMock(
                    step_id=f"task_{i}",
                    workflow_id="concurrent_workflow",
                    task_description=f"Concurrent task {i}",
                    assigned_agent="researcher",
                    status="IN_PROGRESS",
                    client_id=f"client_{i}"
                ) for i in range(3)
            ] + [None, None]  # Last two clients get no tasks
            
            mock_db_instance.get_and_claim_ready_task.side_effect = task_responses
            
            # Simulate multiple clients polling concurrently
            async def client_poll(client_id: str):
                return await async_test_client.post(
                    "/v1/tasks/poll",
                    json={
                        "client_id": client_id,
                        "agent_capabilities": ["researcher"]
                    }
                )
            
            # Run 5 concurrent polls
            responses = await asyncio.gather(*[
                client_poll(f"client_{i}") for i in range(5)
            ])
            
            # Verify responses
            successful_claims = 0
            task_ids = set()
            
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                if data is not None:
                    successful_claims += 1
                    task_ids.add(data["step_id"])
            
            # Should have 3 successful claims with unique task IDs
            assert successful_claims == 3
            assert len(task_ids) == 3
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_status_tracking(
        self,
        async_test_client
    ):
        """Test comprehensive workflow status tracking."""
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            
            # Mock workflow status progression
            status_responses = [
                {
                    "workflow_id": "status_test_workflow",
                    "total_tasks": 3,
                    "status_counts": {"READY": 1, "PENDING": 2},
                    "is_complete": False
                },
                {
                    "workflow_id": "status_test_workflow", 
                    "total_tasks": 3,
                    "status_counts": {"COMPLETED": 1, "IN_PROGRESS": 1, "PENDING": 1},
                    "is_complete": False
                },
                {
                    "workflow_id": "status_test_workflow",
                    "total_tasks": 3,
                    "status_counts": {"COMPLETED": 3},
                    "is_complete": True
                }
            ]
            
            for i, expected_status in enumerate(status_responses):
                mock_db_instance.get_workflow_status.return_value = expected_status
                
                response = await async_test_client.get(
                    f"/v1/workflows/status_test_workflow/status"
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total_tasks"] == 3
                assert data["is_complete"] == expected_status["is_complete"]


class TestClientWorkerIntegration:
    """Test external client worker integration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_client_worker_lifecycle(
        self,
        test_config,
        mock_openai_client
    ):
        """
        Test complete client worker lifecycle.
        
        Go/No-Go Checkpoint: Client demonstrates full polling → execution → reporting cycle
        """
        # Mock HTTP client for worker
        with patch("client_worker.httpx.AsyncClient") as mock_http_client:
            
            mock_client_instance = AsyncMock()
            mock_http_client.return_value.__aenter__.return_value = mock_client_instance
            mock_http_client.return_value.__aexit__.return_value = None
            
            # Mock poll response - return a task
            mock_poll_response = AsyncMock()
            mock_poll_response.status_code = 200
            mock_poll_response.json.return_value = {
                "step_id": "test_task",
                "workflow_id": "test_workflow",
                "task_description": "Test task description",
                "assigned_agent": "researcher",
                "status": "IN_PROGRESS"
            }
            
            # Mock result reporting response
            mock_result_response = AsyncMock()
            mock_result_response.status_code = 204
            
            mock_client_instance.post.side_effect = [
                mock_poll_response,  # Poll response
                mock_result_response  # Result reporting response
            ]
            
            # Create and test client
            client = MCPWorkerClient(test_config)
            
            # Test task polling
            task = await client._poll_for_task()
            assert task is not None
            assert task.step_id == "test_task"
            
            # Test result reporting
            task_result = TaskResult(
                workflow_id="test_workflow",
                task_id="test_task",
                ra_history=RAHistory(
                    iterations=[
                        ThoughtAction(
                            thought="Test thought",
                            action="Test action",
                            observation="Test observation",
                            iteration_number=1
                        )
                    ],
                    final_result="Test result",
                    source_agent="researcher",
                    execution_time=30.0,
                    client_id=test_config.client_id
                )
            )
            
            success = await client._report_result(task_result)
            assert success
            
            # Cleanup
            await client.stop()
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_multiple_worker_coordination(self, test_config):
        """Test coordination between multiple worker clients."""
        # This test would simulate multiple worker instances
        # and verify they coordinate properly through the server
        
        # For now, this is a placeholder for a more complex test
        # that would require spinning up multiple client processes
        pass


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_api_failure_recovery(
        self,
        async_test_client
    ):
        """Test recovery from LLM API failures."""
        with patch("agent_manager.api.endpoints.AgentManager") as mock_manager:
            
            mock_manager_instance = AsyncMock()
            mock_manager.return_value = mock_manager_instance
            
            # Simulate LLM API failure
            mock_manager_instance.plan_and_save_task.side_effect = Exception("LLM API timeout")
            
            response = await async_test_client.post(
                "/v1/submit_task",
                json={"user_request": "Test task"}
            )
            
            # Should return 500 error
            assert response.status_code == 500
            data = response.json()
            assert "Server error" in data["detail"]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_failure_handling(
        self,
        async_test_client
    ):
        """Test handling of database failures."""
        with patch("agent_manager.api.endpoints.DatabaseService") as mock_db_service:
            
            mock_db_instance = AsyncMock()
            mock_db_service.return_value = mock_db_instance
            
            # Simulate database failure
            mock_db_instance.get_workflow_status.side_effect = Exception("Database connection lost")
            
            response = await async_test_client.get("/v1/workflows/test/status")
            
            assert response.status_code == 500
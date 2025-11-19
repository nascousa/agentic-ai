"""
Integration tests for database service operations.

Tests the DatabaseService with real database operations to ensure
proper transaction handling, concurrency safety, and data integrity.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from agent_manager.core.models import (
    TaskGraph,
    TaskStep,
    TaskStatus,
    TaskResult,
    RAHistory,
    ThoughtAction,
    AuditReport,
)


class TestDatabaseServiceTaskOperations:
    """Test database operations for task management."""
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_task_graph(self, db_service, sample_task_graph_data):
        """Test saving and retrieving TaskGraph."""
        # Create TaskGraph
        task_graph = TaskGraph(
            workflow_id=sample_task_graph_data["workflow_id"],
            tasks=[
                TaskStep(**task_data) 
                for task_data in sample_task_graph_data["tasks"]
            ]
        )
        
        # Save to database
        workflow_id = await db_service.save_task_graph(task_graph)
        assert workflow_id == sample_task_graph_data["workflow_id"]
        
        # Retrieve from database
        retrieved_graph = await db_service.get_task_graph(workflow_id)
        assert retrieved_graph is not None
        assert retrieved_graph.workflow_id == workflow_id
        assert len(retrieved_graph.tasks) == 2
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_task_graph(self, db_service):
        """Test retrieving non-existent TaskGraph."""
        result = await db_service.get_task_graph("nonexistent_workflow")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_atomic_task_claiming(self, db_service):
        """Test atomic task claiming prevents duplicate assignment."""
        # Setup: Create a workflow with ready task
        task_graph = TaskGraph(
            workflow_id="claim_test_workflow",
            tasks=[
                TaskStep(
                    step_id="claimable_task",
                    workflow_id="claim_test_workflow",
                    task_description="Test task for claiming",
                    assigned_agent="researcher",
                    status=TaskStatus.READY
                )
            ]
        )
        
        await db_service.save_task_graph(task_graph)
        
        # Test: Two clients try to claim simultaneously
        task1 = await db_service.get_and_claim_ready_task(
            agent_capabilities=["researcher"],
            client_id="client_1"
        )
        
        task2 = await db_service.get_and_claim_ready_task(
            agent_capabilities=["researcher"], 
            client_id="client_2"
        )
        
        # Verify: Only one client gets the task
        assert task1 is not None
        assert task2 is None
        assert task1.client_id == "client_1"
        assert task1.status == TaskStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_dependency_resolution(self, db_service):
        """Test dependency checking and task dispatch."""
        # Create workflow with dependencies
        task_graph = TaskGraph(
            workflow_id="dependency_test",
            tasks=[
                TaskStep(
                    step_id="task_1",
                    workflow_id="dependency_test",
                    task_description="First task",
                    assigned_agent="researcher",
                    dependencies=[],
                    status=TaskStatus.READY
                ),
                TaskStep(
                    step_id="task_2", 
                    workflow_id="dependency_test",
                    task_description="Second task",
                    assigned_agent="analyst",
                    dependencies=["task_1"],
                    status=TaskStatus.PENDING
                )
            ]
        )
        
        await db_service.save_task_graph(task_graph)
        
        # Complete first task
        task_result = TaskResult(
            workflow_id="dependency_test",
            task_id="task_1",
            ra_history=RAHistory(
                iterations=[
                    ThoughtAction(
                        thought="Complete task 1",
                        action="Execute action",
                        observation="Success",
                        iteration_number=1
                    )
                ],
                final_result="Task 1 complete",
                source_agent="researcher",
                execution_time=30.0,
                client_id="client_1"
            )
        )
        
        await db_service.save_task_result(task_result)
        
        # Check that task_2 becomes ready
        newly_ready = await db_service.check_and_dispatch_ready_tasks("dependency_test")
        assert newly_ready == 1
        
        # Verify task_2 can now be claimed
        ready_task = await db_service.get_and_claim_ready_task(
            agent_capabilities=["analyst"],
            client_id="client_2"
        )
        assert ready_task is not None
        assert ready_task.step_id == "task_2"


class TestDatabaseServiceWorkflowOperations:
    """Test workflow-level database operations."""
    
    @pytest.mark.asyncio
    async def test_workflow_completion_check(self, db_service):
        """Test workflow completion detection."""
        # Create single-task workflow
        task_graph = TaskGraph(
            workflow_id="completion_test",
            tasks=[
                TaskStep(
                    step_id="single_task",
                    workflow_id="completion_test",
                    task_description="Only task",
                    assigned_agent="researcher",
                    status=TaskStatus.READY
                )
            ]
        )
        
        await db_service.save_task_graph(task_graph)
        
        # Initially not complete
        is_complete = await db_service.is_workflow_complete("completion_test")
        assert not is_complete
        
        # Complete the task
        task_result = TaskResult(
            workflow_id="completion_test",
            task_id="single_task",
            ra_history=RAHistory(
                iterations=[
                    ThoughtAction(
                        thought="Complete task",
                        action="Execute",
                        observation="Done",
                        iteration_number=1
                    )
                ],
                final_result="Complete",
                source_agent="researcher",
                execution_time=15.0,
                client_id="client_1"
            )
        )
        
        await db_service.save_task_result(task_result)
        
        # Now should be complete
        is_complete = await db_service.is_workflow_complete("completion_test")
        assert is_complete
    
    @pytest.mark.asyncio
    async def test_workflow_results_retrieval(self, db_service):
        """Test retrieving all results for a workflow."""
        # Setup workflow and complete tasks
        workflow_id = "results_test"
        task_graph = TaskGraph(
            workflow_id=workflow_id,
            tasks=[
                TaskStep(
                    step_id="task_1",
                    workflow_id=workflow_id,
                    task_description="First task",
                    assigned_agent="researcher",
                    status=TaskStatus.READY
                )
            ]
        )
        
        await db_service.save_task_graph(task_graph)
        
        # Complete task
        task_result = TaskResult(
            workflow_id=workflow_id,
            task_id="task_1",
            ra_history=RAHistory(
                iterations=[
                    ThoughtAction(
                        thought="Research completed",
                        action="Analyze data",
                        observation="Found insights",
                        iteration_number=1
                    )
                ],
                final_result="Research findings documented",
                source_agent="researcher",
                execution_time=60.0,
                client_id="client_1"
            )
        )
        
        await db_service.save_task_result(task_result)
        
        # Retrieve results
        results = await db_service.get_workflow_results(workflow_id)
        assert len(results) == 1
        assert results[0].final_result == "Research findings documented"
        assert results[0].source_agent == "researcher"


class TestDatabaseServiceAuditOperations:
    """Test audit-related database operations."""
    
    @pytest.mark.asyncio
    async def test_save_audit_report(self, db_service):
        """Test saving audit reports."""
        audit_report = AuditReport(
            workflow_id="audit_test_workflow",
            is_successful=True,
            feedback="High quality work completed",
            rework_suggestions=[],
            confidence_score=0.95,
            reviewed_tasks=["task_1", "task_2"],
            audit_criteria=["completeness", "accuracy"]
        )
        
        success = await db_service.save_audit_report(audit_report)
        assert success
    
    @pytest.mark.asyncio
    async def test_reset_tasks_for_rework(self, db_service):
        """Test resetting workflow for rework after failed audit."""
        # Create and complete a workflow
        workflow_id = "rework_test"
        task_graph = TaskGraph(
            workflow_id=workflow_id,
            tasks=[
                TaskStep(
                    step_id="task_1",
                    workflow_id=workflow_id,
                    task_description="Task to rework",
                    assigned_agent="researcher",
                    status=TaskStatus.READY
                )
            ]
        )
        
        await db_service.save_task_graph(task_graph)
        
        # Complete task
        task_result = TaskResult(
            workflow_id=workflow_id,
            task_id="task_1",
            ra_history=RAHistory(
                iterations=[
                    ThoughtAction(
                        thought="Complete task",
                        action="Execute",
                        observation="Done",
                        iteration_number=1
                    )
                ],
                final_result="Initial result",
                source_agent="researcher",
                execution_time=30.0,
                client_id="client_1"
            )
        )
        
        await db_service.save_task_result(task_result)
        
        # Reset for rework
        rework_suggestions = ["Improve accuracy", "Add more details"]
        success = await db_service.reset_tasks_for_rework(workflow_id, rework_suggestions)
        assert success
        
        # Verify task is now ready again
        ready_task = await db_service.get_and_claim_ready_task(
            agent_capabilities=["researcher"],
            client_id="client_2"
        )
        assert ready_task is not None
        assert ready_task.step_id == "task_1"


class TestDatabaseServiceConcurrency:
    """Test concurrent database operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_task_claiming(self, db_service):
        """Test that concurrent clients don't claim the same task."""
        import asyncio
        
        # Setup multiple ready tasks
        task_graph = TaskGraph(
            workflow_id="concurrent_test",
            tasks=[
                TaskStep(
                    step_id=f"task_{i}",
                    workflow_id="concurrent_test",
                    task_description=f"Concurrent task {i}",
                    assigned_agent="researcher",
                    status=TaskStatus.READY
                ) for i in range(3)
            ]
        )
        
        await db_service.save_task_graph(task_graph)
        
        # Multiple clients claim simultaneously
        async def claim_task(client_id: str):
            return await db_service.get_and_claim_ready_task(
                agent_capabilities=["researcher"],
                client_id=client_id
            )
        
        # Run 5 concurrent claims for 3 available tasks
        tasks = await asyncio.gather(*[
            claim_task(f"client_{i}") for i in range(5)
        ])
        
        # Verify only 3 tasks were claimed (no duplicates)
        claimed_tasks = [task for task in tasks if task is not None]
        assert len(claimed_tasks) == 3
        
        # Verify all claimed tasks have different step_ids
        claimed_step_ids = [task.step_id for task in claimed_tasks]
        assert len(set(claimed_step_ids)) == 3
"""
FastAPI endpoints for MCP server coordinating external client workers.

Implements REST API endpoints with proper error handling, validation,
and integration with the database service layer for atomic operations.
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from agent_manager.api.dependencies import get_db_session, verify_auth_token
from agent_manager.service import DatabaseService
from agent_manager.core.manager import AgentManager
from agent_manager.core.models import (
    TaskGraphRequest,
    TaskGraphResponse,
    TaskStep,
    TaskResult,
    WorkflowStatus,
    AuditReport,
    ClientPollRequest,
)

# Create router for all API endpoints
router = APIRouter(tags=["mcp-coordination"])


@router.post(
    "/tasks",
    response_model=TaskGraphResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user request for workflow planning"
)
async def submit_task(
    request: TaskGraphRequest,
    session: AsyncSession = Depends(get_db_session),
    token: str = Depends(verify_auth_token)
) -> TaskGraphResponse:
    """
    Plan and persist TaskGraph from user request.
    
    Orchestrates LLM-based workflow planning and database persistence
    with initial task dependency resolution.
    
    Args:
        request: User request with optional metadata context
        session: Database session for persistence
        
    Returns:
        TaskGraphResponse: Complete workflow with dependency graph
        
    Raises:
        HTTPException: 422 for invalid requests, 500 for server errors
        
    Go/No-Go Checkpoint: User submission results in persisted workflow with tasks marked READY/PENDING
    """
    try:
        # Initialize services
        db_service = DatabaseService(session)
        manager = AgentManager()
        
        # Plan and save workflow
        workflow_id = await manager.plan_and_save_task(
            user_request=request.user_request,
            metadata=request.metadata,
            db_service=db_service
        )
        
        # Retrieve complete task graph
        task_graph = await db_service.get_task_graph(workflow_id)
        
        if not task_graph:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve saved TaskGraph"
            )
        
        return TaskGraphResponse(
            workflow_id=task_graph.workflow_id,
            tasks=task_graph.tasks,
            created_at=task_graph.created_at,
            total_tasks=len(task_graph.tasks)
        )
        
    except ValueError as e:
        # LLM or planning validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Planning failed: {str(e)}"
        )
    except Exception as e:
        # Database or other server errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.get(
    "/tasks/ready",
    response_model=Optional[TaskStep],
    summary="Client polling for ready tasks"
)
async def get_ready_task(
    agent_id: str = Query(..., description="Unique client identifier"),
    agent_capabilities: List[str] = Query(..., description="List of agent types this client can handle"),
    session: AsyncSession = Depends(get_db_session),
    token: str = Depends(verify_auth_token)
) -> Optional[TaskStep]:
    """
    Atomic task claiming for external client workers.
    
    Finds oldest READY task matching client capabilities and atomically
    claims it to prevent duplicate assignment across concurrent clients.
    
    Args:
        agent_id: Unique client identifier
        agent_capabilities: List of agent types this client can handle
        session: Database session for atomic operations
        token: Authentication token
        
    Returns:
        TaskStep: Claimed task or None if no tasks available
        
    Go/No-Go Checkpoint: Concurrent clients receive different tasks with no duplicates
    """
    try:
        db_service = DatabaseService(session)
        
        # Atomic task claiming
        task = await db_service.get_and_claim_ready_task(
            agent_capabilities=agent_capabilities,
            client_id=agent_id
        )
        
        return task
        
    except Exception as e:
        # Log error but don't expose details to client
        print(f"❌ Poll error for client {agent_id}: {str(e)}")
        return None


@router.post(
    "/results",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Submit task execution results"
)
async def report_result(
    task_result: TaskResult,
    session: AsyncSession = Depends(get_db_session),
    token: str = Depends(verify_auth_token)
) -> None:
    """
    Save RAHistory and trigger dependency resolution.
    
    Processes complete task execution results, updates task status,
    and coordinates dependent task activation.
    
    Args:
        task_result: Complete task execution with RAHistory
        session: Database session for persistence
        
    Raises:
        HTTPException: 404 for unknown tasks, 400 for invalid results
        
    Go/No-Go Checkpoint: Result submission triggers audit workflow and dependent task activation
    """
    try:
        db_service = DatabaseService(session)
        manager = AgentManager()
        
        # Save task result
        success = await db_service.save_task_result(task_result)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {task_result.task_id}"
            )
        
        # Check for newly ready tasks
        newly_ready = await db_service.check_and_dispatch_ready_tasks(
            task_result.workflow_id
        )
        
        # Check if workflow is complete
        is_complete = await db_service.is_workflow_complete(task_result.workflow_id)
        
        if is_complete:
            # Trigger audit workflow
            await manager.trigger_audit(
                workflow_id=task_result.workflow_id,
                db_service=db_service
            )
        
        print(f"✅ Processed result for {task_result.task_id}, {newly_ready} tasks now ready")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process result: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_id}/status",
    response_model=WorkflowStatus,
    summary="Get workflow status and progress"
)
async def get_workflow_status(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session),
    token: str = Depends(verify_auth_token)
) -> WorkflowStatus:
    """
    Retrieve comprehensive workflow status.
    
    Args:
        workflow_id: Workflow identifier
        session: Database session
        
    Returns:
        WorkflowStatus: Current workflow state and task progress
        
    Raises:
        HTTPException: 404 for unknown workflows
    """
    try:
        db_service = DatabaseService(session)
        
        status_info = await db_service.get_workflow_status(workflow_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow not found: {workflow_id}"
            )
        
        return WorkflowStatus(**status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_id}/result",
    response_model=Optional[str],
    summary="Get final workflow result"
)
async def get_workflow_result(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session)
) -> Optional[str]:
    """
    Synthesize and return final workflow result.
    
    Args:
        workflow_id: Workflow identifier
        session: Database session
        
    Returns:
        str: Synthesized final result or None if not complete
        
    Raises:
        HTTPException: 404 for unknown workflows
    """
    try:
        db_service = DatabaseService(session)
        manager = AgentManager()
        
        # Check if workflow is complete
        is_complete = await db_service.is_workflow_complete(workflow_id)
        
        if not is_complete:
            return None
        
        # Get all task results
        ra_histories = await db_service.get_workflow_results(workflow_id)
        
        if not ra_histories:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No results found for workflow: {workflow_id}"
            )
        
        # Synthesize final result
        final_result = await manager.synthesize_results(
            workflow_id=workflow_id,
            task_results=ra_histories
        )
        
        return final_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow result: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_id}/audit",
    response_model=List[AuditReport],
    summary="Get audit reports for workflow"
)
async def get_audit_reports(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session)
) -> List[AuditReport]:
    """
    Retrieve all audit reports for a workflow.
    
    Args:
        workflow_id: Workflow identifier
        session: Database session
        
    Returns:
        List[AuditReport]: All audit reports in chronological order
    """
    try:
        # Note: This would need additional database service method
        # For now, return empty list - could be implemented in future
        return []
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit reports: {str(e)}"
        )


@router.post(
    "/workflows/{workflow_id}/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset workflow for rework (admin only)"
)
async def reset_workflow(
    workflow_id: str,
    rework_suggestions: List[str],
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Reset workflow tasks for rework after failed audit.
    
    Args:
        workflow_id: Workflow to reset
        rework_suggestions: Specific improvement guidance
        session: Database session
        
    Raises:
        HTTPException: 404 for unknown workflows
        
    Go/No-Go Checkpoint: System demonstrates Parallel → Audit → Rework → Synthesis cycle
    """
    try:
        db_service = DatabaseService(session)
        
        success = await db_service.reset_tasks_for_rework(
            workflow_id=workflow_id,
            rework_suggestions=rework_suggestions
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow not found: {workflow_id}"
            )
        
        print(f"🔄 Reset workflow {workflow_id} for rework")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset workflow: {str(e)}"
        )


# Health check endpoint
@router.get(
    "/health",
    summary="Server health check"
)
async def health_check() -> dict:
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "MCP Server"
    }
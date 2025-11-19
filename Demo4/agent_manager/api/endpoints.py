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
        
        # Prepare metadata with workflow_name if provided
        metadata = request.metadata or {}
        if request.workflow_name:
            metadata["workflow_name"] = request.workflow_name
        
        # Add project_name to metadata for use by plan_and_save_task
        if request.project_id:
            metadata["project_id"] = request.project_id
        
        # Add fast_mode to metadata
        if request.fast_mode:
            metadata["fast_mode"] = True
        
        # Plan and save workflow (will create project internally)
        workflow_id = await manager.plan_and_save_task(
            user_request=request.user_request,
            metadata=metadata,
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
            workflow_name=task_graph.workflow_name,
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
    Atomic task claiming for external client workers with optional Redis caching.
    
    Finds oldest READY task matching client capabilities and atomically
    claims it to prevent duplicate assignment across concurrent clients.
    Falls back to database-only operation if Redis is unavailable.
    
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
        
        # Try Redis caching if available (but don't fail if it's not)
        cached_task = None
        try:
            from agent_manager.core.redis_client import get_redis_client_instance
            redis = get_redis_client_instance()
            
            if await redis.is_connected():
                # Try to get cached ready tasks for each capability
                for capability in agent_capabilities:
                    cached_tasks = await redis.get_cached_ready_tasks(capability)
                    if cached_tasks:
                        cached_task = cached_tasks[0]
                        break
                
                # If we have a cached task, try to claim it atomically
                if cached_task:
                    try:
                        claimed_task = await db_service.get_and_claim_ready_task(
                            agent_capabilities=agent_capabilities,
                            client_id=agent_id,
                            preferred_task_id=cached_task.step_id
                        )
                        
                        if claimed_task:
                            # Invalidate cache since we just claimed a task
                            for capability in agent_capabilities:
                                await redis.invalidate_ready_tasks_cache(capability)
                            await redis.increment_counter("cache_hits:ready_tasks", expire=3600)
                            return claimed_task
                    except Exception:
                        # Cached task might be stale, fall through to database query
                        pass
        except Exception:
            # Redis not available, continue with database-only operation
            pass
        
        # Fallback to database query (cache miss or Redis unavailable)
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
    Save RAHistory and trigger dependency resolution with optional cache management.
    
    Processes complete task execution results, updates task status,
    coordinates dependent task activation, and manages Redis cache if available.
    
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
        
        # Try Redis operations if available (but don't fail if it's not)
        try:
            from agent_manager.core.redis_client import get_redis_client_instance
            redis = get_redis_client_instance()
            
            if await redis.is_connected():
                # Cache the task result for future reference
                await redis.cache_task_result(
                    task_result.task_id,
                    {
                        "iterations": [iteration.model_dump() for iteration in task_result.result.iterations],
                        "final_result": task_result.result.final_result,
                        "source_agent": task_result.result.source_agent,
                        "execution_time": task_result.result.execution_time,
                        "completed_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Invalidate ready tasks cache for all agent types since new tasks may be available
                agent_types = ["analyst", "writer", "researcher", "developer", "tester", "architect"]
                for agent_type in agent_types:
                    await redis.invalidate_ready_tasks_cache(agent_type)
        except Exception:
            # Redis not available, continue without caching
            pass
        
        # Save task result to database
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
        
        # Check if workflow is complete and cache status
        is_complete = await db_service.is_workflow_complete(task_result.workflow_id)
        
        # Update workflow status cache if Redis available
        try:
            from agent_manager.core.redis_client import get_redis_client_instance
            redis = get_redis_client_instance()
            
            if await redis.is_connected():
                workflow_status = await db_service.get_workflow_status(task_result.workflow_id)
                if workflow_status:
                    await redis.cache_workflow_status(
                        task_result.workflow_id,
                        workflow_status.model_dump()
                    )
        except Exception:
            pass
        
        if is_complete:
            # Trigger audit workflow
            await manager.trigger_audit(
                workflow_id=task_result.workflow_id,
                db_service=db_service
            )
            
            # Publish workflow completion notification if Redis available
            try:
                from agent_manager.core.redis_client import get_redis_client_instance
                redis = get_redis_client_instance()
                
                if await redis.is_connected():
                    await redis.publish_task_update(
                        "workflow_completed",
                        {
                            "workflow_id": task_result.workflow_id,
                            "completed_at": datetime.utcnow().isoformat(),
                            "audit_triggered": True
                        }
                    )
            except Exception:
                pass
        
        # Update metrics if Redis available
        try:
            from agent_manager.core.redis_client import get_redis_client_instance
            redis = get_redis_client_instance()
            
            if await redis.is_connected():
                await redis.increment_counter("tasks_completed", expire=86400)
                await redis.increment_counter(f"tasks_completed:{task_result.result.source_agent}", expire=86400)
        except Exception:
            pass
        
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


# Cache management and monitoring endpoints
@router.get(
    "/cache/test",
    summary="Test Redis connection"
)
async def test_redis_connection(
    token: str = Depends(verify_auth_token)
) -> dict:
    """Test Redis connection without dependency injection."""
    import os
    from agent_manager.core.redis_client import RedisClient
    
    # Get environment variable directly
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6380")
    
    try:
        # Create a new Redis client instance
        test_client = RedisClient(redis_url)
        await test_client.connect()
        
        # Test basic operations
        await test_client.redis.set("test_key", "test_value", ex=60)
        value = await test_client.redis.get("test_key")
        
        await test_client.disconnect()
        
        return {
            "status": "success",
            "redis_url": redis_url,
            "test_result": value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "redis_url": redis_url,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get(
    "/cache/stats",
    summary="Redis cache statistics"
)
async def get_cache_stats(
    token: str = Depends(verify_auth_token)
) -> dict:
    """Get comprehensive Redis cache statistics and performance metrics."""
    try:
        from agent_manager.core.redis_client import get_redis_client_instance
        redis = get_redis_client_instance()
        
        # Check if Redis is connected
        if not await redis.is_connected():
            try:
                await redis.connect()
            except Exception as e:
                return {
                    "status": "unavailable",
                    "error": f"Redis connection failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        # Get Redis connection stats
        redis_stats = await redis.get_cache_stats()
        
        # Get application-level counters
        app_stats = {
            "cache_hits_ready_tasks": await redis.get_counter("cache_hits:ready_tasks"),
            "cache_misses_ready_tasks": await redis.get_counter("cache_misses:ready_tasks"),
            "cache_errors_ready_tasks": await redis.get_counter("cache_errors:ready_tasks"),
            "tasks_completed": await redis.get_counter("tasks_completed"),
            "tasks_completed_analyst": await redis.get_counter("tasks_completed:analyst"),
            "tasks_completed_writer": await redis.get_counter("tasks_completed:writer"),
            "tasks_completed_researcher": await redis.get_counter("tasks_completed:researcher"),
            "tasks_completed_developer": await redis.get_counter("tasks_completed:developer"),
            "tasks_completed_tester": await redis.get_counter("tasks_completed:tester"),
            "tasks_completed_architect": await redis.get_counter("tasks_completed:architect"),
            "result_processing_errors": await redis.get_counter("result_processing_errors"),
        }
        
        # Calculate cache efficiency
        total_ready_task_requests = app_stats["cache_hits_ready_tasks"] + app_stats["cache_misses_ready_tasks"]
        if total_ready_task_requests > 0:
            app_stats["ready_task_cache_hit_ratio"] = app_stats["cache_hits_ready_tasks"] / total_ready_task_requests
        else:
            app_stats["ready_task_cache_hit_ratio"] = 0.0
        
        return {
            "redis_stats": redis_stats,
            "application_stats": app_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get cache stats: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


@router.delete(
    "/cache/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Redis cache"
)
async def clear_cache(
    pattern: str = Query("*", description="Cache key pattern to clear"),
    token: str = Depends(verify_auth_token)
) -> None:
    """Clear Redis cache entries matching the specified pattern."""
    try:
        from agent_manager.core.redis_client import get_redis_client_instance
        redis = get_redis_client_instance()
        
        if not await redis.is_connected():
            try:
                await redis.connect()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Redis unavailable: {str(e)}"
                )
        
        deleted_count = await redis.clear_cache(pattern)
        print(f"✅ Cleared {deleted_count} cache entries matching pattern '{pattern}'")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


# Health check endpoint
@router.get(
    "/workers/status",
    summary="Get worker status with current tasks"
)
async def get_worker_status(
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get status of all workers including currently executing tasks.
    
    Returns:
        dict: Worker status information with current task assignments
    """
    try:
        from sqlalchemy import select
        from agent_manager.orm import TaskStepORM
        
        # Query all IN_PROGRESS tasks
        stmt = select(TaskStepORM).where(TaskStepORM.status == "IN_PROGRESS")
        result = await session.execute(stmt)
        in_progress_tasks = result.scalars().all()
        
        # Build worker-to-task mapping
        worker_tasks = {}
        for task in in_progress_tasks:
            if task.client_id:
                worker_tasks[task.client_id] = {
                    "task_id": task.step_id,
                    "task_name": task.task_name,
                    "task_description": task.task_description,
                    "workflow_id": task.workflow_id,
                    "started_at": task.started_at.isoformat() if task.started_at else None
                }
        
        return {
            "worker_tasks": worker_tasks,
            "total_active": len(worker_tasks),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker status: {str(e)}"
        )


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
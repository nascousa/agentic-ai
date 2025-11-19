"""
Database service layer with atomic operations for concurrent client coordination.

This module provides thread-safe database operations for the MCP server,
ensuring data consistency and preventing race conditions in concurrent
client environments.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_manager.core.models import (
    TaskGraph,
    TaskStep,
    TaskStatus,
    RAHistory,
    AuditReport,
    TaskResult,
)
from agent_manager.orm import (
    TaskGraphORM,
    TaskStepORM,
    ResultORM,
    AuditReportORM,
    FileAccessORM,
    ProjectORM,
    ProjectORM,
)


class DatabaseService:
    """
    Centralized database operations for MCP server coordination.
    
    Implements atomic operations for concurrent client safety and
    provides high-level database operations for workflow management.
    
    Go/No-Go Checkpoint: Concurrency validated with no duplicate task execution
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize database service with session.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def create_project(self, project_name: str, project_path: str = None, metadata: dict = None) -> tuple[str, UUID]:
        """
        Create a new project in the database.
        
        Args:
            project_name: Name of the project
            project_path: Optional path to project folder
            metadata: Optional project metadata
            
        Returns:
            tuple[str, UUID]: (Sequential project ID like 'PID000001', Internal UUID)
        """
        from agent_manager.orm import ProjectORM
        from agent_manager.id_generator import SequentialIDGenerator
        from datetime import datetime, timezone
        
        # Generate sequential project_id (PID000001, PID000002, etc.)
        project_id = await SequentialIDGenerator.get_next_project_id(self.session)
        
        project = ProjectORM(
            project_id=project_id,
            project_name=project_name,
            project_path=project_path,
            project_metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.session.add(project)
        await self.session.flush()  # Get the generated ID
        
        print(f"✅ Created project {project_id}: {project_name}")
        return project_id, project.id
    
    async def save_task_graph(self, task_graph: TaskGraph, project_uuid: UUID = None) -> str:
        """
        Atomically persist TaskGraph with initial task states.
        
        Args:
            task_graph: TaskGraph to persist
            project_uuid: Optional internal project UUID to link workflow to
            
        Returns:
            str: Workflow ID of saved TaskGraph
            
        Go/No-Go Checkpoint: Task submission results in persisted TaskGraph with initial tasks marked READY
        """
        try:
            from agent_manager.id_generator import SequentialIDGenerator
            
            # Generate sequential workflow ID
            workflow_id = await SequentialIDGenerator.get_next_workflow_id(self.session)
            
            # Create TaskGraphORM with sequential ID
            task_graph_orm = TaskGraphORM(
                workflow_id=workflow_id,
                workflow_name=task_graph.workflow_name,
                user_request=task_graph.metadata.get("user_request", ""),
                workflow_metadata=task_graph.metadata,
                status="IN_PROGRESS",
                project_id=project_uuid,  # Use the internal UUID
                created_at=task_graph.created_at
            )
            
            self.session.add(task_graph_orm)
            await self.session.flush()  # Get the ID
            
            # Create mapping of old step_ids to new sequential IDs
            step_id_mapping = {}
            
            # Create TaskStepORM instances with sequential IDs
            for task in task_graph.tasks:
                # Generate sequential task ID
                task_id = await SequentialIDGenerator.get_next_task_id(self.session)
                step_id_mapping[task.step_id] = task_id
                
                # Update dependencies to use new sequential IDs
                updated_dependencies = [
                    step_id_mapping.get(dep, dep) for dep in task.dependencies
                ]
                
                task_step_orm = TaskStepORM(
                    step_id=task_id,
                    workflow_id=workflow_id,
                    task_name=task.task_name,
                    task_description=task.task_description,
                    assigned_agent=task.assigned_agent,
                    dependencies=updated_dependencies,
                    project_path=task.project_path,
                    status=task.status.value,
                    created_at=task.created_at
                )
                self.session.add(task_step_orm)
            
            # Don't commit here - let the dependency handle it
            await self.session.flush()  # Ensure IDs are generated
            
            print(f"✅ Saved TaskGraph {workflow_id} with {len(task_graph.tasks)} tasks")
            return workflow_id
            
        except Exception as e:
            # Don't rollback here - let the dependency handle it
            print(f"❌ Failed to save TaskGraph: {str(e)}")
            raise
    
    async def update_tasks_project_path(self, workflow_id: str, project_path: str) -> None:
        """
        Update project_path for all tasks in a workflow.
        
        Args:
            workflow_id: Workflow identifier
            project_path: Absolute path to project folder
        """
        try:
            # Update all tasks for this workflow
            stmt = (
                update(TaskStepORM)
                .where(TaskStepORM.workflow_id == workflow_id)
                .values(project_path=project_path)
            )
            
            await self.session.execute(stmt)
            await self.session.flush()
            
            print(f"✅ Updated project_path for all tasks in workflow {workflow_id}")
            
        except Exception as e:
            print(f"❌ Failed to update project_path: {str(e)}")
            raise
    
    async def get_task_graph(self, workflow_id: str) -> Optional[TaskGraph]:
        """
        Retrieve complete workflow state from database.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            TaskGraph: Complete workflow with all tasks, or None if not found
        """
        try:
            # Query with eager loading of relationships
            stmt = (
                select(TaskGraphORM)
                .options(selectinload(TaskGraphORM.tasks))
                .where(TaskGraphORM.workflow_id == workflow_id)
            )
            
            result = await self.session.execute(stmt)
            task_graph_orm = result.scalar_one_or_none()
            
            if not task_graph_orm:
                return None
            
            # Convert ORM to Pydantic
            tasks = [
                TaskStep(
                    step_id=task_orm.step_id,
                    workflow_id=task_orm.workflow_id,
                    task_name=task_orm.task_name,
                    task_description=task_orm.task_description,
                    assigned_agent=task_orm.assigned_agent,
                    dependencies=task_orm.dependencies,
                    project_path=task_orm.project_path,
                    status=TaskStatus(task_orm.status),
                    client_id=task_orm.client_id,
                    started_at=task_orm.started_at,
                    completed_at=task_orm.completed_at,
                    created_at=task_orm.created_at
                )
                for task_orm in task_graph_orm.tasks
            ]
            
            return TaskGraph(
                workflow_id=task_graph_orm.workflow_id,
                workflow_name=task_graph_orm.workflow_name,
                tasks=tasks,
                created_at=task_graph_orm.created_at,
                metadata=task_graph_orm.workflow_metadata
            )
            
        except Exception as e:
            print(f"❌ Failed to retrieve TaskGraph {workflow_id}: {str(e)}")
            raise
    
    async def get_and_claim_ready_task(
        self,
        agent_capabilities: List[str],
        client_id: str,
        preferred_task_id: Optional[str] = None
    ) -> Optional[TaskStep]:
        """
        Atomic query and claim operation for client polling.
        
        Finds the oldest READY task matching capabilities and atomically
        claims it for the requesting client. Can optionally prefer a specific task.
        
        Args:
            agent_capabilities: List of agent types client can handle
            client_id: Client identifier claiming the task
            preferred_task_id: Optional specific task to try claiming first
            
        Returns:
            TaskStep: Claimed task or None if no tasks available
            
        Go/No-Go Checkpoint: Prevents duplicate task assignment across concurrent clients
        """
        try:
            # If preferred task specified, try to claim it first
            if preferred_task_id:
                preferred_stmt = (
                    select(TaskStepORM)
                    .where(
                        TaskStepORM.step_id == preferred_task_id,
                        TaskStepORM.status == TaskStatus.READY,
                        TaskStepORM.assigned_agent.in_(agent_capabilities),
                        TaskStepORM.client_id.is_(None)
                    )
                    .with_for_update()
                )
                
                result = await self.session.execute(preferred_stmt)
                preferred_task = result.scalar_one_or_none()
                
                if preferred_task:
                    # Check dependencies are satisfied for preferred task
                    if await self._check_task_dependencies_satisfied(preferred_task.step_id):
                        # Claim the preferred task
                        preferred_task.client_id = client_id
                        preferred_task.status = TaskStatus.IN_PROGRESS
                        preferred_task.started_at = datetime.utcnow()
                        
                        await self.session.commit()
                        
                        return TaskStep(
                            step_id=preferred_task.step_id,
                            workflow_id=preferred_task.workflow_id,
                            task_name=preferred_task.task_name,
                            task_description=preferred_task.task_description,
                            assigned_agent=preferred_task.assigned_agent,
                            dependencies=preferred_task.dependencies or [],
                            project_path=preferred_task.project_path,
                            file_dependencies=preferred_task.file_dependencies or [],
                            file_access_types=preferred_task.file_access_types or [],
                            status=TaskStatus.IN_PROGRESS,
                            created_at=preferred_task.created_at,
                            updated_at=preferred_task.updated_at
                        )
            
            # Find ready tasks matching capabilities with dependency check
            ready_tasks_stmt = (
                select(TaskStepORM)
                .where(
                    and_(
                        TaskStepORM.status == "READY",
                        TaskStepORM.assigned_agent.in_(agent_capabilities),
                        TaskStepORM.client_id.is_(None)  # Not already claimed
                    )
                )
                .order_by(TaskStepORM.created_at)  # FIFO order
                .limit(1)
                .with_for_update()  # Lock for atomic update
            )
            
            result = await self.session.execute(ready_tasks_stmt)
            task_orm = result.scalar_one_or_none()
            
            if not task_orm:
                return None
            
            # Verify dependencies are still satisfied
            if not await self._check_dependencies_satisfied(task_orm):
                return None
            
            # Atomically claim the task
            task_orm.status = "IN_PROGRESS"
            task_orm.client_id = client_id
            task_orm.started_at = datetime.utcnow()
            
            await self.session.commit()
            
            # Get project path from workflow's project
            workflow_stmt = select(TaskGraphORM).where(TaskGraphORM.workflow_id == task_orm.workflow_id)
            workflow_result = await self.session.execute(workflow_stmt)
            workflow_orm = workflow_result.scalar_one_or_none()
            
            project_path = None
            if workflow_orm and workflow_orm.project_id:
                project_stmt = select(ProjectORM).where(ProjectORM.id == workflow_orm.project_id)
                project_result = await self.session.execute(project_stmt)
                project_orm = project_result.scalar_one_or_none()
                if project_orm:
                    project_path = project_orm.project_path
            
            # Convert to Pydantic model
            task_step = TaskStep(
                step_id=task_orm.step_id,
                workflow_id=task_orm.workflow_id,
                task_name=task_orm.task_name,
                task_description=task_orm.task_description,
                assigned_agent=task_orm.assigned_agent,
                dependencies=task_orm.dependencies,
                project_path=task_orm.project_path or project_path,  # Use task's project_path first, fallback to workflow's
                status=TaskStatus.IN_PROGRESS,
                client_id=client_id,
                started_at=task_orm.started_at,
                completed_at=task_orm.completed_at,
                created_at=task_orm.created_at
            )
            
            print(f"🔒 Client {client_id} claimed task {task_orm.step_id}")
            return task_step
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to claim task for {client_id}: {str(e)}")
            return None
    
    async def _check_dependencies_satisfied(self, task_orm: TaskStepORM) -> bool:
        """Check if all task dependencies are completed."""
        if not task_orm.dependencies:
            return True
        
        # Count completed dependencies
        completed_count_stmt = (
            select(TaskStepORM)
            .where(
                and_(
                    TaskStepORM.workflow_id == task_orm.workflow_id,
                    TaskStepORM.step_id.in_(task_orm.dependencies),
                    TaskStepORM.status == "COMPLETED"
                )
            )
        )
        
        result = await self.session.execute(completed_count_stmt)
        completed_dependencies = result.scalars().all()
        
        return len(completed_dependencies) == len(task_orm.dependencies)
    
    async def save_task_result(self, task_result: TaskResult) -> bool:
        """
        Save complete RAHistory and update task status to COMPLETED.
        
        Args:
            task_result: Complete task execution result
            
        Returns:
            bool: True if saved successfully
            
        Go/No-Go Checkpoint: Client result reporting triggers proper audit workflow
        """
        try:
            # Find the task
            task_stmt = (
                select(TaskStepORM)
                .where(
                    and_(
                        TaskStepORM.workflow_id == task_result.workflow_id,
                        TaskStepORM.step_id == task_result.task_id
                    )
                )
                .with_for_update()
            )
            
            result = await self.session.execute(task_stmt)
            task_orm = result.scalar_one_or_none()
            
            if not task_orm:
                print(f"❌ Task not found: {task_result.task_id}")
                return False
            
            # Create result record
            result_orm = ResultORM(
                task_step_id=task_orm.id,
                iterations=[iter.model_dump() for iter in task_result.ra_history.iterations],
                final_result=task_result.ra_history.final_result,
                source_agent=task_result.ra_history.source_agent,
                client_id=task_result.ra_history.client_id,
                execution_time=task_result.ra_history.execution_time,
                created_at=task_result.completed_at
            )
            
            self.session.add(result_orm)
            
            # Update task status
            task_orm.status = "COMPLETED"
            task_orm.completed_at = task_result.completed_at
            
            # Store workflow_id and project_id before commit
            workflow_id = task_result.workflow_id
            
            # Get workflow to find project_id before commit
            workflow_stmt = (
                select(TaskGraphORM)
                .where(TaskGraphORM.workflow_id == workflow_id)
            )
            workflow_result = await self.session.execute(workflow_stmt)
            workflow_orm = workflow_result.scalar_one_or_none()
            project_id = workflow_orm.project_id if workflow_orm else None
            
            await self.session.commit()
            
            print(f"✅ Saved result for task {task_result.task_id}")
            
            # Update workflow status if all tasks are completed
            workflow_completed = await self.update_workflow_status_if_complete(workflow_id)
            
            # If workflow completed, check and update project status
            if workflow_completed and project_id:
                await self.update_project_status_if_complete(project_id)
            
            return True
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to save task result: {str(e)}")
            return False
    
    async def check_and_dispatch_ready_tasks(self, workflow_id: str) -> int:
        """
        Dependency resolution: find PENDING tasks whose dependencies are COMPLETED.
        
        Args:
            workflow_id: Workflow to check
            
        Returns:
            int: Number of tasks marked as READY
            
        Go/No-Go Checkpoint: Completed task correctly updates dependent task statuses
        """
        try:
            # Get all tasks for the workflow
            tasks_stmt = (
                select(TaskStepORM)
                .where(TaskStepORM.workflow_id == workflow_id)
                .with_for_update()
            )
            
            result = await self.session.execute(tasks_stmt)
            all_tasks = result.scalars().all()
            
            # Build completed tasks set
            completed_tasks = {
                task.step_id for task in all_tasks 
                if task.status == "COMPLETED"
            }
            
            # Find PENDING tasks that can be marked READY
            newly_ready = []
            for task in all_tasks:
                if task.status == "PENDING":
                    # Check if all dependencies are completed
                    if all(dep in completed_tasks for dep in task.dependencies):
                        task.status = "READY"
                        newly_ready.append(task.step_id)
            
            if newly_ready:
                await self.session.commit()
                print(f"🟢 Marked {len(newly_ready)} tasks as READY: {newly_ready}")
            
            return len(newly_ready)
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to dispatch ready tasks: {str(e)}")
            return 0
    
    async def is_workflow_complete(self, workflow_id: str) -> bool:
        """
        Check if all tasks in workflow are completed.
        
        Args:
            workflow_id: Workflow to check
            
        Returns:
            bool: True if all tasks are completed
        """
        try:
            # Count total tasks and completed tasks
            total_stmt = (
                select(TaskStepORM)
                .where(TaskStepORM.workflow_id == workflow_id)
            )
            
            completed_stmt = (
                select(TaskStepORM)
                .where(
                    and_(
                        TaskStepORM.workflow_id == workflow_id,
                        TaskStepORM.status == "COMPLETED"
                    )
                )
            )
            
            total_result = await self.session.execute(total_stmt)
            completed_result = await self.session.execute(completed_stmt)
            
            total_tasks = len(total_result.scalars().all())
            completed_tasks = len(completed_result.scalars().all())
            
            return total_tasks > 0 and total_tasks == completed_tasks
            
        except Exception as e:
            print(f"❌ Failed to check workflow completion: {str(e)}")
            return False
    
    async def update_workflow_status_if_complete(self, workflow_id: str) -> bool:
        """
        Update workflow status to COMPLETED if all tasks are completed.
        
        Args:
            workflow_id: Workflow to check and update
            
        Returns:
            bool: True if workflow was marked as completed
        """
        try:
            # Check if all tasks are completed
            is_complete = await self.is_workflow_complete(workflow_id)
            
            if not is_complete:
                return False
            
            # Update workflow status
            stmt = (
                select(TaskGraphORM)
                .where(TaskGraphORM.workflow_id == workflow_id)
                .with_for_update()
            )
            
            result = await self.session.execute(stmt)
            workflow_orm = result.scalar_one_or_none()
            
            if not workflow_orm:
                print(f"❌ Workflow not found: {workflow_id}")
                return False
            
            # Only update if not already completed
            if workflow_orm.status != "COMPLETED":
                workflow_orm.status = "COMPLETED"
                await self.session.commit()
                print(f"✅ Workflow {workflow_id} marked as COMPLETED")
                return True
            
            return False
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to update workflow status: {str(e)}")
            return False
    
    async def update_project_status_if_complete(self, project_id: UUID) -> bool:
        """
        Update project status to COMPLETED if all workflows are completed.
        
        Args:
            project_id: Project database ID to check and update
            
        Returns:
            bool: True if project was marked as completed
        """
        try:
            # Get project with all workflows
            stmt = (
                select(ProjectORM)
                .where(ProjectORM.id == project_id)
                .with_for_update()
            )
            
            result = await self.session.execute(stmt)
            project_orm = result.scalar_one_or_none()
            
            if not project_orm:
                print(f"❌ Project not found: {project_id}")
                return False
            
            # Check if all workflows are completed
            workflow_stmt = (
                select(TaskGraphORM)
                .where(TaskGraphORM.project_id == project_id)
            )
            
            workflow_result = await self.session.execute(workflow_stmt)
            workflows = workflow_result.scalars().all()
            
            if not workflows:
                return False
            
            all_completed = all(w.status == "COMPLETED" for w in workflows)
            
            if all_completed and project_orm.status != "COMPLETED":
                project_orm.status = "COMPLETED"
                await self.session.commit()
                print(f"✅ Project {project_orm.project_id} marked as COMPLETED")
                return True
            
            return False
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to update project status: {str(e)}")
            return False
    
    async def get_workflow_results(self, workflow_id: str) -> List[RAHistory]:
        """
        Get all task results for a completed workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            List[RAHistory]: All task execution results
        """
        try:
            # Query results with task information
            stmt = (
                select(ResultORM)
                .join(TaskStepORM)
                .where(TaskStepORM.workflow_id == workflow_id)
                .order_by(ResultORM.created_at)
            )
            
            result = await self.session.execute(stmt)
            result_orms = result.scalars().all()
            
            ra_histories = []
            for result_orm in result_orms:
                # Convert iterations back to ThoughtAction objects
                from agent_manager.core.models import ThoughtAction
                iterations = [
                    ThoughtAction.model_validate(iter_data)
                    for iter_data in result_orm.iterations
                ]
                
                ra_history = RAHistory(
                    iterations=iterations,
                    final_result=result_orm.final_result,
                    source_agent=result_orm.source_agent,
                    execution_time=result_orm.execution_time,
                    client_id=result_orm.client_id
                )
                ra_histories.append(ra_history)
            
            return ra_histories
            
        except Exception as e:
            print(f"❌ Failed to get workflow results: {str(e)}")
            return []
    
    async def save_audit_report(self, audit_report: AuditReport) -> bool:
        """
        Save audit report to database.
        
        Args:
            audit_report: Audit report to save
            
        Returns:
            bool: True if saved successfully
        """
        try:
            audit_orm = AuditReportORM(
                workflow_id=audit_report.workflow_id,
                is_successful=audit_report.is_successful,
                feedback=audit_report.feedback,
                rework_suggestions=audit_report.rework_suggestions,
                confidence_score=audit_report.confidence_score,
                reviewed_tasks=audit_report.reviewed_tasks,
                audit_criteria=audit_report.audit_criteria,
                created_at=audit_report.created_at
            )
            
            self.session.add(audit_orm)
            await self.session.commit()
            
            print(f"✅ Saved audit report for workflow {audit_report.workflow_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to save audit report: {str(e)}")
            return False
    
    async def reset_tasks_for_rework(
        self,
        workflow_id: str,
        rework_suggestions: List[str]
    ) -> bool:
        """
        Failed audit coordination: reset specific tasks to PENDING with rework notes.
        
        Args:
            workflow_id: Workflow to reset
            rework_suggestions: Specific rework guidance
            
        Returns:
            bool: True if reset successfully
            
        Go/No-Go Checkpoint: System demonstrates full Parallel → Audit → Rework → Synthesis cycle
        """
        try:
            # Reset all completed tasks to PENDING
            update_stmt = (
                update(TaskStepORM)
                .where(
                    and_(
                        TaskStepORM.workflow_id == workflow_id,
                        TaskStepORM.status == "COMPLETED"
                    )
                )
                .values(
                    status="PENDING",
                    client_id=None,
                    started_at=None,
                    completed_at=None
                )
            )
            
            await self.session.execute(update_stmt)
            
            # Mark initial tasks (no dependencies) as READY
            ready_stmt = (
                update(TaskStepORM)
                .where(
                    and_(
                        TaskStepORM.workflow_id == workflow_id,
                        TaskStepORM.dependencies == []
                    )
                )
                .values(status="READY")
            )
            
            await self.session.execute(ready_stmt)
            
            # Update workflow metadata with rework info
            workflow_update_stmt = (
                update(TaskGraphORM)
                .where(TaskGraphORM.workflow_id == workflow_id)
                .values(
                    workflow_metadata=TaskGraphORM.workflow_metadata.op('||')({
                        'rework_suggestions': rework_suggestions,
                        'rework_timestamp': datetime.utcnow().isoformat()
                    })
                )
            )
            
            await self.session.execute(workflow_update_stmt)
            await self.session.commit()
            
            print(f"🔄 Reset workflow {workflow_id} for rework")
            return True
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to reset tasks for rework: {str(e)}")
            return False
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive workflow status information.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Dict: Workflow status summary or None if not found
        """
        try:
            # Get task counts by status
            tasks_stmt = (
                select(TaskStepORM)
                .where(TaskStepORM.workflow_id == workflow_id)
            )
            
            result = await self.session.execute(tasks_stmt)
            tasks = result.scalars().all()
            
            if not tasks:
                return None
            
            status_counts = {}
            for task in tasks:
                status_counts[task.status] = status_counts.get(task.status, 0) + 1
            
            return {
                "workflow_id": workflow_id,
                "total_tasks": len(tasks),
                "status_counts": status_counts,
                "is_complete": status_counts.get("COMPLETED", 0) == len(tasks),
                "last_updated": max(task.updated_at for task in tasks) if tasks else None
            }
            
        except Exception as e:
            print(f"❌ Failed to get workflow status: {str(e)}")
            return None
    
    # File Access Coordination Methods
    
    async def acquire_file_lock(
        self,
        file_path: str,
        client_id: str,
        access_type: str = "read",
        task_step_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        timeout_minutes: int = 30
    ) -> bool:
        """
        Acquire database-tracked file lock for coordination.
        
        Args:
            file_path: Absolute path to file
            client_id: ID of client requesting lock
            access_type: Type of access ('read', 'write', 'exclusive')
            task_step_id: Associated task step
            workflow_id: Associated workflow
            timeout_minutes: Lock expiration timeout
            
        Returns:
            bool: True if lock acquired successfully
        """
        from agent_manager.orm import FileAccessORM
        from datetime import timedelta
        
        try:
            # Check for conflicting locks
            if not await self._can_acquire_file_lock(file_path, access_type):
                return False
            
            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes) if timeout_minutes > 0 else None
            
            # Create file access record
            file_access = FileAccessORM(
                file_path=file_path,
                client_id=client_id,
                task_step_id=task_step_id,
                workflow_id=workflow_id,
                access_type=access_type,
                expires_at=expires_at,
                is_active=True,
                metadata={"acquired_at": datetime.utcnow().isoformat()}
            )
            
            self.session.add(file_access)
            await self.session.commit()
            
            print(f"🔒 File lock acquired: {file_path} ({access_type}) by {client_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to acquire file lock for {file_path}: {str(e)}")
            return False
    
    async def release_file_lock(
        self,
        file_path: str,
        client_id: str,
        access_type: Optional[str] = None
    ) -> bool:
        """
        Release database-tracked file lock.
        
        Args:
            file_path: Path to file
            client_id: ID of client releasing lock
            access_type: Specific access type to release (None for all)
            
        Returns:
            bool: True if lock released successfully
        """
        from agent_manager.orm import FileAccessORM
        
        try:
            # Build query conditions
            conditions = [
                FileAccessORM.file_path == file_path,
                FileAccessORM.client_id == client_id,
                FileAccessORM.is_active == True
            ]
            
            if access_type:
                conditions.append(FileAccessORM.access_type == access_type)
            
            # Update active locks to inactive
            update_stmt = (
                update(FileAccessORM)
                .where(and_(*conditions))
                .values(is_active=False)
            )
            
            result = await self.session.execute(update_stmt)
            await self.session.commit()
            
            released_count = result.rowcount
            if released_count > 0:
                print(f"🔓 Released {released_count} file lock(s): {file_path} by {client_id}")
            
            return released_count > 0
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to release file lock for {file_path}: {str(e)}")
            return False
    
    async def _can_acquire_file_lock(self, file_path: str, access_type: str) -> bool:
        """
        Check if file lock can be acquired without conflicts.
        
        Lock compatibility matrix:
        - Multiple 'read' locks are allowed
        - 'write' locks are exclusive  
        - 'exclusive' locks block everything
        """
        from agent_manager.orm import FileAccessORM
        
        try:
            # Get active locks for this file
            active_locks_stmt = (
                select(FileAccessORM)
                .where(
                    and_(
                        FileAccessORM.file_path == file_path,
                        FileAccessORM.is_active == True,
                        or_(
                            FileAccessORM.expires_at.is_(None),
                            FileAccessORM.expires_at > datetime.utcnow()
                        )
                    )
                )
            )
            
            result = await self.session.execute(active_locks_stmt)
            existing_locks = result.scalars().all()
            
            for lock in existing_locks:
                existing_type = lock.access_type
                
                # Exclusive locks block everything
                if existing_type == 'exclusive' or access_type == 'exclusive':
                    return False
                
                # Write locks are exclusive
                if existing_type == 'write' or access_type == 'write':
                    return False
                
                # Multiple read locks are OK
                if existing_type == 'read' and access_type == 'read':
                    continue
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to check file lock availability: {str(e)}")
            return False
    
    async def get_file_locks(
        self, 
        file_path: Optional[str] = None,
        client_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get information about file locks.
        
        Args:
            file_path: Filter by specific file path
            client_id: Filter by specific client
            active_only: Only return active locks
            
        Returns:
            List of file lock information
        """
        from agent_manager.orm import FileAccessORM
        
        try:
            # Build query conditions
            conditions = []
            
            if file_path:
                conditions.append(FileAccessORM.file_path == file_path)
            
            if client_id:
                conditions.append(FileAccessORM.client_id == client_id)
            
            if active_only:
                conditions.append(FileAccessORM.is_active == True)
                conditions.append(
                    or_(
                        FileAccessORM.expires_at.is_(None),
                        FileAccessORM.expires_at > datetime.utcnow()
                    )
                )
            
            # Execute query
            if conditions:
                locks_stmt = select(FileAccessORM).where(and_(*conditions))
            else:
                locks_stmt = select(FileAccessORM)
            
            result = await self.session.execute(locks_stmt)
            locks = result.scalars().all()
            
            # Convert to dict format
            return [
                {
                    "file_path": lock.file_path,
                    "client_id": lock.client_id,
                    "access_type": lock.access_type,
                    "task_step_id": lock.task_step_id,
                    "workflow_id": lock.workflow_id,
                    "locked_at": lock.locked_at,
                    "expires_at": lock.expires_at,
                    "is_active": lock.is_active,
                    "metadata": lock.lock_metadata
                }
                for lock in locks
            ]
            
        except Exception as e:
            print(f"❌ Failed to get file locks: {str(e)}")
            return []
    
    async def cleanup_expired_file_locks(self) -> int:
        """
        Clean up expired file locks.
        
        Returns:
            int: Number of locks cleaned up
        """
        from agent_manager.orm import FileAccessORM
        
        try:
            # Mark expired locks as inactive
            update_stmt = (
                update(FileAccessORM)
                .where(
                    and_(
                        FileAccessORM.is_active == True,
                        FileAccessORM.expires_at <= datetime.utcnow()
                    )
                )
                .values(is_active=False)
            )
            
            result = await self.session.execute(update_stmt)
            await self.session.commit()
            
            cleaned_count = result.rowcount
            if cleaned_count > 0:
                print(f"🧹 Cleaned up {cleaned_count} expired file locks")
            
            return cleaned_count
            
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Failed to cleanup expired file locks: {str(e)}")
            return 0
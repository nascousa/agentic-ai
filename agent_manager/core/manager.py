"""
AgentManager for centralized workflow orchestration and coordination.

This module provides the core orchestration logic that coordinates
task planning, dependency resolution, audit workflows, and result
synthesis for the MCP server.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from agent_manager.core.models import (
    UserTaskRequest,
    TaskGraph,
    TaskStep,
    TaskStatus,
    RAHistory,
    AuditReport,
)
from agent_manager.core.llm_client import LLMClient, get_llm_client
from agent_manager.core.auditor import AuditorAgent


class AgentManager:
    """
    Central coordinator for multi-agent workflow orchestration.
    
    Manages task planning, dependency resolution, quality control,
    and result synthesis across distributed agent execution.
    
    Go/No-Go Checkpoint: Task submission results in persisted TaskGraph with initial tasks marked READY
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        auditor: Optional[AuditorAgent] = None
    ):
        """
        Initialize AgentManager.
        
        Args:
            llm_client: Optional LLM client (uses global if None)
            auditor: Optional auditor agent (creates default if None)
        """
        self._llm_client = llm_client
        self.auditor = auditor or AuditorAgent()
        
        # Agent role capabilities for task assignment
        self.agent_capabilities = {
            "researcher": ["research", "information gathering", "fact checking", "analysis"],
            "writer": ["writing", "content creation", "editing", "documentation"],
            "analyst": ["analysis", "evaluation", "data processing", "insights"],
            "planner": ["planning", "strategy", "organization", "coordination"],
            "reviewer": ["review", "quality control", "validation", "feedback"]
        }
    
    async def get_llm_client(self) -> LLMClient:
        """Get LLM client instance."""
        if self._llm_client is None:
            return await get_llm_client()
        return self._llm_client
    
    def get_planning_prompt(self) -> str:
        """
        Get system prompt for task planning and dependency analysis.
        
        Returns:
            str: Complete system prompt for workflow planning
        """
        capabilities_text = "\n".join([
            f"- {role}: {', '.join(caps)}" 
            for role, caps in self.agent_capabilities.items()
        ])
        
        return f"""
You are an expert workflow planner in a multi-agent coordination system.

Your role is to break down complex user requests into executable tasks with proper dependencies and agent assignments.

AVAILABLE AGENT TYPES AND CAPABILITIES:
{capabilities_text}

PLANNING PRINCIPLES:
1. Break complex requests into manageable, specific tasks
2. Identify dependencies between tasks (some tasks must complete before others can start)
3. Assign appropriate agent types based on task requirements
4. Ensure logical flow and proper sequencing
5. Create clear, actionable task descriptions
6. Consider parallel execution opportunities

DEPENDENCY RULES:
- Research tasks often come first to gather information
- Analysis tasks depend on research or data gathering
- Writing tasks depend on research and analysis
- Review tasks come last to validate work
- Planning tasks help coordinate complex workflows

TASK ASSIGNMENT GUIDELINES:
- Use "researcher" for information gathering, fact checking, research
- Use "writer" for content creation, documentation, editing
- use "analyst" for data analysis, evaluation, insights generation
- Use "planner" for breaking down complex work, coordination
- Use "reviewer" for quality control, validation, final checks

RESPONSE FORMAT:
You must respond with valid JSON matching this TaskGraph schema:
{{
  "workflow_id": "unique_identifier",
  "tasks": [
    {{
      "step_id": "unique_step_id",
      "workflow_id": "same_as_above",
      "task_description": "Clear, specific task description",
      "assigned_agent": "agent_type",
      "dependencies": ["list_of_step_ids_that_must_complete_first"],
      "status": "PENDING"
    }}
  ],
  "created_at": "ISO_timestamp",
  "metadata": {{
    "complexity": "low|medium|high",
    "estimated_duration": "time_estimate",
    "priority": "normal|high|urgent"
  }}
}}

IMPORTANT:
- Each task should be specific and actionable
- Dependencies must reference valid step_ids from other tasks
- Tasks with no dependencies can start immediately (will be marked READY)
- Use clear, descriptive step_ids (e.g., "research_market_analysis", "write_executive_summary")
- Ensure proper logical flow from research → analysis → creation → review
"""
    
    async def plan_and_save_task(self, user_request: str, metadata: Optional[Dict] = None, db_service=None) -> str:
        """
        Create TaskGraph with dependencies and persist to database.
        
        Analyzes the user request, creates a structured workflow with
        dependencies, and generates the complete task execution plan.
        
        Args:
            user_request: Original user request for planning
            metadata: Optional additional metadata
            db_service: DatabaseService instance for persistence
            
        Returns:
            str: Workflow ID of the saved TaskGraph
            
        Go/No-Go Checkpoint: Creates TaskGraph and persists to database
        """
        print(f"📋 Planning workflow for request: {user_request[:100]}...")
        
        llm_client = await self.get_llm_client()
        system_prompt = self.get_planning_prompt()
        
        # Prepare planning input
        planning_input = self._prepare_planning_input(user_request, metadata)
        
        try:
            # Generate task plan
            task_graph = await llm_client.run_prompt_for_json(
                system_prompt=system_prompt,
                user_input=planning_input,
                json_schema=TaskGraph
            )
            
            # Ensure workflow_id is set and consistent
            if not task_graph.workflow_id:
                task_graph.workflow_id = str(uuid4())
            
            # Update all tasks with consistent workflow_id and defaults
            for task in task_graph.tasks:
                task.workflow_id = task_graph.workflow_id
                task.status = TaskStatus.PENDING
                task.created_at = datetime.utcnow()
            
            # Validate dependencies
            self._validate_dependencies(task_graph)
            
            # Mark initial tasks (no dependencies) as READY
            self._mark_initial_tasks_ready(task_graph)
            
            # Add metadata to task graph
            if not task_graph.metadata:
                task_graph.metadata = {}
            task_graph.metadata.update(metadata or {})
            task_graph.metadata["user_request"] = user_request
            
            print(f"  ✅ Created workflow {task_graph.workflow_id} with {len(task_graph.tasks)} tasks")
            print(f"  🟢 {self._count_ready_tasks(task_graph)} tasks ready to start")
            
            # Persist to database if db_service provided
            if db_service:
                workflow_id = await db_service.save_task_graph(task_graph)
                print(f"  💾 Persisted workflow to database: {workflow_id}")
                return workflow_id
            else:
                print("  ⚠️ No db_service provided, workflow not persisted")
                return task_graph.workflow_id
            
        except Exception as e:
            print(f"  ❌ Planning failed: {str(e)}")
            # Create fallback single-task workflow
            fallback_graph = self._create_fallback_workflow(user_request, metadata)
            
            # Persist fallback workflow to database if db_service provided
            if db_service:
                workflow_id = await db_service.save_task_graph(fallback_graph)
                print(f"  💾 Persisted fallback workflow to database: {workflow_id}")
                return workflow_id
            else:
                print("  ⚠️ No db_service provided, fallback workflow not persisted")
                return fallback_graph.workflow_id
    
    def _prepare_planning_input(self, user_request: str, metadata: Optional[Dict]) -> str:
        """Prepare comprehensive input for task planning."""
        input_parts = [
            f"USER REQUEST: {user_request}",
            "",
            "Please analyze this request and create a comprehensive workflow plan."
        ]
        
        if metadata:
            input_parts.extend([
                "",
                "ADDITIONAL CONTEXT:",
                json.dumps(metadata, indent=2)
            ])
        
        input_parts.extend([
            "",
            "PLANNING CONSIDERATIONS:",
            "- What information needs to be gathered first?",
            "- What analysis or processing is required?",
            "- What deliverables need to be created?",
            "- How should the work be sequenced for optimal results?",
            "- Which agent types are best suited for each task?",
            "",
            "Create a detailed workflow plan with proper task dependencies."
        ])
        
        return "\n".join(input_parts)
    
    def _validate_dependencies(self, task_graph: TaskGraph) -> None:
        """Validate that all task dependencies reference valid step_ids."""
        step_ids = {task.step_id for task in task_graph.tasks}
        
        for task in task_graph.tasks:
            for dep in task.dependencies:
                if dep not in step_ids:
                    raise ValueError(f"Task {task.step_id} has invalid dependency: {dep}")
    
    def _mark_initial_tasks_ready(self, task_graph: TaskGraph) -> None:
        """Mark tasks with no dependencies as READY."""
        for task in task_graph.tasks:
            if not task.dependencies:
                task.status = TaskStatus.READY
    
    def _count_ready_tasks(self, task_graph: TaskGraph) -> int:
        """Count tasks that are currently READY."""
        return sum(1 for task in task_graph.tasks if task.status == TaskStatus.READY)
    
    def _create_fallback_workflow(self, user_request: str, metadata: Optional[Dict]) -> TaskGraph:
        """Create a simple fallback workflow when planning fails."""
        workflow_id = str(uuid4())
        
        fallback_task = TaskStep(
            step_id="fallback_task",
            workflow_id=workflow_id,
            task_description=f"Complete the user request: {user_request}",
            assigned_agent="analyst",  # Generic agent type
            dependencies=[],
            status=TaskStatus.READY,
            created_at=datetime.utcnow()
        )
        
        return TaskGraph(
            workflow_id=workflow_id,
            tasks=[fallback_task],
            created_at=datetime.utcnow(),
            metadata=metadata or {"fallback": True}
        )
    
    async def check_and_dispatch_ready_tasks(self, workflow_id: str, db_service=None) -> int:
        """
        Identify and mark tasks that are ready for execution.
        
        Analyzes task dependencies and marks tasks as READY when
        all their dependencies are COMPLETED. Uses DatabaseService for persistence.
        
        Args:
            workflow_id: Workflow identifier
            db_service: DatabaseService instance for persistence
            
        Returns:
            int: Number of tasks that were newly marked as READY
            
        Go/No-Go Checkpoint: Completed task correctly updates dependent task statuses
        """
        if not db_service:
            print("⚠️ No db_service provided for task dispatch")
            return 0
        
        return await db_service.check_and_dispatch_ready_tasks(workflow_id)
    
    async def check_workflow_completion(self, workflow_id: str, db_service=None) -> bool:
        """
        Check if all tasks in the workflow are completed.
        
        Args:
            workflow_id: Workflow identifier
            db_service: DatabaseService instance
            
        Returns:
            bool: True if all tasks are completed
        """
        if not db_service:
            return False
        
        return await db_service.is_workflow_complete(workflow_id)
    
    async def trigger_audit(self, workflow_id: str, db_service=None) -> AuditReport:
        """
        Trigger quality audit for completed workflow.
        
        Args:
            workflow_id: Workflow identifier
            db_service: DatabaseService instance for retrieving results and persistence
            
        Returns:
            AuditReport: Quality assessment results
            
        Go/No-Go Checkpoint: Failed audit updates DB and resets tasks for rework
        """
        print(f"🔍 Triggering audit for workflow: {workflow_id}")
        
        try:
            if not db_service:
                raise ValueError("DatabaseService required for audit operations")
            
            # Get all task results for the workflow
            task_results = await db_service.get_workflow_results(workflow_id)
            
            if not task_results:
                raise ValueError(f"No task results found for workflow {workflow_id}")
            
            # Run the audit
            audit_report = await self.auditor.run_audit(workflow_id, task_results)
            
            # Save audit report to database
            await db_service.save_audit_report(audit_report)
            
            if audit_report.is_successful:
                print(f"  ✅ Audit PASSED - Workflow approved")
            else:
                print(f"  ❌ Audit FAILED - {len(audit_report.rework_suggestions)} rework items")
                for i, suggestion in enumerate(audit_report.rework_suggestions, 1):
                    print(f"    {i}. {suggestion}")
                
                # Reset tasks for rework
                await db_service.reset_tasks_for_rework(
                    workflow_id=workflow_id,
                    rework_suggestions=audit_report.rework_suggestions
                )
                print(f"  🔄 Workflow reset for rework")
            
            return audit_report
            
        except Exception as e:
            print(f"  ❌ Audit error: {str(e)}")
            # Return failed audit
            audit_report = AuditReport(
                workflow_id=workflow_id,
                is_successful=False,
                feedback=f"Audit failed due to error: {str(e)}",
                rework_suggestions=["Review audit system configuration"],
                confidence_score=0.0,
                reviewed_tasks=[],
                audit_criteria=[]
            )
            
            # Try to save the failed audit report
            if db_service:
                try:
                    await db_service.save_audit_report(audit_report)
                except Exception as save_error:
                    print(f"  ❌ Failed to save audit report: {save_error}")
            
            return audit_report
    
    async def synthesize_results(self, workflow_id: str, task_results: List[RAHistory]) -> str:
        """
        Synthesize all task results into final consolidated response.
        
        Args:
            workflow_id: Workflow identifier
            task_results: All completed task results
            
        Returns:
            str: Final consolidated response
        """
        print(f"🔧 Synthesizing results for workflow: {workflow_id}")
        
        if not task_results:
            return f"Workflow {workflow_id} completed but no results to synthesize."
        
        llm_client = await self.get_llm_client()
        
        synthesis_prompt = f"""
You are synthesizing the final deliverable for a completed multi-agent workflow.

WORKFLOW ID: {workflow_id}
TOTAL TASKS: {len(task_results)}

TASK RESULTS TO SYNTHESIZE:
"""
        
        for i, result in enumerate(task_results, 1):
            synthesis_prompt += f"""
TASK {i} ({result.source_agent}):
{result.final_result}

---
"""
        
        synthesis_prompt += """
Please create a comprehensive, well-organized final response that:
1. Integrates all task results coherently
2. Addresses the original user request completely
3. Presents information in a logical, professional format
4. Highlights key insights and recommendations
5. Provides clear, actionable conclusions

The response should be polished, complete, and ready for delivery to the end user.
"""
        
        try:
            final_response = await llm_client.run_simple_prompt(synthesis_prompt)
            print(f"  ✅ Synthesis completed ({len(final_response)} characters)")
            return final_response
            
        except Exception as e:
            print(f"  ❌ Synthesis error: {str(e)}")
            # Fallback to simple concatenation
            return self._fallback_synthesis(workflow_id, task_results)
    
    def _fallback_synthesis(self, workflow_id: str, task_results: List[RAHistory]) -> str:
        """Fallback synthesis when LLM synthesis fails."""
        parts = [
            f"Workflow {workflow_id} Results Summary",
            "=" * 50,
            ""
        ]
        
        for i, result in enumerate(task_results, 1):
            parts.extend([
                f"Task {i} ({result.source_agent}):",
                result.final_result,
                ""
            ])
        
        return "\n".join(parts)
    
    async def handle_audit_failure(
        self,
        task_graph: TaskGraph,
        audit_report: AuditReport
    ) -> TaskGraph:
        """
        Handle audit failure by resetting tasks for rework.
        
        Args:
            task_graph: Current workflow state
            audit_report: Failed audit report with suggestions
            
        Returns:
            TaskGraph: Updated workflow with tasks reset for rework
        """
        print(f"🔄 Handling audit failure for workflow: {task_graph.workflow_id}")
        
        # Reset all completed tasks to PENDING for rework
        rework_count = 0
        for task in task_graph.tasks:
            if task.status == TaskStatus.COMPLETED:
                task.status = TaskStatus.PENDING
                task.client_id = None
                task.started_at = None
                task.completed_at = None
                rework_count += 1
        
        # Mark initial tasks as READY again
        self._mark_initial_tasks_ready(task_graph)
        
        # Update metadata with rework information
        task_graph.metadata["audit_failure"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "feedback": audit_report.feedback,
            "suggestions": audit_report.rework_suggestions,
            "rework_count": rework_count
        }
        
        print(f"  🔄 Reset {rework_count} tasks for rework")
        print(f"  🟢 {self._count_ready_tasks(task_graph)} tasks ready to restart")
        
        return task_graph
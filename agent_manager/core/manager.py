"""
AgentManager for centralized workflow orchestration and coordination.

This module provides the core orchestration logic that coordinates
task planning, dependency resolution, audit workflows, and result
synthesis for the MCP server.
"""

import json
import os
from datetime import datetime
from pathlib import Path
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
        auditor: Optional[AuditorAgent] = None,
        base_project_dir: str = "./projects"
    ):
        """
        Initialize AgentManager.
        
        Args:
            llm_client: Optional LLM client (uses global if None)
            auditor: Optional auditor agent (creates default if None)
            base_project_dir: Base directory for project folders (default: ./projects)
        """
        self._llm_client = llm_client
        self.auditor = auditor or AuditorAgent()
        self.base_project_dir = Path(base_project_dir)
        
        # Ensure base project directory exists
        self.base_project_dir.mkdir(parents=True, exist_ok=True)
        
        # Agent role capabilities for task assignment
        # IMPORTANT: These MUST match the workers defined in docker-compose.yml
        self.agent_capabilities = {
            "researcher": ["research", "information gathering", "fact checking", "data collection"],
            "writer": ["writing", "content creation", "editing", "documentation"],
            "analyst": ["analysis", "evaluation", "data processing", "insights", "review", "quality control"],
            "developer": ["software development", "coding", "implementation", "programming"],
            "tester": ["testing", "quality assurance", "validation", "debugging"],
            "architect": ["system design", "architecture", "technical planning", "infrastructure", "planning", "strategy"]
        }
    
    def get_today_project_folder(self, project_id: str, project_name: Optional[str] = None) -> Path:
        """
        Get or create project folder with projectid_projectname naming.
        
        Args:
            project_id: Project ID (e.g., PID000001)
            project_name: Optional project name. If None, uses "Untitled".
                         Spaces will be replaced with underscores.
            
        Returns:
            Path: Path to project folder in format projects/PID000001_ProjectName
        """
        if project_name:
            # Replace spaces with underscores for consistent naming
            sanitized_name = project_name.replace(" ", "_")
            folder_name = f"{project_id}_{sanitized_name}"
        else:
            folder_name = f"{project_id}_Untitled"
            
        project_folder = self.base_project_dir / folder_name
        project_folder.mkdir(parents=True, exist_ok=True)
        
        # Create standard project structure
        (project_folder / "src").mkdir(exist_ok=True)
        (project_folder / "tests").mkdir(exist_ok=True)
        
        return project_folder
    
    def save_workflow_request(
        self,
        workflow_id: str,
        user_request: str,
        metadata: Optional[Dict] = None,
        project_name: Optional[str] = None
    ) -> Path:
        """
        Save the original workflow request to the project folder.
        
        Args:
            workflow_id: Workflow identifier
            user_request: Original user request
            metadata: Request metadata
            project_name: Optional project name for folder structure
            
        Returns:
            Path: Path to the saved request file
        """
        project_folder = self.get_today_project_folder(project_name or workflow_id)
        
        # Sanitize project name for filename
        sanitized_name = (project_name or workflow_id).replace(" ", "_")
        
        # Save request as JSON in project root
        request_file = project_folder / f"{sanitized_name}_request.json"
        request_data = {
            "user_request": user_request,
            "metadata": metadata or {},
            "workflow_id": workflow_id,
            "submitted_at": datetime.now().isoformat()
        }
        request_file.write_text(json.dumps(request_data, indent=2), encoding="utf-8")
        
        print(f"[SAVED] Workflow request to: {request_file}")
        return request_file
    
    def save_workflow_results(
        self, 
        workflow_id: str, 
        results: List[RAHistory], 
        final_output: str,
        project_name: Optional[str] = None,
        user_request: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Path:
        """
        Save all workflow results to today's project folder.
        
        Args:
            workflow_id: Workflow identifier
            results: List of task results
            final_output: Final synthesized output
            project_name: Optional project name for folder structure
            user_request: Optional original user request to save
            metadata: Optional request metadata
            
        Returns:
            Path: Path to the saved project folder
        """
        project_folder = self.get_today_project_folder(workflow_id, project_name or workflow_id)
        
        # Save the original request if provided
        if user_request:
            self.save_workflow_request(
                workflow_id=workflow_id,
                user_request=user_request,
                metadata=metadata,
                project_name=project_name
            )
        
        # Save final output
        final_output_file = project_folder / "FINAL_OUTPUT.md"
        final_output_file.write_text(final_output, encoding="utf-8")
        
        # Save individual task results to src/ folder
        results_folder = project_folder / "src"
        results_folder.mkdir(exist_ok=True)
        
        for i, result in enumerate(results, 1):
            result_file = results_folder / f"task_{i}_{result.source_agent}.md"
            
            content = f"""# Task Result: {result.source_agent}

## Execution Time
{result.execution_time:.2f} seconds

## Reasoning & Actions
"""
            for j, iteration in enumerate(result.iterations, 1):
                content += f"\n### Iteration {j}\n"
                content += f"**Thought:** {iteration.thought}\n\n"
                content += f"**Action:** {iteration.action}\n\n"
                content += f"**Observation:** {iteration.observation}\n\n"
            
            content += f"\n## Final Result\n\n{result.final_result}\n"
            
            result_file.write_text(content, encoding="utf-8")
        
        # Save workflow summary
        summary_file = project_folder / "workflow_summary.json"
        summary_data = {
            "workflow_id": workflow_id,
            "created_at": datetime.now().isoformat(),
            "total_tasks": len(results),
            "total_execution_time": sum(r.execution_time for r in results),
            "agents_used": list(set(r.source_agent for r in results)),
            "task_count_by_agent": {
                agent: sum(1 for r in results if r.source_agent == agent)
                for agent in set(r.source_agent for r in results)
            }
        }
        summary_file.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
        
        print(f"📁 Saved workflow results to: {project_folder}")
        return project_folder
    
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
- Use "researcher" for gathering requirements, specifications, defining project needs
- Use "writer" for creating documentation, README files, user guides
- Use "analyst" for code review, quality assurance, final validation, testing analysis
- Use "developer" for implementing source code, writing actual program files
- Use "tester" for creating test suites, test cases, quality assurance testing
- Use "architect" for system design, planning project structure, technical architecture

CRITICAL: You MUST ONLY use these 6 agent types. DO NOT invent new agent types.
For review/quality control tasks, use "analyst". For planning/coordination, use "architect".

PROJECT DELIVERABLES - PRODUCTION-READY OUTPUT:
Each workflow creates a COMPLETE, READY-TO-USE project in: projects/PID000001_ProjectName/

Agents will create these files based on their roles:
- researcher → REQUIREMENTS.md (detailed specifications)
- architect → DESIGN.md, PROJECT_STRUCTURE.txt (architecture, file organization)
- developer → Complete source code files (e.g., calculator.py, app.py, main.py, __init__.py, requirements.txt)
- tester → Complete test suites in tests/ folder (e.g., test_calculator.py with pytest tests)
- writer → README.md (installation, usage, examples)
- analyst → ANALYSIS.md (quality review, recommendations)

CRITICAL INSTRUCTIONS FOR TASK DESCRIPTIONS:
When creating task descriptions, be EXPLICIT about deliverables:
- For developers: "Implement calculator.py with Calculator class containing add, subtract, multiply, divide methods. Include type hints, docstrings, and error handling."
- For testers: "Create test_calculator.py with pytest test cases for all Calculator methods, including edge cases and error conditions."
- For writers: "Create README.md with project description, installation steps, usage examples with code snippets, and requirements."

The final project folder should be immediately usable - someone should be able to clone it and run it.

RESPONSE FORMAT:
You must respond with valid JSON matching this TaskGraph schema:
{{
  "workflow_id": "unique_identifier",
  "workflow_name": "AI-generated concise workflow name (3-6 words)",
  "tasks": [
    {{
      "step_id": "unique_step_id",
      "workflow_id": "same_as_above",
      "task_name": "AI-generated concise task name (2-5 words)",
      "task_description": "Clear, specific task description",
      "assigned_agent": "agent_type",
      "dependencies": ["list_of_step_ids_that_must_complete_first"],
      "status": "PENDING"
    }}
  ],
  "metadata": {{
    "complexity": "low|medium|high",
    "estimated_duration": "time_estimate",
    "priority": "normal|high|urgent",
    "project_name": "optional_project_name"
  }}
}}

IMPORTANT:
- Each task should be specific and actionable
- Dependencies must reference valid step_ids from other tasks
- Tasks with no dependencies can start immediately (will be marked READY)
- Use clear, descriptive step_ids (e.g., "research_market_analysis", "write_executive_summary")
- Ensure proper logical flow from research → analysis → creation → review
- Do NOT include created_at field - it will be set automatically
- Note: step_id and workflow_id will be automatically reformatted to custom format (TID12345678, WID123456)

NAMING REQUIREMENTS:
- Generate a concise, descriptive workflow_name (3-6 words) that captures the essence of the request
- Generate a concise task_name (2-5 words) for each task that summarizes what it does
- Examples:
  * Workflow: "Build Todo List Application" → task_name: "Design Database Schema", "Implement API Endpoints"
  * Workflow: "Market Analysis Report" → task_name: "Research Competitors", "Analyze Market Trends"
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
        print(f"[PLANNING] Workflow for request: {user_request[:100]}...")
        
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
            
            # Generate sequential IDs via database service
            # Workflow ID will be assigned by db_service during save
            # Task IDs will be assigned during save as well
            # Keep placeholder IDs for now
            
            # Set workflow name from metadata or generate from user request
            if not task_graph.workflow_name or task_graph.workflow_name == "Untitled Workflow":
                if metadata and metadata.get("workflow_name"):
                    task_graph.workflow_name = metadata.get("workflow_name")
                else:
                    # Generate a descriptive name from the user request (first 50 chars)
                    task_graph.workflow_name = user_request[:50] + ("..." if len(user_request) > 50 else "")
            
            # Determine project name from metadata or workflow name
            project_name = None
            if metadata and metadata.get("project_name"):
                project_name = metadata.get("project_name")
            elif task_graph.workflow_name and task_graph.workflow_name != "Untitled Workflow":
                project_name = task_graph.workflow_name
            else:
                # Use truncated user request as fallback
                project_name = user_request[:50] + ("..." if len(user_request) > 50 else "")
            
            # Placeholder - will be updated after DB save assigns real workflow_id
            project_folder = None
            project_path_str = None
            
            # Update all tasks with consistent workflow_id and project_path
            # Task IDs will be assigned sequentially during database save
            for task in task_graph.tasks:
                task.workflow_id = task_graph.workflow_id
                task.status = TaskStatus.PENDING
                task.created_at = datetime.utcnow()
                task.project_path = project_path_str
            
            # Validate dependencies
            self._validate_dependencies(task_graph)
            
            # Validate agent assignments and auto-correct invalid ones
            self._validate_agent_assignments(task_graph)
            
            # Mark initial tasks (no dependencies) as READY
            self._mark_initial_tasks_ready(task_graph)
            
            # Add metadata to task graph
            if not task_graph.metadata:
                task_graph.metadata = {}
            task_graph.metadata.update(metadata or {})
            task_graph.metadata["user_request"] = user_request
            
            print(f"  [CREATED] Workflow {task_graph.workflow_id} with {len(task_graph.tasks)} tasks")
            print(f"  [READY] {self._count_ready_tasks(task_graph)} tasks ready to start")
            
            # Persist to database if db_service provided
            if db_service:
                # First, create or get the project to get its PID and internal UUID
                project_id, project_uuid = await db_service.create_project(project_name)
                print(f"  [PROJECT] Project ID: {project_id}")
                
                # Save task graph with project UUID (for foreign key)
                workflow_id = await db_service.save_task_graph(task_graph, project_uuid)
                print(f"  [SAVED] Persisted workflow to database: {workflow_id}")
                
                # Now create project folder using PID
                project_folder = self.get_today_project_folder(project_id, project_name)
                project_path_str = str(project_folder.absolute())
                print(f"  [PROJECT] Created folder: {project_path_str}")
                
                # Update all tasks with project_path
                await db_service.update_tasks_project_path(workflow_id, project_path_str)
                
                # Save request JSON to project folder
                project_name = metadata.get("project_name") if metadata else None
                if project_name:
                    try:
                        self.save_workflow_request(
                            workflow_id=workflow_id,
                            user_request=user_request,
                            metadata=metadata,
                            project_name=project_name
                        )
                        print(f"  [SAVED] Request JSON to project folder: {project_name}")
                    except Exception as e:
                        print(f"  [WARNING] Failed to save request JSON: {str(e)}")
                
                return workflow_id
            else:
                print("  [WARNING] No db_service provided, workflow not persisted")
                return task_graph.workflow_id
            
        except Exception as e:
            print(f"  [ERROR] Planning failed: {str(e)}")
            # Create fallback single-task workflow
            fallback_graph = self._create_fallback_workflow(user_request, metadata)
            
            # Persist fallback workflow to database if db_service provided
            if db_service:
                workflow_id = await db_service.save_task_graph(fallback_graph)
                print(f"  [SAVED] Persisted fallback workflow to database: {workflow_id}")
                
                # Save request JSON to project folder
                project_name = metadata.get("project_name") if metadata else None
                if project_name:
                    try:
                        self.save_workflow_request(
                            workflow_id=workflow_id,
                            user_request=user_request,
                            metadata=metadata,
                            project_name=project_name
                        )
                        print(f"  [SAVED] Request JSON to project folder: {project_name}")
                    except Exception as e:
                        print(f"  [WARNING] Failed to save request JSON: {str(e)}")
                
                return workflow_id
            else:
                print("  [WARNING] No db_service provided, fallback workflow not persisted")
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
    
    def _validate_agent_assignments(self, task_graph: TaskGraph) -> None:
        """
        Validate that all tasks are assigned to valid agent roles.
        Auto-corrects invalid assignments to prevent tasks from getting stuck.
        """
        valid_agents = set(self.agent_capabilities.keys())
        
        for task in task_graph.tasks:
            if task.assigned_agent not in valid_agents:
                old_agent = task.assigned_agent
                # Map common invalid agents to valid ones
                agent_mapping = {
                    "reviewer": "analyst",  # Review tasks → analyst
                    "planner": "architect",  # Planning tasks → architect
                    "coordinator": "architect",
                    "manager": "architect",
                }
                
                new_agent = agent_mapping.get(old_agent, "analyst")  # Default to analyst
                print(f"  [WARNING] Invalid agent '{old_agent}' for task {task.step_id}, auto-corrected to '{new_agent}'")
                task.assigned_agent = new_agent
    
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
        # Placeholder IDs - will be replaced during database save
        workflow_id = "WID_PENDING"
        
        # Generate workflow name from metadata or user request
        if metadata and metadata.get("workflow_name"):
            workflow_name = metadata.get("workflow_name")
        else:
            workflow_name = user_request[:50] + ("..." if len(user_request) > 50 else "")
        
        fallback_task = TaskStep(
            step_id="TID_PENDING",
            workflow_id=workflow_id,
            task_description=f"Complete the user request: {user_request}",
            assigned_agent="analyst",  # Generic agent type
            dependencies=[],
            status=TaskStatus.READY,
            created_at=datetime.utcnow()
        )
        
        return TaskGraph(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
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
            print("[WARNING] No db_service provided for task dispatch")
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
        print(f"[AUDIT] Triggering audit for workflow: {workflow_id}")
        
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
                print(f"  [PASSED] Audit PASSED - Workflow approved")
            else:
                print(f"  [FAILED] Audit FAILED - {len(audit_report.rework_suggestions)} rework items")
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
            print(f"  [ERROR] Audit error: {str(e)}")
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
                    print(f"  [ERROR] Failed to save audit report: {save_error}")
            
            return audit_report
    
    async def synthesize_results(
        self, 
        workflow_id: str, 
        task_results: List[RAHistory],
        project_name: Optional[str] = None,
        save_to_disk: bool = True
    ) -> str:
        """
        Synthesize all task results into final consolidated response.
        
        Args:
            workflow_id: Workflow identifier
            task_results: All completed task results
            project_name: Optional project name for folder structure
            save_to_disk: Whether to save results to today's project folder
            
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
            print(f"  [COMPLETE] Synthesis completed ({len(final_response)} characters)")
            
            # Save results to today's project folder
            if save_to_disk:
                project_folder = self.save_workflow_results(
                    workflow_id=workflow_id,
                    results=task_results,
                    final_output=final_response,
                    project_name=project_name
                )
                print(f"  [SAVED] Results saved to: {project_folder}")
            
            return final_response
            
        except Exception as e:
            print(f"  [ERROR] Synthesis error: {str(e)}")
            # Fallback to simple concatenation
            fallback_result = self._fallback_synthesis(workflow_id, task_results)
            
            # Save fallback results too
            if save_to_disk:
                project_folder = self.save_workflow_results(
                    workflow_id=workflow_id,
                    results=task_results,
                    final_output=fallback_result,
                    project_name=project_name
                )
                print(f"  📁 Fallback results saved to: {project_folder}")
            
            return fallback_result
    
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
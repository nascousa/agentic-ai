"""
Pydantic models for MCP Server API communication.

This module defines all data structures used for communication between
the FastAPI server and external worker clients, following the configuration
contract specified in the CCS documentation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task execution status for workflow coordination."""
    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ThoughtAction(BaseModel):
    """
    Single iteration in the Reasoning-Acting (RA) pattern.
    
    Represents one cycle of agent reasoning followed by action decision.
    Used to track the complete thinking process of worker agents.
    """
    thought: str = Field(..., description="Agent's reasoning about the current situation")
    action: str = Field(..., description="Specific action the agent decides to take")
    observation: Optional[str] = Field(None, description="Results or feedback from the action")
    iteration_number: int = Field(..., description="Sequential number of this RA iteration")


class TaskStep(BaseModel):
    """
    Individual task within a workflow with dependency tracking.
    
    Core data structure for task coordination between server and clients.
    Contains all information needed for client execution and dependency resolution.
    """
    step_id: str = Field(..., description="Unique identifier for dependency tracking")
    workflow_id: str = Field(..., description="Reference to parent TaskGraph")
    task_description: str = Field(..., description="Detailed task description for execution")
    assigned_agent: str = Field(..., description="Agent type responsible for execution")
    dependencies: List[str] = Field(default_factory=list, description="List of step_ids that must complete first")
    
    # File access coordination
    file_dependencies: List[str] = Field(
        default_factory=list, 
        description="List of file paths this task will access"
    )
    file_access_types: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of file paths to access types ('read', 'write', 'exclusive')"
    )
    
    # Execution tracking
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current execution status")
    client_id: Optional[str] = Field(None, description="ID of client currently executing task")
    started_at: Optional[datetime] = Field(None, description="Task execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task execution completion timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation timestamp")


class TaskGraph(BaseModel):
    """
    Complete workflow representation with task dependencies.
    
    Represents the planned workflow structure created by the AgentManager
    during the planning phase. Contains all tasks and their relationships.
    """
    workflow_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique workflow identifier")
    tasks: List[TaskStep] = Field(..., description="Complete task dependency graph")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Workflow creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional workflow information")


class UserTaskRequest(BaseModel):
    """
    External client task submission format.
    
    Input model for the POST /v1/tasks endpoint.
    Contains the user's request and optional metadata for processing.
    """
    user_request: str = Field(..., description="Original user request for planning")
    complexity: str = Field(default="medium", description="Expected task complexity level")
    deadline: Optional[datetime] = Field(None, description="Optional deadline for task completion")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional request context")


class TaskGraphResponse(BaseModel):
    """
    Server response for task submission.
    
    Output model for the POST /v1/tasks endpoint.
    Returns the created workflow with all planned tasks.
    """
    workflow_id: str = Field(..., description="Unique workflow identifier for tracking")
    tasks: List[TaskStep] = Field(..., description="Complete task dependency graph")
    created_at: datetime = Field(..., description="Workflow creation timestamp")
    total_tasks: int = Field(..., description="Total number of tasks in the workflow")


class RAHistory(BaseModel):
    """
    Complete Reasoning-Acting execution history.
    
    Contains the full execution trace from a worker agent,
    including all RA iterations and the final result.
    """
    iterations: List[ThoughtAction] = Field(..., description="Complete reasoning history")
    final_result: str = Field(..., description="Final task output after all iterations")
    source_agent: str = Field(..., description="Agent type that produced the result")
    execution_time: float = Field(..., description="Total task execution duration in seconds")
    client_id: str = Field(..., description="ID of client that executed the task")


class TaskResult(BaseModel):
    """
    Task completion report from external clients.
    
    Input model for the POST /v1/results endpoint.
    Contains complete execution details and results.
    """
    workflow_id: str = Field(..., description="Reference to parent workflow")
    task_id: str = Field(..., description="Step ID of the completed task")
    ra_history: RAHistory = Field(..., description="Complete execution trace")
    completed_at: datetime = Field(default_factory=datetime.utcnow, description="Task completion timestamp")


class AuditReport(BaseModel):
    """
    Quality assessment report from AuditorAgent.
    
    Contains the evaluation of completed workflow quality
    and specific suggestions for improvement if needed.
    """
    workflow_id: str = Field(..., description="Reference to audited workflow")
    is_successful: bool = Field(..., description="Whether work meets quality standards")
    feedback: str = Field(..., description="Detailed quality assessment")
    rework_suggestions: List[str] = Field(default_factory=list, description="Specific actionable improvements")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Auditor's confidence in assessment")
    reviewed_tasks: List[str] = Field(..., description="List of task IDs that were audited")
    audit_criteria: List[str] = Field(default_factory=list, description="Criteria used for evaluation")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Audit completion timestamp")


class ResultResponse(BaseModel):
    """
    Server response for result submission.
    
    Output model for the POST /v1/results endpoint.
    Confirms successful result processing and workflow status.
    """
    success: bool = Field(..., description="Whether result was processed successfully")
    workflow_id: str = Field(..., description="Reference to the workflow")
    message: str = Field(default="Result processed successfully", description="Status message")
    audit_triggered: bool = Field(default=False, description="Whether audit was triggered")


class ClientConfiguration(BaseModel):
    """
    External client configuration contract.
    
    Represents the structure of mcp_client_config.json
    that external worker clients must provide.
    """
    client_agent_id: str = Field(..., description="Unique identifier for the worker client")
    server_url: str = Field(..., description="Base URL of the FastAPI server")
    auth_token: str = Field(..., description="Secure token for API authentication")
    polling_interval_sec: int = Field(default=5, ge=1, description="How often client polls for new tasks")
    max_parallel_tasks: int = Field(default=2, ge=1, description="Local resource management limit")
    agent_capabilities: List[str] = Field(..., description="List of agent types this client can execute")


class WorkflowStatus(BaseModel):
    """
    Workflow progress summary.
    
    Provides overview of workflow execution status
    for monitoring and coordination purposes.
    """
    workflow_id: str = Field(..., description="Workflow identifier")
    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    pending_tasks: int = Field(..., description="Number of pending tasks")
    in_progress_tasks: int = Field(..., description="Number of tasks currently executing")
    is_complete: bool = Field(..., description="Whether all tasks are completed")
    audit_status: Optional[str] = Field(None, description="Current audit status if applicable")


class TaskGraphRequest(BaseModel):
    """
    Task submission request from external clients.
    
    Input model for the POST /v1/submit_task endpoint.
    Simplified interface for user task submission.
    """
    user_request: str = Field(..., description="Original user request for planning")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional request context")


class ClientPollRequest(BaseModel):
    """
    Client polling request for task claiming.
    
    Input model for the POST /v1/tasks/poll endpoint.
    Contains client identification and capabilities.
    """
    client_id: str = Field(..., description="Unique client identifier")
    agent_capabilities: List[str] = Field(..., description="List of agent types this client can handle")


class ErrorResponse(BaseModel):
    """
    Standardized error response format.
    
    Used across all API endpoints for consistent error reporting.
    """
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error occurrence timestamp")
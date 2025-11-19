"""
SQLAlchemy ORM models for MCP Server persistent storage.

This module defines the database schema with TaskGraphORM, TaskStepORM,
ResultORM, and AuditReportORM models supporting both SQLite and PostgreSQL
with proper relationships and JSON field storage for complex data.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4, UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# Create base class for all ORM models
Base = declarative_base()


class ProjectORM(Base):
    """
    Project management for grouping related workflows.
    
    Represents a logical project that contains multiple workflows.
    Projects can correspond to physical directories on disk.
    """
    __tablename__ = "projects"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal database ID"
    )
    
    # Project identification
    project_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="External project identifier (e.g., PROJECT-20251110-001)"
    )
    
    # Project name
    project_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Human-readable project name"
    )
    
    # Optional project path on filesystem
    project_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Physical directory path for project files"
    )
    
    # Project metadata
    project_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional project metadata and configuration"
    )
    
    # Project status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="IN_PROGRESS",
        index=True,
        comment="Overall project status: PENDING, IN_PROGRESS, COMPLETED, FAILED"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Project creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last project update timestamp"
    )
    
    # Relationships
    workflows: Mapped[List["TaskGraphORM"]] = relationship(
        "TaskGraphORM",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<ProjectORM(project_id='{self.project_id}', name='{self.project_name}')>"


class TaskGraphORM(Base):
    """
    Workflow management with complete TaskGraph persistence.
    
    Stores the top-level workflow information with relationships
    to individual tasks and audit reports.
    
    Go/No-Go Checkpoint: ORM test persists and retrieves full TaskGraph structure
    """
    __tablename__ = "task_graphs"
    
    # Primary key - use UUID for better distribution
    id: Mapped[UUID] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal database ID"
    )
    
    # Workflow identification
    workflow_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="External workflow identifier for API access"
    )
    
    # Workflow name
    workflow_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Untitled Workflow",
        comment="Human-readable workflow name"
    )
    
    # Project relationship
    project_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to parent project"
    )
    
    # Workflow content
    user_request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original user request that created this workflow"
    )
    
    # Workflow metadata storage as JSON - renamed to avoid SQLAlchemy conflict
    workflow_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional workflow metadata and configuration"
    )
    
    # Workflow status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        index=True,
        comment="Overall workflow status: PENDING, IN_PROGRESS, COMPLETED, FAILED"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Workflow creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last workflow update timestamp"
    )
    
    # Relationships
    project: Mapped[Optional["ProjectORM"]] = relationship(
        "ProjectORM",
        back_populates="workflows",
        lazy="selectin"
    )
    
    tasks: Mapped[List["TaskStepORM"]] = relationship(
        "TaskStepORM",
        back_populates="task_graph",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    audit_reports: Mapped[List["AuditReportORM"]] = relationship(
        "AuditReportORM",
        back_populates="task_graph",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<TaskGraphORM(workflow_id={self.workflow_id}, status={self.status})>"


class TaskStepORM(Base):
    """
    Individual task tracking with dependencies and client assignment.
    
    Stores each task within a workflow with dependency relationships,
    execution status, and client assignment for distributed coordination.
    
    Go/No-Go Checkpoint: Completed task correctly updates dependent task statuses
    """
    __tablename__ = "task_steps"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal database ID"
    )
    
    # Task identification
    step_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="External step identifier for dependency tracking"
    )
    
    # Workflow relationship
    workflow_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("task_graphs.workflow_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to parent workflow"
    )
    
    # Task content
    task_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Untitled Task",
        comment="AI-generated human-readable task name"
    )
    
    task_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Detailed task description for execution"
    )
    
    # Agent assignment
    assigned_agent: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Agent type responsible for execution"
    )
    
    # Dependencies as JSON array
    dependencies: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="List of step_ids that must complete first"
    )
    
    # Project path for file operations
    project_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Absolute path to project folder for file operations"
    )
    
    # File access coordination
    file_dependencies: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="List of file paths this task will access"
    )
    
    file_access_types: Mapped[Dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Mapping of file paths to access types ('read', 'write', 'exclusive')"
    )
    
    # Execution status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        index=True,
        comment="Task execution status: PENDING, READY, IN_PROGRESS, COMPLETED, FAILED"
    )
    
    # Client assignment
    client_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="ID of client currently executing task"
    )
    
    # Execution timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Task execution start timestamp"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Task execution completion timestamp"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Task creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last task update timestamp"
    )
    
    # Relationships
    task_graph: Mapped["TaskGraphORM"] = relationship(
        "TaskGraphORM",
        back_populates="tasks"
    )
    
    results: Mapped[List["ResultORM"]] = relationship(
        "ResultORM",
        back_populates="task_step",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Unique constraint for step_id within workflow
    __table_args__ = (
        UniqueConstraint("workflow_id", "step_id", name="uq_workflow_step"),
    )
    
    def __repr__(self) -> str:
        return f"<TaskStepORM(step_id={self.step_id}, agent={self.assigned_agent}, status={self.status})>"


class ResultORM(Base):
    """
    Complete RAHistory storage with execution details.
    
    Stores the complete Reasoning-Acting execution trace from
    worker agents including all iterations and final results.
    
    Go/No-Go Checkpoint: Worker test generates complete RA history in structured Result
    """
    __tablename__ = "results"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal database ID"
    )
    
    # Task relationship
    task_step_id: Mapped[UUID] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        ForeignKey("task_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the task that produced this result"
    )
    
    # Execution trace - stored as JSON
    iterations: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        comment="Complete ThoughtAction history as JSON array"
    )
    
    # Final result
    final_result: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Final task output after all iterations"
    )
    
    # Agent information
    source_agent: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Agent type that produced the result"
    )
    
    # Client information
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="ID of client that executed the task"
    )
    
    # Performance metrics
    execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Total task execution duration in seconds"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Result creation timestamp"
    )
    
    # Relationships
    task_step: Mapped["TaskStepORM"] = relationship(
        "TaskStepORM",
        back_populates="results"
    )
    
    def __repr__(self) -> str:
        return f"<ResultORM(task_step_id={self.task_step_id}, agent={self.source_agent}, time={self.execution_time}s)>"


class AuditReportORM(Base):
    """
    Quality control assessments with rework coordination.
    
    Stores audit reports from the AuditorAgent with quality assessments
    and specific rework suggestions for workflow improvement.
    
    Go/No-Go Checkpoint: Failed audit updates DB and resets tasks for rework
    """
    __tablename__ = "audit_reports"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal database ID"
    )
    
    # Workflow relationship
    workflow_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("task_graphs.workflow_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to audited workflow"
    )
    
    # Audit results
    is_successful: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Whether work meets quality standards"
    )
    
    feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Detailed quality assessment"
    )
    
    # Rework coordination
    rework_suggestions: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Specific actionable improvements as JSON array"
    )
    
    # Quality metrics
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Auditor's confidence in assessment (0.0 to 1.0)"
    )
    
    # Audit scope
    reviewed_tasks: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        comment="List of task step_ids that were audited"
    )
    
    audit_criteria: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Criteria used for evaluation as JSON array"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Audit completion timestamp"
    )
    
    # Relationships
    task_graph: Mapped["TaskGraphORM"] = relationship(
        "TaskGraphORM",
        back_populates="audit_reports"
    )
    
    def __repr__(self) -> str:
        return f"<AuditReportORM(workflow_id={self.workflow_id}, successful={self.is_successful}, confidence={self.confidence_score})>"


class FileAccessORM(Base):
    """
    File access coordination and locking for concurrent worker safety.
    
    Tracks which files are being accessed by which workers to prevent
    conflicts when multiple agents need to work with the same files.
    
    Go/No-Go Checkpoint: File locking prevents concurrent access conflicts
    """
    __tablename__ = "file_access"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal database ID for file access record"
    )
    
    # File identification
    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Absolute path to the file being accessed"
    )
    
    # Worker identification
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ID of the client/worker accessing the file"
    )
    
    # Task context
    task_step_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Associated task step for this file access"
    )
    
    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Associated workflow for this file access"
    )
    
    # Access control
    access_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="read",
        comment="Type of access: 'read', 'write', 'exclusive'"
    )
    
    # Lock timing
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the file lock was acquired"
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the file lock expires (NULL for no expiration)"
    )
    
    # Lock status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this lock is currently active"
    )
    
    # Additional metadata - renamed to avoid SQLAlchemy conflict
    lock_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional metadata about the file access"
    )
    
    # Constraints for file access coordination
    __table_args__ = (
        # Prevent multiple exclusive locks on same file
        UniqueConstraint(
            'file_path', 'access_type',
            name='uq_file_exclusive_access',
            sqlite_on_conflict='FAIL'
        ),
    )
    
    def __repr__(self) -> str:
        return f"<FileAccessORM(file={self.file_path}, client={self.client_id}, type={self.access_type}, active={self.is_active})>"


# Utility functions for ORM operations
def get_all_tables():
    """Get list of all table names defined in this module."""
    return [table.name for table in Base.metadata.tables.values()]


class IDCounterORM(Base):
    """
    Sequential ID counter for PID/WID/TID generation.
    
    Maintains atomic counters for generating sequential IDs across
    distributed workers and server restarts.
    """
    __tablename__ = "id_counters"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgreSQL_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal database ID"
    )
    
    # Counter type (project/workflow/task)
    counter_type: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Type of counter: project, workflow, task"
    )
    
    # Current counter value
    current_value: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Current counter value for sequential ID generation"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Counter creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last counter update timestamp"
    )
    
    def __repr__(self) -> str:
        return f"<IDCounterORM(type={self.counter_type}, value={self.current_value})>"


def get_table_dependencies():
    """Get table creation order based on foreign key dependencies."""
    return {
        "id_counters": [],  # Independent table for ID generation
        "task_graphs": [],
        "task_steps": ["task_graphs"],
        "results": ["task_steps"],
        "audit_reports": ["task_graphs"],
        "file_access": [],  # Independent table for file locking
    }
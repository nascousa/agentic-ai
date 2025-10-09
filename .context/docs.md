# AM (AgentManager) - MCP Server Technical Documentation

## MCP Server Configuration Contract

### Client Configuration Structure (`mcp_client_config.json`)
```json
{
  "client_agent_id": "worker_001",
  "server_url": "http://localhost:8000",
  "auth_token": "your_secure_api_token",
  "polling_interval_sec": 5,
  "max_parallel_tasks": 2,
  "agent_capabilities": ["researcher", "writer", "analyst"]
}
```

This configuration file is the **contract** between the FastAPI server and external worker clients:
- **`client_agent_id`**: Unique identifier for the worker client
- **`server_url`**: Base URL of the FastAPI server
- **`auth_token`**: Secure token for API authentication
- **`polling_interval_sec`**: How often client polls for new tasks
- **`max_parallel_tasks`**: Local resource management limit
- **`agent_capabilities`**: List of agent types this client can execute

### Server Environment Configuration (`.env`)
```bash
# Database Configuration
DATABASE_URL=sqlite:///./agent_manager.db  # Development
# DATABASE_URL=postgresql://user:pass@localhost/agent_manager  # Production

# API Security
SERVER_API_TOKEN=your_secure_server_token
SECRET_KEY=your_jwt_secret_key

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4
LLM_MAX_TOKENS=2000
```

## Development Guidelines

### Code Quality Standards

- **Python Version**: Use Python 3.11+ with full async/await support for FastAPI operations
- **FastAPI Best Practices**: Follow FastAPI patterns for dependency injection, async endpoints, and error handling
- **SQLAlchemy ORM**: Use declarative models with proper relationships and query optimization
- **Code Style**: Follow PEP 8 for formatting and naming conventions
- **Type Safety**: All functions and methods must include comprehensive type hints
- **Documentation**: Every class and method requires docstrings with clear explanations
- **Error Handling**: Implement graceful HTTP error responses with proper status codes and client retry logic
- **Testing**: Write unit tests for all components and integration tests for client-server workflows

### Enhanced Dependency Management

- **Core Dependencies**: `fastapi`, `uvicorn`, `SQLAlchemy`, `pydantic` (v2), `openai`, `python-dotenv`
- **Database Dependencies**: `psycopg2-binary` for PostgreSQL readiness, SQLite built-in support
- **Development Dependencies**: `pytest`, `pytest-asyncio`, `httpx` (for testing), `mypy`, `black`, `isort`
- **Production Dependencies**: Database connection pooling, monitoring, and logging libraries

## MCP Server Technical Implementation Details

### FastAPI Server Architecture

#### Core Server Setup with Authentication
```python
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

app = FastAPI(title="AM MCP Server", version="1.0.0")

async def verify_auth_token(authorization: str = Header(...)) -> str:
    """Verify client authentication token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    if token != os.getenv("SERVER_API_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid auth token")
    return token

async def get_database_session() -> AsyncSession:
    """Provide async database session for request handling"""
    # Implementation with proper session management and rollback
```

#### Enhanced API Endpoints

##### 1. Task Submission Endpoint
```python
@app.post("/v1/tasks", response_model=TaskGraphResponse)
async def submit_task(
    request: UserTaskRequest,
    db: AsyncSession = Depends(get_database_session),
    token: str = Depends(verify_auth_token)
):
    """
    Submit a new task for processing by the MCP server.
    
    Request Flow:
    1. Validate UserTaskRequest with Pydantic
    2. AgentManager.plan_and_save_task() creates TaskGraph
    3. Persist TaskGraph to database via SQLAlchemy ORM
    4. Mark initial tasks as READY status
    5. Return TaskGraphResponse with workflow_id
    
    Go/No-Go Checkpoint: API endpoint accepts Pydantic data and validates auth token
    """
    try:
        # Create TaskGraph with dependencies
        task_graph = await agent_manager.plan_and_save_task(request.user_request)
        
        # Persist to database
        await db_service.save_task_graph(task_graph)
        
        # Mark initial tasks as READY
        await db_service.update_ready_tasks(task_graph.workflow_id)
        
        return TaskGraphResponse(
            workflow_id=task_graph.workflow_id,
            tasks=task_graph.tasks,
            created_at=task_graph.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

##### 2. Task Polling Endpoint
```python
@app.get("/v1/tasks/ready", response_model=Optional[TaskStep])
async def get_ready_task(
    agent_id: str = Query(...),
    client_capabilities: List[str] = Query([]),
    db: AsyncSession = Depends(get_database_session),
    token: str = Depends(verify_auth_token)
):
    """
    Poll for ready tasks assigned to specific agent type.
    
    Query Logic:
    1. Find READY tasks matching agent capabilities
    2. Check all dependencies are COMPLETED
    3. Atomically update task status to IN_PROGRESS
    4. Return TaskStep or None if no tasks available
    
    Go/No-Go Checkpoint: Returns oldest READY task for specified agent
    """
    # Atomic query with dependency checking
    task = await db_service.get_and_claim_ready_task(
        agent_capabilities=client_capabilities,
        client_id=agent_id
    )
    
    if task:
        # Update status atomically
        await db_service.update_task_status(
            task.step_id, 
            TaskStatus.IN_PROGRESS,
            client_id=agent_id
        )
        return task
    
    return None  # No tasks available
```

##### 3. Result Reporting Endpoint
```python
@app.post("/v1/results", response_model=ResultResponse)
async def report_result(
    result: TaskResult,
    db: AsyncSession = Depends(get_database_session),
    token: str = Depends(verify_auth_token)
):
    """
    Report completed task results from external client.
    
    Processing Flow:
    1. Validate TaskResult with complete RAHistory
    2. Update task status to COMPLETED in database
    3. Save result data to ResultORM table
    4. Check if all workflow tasks are complete
    5. If complete, trigger audit workflow
    6. Return success confirmation
    
    Go/No-Go Checkpoint: Final result triggers audit and handles rework cycle
    """
    try:
        # Save result and update status
        await db_service.save_task_result(result)
        await db_service.update_task_status(result.task_id, TaskStatus.COMPLETED)
        
        # Check workflow completion
        if await db_service.is_workflow_complete(result.workflow_id):
            # Trigger audit
            audit_report = await auditor_agent.run_audit(result.workflow_id)
            await db_service.save_audit_report(audit_report)
            
            if not audit_report.is_successful:
                # Reset tasks for rework
                await db_service.reset_tasks_for_rework(
                    result.workflow_id, 
                    audit_report.rework_suggestions
                )
        
        return ResultResponse(success=True, workflow_id=result.workflow_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### API Security and Authentication
- API key validation middleware for client authorization
- Request rate limiting and throttling for production deployment
- CORS configuration for cross-origin client access
- Input validation and sanitization for security

### SQLAlchemy ORM Implementation

#### Enhanced Database Models with JSON Support
```python
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from datetime import datetime
from typing import List, Optional

Base = declarative_base()

class TaskGraphORM(Base):
    """
    Workflow management with complete TaskGraph persistence.
    
    Go/No-Go Checkpoint: ORM test persists and retrieves full TaskGraph structure
    """
    __tablename__ = "task_graphs"
    
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    workflow_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_request: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSON)  # Store complex Pydantic data
    status: Mapped[str] = mapped_column(String, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks: Mapped[List["TaskStepORM"]] = relationship(back_populates="task_graph")
    audit_reports: Mapped[List["AuditReportORM"]] = relationship(back_populates="task_graph")

class TaskStepORM(Base):
    """
    Individual task tracking with dependencies and client assignment.
    
    Go/No-Go Checkpoint: Completed task correctly updates dependent task statuses
    """
    __tablename__ = "task_steps"
    
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("task_graphs.workflow_id"))
    step_id: Mapped[str] = mapped_column(String, index=True)
    task_description: Mapped[str] = mapped_column(Text)
    assigned_agent: Mapped[str] = mapped_column(String, index=True)
    dependencies: Mapped[List[str]] = mapped_column(JSON)  # Store dependency list
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    client_id: Mapped[Optional[str]] = mapped_column(String)  # Client claiming task
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    task_graph: Mapped["TaskGraphORM"] = relationship(back_populates="tasks")
    results: Mapped[List["ResultORM"]] = relationship(back_populates="task_step")
    
class ResultORM(Base):
    """
    Complete RAHistory storage with execution details.
    
    Go/No-Go Checkpoint: Worker test generates complete RA history in structured Result
    """
    __tablename__ = "results"
    
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    task_step_id: Mapped[UUID] = mapped_column(UUID, ForeignKey("task_steps.id"))
    iterations: Mapped[List[dict]] = mapped_column(JSON)  # ThoughtAction history
    final_result: Mapped[str] = mapped_column(Text)
    source_agent: Mapped[str] = mapped_column(String)
    client_id: Mapped[str] = mapped_column(String)
    execution_time: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task_step: Mapped["TaskStepORM"] = relationship(back_populates="results")

class AuditReportORM(Base):
    """
    Quality control assessments with rework coordination.
    
    Go/No-Go Checkpoint: Failed audit updates DB and resets tasks for rework
    """
    __tablename__ = "audit_reports"
    
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("task_graphs.workflow_id"))
    is_successful: Mapped[bool] = mapped_column(Boolean)
    feedback: Mapped[str] = mapped_column(Text)
    rework_suggestions: Mapped[List[str]] = mapped_column(JSON)
    confidence_score: Mapped[float] = mapped_column(Float)
    reviewed_tasks: Mapped[List[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task_graph: Mapped["TaskGraphORM"] = relationship(back_populates="audit_reports")

class FileAccessORM(Base):
    """
    File access coordination and locking for concurrent worker safety.
    
    Tracks which files are being accessed by which workers to prevent
    conflicts when multiple agents need to work with the same files.
    
    Go/No-Go Checkpoint: File locking prevents concurrent access conflicts
    """
    __tablename__ = "file_access"
    
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    file_path: Mapped[str] = mapped_column(String(512), index=True)  # Absolute file path
    client_id: Mapped[str] = mapped_column(String(255))  # Worker client ID
    task_step_id: Mapped[Optional[str]] = mapped_column(String(255))  # Associated task
    workflow_id: Mapped[Optional[str]] = mapped_column(String(255))  # Associated workflow
    access_type: Mapped[str] = mapped_column(String(50), default="read")  # read/write/exclusive
    locked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # Lock expiration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Lock status
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional context
    
    # Constraints for file access coordination
    __table_args__ = (
        UniqueConstraint('file_path', 'access_type', name='uq_file_exclusive_access'),
    )
```

#### File Access Coordination Implementation
```python
class DatabaseService:
    """Enhanced with file access coordination methods"""
    
    async def acquire_file_lock(
        self,
        file_path: str,
        client_id: str,
        access_type: str = "read",
        timeout_minutes: int = 30
    ) -> bool:
        """
        Acquire database-tracked file lock for coordination.
        
        Lock compatibility matrix:
        - Multiple 'read' locks are allowed
        - 'write' locks are exclusive
        - 'exclusive' locks block everything
        
        Go/No-Go Checkpoint: Concurrent workers prevented from conflicting file access
        """
        
    async def release_file_lock(self, file_path: str, client_id: str) -> bool:
        """Release database-tracked file lock."""
        
    async def cleanup_expired_file_locks(self) -> int:
        """Clean up expired file locks for resource management."""
```

#### Database Configuration with SQLite/PostgreSQL Flexibility
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

def create_database_engine(database_url: str = None):
    """
    Create async database engine with proper configuration.
    
    Development: SQLite with file persistence
    Production: PostgreSQL with connection pooling
    """
    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agent_manager.db")
    
    return create_async_engine(
        database_url,
        echo=True,  # Development logging
        pool_pre_ping=True,  # Connection health checks
        pool_recycle=3600,  # Connection recycling for production
    )

# Session factory for dependency injection
AsyncSessionLocal = async_sessionmaker(
    bind=create_database_engine(),
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_database_session() -> AsyncSession:
    """
    FastAPI dependency for database session injection.
    
    Go/No-Go Checkpoint: All database operations handle transactions properly
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

#### Critical Database Operations for MCP Coordination
```python
class DatabaseService:
    """
    Centralized database operations for MCP server coordination.
    Implements atomic operations for concurrent client safety.
    """
    
    async def save_task_graph(self, task_graph: TaskGraph) -> str:
        """
        Atomically persist TaskGraph with initial task states.
        
        Go/No-Go: Task submission results in persisted TaskGraph with initial tasks marked READY
        """
        
    async def get_and_claim_ready_task(self, agent_capabilities: List[str], client_id: str) -> Optional[TaskStep]:
        """
        Atomic query and claim operation for client polling.
        Prevents duplicate task assignment across concurrent clients.
        
        Go/No-Go: Concurrency validated with no duplicate task execution
        """
        
    async def save_task_result(self, result: TaskResult) -> bool:
        """
        Save complete RAHistory and update task status to COMPLETED.
        
        Go/No-Go: Client result reporting triggers proper audit workflow
        """
        
    async def check_and_dispatch_ready_tasks(self, workflow_id: str) -> int:
        """
        Dependency resolution: find PENDING tasks whose dependencies are COMPLETED.
        Atomically update their status to READY.
        
        Go/No-Go: Completed task correctly updates dependent task statuses
        """
        
    async def reset_tasks_for_rework(self, workflow_id: str, rework_suggestions: List[str]) -> bool:
        """
        Failed audit coordination: reset specific tasks to PENDING with rework notes.
        
        Go/No-Go: System demonstrates full Parallel → Audit → Rework → Synthesis cycle
        """
```

### Enhanced Pydantic Model Design for MCP

#### API Request/Response Models
```python
class UserTaskRequest(BaseModel):
    """External client task submission format"""
    description: str
    complexity: str = "medium"
    deadline: Optional[datetime] = None
    metadata: dict[str, Any] = {}

class TaskGraphResponse(BaseModel):
    """Server response for task submission"""
    workflow_id: str
    total_tasks: int
    estimated_completion: datetime
    status: str

class TaskResult(BaseModel):
    """External client result reporting format"""
    step_id: str
    workflow_id: str
    ra_history: RAHistory
    execution_time: float
    client_id: str

class ResultResponse(BaseModel):
    """Server response for result submission"""
    success: bool
    workflow_status: str
    next_action: str  # "continue", "audit", "complete"
```

#### ORM-Pydantic Conversion Utilities
```python
def taskgraph_orm_to_pydantic(orm_obj: TaskGraphORM) -> TaskGraph:
    """Convert SQLAlchemy ORM to Pydantic for API responses"""
    
def taskstep_pydantic_to_orm(pydantic_obj: TaskStep) -> TaskStepORM:
    """Convert Pydantic to SQLAlchemy ORM for database storage"""
    
def sync_pydantic_to_database(db: Session, pydantic_obj: BaseModel) -> bool:
    """Atomic conversion and persistence with transaction management"""
```

### Advanced Client-Server Coordination Patterns

#### External Client Worker Implementation
```python
import httpx
import asyncio
from typing import Optional

class ExternalWorkerClient:
    def __init__(self, server_url: str, client_id: str, agent_role: str, api_key: str):
        """Initialize client with server connection details"""
        
    async def poll_for_tasks(self, poll_interval: float = 5.0):
        """Continuous polling for available tasks from server"""
        
    async def execute_task_locally(self, task: TaskStep) -> RAHistory:
        """Execute task with local RA loop and LLM client"""
        
    async def report_result_to_server(self, result: TaskResult) -> bool:
        """Report completion back to server via HTTP POST"""
        
    async def handle_connection_errors(self, error: Exception):
        """Implement retry logic and graceful error handling"""
```

#### Multi-Client Coordination
- Client registration and heartbeat mechanisms
- Task assignment and conflict resolution
- Load balancing across available clients
- Graceful client disconnection and task reassignment

### Sophisticated Database Integration Patterns

#### Atomic Transaction Management
```python
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

@asynccontextmanager
async def atomic_transaction(db: Session):
    """Ensure atomic operations for concurrent client requests"""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

async def atomic_status_update(db: Session, step_id: str, 
                             old_status: str, new_status: str) -> bool:
    """Atomic compare-and-swap status update for client coordination"""
    
async def claim_ready_task(db: Session, client_id: str, agent_role: str) -> Optional[TaskStepORM]:
    """Atomically claim next available task for client execution"""
```

#### Database Performance Optimization
- Indexed queries for task status and dependency resolution
- Connection pooling for high-concurrency scenarios
- Query optimization for large TaskGraph operations
- Database monitoring and performance metrics collection

### Agent Coordination Patterns

#### Central Coordinator Pattern Implementation
1. **Single Point of Control**: AgentManager is the only component that coordinates workflows
2. **Delegation Strategy**: Tasks are assigned based on agent capabilities and roles
3. **Result Aggregation**: All outputs are collected and synthesized by the coordinator
4. **Error Recovery**: Failed tasks can be reassigned or handled gracefully

#### Enhanced WorkerAgent with File Safety Coordination
```python
class WorkerAgent:
    """Enhanced WorkerAgent with integrated file access safety"""
    
    def __init__(self, name: str, role: str, client_id: str, max_iterations: int = 10):
        """Initialize with file safety coordination capabilities"""
        
    async def execute_task(self, task: TaskStep) -> RAHistory:
        """
        Execute task with multi-level file access protection:
        1. Pre-acquire locks for declared file dependencies
        2. Extract file paths from dynamic actions
        3. Acquire locks with timeout and conflict resolution
        4. Execute actions with OS-level and database coordination
        5. Release all locks automatically on completion
        
        Go/No-Go Checkpoint: File access conflicts prevented across concurrent workers
        """
        async with self._manage_task_file_locks(task):
            # Execute RA loop with file safety coordination
            for iteration in range(self.max_iterations):
                action = await self._get_next_action()
                await self._execute_action_safely(action, task)
        
    async def _manage_task_file_locks(self, task: TaskStep):
        """Context manager for task-level file lock coordination"""
        # Pre-acquire locks for declared dependencies
        for file_path in task.file_dependencies:
            access_type = task.file_access_types.get(file_path, "read")
            # Coordinate with database and OS-level locks
            
    async def _execute_action_safely(self, action: str, task: TaskStep):
        """Execute action with dynamic file path extraction and locking"""
        file_paths = extract_file_paths_from_action(action)
        async with self._acquire_action_file_locks(action, file_paths):
            return await self._execute_action(action, task)
```

#### File Access Coordination Architecture
```python
# Multi-level file access coordination:

# Level 1: Task Declaration (Planning Phase)
task_step = TaskStep(
    file_dependencies=["/data/input.csv", "/output/report.txt"],
    file_access_types={
        "/data/input.csv": "read",     # Shared read access
        "/output/report.txt": "write"  # Exclusive write access
    }
)

# Level 2: Database Coordination (Server-Side)
await db_service.acquire_file_lock(
    file_path="/data/input.csv",
    client_id="worker_1", 
    access_type="read"
)

# Level 3: OS-Level Protection (Worker-Side)
async with file_lock("/data/input.csv", "read", client_id="worker_1"):
    # Perform file operations with hardware-level coordination
    pass

# Level 4: Automatic Path Extraction
action = "Edit /src/main.py and save to ./output/result.txt"
detected_paths = extract_file_paths_from_action(action)
# Automatically acquire appropriate locks based on action analysis
```

#### Communication Protocol
- All inter-agent communication uses Pydantic models
- No direct agent-to-agent communication is allowed
- State is maintained centrally by the AgentManager
- Results are type-validated before processing

## Enhanced Business Domain Information

### Advanced MCP Server Use Cases

#### Enterprise Task Coordination
- Centralized coordination server for multiple development teams
- HTTP API integration with existing enterprise workflows and CI/CD pipelines
- Scalable task distribution across geographically distributed development environments
- Audit trail compliance with persistent database storage and reporting

#### Multi-Client Agent Networks
- External AI agent coordination through standardized REST API endpoints
- Third-party integration with webhook notifications and status reporting
- Load-balanced task execution across heterogeneous client environments
- Quality-controlled workflows with centralized audit and rework coordination

#### Production-Scale AI Operations
- High-availability server deployment with PostgreSQL clustering
- API rate limiting and authentication for secure multi-tenant operations
- Monitoring and analytics dashboard for task execution metrics and performance
- Disaster recovery with database replication and automated failover

### Enhanced Agent Specialization for MCP Server

#### Server-Side Agent Logic
- **Planning Agent**: FastAPI endpoint integration for complex task decomposition
- **Audit Agent**: Server-side quality control with database-driven rework coordination
- **Coordination Agent**: HTTP API orchestration with external client management
- **Monitoring Agent**: Performance tracking and system health monitoring with metrics collection

#### External Client Agent Types
- **Polling Worker Clients**: HTTP-based task polling with local RA execution
- **Webhook-Driven Clients**: Event-driven task execution with server notifications
- **Batch Processing Clients**: Large-scale task execution with result bulk reporting
- **Specialized Domain Clients**: Industry-specific agents with custom API integration

#### API-Integrated Quality Control
- **Real-Time Audit API**: Live quality assessment with immediate feedback
- **Batch Audit Processing**: Scheduled quality reviews with comprehensive reporting
- **Compliance Audit API**: Regulatory compliance checking with audit trail storage
- **Performance Audit API**: Execution metrics analysis with optimization recommendations

## Advanced MCP Server Integration Patterns

### FastAPI Production Deployment

#### High-Performance Server Configuration
- **Uvicorn/Gunicorn**: Multi-worker deployment with async request handling
- **Database Connection Pooling**: PostgreSQL connection management for high concurrency
- **API Gateway Integration**: Load balancing and rate limiting with enterprise gateways
- **Container Deployment**: Docker containerization with Kubernetes orchestration

#### Enterprise Integration Capabilities
- **SSO Authentication**: Enterprise identity provider integration with JWT tokens
- **API Versioning**: Backward-compatible API evolution with versioned endpoints
- **Webhook Infrastructure**: Event-driven notifications for external system integration
- **Monitoring and Observability**: Prometheus metrics and distributed tracing integration

### SQLAlchemy Production Patterns

#### Database Performance Optimization
- **Query Optimization**: Indexed database access with efficient JOIN operations
- **Connection Management**: Async connection pooling with automatic retry logic
- **Database Migrations**: Alembic integration for schema evolution and version control
- **Backup and Recovery**: Automated backup procedures with point-in-time recovery

#### Multi-Tenant Data Architecture
- **Tenant Isolation**: Logical data separation with secure multi-tenant access
- **Scaling Patterns**: Horizontal partitioning and read replica configuration
- **Data Retention**: Automated archival and cleanup policies for long-running workflows
- **Compliance Storage**: Audit trail persistence with regulatory retention requirements

## Comprehensive MCP Server Troubleshooting

### FastAPI Server Issues

#### API Performance Problems
- **Symptom**: Slow response times or timeout errors from external clients
- **Solution**: Implement async request handling with database query optimization
- **Prevention**: Use connection pooling and implement proper caching strategies

#### Database Connection Issues
- **Symptom**: Connection pool exhaustion or database deadlocks
- **Solution**: Implement proper session management with transaction isolation
- **Prevention**: Use async database operations and monitor connection health

#### Client Coordination Failures
- **Symptom**: Tasks stuck in IN_PROGRESS or client polling failures
- **Solution**: Implement heartbeat monitoring with automatic task reassignment
- **Prevention**: Use timeout handling and graceful client disconnection

### SQLAlchemy ORM Issues

#### Data Consistency Problems
- **Symptom**: Inconsistent TaskGraph state or missing dependencies
- **Solution**: Implement atomic transactions with proper rollback handling
- **Prevention**: Use database constraints and validation at ORM level

#### Performance Degradation
- **Symptom**: Slow database queries or high CPU usage
- **Solution**: Optimize queries with proper indexing and query analysis
- **Prevention**: Monitor query performance and implement database profiling

### External Client Issues

#### Client Authentication Problems
- **Symptom**: Unauthorized API access or authentication failures
- **Solution**: Implement proper API key validation and token refresh mechanisms
- **Prevention**: Use secure authentication patterns and monitor access logs

#### Task Execution Failures
- **Symptom**: Client task failures or incomplete result reporting
- **Solution**: Implement comprehensive error handling with retry logic
- **Prevention**: Use structured error reporting and client health monitoring

## Security and Compliance for MCP Server

### API Security Implementation

#### Authentication and Authorization
- **API Key Management**: Secure key generation and rotation with client management
- **JWT Token Integration**: Stateless authentication with enterprise identity providers
- **Rate Limiting**: Request throttling and abuse prevention with client quotas
- **CORS Configuration**: Secure cross-origin access with domain whitelisting

#### Data Protection
- **Transport Security**: TLS encryption for all API communications
- **Data Validation**: Input sanitization and output encoding for security
- **Audit Logging**: Complete request logging with security event monitoring
- **Vulnerability Management**: Regular security scanning and dependency updates

### Compliance and Governance

#### Regulatory Compliance
- **Audit Trail Storage**: Complete workflow history with tamper-evident logging
- **Data Retention Policies**: Automated compliance with regulatory requirements
- **Privacy Protection**: Data anonymization and secure deletion procedures
- **Access Control**: Role-based permissions with principle of least privilege

#### Operational Governance
- **Change Management**: Version-controlled deployments with rollback capabilities
- **Incident Response**: Automated alerting with escalation procedures
- **Business Continuity**: Disaster recovery planning with backup coordination
- **Performance Monitoring**: SLA tracking with proactive performance management

## Security Considerations

### API Key Management
- Store all credentials in environment variables
- Use secure credential management systems
- Rotate API keys regularly
- Monitor usage for anomalies

### Data Privacy
- Avoid logging sensitive information
- Implement data sanitization for outputs
- Ensure compliance with privacy regulations
- Use secure communication channels

### Access Control
- Implement role-based access for different components
- Validate all inputs and outputs
- Monitor system access and usage
- Implement audit trails for all operations

### File Access Security
- Cross-platform file locking prevents unauthorized concurrent access
- Database-tracked file coordination with audit logging
- Timeout-based lock expiration prevents resource deadlocks
- Lock compatibility matrix enforces appropriate access controls:
  - Read locks: Shared access for multiple workers
  - Write locks: Exclusive access for data integrity
  - Exclusive locks: Complete isolation for critical operations
- Automatic cleanup of expired locks prevents resource leaks
- File path validation and sanitization prevent directory traversal attacks
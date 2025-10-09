# Copilot Instructions for AM (AgentManager)

## Project Context

**IMPORTANT**: Before starting any task, read the `.context` directory for architectural overview and project context starting at `.context/index.md`. This project follows the Codebase Context Specification (CCS) v1.1 for structured documentation.

## Project Overview
**AM (AgentManager)** is a Multi-Agent Coordination/Planning (MCP) Server using FastAPI and SQLAlchemy ORM. This project implements a **centralized MCP server** that coordinates external client workers through REST API endpoints, enabling distributed multi-agent task execution with structured JSON communication.

## Project Architecture

### Core Design Principles
1. **MCP Server Pattern**: Centralized FastAPI server coordinating external client workers
2. **REST API Communication**: All coordination via HTTP endpoints with JSON payloads
3. **SQLAlchemy ORM Integration**: Type-safe database operations with automatic migration support
4. **External Client Coordination**: Independent worker clients poll for tasks and report results
5. **Pydantic Data Validation**: Comprehensive request/response validation and serialization

### Key Components
- **FastAPI Server**: HTTP API server with async endpoints for task coordination
- **SQLAlchemy ORM**: Database abstraction with TaskGraphORM, TaskStepORM, ResultORM models
- **External Client Workers**: Independent processes polling for tasks via API endpoints
- **AgentManager**: Server-side coordinator implementing planning and synthesis logic
- **AuditorAgent**: Quality control agent reviewing completed workflows

## Development Guidelines

### Code Style and Standards
- Use Python 3.11+ features and type hints everywhere
- Follow PEP 8 for code formatting
- Use Pydantic v2 for all API request/response models
- Use SQLAlchemy 2.0+ ORM patterns with async operations
- Implement proper FastAPI middleware and error handling
- Write comprehensive docstrings and API documentation

### File Structure
```
agent_manager/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py          # Pydantic schemas for API requests/responses
│   ├── manager.py         # AgentManager server-side coordination
│   ├── worker.py          # WorkerAgent logic for external clients
│   ├── auditor.py         # AuditorAgent for quality control
│   └── llm_client.py      # Async LLM API abstraction
├── api/
│   ├── __init__.py
│   ├── main.py           # FastAPI application and middleware setup
│   ├── endpoints.py      # API route handlers
│   └── dependencies.py   # FastAPI dependency injection
├── orm.py                # SQLAlchemy ORM models
├── db.py                 # Database configuration and session management
└── exceptions.py         # Custom exceptions
client_worker.py          # External worker client implementation
```

### Key Pydantic Models
When creating models in `agent_manager/core/models.py`:

1. **TaskStep Model** (API request/response):
   - `step_id: str` - Unique identifier for dependency tracking
   - `workflow_id: str` - Reference to parent TaskGraph
   - `task_description: str` - Detailed task description
   - `assigned_agent: str` - Agent type for client filtering
   - `dependencies: list[str]` - List of step_ids that must complete first
   - `status: TaskStatus` - Current execution status
   - `created_at: datetime` - Task creation timestamp

2. **TaskGraphRequest Model** (API input):
   - `user_request: str` - Original user request for planning
   - `metadata: dict[str, Any]` - Additional request context

3. **TaskGraphResponse Model** (API output):
   - `workflow_id: str` - Unique workflow identifier
   - `tasks: list[TaskStep]` - Complete task dependency graph
   - `created_at: datetime` - Workflow creation timestamp

4. **RAHistory Model** (reasoning-acting results):
   - `iterations: list[ThoughtAction]` - Complete reasoning history
   - `final_result: str` - Final task output
   - `source_agent: str` - Agent that produced the result
   - `execution_time: float` - Task execution duration

5. **AuditReport Model** (quality assessment):
   - `workflow_id: str` - Reference to audited workflow
   - `is_successful: bool` - Whether work meets quality standards
   - `feedback: str` - Detailed quality assessment
   - `rework_suggestions: list[str]` - Specific actionable improvements
   - `confidence_score: float` - Auditor's confidence in assessment

### SQLAlchemy ORM Implementation
The ORM models in `agent_manager/orm.py` must include:

1. **TaskGraphORM Model**:
   - Primary key: `id` (UUID)
   - Fields: `workflow_id`, `user_request`, `created_at`, `status`
   - Relationships: One-to-many with TaskStepORM

2. **TaskStepORM Model**:
   - Primary key: `id` (UUID)
   - Foreign key: `workflow_id` referencing TaskGraphORM
   - Fields: `step_id`, `task_description`, `assigned_agent`, `dependencies`, `status`
   - Relationships: Many-to-one with TaskGraphORM, One-to-many with ResultORM

3. **ResultORM Model**:
   - Primary key: `id` (UUID)
   - Foreign key: `task_step_id` referencing TaskStepORM
   - Fields: `iterations`, `final_result`, `source_agent`, `execution_time`

4. **AuditReportORM Model**:
   - Primary key: `id` (UUID)
   - Foreign key: `workflow_id` referencing TaskGraphORM
   - Fields: `is_successful`, `feedback`, `rework_suggestions`, `confidence_score`

### FastAPI Endpoints Implementation
The API endpoints in `agent_manager/api/endpoints.py` must include:

1. **POST /v1/submit_task**:
   - Input: `TaskGraphRequest`
   - Processing: AgentManager.plan_task() with LLM integration
   - Output: `TaskGraphResponse`
   - Database: Create TaskGraphORM and TaskStepORM records

2. **GET /v1/tasks/{role}/ready**:
   - Parameters: `role` (agent type for filtering)
   - Processing: Query ready tasks with resolved dependencies
   - Output: `TaskStep` or 204 No Content
   - Database: SELECT with dependency checking and atomic claiming

3. **POST /v1/report_result**:
   - Input: `RAHistory` with task identification
   - Processing: Save result and update task status
   - Output: Success confirmation
   - Database: CREATE ResultORM, UPDATE TaskStepORM status

4. **GET /v1/workflows/{workflow_id}/status**:
   - Parameters: `workflow_id`
   - Processing: Aggregate task statuses
   - Output: Workflow completion status
   - Database: Query all related TaskStepORM records

### Database Configuration
The database setup in `agent_manager/db.py` must include:
- SQLAlchemy 2.0+ async engine configuration
- Session factory with proper connection pooling
- Alembic integration for database migrations
- Support for SQLite (development) and PostgreSQL (production)
- Proper transaction management and rollback handling

### External Client Worker Implementation
The `client_worker.py` script must include:
- Constructor: `WorkerClient(role: str, server_url: str, poll_interval: float = 5.0)`
- Method: `async poll_for_tasks()` - Continuous API polling for ready tasks
- Method: `async execute_task(task: TaskStep) -> RAHistory` - Local task execution
- Method: `async report_result(task_id: str, result: RAHistory)` - Result submission
- HTTP client with proper retry logic and error handling

### AgentManager Implementation
Key methods for server-side coordination:
1. `async plan_task(user_request: str) -> TaskGraphResponse` - LLM-based planning with database persistence
2. `async get_ready_tasks(role: str) -> list[TaskStep]` - Dependency-resolved task queries
3. `async check_workflow_completion(workflow_id: str) -> bool` - Status aggregation
4. `async trigger_audit(workflow_id: str) -> AuditReport` - Quality control coordination
5. `async synthesize_results(workflow_id: str) -> str` - Final result consolidation

### Enhanced Workflow Pattern
The system follows a **MCP Server Architecture**: **API Planning → Client Polling → Distributed Execution → Server Audit → Coordinated Re-planning**
1. **Planning**: FastAPI endpoint receives requests, AgentManager creates TaskGraphs via LLM
2. **Polling**: External clients continuously poll GET endpoints for ready tasks
3. **Execution**: Tasks execute on client workers with local RA pattern implementation
4. **Audit**: Server-side AuditorAgent reviews all work via database queries
5. **Re-planning**: Failed audits trigger database updates coordinated through API

## Development Phases

### Phase 0: FastAPI Infrastructure and Database Setup
- Create `pyproject.toml` with dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `openai`, `python-dotenv`
- Set up `.env` for API keys and database connection strings
- Implement `agent_manager/db.py` with async SQLAlchemy configuration
- Create `agent_manager/orm.py` with all ORM models

### Phase 1: Core Pydantic Models and API Foundation
- Implement `core/models.py` with TaskStep, TaskGraphRequest/Response, RAHistory, AuditReport schemas
- Create `api/main.py` with FastAPI application setup and middleware
- Implement `api/dependencies.py` for database session injection
- Ensure proper Pydantic/SQLAlchemy integration with validation

### Phase 2: API Endpoints and Server Logic
- Implement `api/endpoints.py` with all required REST endpoints
- Create `core/manager.py` with AgentManager server-side coordination
- Implement `core/llm_client.py` with async LLM abstraction
- Add comprehensive error handling and API documentation

### Phase 3: External Client Workers and Quality Control
- Implement `client_worker.py` for external worker coordination
- Create `core/worker.py` with WorkerAgent logic for client use
- Implement `core/auditor.py` with AuditorAgent for quality control
- Add client-server communication patterns and retry logic

### Phase 4: Integration Testing and Production Deployment
- Create integration tests for API endpoints and client coordination
- Implement database migrations with Alembic
- Add Docker containerization for server deployment
- Test multi-client coordination and failure recovery scenarios

## Specific Implementation Notes

### Error Handling
- Use FastAPI HTTPException for API errors
- Implement proper status codes (200, 204, 400, 404, 500)
- Handle database transaction failures gracefully
- Log API requests and errors for debugging

### API Security and Validation
- Implement request/response validation with Pydantic
- Add proper CORS configuration for external clients
- Use dependency injection for database sessions
- Implement rate limiting and request timeout handling

### Database Best Practices
- Use async SQLAlchemy operations throughout
- Implement proper connection pooling and session management
- Add database indexes for query optimization
- Use transactions for atomic operations

### LLM Integration Patterns
- Async HTTP clients with proper timeout handling
- Structured JSON enforcement for reliable parsing
- Retry logic with exponential backoff
- Token usage tracking and cost optimization

## Testing Strategy
- Unit tests for individual API endpoints
- Integration tests for client-server coordination
- Database transaction testing with rollbacks
- Multi-client concurrent execution testing
- LLM integration mocking for reliable tests

## When Generating Code
1. **Context Awareness**: Always check `.context/index.md` and `.context/docs.md` for current project state
2. Use FastAPI patterns with proper async/await
3. Implement SQLAlchemy ORM with type hints
4. Use Pydantic v2 for all API data validation
5. Follow REST API conventions and HTTP status codes
6. Add comprehensive error handling and logging
7. Ensure proper database transaction management
8. Test API endpoints with realistic client scenarios

## Codebase Context Specification (CCS) Integration

This project follows CCS v1.1 for documentation and AI tool integration:

### Context Directory Structure
```
.context/
├── index.md           # Primary context with YAML frontmatter
├── docs.md           # Detailed implementation guidelines
└── diagrams/         # Visual documentation
    ├── architecture.mmd
    └── data-flow.mmd
```

### AI Tool Integration Instructions
- **Simple Integration**: Read `.context/index.md` for architectural overview before starting tasks
- **Advanced Integration**: Parse YAML frontmatter for structured metadata, process Mermaid diagrams for visual understanding
- **Context Hierarchy**: Follow project → module → feature level context inheritance

### Documentation Standards
- Keep language clear and precise
- Update documentation alongside code changes
- Include relevant examples and API specifications
- Maintain consistency in terminology
- Regular review and validation of context information

## Common Patterns to Follow
- **FastAPI Dependency Injection**: For database sessions and configuration
- **Repository Pattern**: For database operations with ORM abstraction
- **Factory Pattern**: For creating different types of client workers
- **Strategy Pattern**: For different LLM providers and agent roles
- **Circuit Breaker Pattern**: For external API resilience

Remember: The goal is to create a robust, scalable MCP server that coordinates distributed multi-agent workflows through clean REST API patterns, comprehensive data validation, and reliable database operations.
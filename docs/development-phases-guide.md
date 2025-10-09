
## 🚀 AM (AgentManager) Development Phases Guide (MCP Server Edition)

### Phase 1: Server and Data Persistence Setup (Configuration Contract Sprint)

**Objective:** Create the service backbone, establish the ORM for SQLite, and define the configuration contract for external clients.

| Task Focus | Key Deliverables | Go/No-Go Checkpoint |
| :--- | :--- | :--- |
| **Configuration Contract** | The **`mcp_client_config.json`** file structure is finalized, detailing `client_agent_id`, `server_url`, and `auth_token`. | ✅ The `mcp_client_config` schema is defined and loaded successfully by a test script. |
| **Database & ORM** | Finalize `db.py` (SQLite/Postgres readiness) and `orm.py`. All Pydantic models must have corresponding SQLAlchemy models for persistence. | ✅ A simple ORM test successfully persists and retrieves a full `TaskGraph` structure to the SQLite file. |
| **Core API Endpoints** | Implement **`POST /v1/tasks`** and the crucial **`POST /v1/results`** endpoints, focusing only on request/response validation using Pydantic schemas. | ✅ API endpoints are live, correctly accepting the required Pydantic data and validating the `auth_token`. |

***

### Phase 2: Agent Core Logic (RA & Decoupling Sprint)

**Objective:** Implement the core Agent intelligence (RA) logic, decoupling it entirely from the API layer, and finalizing the required system prompts.

| Task Focus | Key Deliverables | Go/No-Go Checkpoint |
| :--- | :--- | :--- |
| **Worker RA Implementation** | The **`execute_task`** logic is implemented. It must run the internal loop, generating a structured **`ThoughtAction`** output at each step, and return a final `Result` object. | ✅ A test run of the Worker logic confirms the full RA history is generated and contained in the final structured `Result`. |
| **Auditor Logic** | Implement **`run_audit`** with its strict, critical system prompt. The output must be the **`AuditReport`** Pydantic object, containing actionable rework suggestions. | ✅ Auditor successfully flags a known "bad" input and returns an `AuditReport` with concrete **`rework_suggestions`**. |
| **LLM Client Finalization** | Verify the `LLMClient` strictly enforces Pydantic output for both the **Worker's RA steps** and the **Auditor's report**. | ✅ LLM calls reliably return structured Python objects, not just raw text. |

***

### Phase 3: Manager Orchestration and Control (Scheduling Sprint)

**Objective:** Implement the central MCP logic: scheduling, dependency management, and the full audit loop, making the server functional.

| Task Focus | Key Deliverables | Go/No-Go Checkpoint |
| :--- | :--- | :--- |
| **Database-Driven Planning** | **`plan_and_save_task`** is completed. It must persist the initial `TaskGraph` to the DB and mark the first tasks as `READY`. | ✅ Submitting a task via API results in a persisted `TaskGraph` with initial tasks correctly marked `READY` in the database. |
| **Dependency Scheduling** | Implement **`check_and_dispatch_ready_tasks`**. This logic must correctly query the DB, identify `READY` tasks based on dependencies, and **atomically update their status to `READY`**. | ✅ After one task is marked `COMPLETED` in the DB, the Manager correctly updates the status of its dependent tasks to `READY`. |
| **Audit Control Loop** | The logic handling the **`POST /v1/results`** endpoint (Phase 3.3) must: **update the DB result**, check for completion, and initiate the **`run_audit`** when the graph is complete. | ✅ Submitting a final result triggers the audit. If the audit fails, the DB is updated with rework notes, and necessary tasks are reset to `PENDING` to trigger the rework cycle. |

***

### Phase 4: Client Simulation and Production Readiness

**Objective:** Create the external Worker Client, prove the decoupled system works, and validate the project's resilience.

| Task Focus | Key Deliverables | Go/No-Go Checkpoint |
| :--- | :--- | :--- |
| **Worker Client Implementation** | Create **`client_worker.py`**. It must implement the **polling loop** and use `httpx` for all API calls (polling tasks and reporting results), strictly adhering to the **`mcp_client_config.json`** for its identity. | ✅ Running the client script successfully connects to the AM server, polls for a task, executes it, and posts the result back to the server API. |
| **Concurrency Validation** | Run the server and multiple `client_worker.py` instances simultaneously. **Verify through database logs** that the scheduling logic successfully handles concurrent requests, and that **atomic status updates prevent tasks from being claimed by two workers**. | ✅ Concurrency is validated; no two workers execute the same task, and status transitions are reliable under load. |
| **Full Resilience Test** | Conduct an end-to-end integration test involving parallel tasks, dependency locking, and at least one **forced audit failure**. Verify the entire system—from client polling to server rework update—functions to complete the task successfully. | ✅ The system demonstrates full resilience, successfully executing the **Parallel $\rightarrow$ Audit $\rightarrow$ Rework $\rightarrow$ Synthesis** cycle. |
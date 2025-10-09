
---

## 🗺️ Full Project Roadmap: AM (AgentManager) - Centralized MCP Server

**Core Principle:** The AM system is a centralized **FastAPI server** managing state via SQLite (with PostgreSQL readiness). Worker Agents are **decoupled HTTP clients** that poll the server for tasks using a local configuration file.

### Phase 0: Server Infrastructure and Configuration Contract

**Objective:** Establish the FastAPI server, define persistence via SQLAlchemy ORM, and create the necessary configuration files for both the server and the external Worker clients.

| Step | File/Action | Description & Copilot Prompt Guidance |
| :--- | :--- | :--- |
| **0.1** | `pyproject.toml` | **Dependencies:** Add `fastapi`, `uvicorn`, `SQLAlchemy`, `pydantic`, and `psycopg2-binary`. |
| **0.2** | `.env` | **Server Configuration:** Define `DATABASE_URL` (SQLite default) and `SERVER_API_TOKEN` for securing endpoints. |
| **0.3** | `agent_manager/db.py` | **SQLAlchemy Engine & Session:** Implement the DB setup, ensuring the engine can be switched between SQLite and PostgreSQL based on `DATABASE_URL`. |
| **0.4** | `agent_manager/orm.py` | **ORM Models:** Define `TaskGraphORM`, `TaskStepORM`, and `ResultORM`. Include a **`status`** field (e.g., PENDING, READY, IN_PROGRESS, COMPLETED) for state management. |
| **0.5** | `mcp_client_config.json` | **Worker Configuration Contract:** Define the required structure for the external Worker's local configuration file. Must include: **`client_agent_id`**, **`server_url`**, **`auth_token`**, and **`polling_interval_sec`**. |
| **0.6** | `main.py` | **FastAPI App Setup:** Initialize the FastAPI app and integrate DB connection/shutdown hooks. |

---

### Phase 1: Data Contracts and API Definitions

**Objective:** Finalize all Pydantic schemas and define the core communication endpoints the external Workers will use.

| Step | File/Action | Description & Copilot Prompt Guidance |
| :--- | :--- | :--- |
| **1.1** | `agent_manager/models.py` | **Pydantic Schemas:** Define `TaskGraph`, `ThoughtAction`, `Result`, and `AuditReport`. These models define the **input/output for all API endpoints**. |
| **1.2** | `agent_manager/api/endpoints.py` | **API Endpoint: Task Submission:** Implement **`POST /v1/tasks`** to receive new user requests. Requires validation via Pydantic model (`UserTaskRequest`). |
| **1.3** | `agent_manager/api/endpoints.py` | **API Endpoint: Task Polling/Distribution:** Implement **`GET /v1/tasks/ready`**. This endpoint accepts a query parameter for **`agent_id`** and returns the oldest task currently marked **`READY`** for that agent. Requires **`auth_token`** validation. |
| **1.4** | `agent_manager/api/endpoints.py` | **API Endpoint: Result Reporting:** Implement **`POST /v1/results`**. This endpoint receives the completed, structured `Result` from a Worker. Requires **`auth_token`** validation and passes the data to the Manager's control logic. |

---

### Phase 2: Agent Core Logic (RA and Auditing)

**Objective:** Implement the internal, reusable business logic for Agent behavior, decoupled from the API layer.

| Step | File/Action | Description & Copilot Prompt Guidance |
| :--- | :--- | :--- |
| **2.1** | `agent_manager/core/llm_client.py` | **Async LLM Client:** Implement the `LLMClient` with `async` methods to strictly enforce Pydantic output. |
| **2.2** | `agent_manager/core/worker.py` | **Worker Execution Logic:** Implement **`async execute_task(task_step_data)`**. This function contains the Worker's **iterative RA loop** (forcing `ThoughtAction` output) and returns the final structured `Result`. |
| **2.3** | `agent_manager/core/auditor.py` | **Auditor Logic:** Implement **`async run_audit(task_graph, results)`**. This function contains the critical audit prompt logic and forces the actionable **`AuditReport`** output. |
| **2.4** | `agent_manager/core/worker.py` | **LLM Prompts:** Define the detailed system prompts for the Worker and Auditor, emphasizing the RA pattern and their specific roles. |

---

### Phase 3: Manager Orchestration and Control

**Objective:** Implement the central control logic: planning, dependency resolution, status management, and the crucial audit loop, all centered on the database.

| Step | File/Action | Description & Copilot Prompt Guidance |
| :--- | :--- | :--- |
| **3.1** | `agent_manager/core/manager.py` | **Task Planning:** Implement **`plan_and_save_task(user_request)`**. Generates the `TaskGraph` (with dependencies) and **saves it to the ORM/DB** with all statuses set to `PENDING`. |
| **3.2** | `agent_manager/core/manager.py` | **Dependency Resolver & Dispatcher:** Implement **`check_and_dispatch_ready_tasks(graph_id)`**. This function: 1) Queries the DB to find `PENDING` tasks whose dependencies are `COMPLETED`. 2) **Atomically** updates their status to **`READY`** in the DB. |
| **3.3** | `agent_manager/core/manager.py` | **Result Handler & Audit Loop Trigger:** Implement the logic for the `/v1/results` endpoint (Phase 1.4). This logic must: Update the result and status in the DB, and **if all tasks are done**, trigger the **`run_audit`** function. |
| **3.4** | `agent_manager/core/manager.py` | **Audit State Update:** Implement the core loop logic: If audit fails, the Manager **updates the DB ORM** with the `rework_suggestions` and resets the required task statuses to **`READY`** or `PENDING`, initiating the rework cycle. |

---

### Phase 4: Client Development and System Validation

**Objective:** Create the external Worker Client, proving the decoupled system works, and finalizing the project.

| Step | File/Action | Description & Copilot Prompt Guidance |
| :--- | :--- | :--- |
| **4.1** | `client_worker.py` | **Worker Client Logic:** Create the external client script. It must: 1) Load **`mcp_client_config.json`**. 2) Implement a polling loop using `asyncio` and `httpx` to continuously call **`GET /v1/tasks/ready`**. 3) Call the local **`execute_task`** logic (Phase 2.2). 4) **POST** the result back to **`/v1/results`**. |
| **4.2** | `client_worker.py` | **Concurrency Management:** The client must honor the **`max_parallel_tasks`** setting from its local configuration to limit local resource usage. |
| **4.3** | `main.py` | **Final Server Setup:** Ensure the server correctly handles multiple concurrent **`GET`** and **`POST`** requests from multiple simulated clients, proving it's ready for multi-device operation. |
| **4.4** | `tests/integration_test.py` | **End-to-End Validation:** Write an integration test that simulates the entire workflow from task submission, through client polling, parallel execution, and the final audit/rework cycle. |

---

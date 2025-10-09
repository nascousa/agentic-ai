# AM (AgentManager) - Distributed State Management

```mermaid
graph TB
    subgraph "FastAPI Server State"
        ServerState[Server State]
        ServerState --> TaskGraphs[Task Graphs<br/>workflow_id -> TaskGraph]
        ServerState --> TaskSteps[Task Steps<br/>step_id -> TaskStep]
        ServerState --> Results[Results<br/>task_id -> RAHistory]
        ServerState --> AuditReports[Audit Reports<br/>workflow_id -> AuditReport]
        ServerState --> FileLocks[File Access Locks<br/>file_path -> FileAccess]
    end
    
    subgraph "Database Persistence Layer"
        Database[(SQLAlchemy Database)]
        Database --> TaskGraphORM[TaskGraphORM<br/>Persistent Workflows]
        Database --> TaskStepORM[TaskStepORM<br/>Task Coordination]
        Database --> ResultORM[ResultORM<br/>Execution History]
        Database --> AuditReportORM[AuditReportORM<br/>Quality Control]
        Database --> FileAccessORM[FileAccessORM<br/>File Coordination]
    end
    
    subgraph "External Client 1 State"
        Client1State[Client 1 State]
        Client1State --> C1CurrentTask[Current Task<br/>TaskStep]
        Client1State --> C1ExecutionState[Execution State<br/>RAHistory]
        Client1State --> C1FileLocks[Acquired File Locks<br/>Set[file_path]]
        Client1State --> C1LLMContext[LLM Context<br/>ThoughtAction[]]
    end
    
    subgraph "External Client 2 State"
        Client2State[Client 2 State]
        Client2State --> C2CurrentTask[Current Task<br/>TaskStep]
        Client2State --> C2ExecutionState[Execution State<br/>RAHistory]
        Client2State --> C2FileLocks[Acquired File Locks<br/>Set[file_path]]
        Client2State --> C2LLMContext[LLM Context<br/>ThoughtAction[]]
    end
    
    subgraph "External Client N State"
        ClientNState[Client N State]
        ClientNState --> CNCurrentTask[Current Task<br/>TaskStep]
        ClientNState --> CNExecutionState[Execution State<br/>RAHistory]
        ClientNState --> CNFileLocks[Acquired File Locks<br/>Set[file_path]]
        ClientNState --> CNLLMContext[LLM Context<br/>ThoughtAction[]]
    end
    
    subgraph "State Synchronization"
        APIEndpoints[REST API Endpoints]
        APIEndpoints --> GetTasks[GET /v1/tasks/{role}/ready]
        APIEndpoints --> ReportResults[POST /v1/report_result]
        APIEndpoints --> StatusCheck[GET /v1/workflows/{id}/status]
        APIEndpoints --> FileCoordination[File Lock Coordination]
    end
    
    %% State Synchronization Flows
    TaskGraphs -.->|Read| TaskGraphORM
    TaskSteps -.->|Read/Write| TaskStepORM
    Results -.->|Write| ResultORM
    AuditReports -.->|Write| AuditReportORM
    FileLocks -.->|Read/Write| FileAccessORM
    
    %% Client Communication
    GetTasks -.->|Pull| TaskSteps
    C1CurrentTask -.->|Push| ReportResults
    C2CurrentTask -.->|Push| ReportResults
    CNCurrentTask -.->|Push| ReportResults
    
    %% File Lock Coordination
    FileCoordination -.->|Coordinate| C1FileLocks
    FileCoordination -.->|Coordinate| C2FileLocks
    FileCoordination -.->|Coordinate| CNFileLocks
    FileLocks -.->|Track| FileCoordination
    
    %% Status Propagation
    Results -.->|Update| StatusCheck
    TaskSteps -.->|Monitor| StatusCheck
    
    classDef serverNode fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef clientNode fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef dbNode fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef syncNode fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef fileNode fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class ServerState,TaskGraphs,TaskSteps,Results,AuditReports serverNode
    class Client1State,Client2State,ClientNState,C1CurrentTask,C2CurrentTask,CNCurrentTask,C1ExecutionState,C2ExecutionState,CNExecutionState,C1LLMContext,C2LLMContext,CNLLMContext clientNode
    class Database,TaskGraphORM,TaskStepORM,ResultORM,AuditReportORM dbNode
    class APIEndpoints,GetTasks,ReportResults,StatusCheck syncNode
    class FileLocks,FileAccessORM,C1FileLocks,C2FileLocks,CNFileLocks,FileCoordination fileNode
```

## Distributed State Management Overview

This diagram illustrates how state is managed across the distributed AM (AgentManager) system, showing the coordination between the central FastAPI server, persistent database layer, and multiple external client workers.

### Key State Management Features

- **Centralized Coordination**: Server maintains authoritative state in database
- **Distributed Execution**: Clients maintain local execution state independently
- **File Access Safety**: Coordinated file locking prevents concurrent conflicts
- **Async Synchronization**: REST API endpoints enable eventual consistency

# AM (AgentManager) - System Architecture

```mermaid
graph TB
    subgraph "External Clients"
        Client1[Client Worker 1<br/>Role: Researcher]
        Client2[Client Worker 2<br/>Role: Writer]
        Client3[Client Worker 3<br/>Role: Analyst]
    end
    
    subgraph "FastAPI MCP Server"
        API[FastAPI Application]
        Endpoints[API Endpoints]
        Core[Agent Core Logic]
        
        subgraph "API Endpoints"
            Submit[POST /v1/submit_task]
            Report[POST /v1/report_result]
            Poll[GET /v1/tasks/{role}/ready]
            Health[GET /health]
        end
        
        subgraph "Core Logic"
            Manager[AgentManager]
            Worker[WorkerAgent Logic]
            Auditor[AuditorAgent Logic]
            LLM[LLMClient]
            FileLock[File Access Manager]
        end
    end
    
    subgraph "Database Layer"
        ORM[SQLAlchemy ORM]
        DB[(SQLite/PostgreSQL)]
        
        subgraph "ORM Models"
            TaskGraphORM[TaskGraphORM]
            TaskStepORM[TaskStepORM] 
            ResultORM[ResultORM]
            AuditORM[AuditReportORM]
            FileAccessORM[FileAccessORM]
        end
    end
    
    subgraph "File Coordination System"
        FileManager[File Access Manager]
        OSLocks[OS-Level Locks<br/>fcntl/msvcrt]
        DBLocks[Database Locks<br/>FileAccessORM]
        
        FileManager --> OSLocks
        FileManager --> DBLocks
    end
    
    subgraph "Workflow Execution"
        User[User/System] --> Submit
        Submit --> Manager
        Manager --> TaskGraphORM
        TaskGraphORM --> DB
        
        Client1 --> Poll
        Client2 --> Poll
        Client3 --> Poll
        Poll --> TaskStepORM
        
        Client1 --> Report
        Client2 --> Report
        Client3 --> Report
        Report --> ResultORM
        
        Manager --> Auditor
        Auditor --> AuditORM
        AuditORM --> DB
        
        Manager --> LLM
        Worker --> LLM
        Auditor --> LLM
        
        Worker --> FileLock
        FileLock --> FileManager
    end
    
    API --> Endpoints
    Endpoints --> Core
    Core --> ORM
    ORM --> DB
    
    classDef client fill:#e3f2fd,stroke:#01579b,stroke-width:2px
    classDef server fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef database fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef api fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef logic fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef fileSystem fill:#fff8e1,stroke:#f57f17,stroke-width:2px
    
    class Client1,Client2,Client3 client
    class API,Endpoints,Core server
    class DB,ORM,TaskGraphORM,TaskStepORM,ResultORM,AuditORM,FileAccessORM database
    class Submit,Report,Poll,Health api
    class Manager,Worker,Auditor,LLM,FileLock logic
    class FileManager,OSLocks,DBLocks fileSystem
```

## Architecture Overview

The AM (AgentManager) system follows a centralized Multi-Agent Coordination/Planning (MCP) server architecture with enhanced file access coordination and distributed worker execution.

### Key Components

- **External Clients**: Distributed worker clients with specialized roles (Researcher, Writer, Analyst)
- **FastAPI MCP Server**: Central coordination server with REST API endpoints
- **Database Layer**: SQLAlchemy ORM with SQLite/PostgreSQL support
- **File Coordination System**: Multi-level file locking for concurrent worker safety

### Enhanced Features

- **File Access Coordination**: Cross-platform file locking preventing concurrent conflicts
- **Database-Tracked Locks**: Server-side coordination with FileAccessORM
- **Worker Agent Integration**: Automatic file safety in task execution
- **Atomic Operations**: Transaction safety for concurrent client operations
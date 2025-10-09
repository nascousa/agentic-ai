# AM (AgentManager) - Task Dependencies Graph

```mermaid
graph TD
    subgraph "Workflow: User Research Project"
        %% Initial Planning Tasks
        A[Task A: Define Research Scope<br/>Role: researcher<br/>Dependencies: []<br/>Status: READY]
        B[Task B: Identify Key Questions<br/>Role: researcher<br/>Dependencies: [A]<br/>Status: PENDING]
        
        %% Research Execution Tasks
        C[Task C: Literature Review<br/>Role: researcher<br/>Dependencies: [B]<br/>Status: PENDING]
        D[Task D: Data Collection<br/>Role: analyst<br/>Dependencies: [B]<br/>Status: PENDING]
        E[Task E: Survey Design<br/>Role: researcher<br/>Dependencies: [B]<br/>Status: PENDING]
        
        %% Analysis Tasks
        F[Task F: Statistical Analysis<br/>Role: analyst<br/>Dependencies: [C, D]<br/>Status: PENDING]
        G[Task G: Content Analysis<br/>Role: analyst<br/>Dependencies: [C, E]<br/>Status: PENDING]
        
        %% Synthesis Tasks
        H[Task H: Results Integration<br/>Role: researcher<br/>Dependencies: [F, G]<br/>Status: PENDING]
        I[Task I: Conclusion Drafting<br/>Role: writer<br/>Dependencies: [H]<br/>Status: PENDING]
        
        %% Final Tasks
        J[Task J: Report Writing<br/>Role: writer<br/>Dependencies: [I]<br/>Status: PENDING]
        K[Task K: Final Review<br/>Role: auditor<br/>Dependencies: [J]<br/>Status: PENDING]
    end
    
    subgraph "File Dependencies"
        %% File coordination examples
        F1[research_scope.md<br/>READ: Task B<br/>WRITE: Task A]
        F2[questions.json<br/>READ: Task C, D, E<br/>WRITE: Task B]
        F3[literature.md<br/>READ: Task F<br/>WRITE: Task C]
        F4[data.csv<br/>READ: Task F<br/>WRITE: Task D]
        F5[survey.json<br/>READ: Task G<br/>WRITE: Task E]
        F6[analysis_results.json<br/>READ: Task H<br/>WRITE: Task F, G]
        F7[final_report.md<br/>READ: Task K<br/>WRITE: Task J]
    end
    
    %% Task Dependencies
    A --> B
    B --> C
    B --> D
    B --> E
    C --> F
    D --> F
    C --> G
    E --> G
    F --> H
    G --> H
    H --> I
    I --> J
    J --> K
    
    %% File Dependencies
    A -.->|writes| F1
    B -.->|reads| F1
    B -.->|writes| F2
    C -.->|reads| F2
    D -.->|reads| F2
    E -.->|reads| F2
    C -.->|writes| F3
    F -.->|reads| F3
    D -.->|writes| F4
    F -.->|reads| F4
    E -.->|writes| F5
    G -.->|reads| F5
    F -.->|writes| F6
    G -.->|writes| F6
    H -.->|reads| F6
    J -.->|writes| F7
    K -.->|reads| F7
    
    %% Status Styling
    classDef ready fill:#c8e6c9,stroke:#4caf50,stroke-width:3px
    classDef pending fill:#ffecb3,stroke:#ff9800,stroke-width:2px
    classDef inProgress fill:#bbdefb,stroke:#2196f3,stroke-width:3px
    classDef completed fill:#e1bee7,stroke:#9c27b0,stroke-width:2px
    classDef fileRead fill:#fff3e0,stroke:#e65100,stroke-width:1px
    classDef fileWrite fill:#ffebee,stroke:#c62828,stroke-width:1px
    
    class A ready
    class B,C,D,E,F,G,H,I,J,K pending
    class F1,F2,F3,F4,F5,F6,F7 fileRead
```


## Task Dependencies Overview

This diagram shows a complete task dependency graph for a research project workflow, illustrating how tasks must be executed in specific order based on their dependencies and file access requirements.

### Key Dependency Features

- **Sequential Dependencies**: Tasks must wait for prerequisite completion
- **Parallel Execution**: Independent tasks can run simultaneously
- **File Coordination**: Read/write dependencies prevent conflicts
- **Role-Based Assignment**: Tasks routed to appropriate agent types


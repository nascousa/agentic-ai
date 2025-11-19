# Data Model Relationship Analysis - Projects, Workflows, and Tasks

## Current Date: October 14, 2025 PST

## Executive Summary

Based on the design requirements analysis, the AgentManager system has a **2-tier hierarchy** (Workflow → Tasks) but **SHOULD have a 3-tier hierarchy** (Project → Workflows → Tasks) for better organization and scalability.

## Current Data Model (2-Tier)

### Existing Hierarchy
```
Workflow (TaskGraphORM)
    ├── Task 1 (TaskStepORM)
    ├── Task 2 (TaskStepORM)
    └── Task N (TaskStepORM)
```

### Current ORM Models

#### 1. TaskGraphORM (Workflow Level)
```python
class TaskGraphORM(Base):
    __tablename__ = "task_graphs"
    
    # Primary identification
    id: UUID                          # Internal database ID
    workflow_id: str                  # External workflow identifier
    
    # Content
    user_request: str                 # Original user request
    workflow_metadata: Dict[str, Any] # Additional metadata
    
    # Status & timing
    status: str                       # PENDING, IN_PROGRESS, COMPLETED, FAILED
    created_at: datetime              # Creation timestamp
    updated_at: datetime              # Last update
    
    # Relationships
    tasks: List[TaskStepORM]          # One-to-many with tasks
    audit_reports: List[AuditReportORM] # One-to-many with audits
```

#### 2. TaskStepORM (Task Level)
```python
class TaskStepORM(Base):
    __tablename__ = "task_steps"
    
    # Primary identification
    id: UUID                          # Internal database ID
    step_id: str                      # External step identifier
    workflow_id: str                  # Foreign key to TaskGraphORM
    
    # Content
    task_description: str             # Detailed task description
    assigned_agent: str               # Agent type for execution
    
    # Dependencies
    dependencies: List[str]           # List of step_ids that must complete first
    file_dependencies: List[str]      # File paths this task accesses
    file_access_types: Dict[str, str] # File access types (read/write/exclusive)
    
    # Status & timing
    status: str                       # PENDING, READY, IN_PROGRESS, COMPLETED, FAILED
    created_at: datetime              # Creation timestamp
    updated_at: datetime              # Last update
    
    # Relationships
    task_graph: TaskGraphORM          # Many-to-one with workflow
    results: List[ResultORM]          # One-to-many with results
```

## Proposed Data Model (3-Tier)

### Enhanced Hierarchy
```
Project (ProjectORM) - NEW
    ├── Workflow 1 (TaskGraphORM)
    │   ├── Task 1.1 (TaskStepORM)
    │   ├── Task 1.2 (TaskStepORM)
    │   └── Task 1.N (TaskStepORM)
    ├── Workflow 2 (TaskGraphORM)
    │   ├── Task 2.1 (TaskStepORM)
    │   └── Task 2.M (TaskStepORM)
    └── Workflow N (TaskGraphORM)
        └── Tasks...
```

### Benefits of 3-Tier Model

#### 1. Better Organization
- **Projects**: High-level business objectives (e.g., "Build Calculator App", "Create Dashboard")
- **Workflows**: Sequential processes within projects (e.g., "Planning Phase", "Development Phase", "Testing Phase")
- **Tasks**: Individual actions within workflows (e.g., "Create UI Layout", "Implement Calculator Logic")

#### 2. Enhanced Tracking
- **Project Progress**: Aggregate of all workflows within project
- **Workflow Progress**: Aggregate of all tasks within workflow
- **Task Progress**: Individual task completion status

#### 3. Better Scalability
- Complex projects with multiple workflows become manageable
- Clear separation of concerns
- Easier reporting and analytics

## Current Dashboard Analysis

### Existing Tabs (4 tabs)
1. **👷 Workers** - Container and worker status monitoring
2. **📊 Workflows** - TaskGraphORM records display
3. **📋 Tasks** - TaskStepORM records display  
4. **📈 Metrics** - System performance monitoring

### What's Missing: Projects Tab

The dashboard currently shows:
- **Workflows**: Direct display of TaskGraphORM records
- **Tasks**: Direct display of TaskStepORM records

But there's no concept of **Projects** that group related workflows together.

## Relationship Analysis

### Current Relationships
```
Database:
TaskGraphORM (1) ←→ (many) TaskStepORM
TaskGraphORM (1) ←→ (many) AuditReportORM
TaskStepORM (1) ←→ (many) ResultORM

Dashboard Display:
Workflows Tab: Shows TaskGraphORM records
Tasks Tab: Shows TaskStepORM records
```

### Proposed Relationships
```
Database:
ProjectORM (1) ←→ (many) TaskGraphORM
TaskGraphORM (1) ←→ (many) TaskStepORM
TaskStepORM (1) ←→ (many) ResultORM

Dashboard Display:
Projects Tab: Shows ProjectORM records
Workflows Tab: Shows TaskGraphORM records (filtered by selected project)
Tasks Tab: Shows TaskStepORM records (filtered by selected workflow)
```

## Dashboard Enhancement Plan

### Current Dashboard Structure
```
AgentManagerDashboard
├── 👷 Workers (13 workers in 4-column grid)
├── 📊 Workflows (TaskGraphORM records)
├── 📋 Tasks (TaskStepORM records)
└── 📈 Metrics (System monitoring)
```

### Proposed Enhanced Dashboard Structure
```
AgentManagerDashboard
├── 🎯 Projects (NEW - ProjectORM records)
├── 📊 Workflows (TaskGraphORM records - filtered by selected project)
├── 📋 Tasks (TaskStepORM records - filtered by selected workflow)
├── 👷 Workers (13 workers in 4-column grid)
└── 📈 Metrics (System monitoring)
```

## Timezone Requirements: PST Everywhere

### Current Timezone Issues
1. **Database timestamps**: Stored in UTC by default
2. **Display formatting**: Some places may not show PST
3. **API responses**: May return UTC timestamps

### PST Implementation Plan

#### 1. Application Level (Convert to PST for display)
```python
from datetime import timezone, timedelta

PST = timezone(timedelta(hours=-8))  # PST is UTC-8

def to_pst(utc_datetime: datetime) -> datetime:
    """Convert UTC datetime to PST for display"""
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    return utc_datetime.astimezone(PST)

def format_pst_timestamp(dt: datetime) -> str:
    """Format datetime as PST string"""
    pst_dt = to_pst(dt)
    return pst_dt.strftime("%Y-%m-%d %H:%M:%S PST")
```

## Immediate Action Plan

Since the analysis shows we need a Projects tab and PST timezone consistency, let me implement these changes:

### 1. Add PST timezone utility functions
### 2. Add Projects tab to dashboard
### 3. Update existing timestamp displays to PST

## Conclusion and Recommendations

**"What's the relationship between workflow/task/project? Should there be a project tab?"**

**YES, absolutely!** The current system has a 2-tier model (Workflow → Tasks) but **should have a 3-tier model** (Project → Workflows → Tasks) for better organization. A **Projects tab is essential** for:

1. **Grouping related workflows** under common business objectives
2. **Providing project-level progress tracking** and reporting  
3. **Enabling better navigation** and context switching
4. **Supporting complex multi-workflow projects** like software development

The enhanced dashboard should show:
- **Projects Tab**: High-level project management and progress
- **Workflows Tab**: Filtered by selected project, showing workflow phases
- **Tasks Tab**: Filtered by selected workflow, showing individual actions

All timestamps should be displayed in **PST timezone** as requested.

---

**Analysis Date**: October 14, 2025 PST  
**Status**: Ready for implementation  
**Priority**: High - Essential for project scalability
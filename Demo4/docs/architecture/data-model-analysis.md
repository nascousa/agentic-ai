# AgentManager Data Model Analysis
## Relationship Between Workflow, Task, and Project

**Analysis Date**: October 14, 2025

## Current Data Model Structure

### Hierarchy Overview
Based on the design requirements and ORM implementation, the current system has a **2-tier hierarchy**:

```
TaskGraphORM (Workflow)
    ↓ one-to-many
TaskStepORM (Task)
    ↓ one-to-many  
ResultORM (Task Results)
```

### 🔍 Key Finding: NO PROJECT ENTITY EXISTS

**Important Discovery**: The current design does **NOT include a Project concept**. The system uses:

1. **TaskGraph/Workflow** = Top-level organizational unit (what you might call a "project")
2. **TaskStep/Task** = Individual units of work within a workflow
3. **Result** = Output/completion record for each task

## Terminology Clarification

### Current System Terminology

| Database Term | API/Code Term | Dashboard Display | Meaning |
|---------------|---------------|-------------------|---------|
| `TaskGraphORM` | `TaskGraph` | "Workflow" | Top-level work container |
| `workflow_id` | `workflow_id` | "Workflow ID" | Unique identifier for the graph |
| `TaskStepORM` | `TaskStep` | "Task" | Individual work unit |
| `step_id` | `step_id` | "Task ID/Name" | Unique identifier for the step |

### Semantic Analysis

**"Workflow"** in this system actually means:
- A **collection of related tasks** working toward a common goal
- What might traditionally be called a **"project"** in project management
- Example: "Build Python Calculator" is ONE workflow/project with multiple tasks

**"Task"** means:
- A single, atomic unit of work
- Has dependencies on other tasks
- Assigned to a specific agent role
- Example: "Create calculator.py file" is ONE task

## Current Dashboard Structure

### Tab Layout
```
┌─────────────────────────────────────────┐
│  👷 Workers  │  📊 Workflows  │  📋 Tasks  │  📈 Metrics  │
└─────────────────────────────────────────┘
```

### What Each Tab Shows

#### 1. **Workers Tab** (👷)
Shows the 13 Docker containers:
- 3 infrastructure (agent-manager, postgres, redis)
- 10 worker containers (analysts, developers, etc.)
- **Purpose**: Monitor which workers are available/busy

#### 2. **Workflows Tab** (📊)
Shows TaskGraphs from database:
- Each row = one workflow/project
- Columns: Created, ID, Name, Description, Status, Progress
- **Current Issue**: No clear project grouping

#### 3. **Tasks Tab** (📋)
Shows TaskSteps from database:
- Each row = one task
- Columns: ID, Name, Workflow, Agent, Status, Description, Updated
- **Current Issue**: Workflow relationship only shown as ID

#### 4. **Metrics Tab** (📈)
Shows system-wide statistics:
- Total workflows, tasks, completed counts
- Worker utilization
- **Current Issue**: No project-level metrics

## Relationship Problems Identified

### ❌ Problem 1: Missing Project Concept
**Current State**: No explicit "Project" entity
**Impact**: 
- Can't group multiple related workflows together
- No way to track "Python Calculator Project" containing both "Build App" and "Write Tests" workflows

**Example Scenario**:
```
Desired:
  Project: "AgentManager System"
    ├── Workflow: "Build Dashboard"
    │   ├── Task: "Create UI components"
    │   └── Task: "Implement API client"
    └── Workflow: "Setup Monitoring"
        ├── Task: "Configure Prometheus"
        └── Task: "Setup Grafana"

Current:
  Workflow: "Build Dashboard" (standalone)
  Workflow: "Setup Monitoring" (standalone, no connection)
```

### ❌ Problem 2: Workflow-Task Relationship Not Visible
**Current State**: Tasks show `workflow_id` as a UUID string
**Impact**:
- Can't easily see which tasks belong to which workflow
- No hierarchical view or filtering
- Users must mentally map UUIDs to workflow names

**Dashboard Display**:
```
Tasks Tab:
┌──────────┬────────────┬───────────────────────┬───────┐
│ Task ID  │ Name       │ Workflow ID           │ Agent │
├──────────┼────────────┼───────────────────────┼───────┤
│ b4300... │ create_ui  │ fa3fe9df-8e21-4321... │ dev   │  ← UUID not helpful
│ c5411... │ setup_api  │ fa3fe9df-8e21-4321... │ dev   │  ← Same workflow, not obvious
│ d6522... │ test_code  │ a2b1c3d4-5e6f-7g8h... │ test  │  ← Different workflow
└──────────┴────────────┴───────────────────────┴───────┘
```

### ❌ Problem 3: No Hierarchical Navigation
**Current State**: Flat list views for both workflows and tasks
**Impact**:
- Can't drill down from workflow to see its tasks
- Can't roll up from task to see its workflow context
- No parent-child navigation

### ❌ Problem 4: Timezone Inconsistency (CRITICAL)
**Current State**: Multiple timezone formats in use
**Impact**: Confusion and incorrect time displays

**Issues Found**:
1. Database stores `datetime` with `timezone=True` (likely UTC)
2. Dashboard shows PST for current time display
3. Workflow/Task timestamps might not be in PST

## Proposed Solutions

### 🎯 Solution 1: Add Workflow Context to Tasks Tab

**Implementation**: Add "Workflow Name" column to Tasks tab

**Before**:
```python
columns = ('Created', 'ID', 'Name', 'Workflow', 'Agent', 'Status', 'Description')
# Workflow shows as UUID: "fa3fe9df-8e21..."
```

**After**:
```python
columns = ('Created', 'ID', 'Name', 'Workflow', 'Agent', 'Status', 'Description')
# Workflow shows as Name: "Build Python Calculator"
```

**Database Query Change**:
```sql
-- Current query
SELECT id, step_id, workflow_id, assigned_agent, status, description
FROM task_steps;

-- Improved query with JOIN
SELECT 
    ts.id, 
    ts.step_id, 
    tg.workflow_id,
    tg.user_request as workflow_name,  -- Show workflow name instead of UUID
    ts.assigned_agent, 
    ts.status, 
    ts.description
FROM task_steps ts
JOIN task_graphs tg ON ts.workflow_id = tg.workflow_id;
```

**Benefits**:
- ✅ Immediate context: see which workflow owns each task
- ✅ No schema changes needed
- ✅ Simple JOIN operation
- ✅ Better user experience

### 🎯 Solution 2: Add Filtering/Grouping in Tasks Tab

**Implementation**: Add dropdown to filter tasks by workflow

```
Tasks Tab:
┌─────────────────────────────────────────┐
│ Filter by Workflow: [All Workflows ▼]  │
├─────────────────────────────────────────┤
│ Task List (filtered)                    │
└─────────────────────────────────────────┘
```

**Code Addition**:
```python
# Add dropdown
filter_frame = tk.Frame(tasks_frame)
filter_frame.pack(fill='x', padx=20, pady=5)

tk.Label(filter_frame, text="Filter by Workflow:").pack(side='left')
self.workflow_filter = ttk.Combobox(filter_frame, state='readonly')
self.workflow_filter.pack(side='left', padx=10)
self.workflow_filter.bind('<<ComboboxSelected>>', self.filter_tasks)
```

**Benefits**:
- ✅ Focus on specific workflow's tasks
- ✅ Reduces visual clutter
- ✅ Better task discovery

### 🎯 Solution 3: Add Project Tab (Future Enhancement)

**When Needed**: If you start managing multiple related workflows

**Database Schema Addition**:
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    project_id VARCHAR(255) UNIQUE NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Add foreign key to task_graphs
ALTER TABLE task_graphs 
ADD COLUMN project_id VARCHAR(255) REFERENCES projects(project_id);
```

**Hierarchy**:
```
Project (e.g., "AgentManager System")
    ↓ one-to-many
TaskGraph/Workflow (e.g., "Build Dashboard", "Add Monitoring")
    ↓ one-to-many
TaskStep/Task (e.g., "Create UI", "Setup Prometheus")
    ↓ one-to-many
Result (e.g., "UI Created Successfully")
```

**Dashboard Addition**:
```
┌───────────────────────────────────────────────────────┐
│  📁 Projects  │  👷 Workers  │  📊 Workflows  │  📋 Tasks  │
└───────────────────────────────────────────────────────┘
```

**Benefits**:
- ✅ Group related workflows
- ✅ Project-level metrics
- ✅ Better organization for large systems

**Recommendation**: **NOT needed immediately** because:
- Current system handles single-project scenarios well
- Workflows already serve as "projects" effectively
- Adding complexity without current need

### 🎯 Solution 4: Fix All Timezone Issues (CRITICAL - DO THIS NOW)

**Problem Areas**:
1. Database timestamps
2. Workflow created_at display
3. Task updated_at display
4. Current time display (already in PST)

**Implementation**:

#### Part 1: Ensure Database Stores UTC
```python
# agent_manager/orm.py
from datetime import datetime, timezone

# Already correct - stores UTC
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),  # timezone=True means UTC
    nullable=False,
    server_default=func.now(),
)
```

#### Part 2: Convert All Display Times to PST
```python
# app/api_client.py
from datetime import timezone, timedelta

# Add timezone conversion utility
def utc_to_pst(utc_time_str: str) -> str:
    """Convert UTC timestamp string to PST format"""
    try:
        # Parse UTC timestamp
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        
        # Convert to PST (UTC-8)
        pst_time = utc_time.astimezone(timezone(timedelta(hours=-8)))
        
        # Format as YYYY-MM-DD HH:MM:SS PST
        return pst_time.strftime('%Y-%m-%d %H:%M:%S PST')
    except Exception:
        return utc_time_str  # Return original on error
```

#### Part 3: Update Dashboard Display
```python
# app/dashboard.py - update_workflows_ui()
for workflow in workflows:
    created_pst = api_client.utc_to_pst(workflow.get('created_at', ''))
    self.workflows_tree.insert('', 'end', 
        values=(
            created_pst,  # Now in PST
            workflow.get('id', ''),
            # ... other fields
        ),
        tags=(workflow.get('status', 'PENDING'),)
    )

# app/dashboard.py - update_tasks_ui()
for task in tasks:
    updated_pst = api_client.utc_to_pst(task.get('updated_at', ''))
    self.tasks_tree.insert('', 'end',
        values=(
            updated_pst,  # Now in PST
            task.get('task_id', ''),
            # ... other fields
        ),
        tags=(task.get('status', 'PENDING'),)
    )
```

**Benefits**:
- ✅ Consistent PST display across entire dashboard
- ✅ Database stores proper UTC for portability
- ✅ Easy timezone conversion
- ✅ User-friendly time format

## Recommended Implementation Order

### Phase 1: Fix Critical Issues (Do Immediately) ⚠️
1. ✅ **Fix timezone display** - All times should show in PST
2. ✅ **Add workflow name to tasks** - Show workflow context

### Phase 2: Improve Usability (Do Soon) 📈
3. ✅ **Add workflow filtering** - Filter tasks by workflow
4. ✅ **Add task count to workflows** - Show "15/20 tasks completed"
5. ✅ **Add click navigation** - Click workflow to filter tasks

### Phase 3: Future Enhancements (When Needed) 🔮
6. ⏰ **Add Projects tab** - Only if managing multiple projects
7. ⏰ **Hierarchical tree view** - If deep nesting needed
8. ⏰ **Project-level metrics** - Aggregated statistics

## Current Design Is Mostly Correct ✅

**Good News**: The current 2-tier model is appropriate for most use cases:
- **Workflow** = What you'd typically call a "Project"
- **Task** = Individual work items
- No need for extra "Project" layer unless you're managing multiple related workflows

**Analogy**:
```
Traditional PM Tool:
  Project: "Build Website"
    → Sprint 1, Sprint 2, Sprint 3
      → Task 1, Task 2, Task 3

AgentManager (Current):
  Workflow: "Build Website"  ← This IS the project
    → Task 1, Task 2, Task 3

AgentManager (Future with Projects):
  Project: "E-commerce Platform"
    → Workflow: "Build Website"
    → Workflow: "Build Mobile App"
    → Workflow: "Setup Infrastructure"
      → Task 1, Task 2, Task 3
```

## Summary of Relationships

### Current Model (2-Tier)
```
┌──────────────────────────────────────┐
│  TaskGraph/Workflow                  │  ← Top level (acts as "project")
│  • workflow_id                       │
│  • user_request (description)        │
│  • status                            │
│  • created_at                        │
└────────────┬─────────────────────────┘
             │ one-to-many
             ↓
┌──────────────────────────────────────┐
│  TaskStep/Task                       │  ← Work unit
│  • step_id                           │
│  • workflow_id (FK)                  │
│  • task_description                  │
│  • assigned_agent                    │
│  • dependencies                      │
│  • status                            │
└────────────┬─────────────────────────┘
             │ one-to-many
             ↓
┌──────────────────────────────────────┐
│  Result                              │  ← Completion record
│  • task_step_id (FK)                 │
│  • ra_history                        │
│  • final_result                      │
└──────────────────────────────────────┘
```

### Proposed Model (3-Tier) - Optional Future
```
┌──────────────────────────────────────┐
│  Project                             │  ← Portfolio level (optional)
│  • project_id                        │
│  • project_name                      │
│  • description                       │
└────────────┬─────────────────────────┘
             │ one-to-many
             ↓
┌──────────────────────────────────────┐
│  TaskGraph/Workflow                  │  ← Work package
│  • workflow_id                       │
│  • project_id (FK)                   │
│  • user_request                      │
└────────────┬─────────────────────────┘
             │ one-to-many
             ↓
┌──────────────────────────────────────┐
│  TaskStep/Task                       │  ← Work unit
│  • step_id                           │
│  • workflow_id (FK)                  │
└────────────┬─────────────────────────┘
             │ one-to-many
             ↓
┌──────────────────────────────────────┐
│  Result                              │  ← Completion record
│  • task_step_id (FK)                 │
└──────────────────────────────────────┘
```

## Action Items

### Must Do Now (Critical) 🔴
- [ ] Fix timezone display to PST everywhere
- [ ] Add workflow name/context to Tasks tab
- [ ] Test timezone conversion with real data

### Should Do Soon (High Priority) 🟡
- [ ] Add workflow filtering to Tasks tab
- [ ] Add task count to Workflows tab
- [ ] Implement click-to-filter navigation

### Can Do Later (Nice to Have) 🟢
- [ ] Consider Projects tab if managing multiple related workflows
- [ ] Add hierarchical tree view for complex dependencies
- [ ] Implement project-level rollup metrics

---

**Conclusion**: The current 2-tier (Workflow→Task) design is **appropriate and sufficient** for most use cases. The main improvements needed are **better visualization of relationships** and **consistent PST timezone display**, not fundamental schema changes.

# Scripts Directory

This directory contains utility scripts for testing, monitoring, and maintaining AgentManager.

## Test Scripts

### Database Testing
- `check_db.py` - Verify database contents and query workflows/tasks
- `test_db_direct.py` - Direct database connection and save testing
- `test_db_init.py` - Database initialization tests

### API Testing
- `test_api_direct.py` - Direct API endpoint testing with authentication
- `test_api_endpoints.py` - Comprehensive API endpoint test suite
- `test_client_worker.py` - Worker client functionality tests

### Environment
- `check_env.py` - Verify environment variables and configuration

## Workflow Submission Scripts

- `submit_calc_app.py` - Submit calculator app project workflow
- `submit_calculator_project.py` - Alternative calculator project submission
- `submit_paint_app.py` - Submit paint application project workflow

## Monitoring Scripts

- `monitor_workflow.py` - Monitor workflow execution and progress
- `monitor_paint_app.ps1` - PowerShell script to monitor paint app workflow
- `synthesize_workflow.py` - Synthesize workflow results

## Migration Scripts

- `migrate_add_workflow_name.py` - Database migration to add workflow_name column

## Utility Scripts

- `create_project_dir.py` - Create project directories with automatic conflict resolution
- `generate_keys.py` - Generate authentication keys and tokens

### create_project_dir.py
**Purpose**: Create project directories under `projects/<today's date>/` with automatic name conflict resolution.

**Usage**:
```bash
python scripts/create_project_dir.py "Project Name"
python scripts/create_project_dir.py "Calculator App"
```

**Features**:
- Creates directories under `projects/YYYY-MM-DD/project_name/`
- Automatically appends numbers if name exists (e.g., `project_1`, `project_2`)
- Sanitizes project names (spaces → underscores, removes special chars)
- Creates README.md with timestamp in each project directory

**Example**:
```bash
# First call creates: projects/2025-11-10/My_App/
python scripts/create_project_dir.py "My App"

# Second call creates: projects/2025-11-10/My_App_1/
python scripts/create_project_dir.py "My App"

# Third call creates: projects/2025-11-10/My_App_2/
python scripts/create_project_dir.py "My App"
```

## Usage

Most scripts can be run directly with Python:
```bash
python scripts/check_db.py
python scripts/test_api_direct.py
```

PowerShell scripts:
```powershell
.\scripts\monitor_paint_app.ps1
```

## Notes

- Scripts assume you're running from the repository root
- Some scripts require the AgentManager server to be running
- Test scripts may create temporary data in the database

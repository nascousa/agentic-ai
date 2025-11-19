# Request JSON Implementation

## Overview

AgentManager now automatically saves the original workflow request as a JSON file inside the project folder at the time of workflow submission. This ensures that all project-related files are consolidated in one location.

## Implementation Details

### When Request JSON is Created

The request JSON file is created **immediately upon workflow submission**, before task execution begins. This ensures:
- The original user request is captured with exact metadata
- Submission timestamp is recorded
- Complete traceability from request to results

### File Location

Request JSON files are saved with the naming pattern: `{project_name}_request.json`

**Example structure:**
```
projects/2025-10-14/paint_app/
├── paint_app_request.json         # ✅ Saved at submission time
├── FINAL_OUTPUT.md                # Saved when workflow completes
├── workflow_summary.json          # Saved when workflow completes
└── task_results/                  # Saved as tasks complete
    ├── task_1_researcher.md
    ├── task_2_analyst.md
    └── ...
```

### Request JSON Format

```json
{
  "workflow_id": "workflow_abc123",
  "user_request": "Create a Python calculator application",
  "metadata": {
    "project_name": "calculator",
    "priority": "high",
    "complexity": "medium"
  },
  "submitted_at": "2025-10-14T12:34:56.789012"
}
```

### Key Fields

- **workflow_id**: Unique identifier assigned by AgentManager
- **user_request**: Original request string exactly as submitted
- **metadata**: Complete metadata dictionary including project_name
- **submitted_at**: ISO-8601 timestamp of workflow submission

## Implementation Changes

### Code Changes in `agent_manager/core/manager.py`

#### 1. New Method: `save_workflow_request()`
```python
async def save_workflow_request(
    self, 
    workflow_id: str, 
    user_request: str, 
    metadata: Optional[Dict], 
    project_name: str
) -> None:
    """
    Save workflow request JSON to project folder.
    
    Creates:
    - projects/YYYY-MM-DD/{project_name}/{project_name}_request.json
    """
```

**Location**: Lines 91-122

#### 2. Enhanced Method: `plan_and_save_task()`
Updated to call `save_workflow_request()` immediately after workflow creation:

**Main workflow path** (lines 350-367):
```python
# Persist to database if db_service provided
if db_service:
    workflow_id = await db_service.save_task_graph(task_graph)
    print(f"  💾 Persisted workflow to database: {workflow_id}")
    
    # Save request JSON to project folder
    project_name = metadata.get("project_name") if metadata else None
    if project_name:
        try:
            await self.save_workflow_request(
                workflow_id=workflow_id,
                user_request=user_request,
                metadata=metadata,
                project_name=project_name
            )
            print(f"  📋 Saved request JSON to project folder: {project_name}")
        except Exception as e:
            print(f"  ⚠️ Failed to save request JSON: {str(e)}")
```

**Fallback workflow path** (lines 370-387):
Same logic applied to fallback workflows when planning fails.

#### 3. Enhanced Method: `save_workflow_results()`
Updated to accept optional `user_request` and `metadata` parameters:

```python
async def save_workflow_results(
    self, 
    workflow_id: str, 
    results: List[Dict], 
    final_output: str, 
    user_request: Optional[str] = None,  # ✅ New parameter
    metadata: Optional[Dict] = None,     # ✅ New parameter
    project_name: Optional[str] = None
) -> None:
```

When both `user_request` and `metadata` are provided, this method also saves the request JSON as a backup during result consolidation.

**Location**: Lines 124-171

## Workflow Timeline

### Step-by-Step Process

1. **User Submits Request**
   ```bash
   POST /v1/tasks
   {
     "user_request": "Create a calculator",
     "metadata": {"project_name": "calculator"}
   }
   ```

2. **AgentManager Creates Workflow**
   - Calls LLM to generate task graph
   - Persists TaskGraph to database
   - Returns workflow_id to user

3. **Request JSON Saved** ✅ **NEW**
   - Creates `projects/2025-10-14/calculator/`
   - Saves `calculator_request.json` with:
     - workflow_id
     - user_request
     - metadata
     - submitted_at timestamp

4. **Tasks Execute**
   - Workers poll and execute tasks
   - Results saved to database
   - Individual task_results/ files created

5. **Workflow Completes**
   - AgentManager synthesizes final output
   - Saves FINAL_OUTPUT.md
   - Saves workflow_summary.json
   - Consolidates all task results

## Benefits

### Complete Project Traceability
- Original request preserved exactly as submitted
- Submission timestamp for audit trails
- Complete metadata including priority, complexity, etc.

### Self-Contained Project Folders
- All project-related files in one location
- Easy to archive, share, or analyze
- No need to search logs or database for original request

### Debugging and Analysis
- Compare original request vs. actual results
- Understand scope creep or requirements drift
- Reproduce workflows with exact original parameters

### Documentation and Reporting
- Include original request in project documentation
- Generate reports showing request-to-delivery pipeline
- Track project evolution over time

## Example Usage

### Submitting a Workflow

```bash
# Using curl with JSON file
curl -X POST http://localhost:8001/v1/tasks \
  -H "Authorization: Bearer am_server_30j_MNJFG086I8kh2fdsAU_aA7ggR4OTv5iR-tYcuyQ" \
  -H "Content-Type: application/json" \
  -d @paint_request.json

# Response includes workflow_id
{
  "workflow_id": "paint_app_workflow",
  "status": "created"
}
```

### Verifying Request JSON

```bash
# Check that request JSON was created
cat projects/2025-10-14/paint_app/paint_app_request.json

# Output shows complete original request
{
  "workflow_id": "paint_app_workflow",
  "user_request": "Create a complete Paint desktop application...",
  "metadata": {
    "project_name": "paint_app",
    "complexity": "high",
    "priority": "normal"
  },
  "submitted_at": "2025-10-14T15:23:45.123456"
}
```

### Complete Project Structure

After workflow completes, you'll have:

```
projects/2025-10-14/paint_app/
├── paint_app_request.json         # ✅ Original request at submission
├── FINAL_OUTPUT.md                # Final synthesized deliverable
├── workflow_summary.json          # Statistics and execution data
└── task_results/                  # Individual task outputs
    ├── task_1_researcher.md       # Research phase
    ├── task_2_architect.md        # Architecture design
    ├── task_3_developer.md        # Implementation
    ├── task_4_developer.md        # Feature additions
    ├── task_5_tester.md           # Quality assurance
    └── ...                        # Additional tasks
```

## Testing the Implementation

### Current Paint App Example

The Paint app workflow was submitted before this implementation. When it completes, you can verify:

1. **Request JSON exists**: `projects/2025-10-14/paint_app/paint_app_request.json`
2. **Contains workflow_id**: Matches the workflow_id from submission
3. **Matches original request**: Compare with `paint_request.json` in root
4. **Includes timestamp**: Check submitted_at field

### New Workflow Testing

To test with a new workflow:

```bash
# Submit a simple test workflow
curl -X POST http://localhost:8001/v1/tasks \
  -H "Authorization: Bearer am_server_30j_MNJFG086I8kh2fdsAU_aA7ggR4OTv5iR-tYcuyQ" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Create a simple calculator",
    "metadata": {"project_name": "calculator_test"}
  }'

# Immediately check for request JSON (should exist right away)
ls projects/2025-10-14/calculator_test/
# Should show: calculator_test_request.json

# Read the file to verify contents
cat projects/2025-10-14/calculator_test/calculator_test_request.json
```

## Error Handling

### Graceful Degradation

If request JSON saving fails:
- Workflow continues normally (no blocking)
- Warning logged: `⚠️ Failed to save request JSON: {error}`
- Results still saved when workflow completes
- Request can be reconstructed from database if needed

### Common Failure Scenarios

1. **Directory creation fails**: Insufficient permissions or disk full
2. **JSON serialization fails**: Invalid metadata structure
3. **File write fails**: Network storage issues

All scenarios are non-fatal and logged for troubleshooting.

## Future Enhancements

### Potential Additions

1. **Request versioning**: Track request modifications or re-submissions
2. **Audit trail**: Link request JSON to audit reports
3. **Metadata enrichment**: Add user info, API version, system state
4. **Request comparison**: Tool to compare requests across workflows
5. **Request templates**: Save successful requests as reusable templates

## Related Documentation

- [Project Folder Structure](./project-folder-structure.md) - Complete project organization details
- [Project Usage Guide](./project-usage-guide.md) - Practical examples and patterns
- [DOCUMENTATION_UPDATE.md](./DOCUMENTATION_UPDATE.md) - Recent changes and migration guide

## Summary

The request JSON implementation ensures complete project traceability by capturing the original workflow request at submission time. All project-related files (request, results, outputs, summaries) are now consolidated in dated project folders, making AgentManager outputs self-contained, shareable, and easy to manage.

**Key Takeaway**: When you submit a workflow with `project_name` in metadata, the request JSON is immediately saved to `projects/YYYY-MM-DD/{project_name}/{project_name}_request.json`, creating a complete audit trail from request to delivery.

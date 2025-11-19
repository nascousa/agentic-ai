# Project Structure Update (v1.2.0)

## Summary of Changes - October 14, 2025

This update standardizes the AgentManager project output structure with automatic name sanitization, consistent subfolder organization, and updated documentation.

## Key Changes

### 1. Project Name Sanitization

**Previous Behavior:**
- Project names with spaces created folders with spaces
- Inconsistent naming across different projects

**New Behavior:**
- **All spaces automatically replaced with underscores**
- Example: `"paint app"` → `projects/2025-10-14/paint_app/`
- Example: `"todo manager app"` → `projects/2025-10-14/todo_manager_app/`

**Implementation:**
```python
# In agent_manager/core/manager.py
def get_today_project_folder(self, project_name: Optional[str] = None) -> Path:
    if project_name:
        # Replace spaces with underscores for consistent naming
        sanitized_name = project_name.replace(" ", "_")
        project_folder = self.base_project_dir / today / sanitized_name
```

### 2. Standard Subfolder Structure

**New Structure:**
```
projects/YYYY-MM-DD/project_name/
├── project_name_request.json    # Original workflow request
├── FINAL_OUTPUT.md              # Synthesized deliverable
├── workflow_summary.json        # Execution statistics
├── src/                         # Source files and task results
│   ├── task_1_researcher.md
│   ├── task_2_analyst.md
│   └── ...
└── tests/                       # Test files (when applicable)
```

**Changes from Previous Structure:**
- `task_results/` → `src/` - More intuitive naming for source content
- Added `tests/` folder - Reserved for test files and validation outputs
- Both folders created automatically on project initialization

**Implementation:**
```python
# In get_today_project_folder()
project_folder.mkdir(parents=True, exist_ok=True)

# Create standard project structure
(project_folder / "src").mkdir(exist_ok=True)
(project_folder / "tests").mkdir(exist_ok=True)
```

### 3. Consistent File Naming

**Request JSON Files:**
- Filename uses sanitized project name
- Example: `todo_manager_app_request.json` (not `todo manager app_request.json`)

**Implementation:**
```python
# In save_workflow_request()
sanitized_name = (project_name or workflow_id).replace(" ", "_")
request_file = project_folder / f"{sanitized_name}_request.json"
```

## Updated Documentation

### Files Modified:

1. **`agent_manager/core/manager.py`**:
   - Updated `get_today_project_folder()` to sanitize names and create subfolders
   - Updated `save_workflow_request()` to use sanitized names
   - Updated `save_workflow_results()` to save task results in `src/` folder

2. **`docs/project-folder-structure.md`**:
   - Added naming conventions section
   - Updated directory layout with new structure
   - Added example showing space-to-underscore conversion
   - Updated all references from `task_results/` to `src/`

3. **`docs/REQUEST_JSON_IMPLEMENTATION.md`**:
   - (Existing documentation automatically compatible with changes)

4. **`.context/index.md`** (CCS):
   - Updated version to 1.2.0
   - Updated last-updated date to 2025-10-14

5. **`.context/docs.md`** (CCS):
   - Added new "Project Output Structure" section at the beginning
   - Documented automatic name sanitization
   - Documented standard subfolder structure
   - Added implementation details

## Benefits

### 1. Cross-Platform Compatibility
- Underscores work consistently across Windows, macOS, and Linux
- No issues with spaces in shell commands or file paths
- Better compatibility with version control systems

### 2. Consistent Project Organization
- All projects follow the same structure
- Easy to find source files (`src/`)
- Clear separation between source and test files
- Predictable folder names

### 3. Better Developer Experience
- No need to quote paths with spaces
- Easier tab completion in terminals
- Simpler scripting and automation
- Clean, professional naming

### 4. Self-Contained Projects
- All project files in one location
- Easy to archive or share entire projects
- Clear organization from request to results

## Testing Verification

### Test Case 1: Project with Spaces
```bash
curl -X POST "http://localhost:8001/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Create a simple todo manager",
    "metadata": {"project_name": "todo manager app"}
  }'
```

**Result:**
```
✅ Folder created: projects/2025-10-14/todo_manager_app/
✅ Request JSON: todo_manager_app_request.json
✅ Subfolders: src/ and tests/ created automatically
✅ Metadata preserved: "project_name": "todo manager app"
✅ Workflow ID: "todo_manager_app"
```

### Test Case 2: Simple Project Name
```bash
curl -X POST "http://localhost:8001/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Create a simple timer CLI app",
    "metadata": {"project_name": "timer_test"}
  }'
```

**Result:**
```
✅ Folder created: projects/2025-10-14/timer_test/
✅ Request JSON: timer_test_request.json
✅ Subfolders: src/ and tests/ created automatically
✅ No changes needed (no spaces to sanitize)
```

## Migration Notes

### For Existing Projects

**Old projects** (created before this update) may have:
- Folder names with spaces
- `task_results/` instead of `src/`
- No `tests/` folder

**New projects** (created after this update) will have:
- Folder names with underscores
- `src/` folder for task results
- `tests/` folder (empty if not used)

### No Breaking Changes

- Old API requests still work
- Metadata is preserved exactly as submitted
- Only folder names and internal organization changed
- Request JSON still captures original project name

## Log Output Examples

**Clean, Professional Logs:**
```
[PLANNING] Workflow for request: Create a simple todo manager...
  [CREATED] Workflow todo_manager_app with 7 tasks
  [READY] 1 tasks ready to start
  [SAVED] Persisted workflow to database: todo_manager_app
  [SAVED] Workflow request to: projects/2025-10-14/todo_manager_app/todo_manager_app_request.json
  [SAVED] Request JSON to project folder: todo manager app
```

## API Compatibility

### Request Format (Unchanged)
```json
{
  "user_request": "Create a paint desktop app",
  "metadata": {
    "project_name": "paint app"
  }
}
```

### Response Format (Unchanged)
```json
{
  "workflow_id": "paint_app_workflow",
  "tasks": [...],
  "created_at": "2025-10-14T12:34:56Z",
  "total_tasks": 10
}
```

### Behavior Changes
- Folder created: `projects/2025-10-14/paint_app/` (was: `paint app/`)
- Request JSON: `paint_app_request.json` (was: `paint app_request.json`)
- Structure: Includes `src/` and `tests/` subfolders

## Future Enhancements

Potential additions for future versions:

1. **Additional Subfolders**:
   - `docs/` for documentation
   - `config/` for configuration files
   - `logs/` for execution logs

2. **Metadata-Driven Structure**:
   - Custom folder layouts based on project type
   - Configurable subfolder creation

3. **Project Templates**:
   - Pre-defined structures for common project types
   - Language-specific folder organization

4. **Archive Support**:
   - Automatic project compression
   - Easy export/import of complete projects

## Related Documentation

- [Project Folder Structure](./project-folder-structure.md) - Complete structure documentation
- [Request JSON Implementation](./REQUEST_JSON_IMPLEMENTATION.md) - Request tracking details
- [Project Usage Guide](./project-usage-guide.md) - Practical examples
- [CCS Documentation](./.context/docs.md) - Technical implementation details

## Summary

The v1.2.0 update brings consistency and professionalism to AgentManager project organization:

✅ **Automatic name sanitization** - Spaces replaced with underscores  
✅ **Standard subfolder structure** - `src/` and `tests/` folders  
✅ **Cross-platform compatibility** - Works everywhere  
✅ **Clean log output** - No emoji encoding issues  
✅ **Self-contained projects** - Everything in one place  
✅ **Updated documentation** - Complete CCS integration  

All changes are backward compatible with existing workflows and APIs.

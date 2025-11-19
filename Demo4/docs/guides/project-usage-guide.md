# Using AgentManager Projects

## Quick Start Guide

This guide shows you how to create projects and organize outputs using AgentManager's dated folder structure.

## Basic Usage

### 1. Submit a Task with Project Name

When you submit a task, include a `project_name` in the metadata:

```bash
curl -X POST http://localhost:8001/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "user_request": "Create a Python calculator application with tests",
    "metadata": {
      "project_name": "calculator",
      "priority": "high"
    }
  }'
```

**Response:**
```json
{
  "workflow_id": "wf_20251014_abc123",
  "tasks": [...],
  "created_at": "2025-10-14T12:00:00Z"
}
```

### 2. Monitor Workflow Progress

Check workflow status:

```bash
curl http://localhost:8001/v1/workflows/wf_20251014_abc123/status \
  -H "Authorization: Bearer your_token"
```

**Response:**
```json
{
  "workflow_id": "wf_20251014_abc123",
  "status": "completed",
  "total_tasks": 5,
  "completed_tasks": 5,
  "in_progress_tasks": 0,
  "pending_tasks": 0
}
```

### 3. Access Project Results

Once completed, find your results in:

```
projects/2025-10-14/calculator/
├── FINAL_OUTPUT.md              # ⭐ Main deliverable
├── workflow_summary.json        # Workflow statistics
└── task_results/
    ├── task_1_architect.md      # Architecture design
    ├── task_2_developer.md      # Calculator implementation
    ├── task_3_developer.md      # Test suite
    ├── task_4_tester.md         # Test execution
    └── task_5_writer.md         # Documentation
```

## Example Projects

### Example 1: Web Scraper Development

**Request:**
```json
{
  "user_request": "Build a Python web scraper for news articles with error handling and rate limiting",
  "metadata": {
    "project_name": "news_scraper",
    "complexity": "medium",
    "priority": "high"
  }
}
```

**Expected Workflow:**
1. **Architect** - Design scraper architecture and data models
2. **Researcher** - Research best practices and libraries
3. **Developer** - Implement core scraping logic
4. **Developer** - Add error handling and rate limiting
5. **Tester** - Create and run test suite
6. **Writer** - Document usage and API

**Output Structure:**
```
projects/2025-10-14/news_scraper/
├── FINAL_OUTPUT.md              # Complete scraper with documentation
├── workflow_summary.json
└── task_results/
    ├── task_1_architect.md      # Architecture decisions
    ├── task_2_researcher.md     # Library recommendations
    ├── task_3_developer.md      # Core implementation
    ├── task_4_developer.md      # Error handling code
    ├── task_5_tester.md         # Test results
    └── task_6_writer.md         # User documentation
```

### Example 2: Content Creation

**Request:**
```json
{
  "user_request": "Write a comprehensive blog post about AI agents with examples and references",
  "metadata": {
    "project_name": "ai_agents_blog",
    "complexity": "low"
  }
}
```

**Expected Workflow:**
1. **Researcher** - Gather information and references
2. **Analyst** - Identify key themes and structure
3. **Writer** - Create blog post content
4. **Writer** - Add examples and format
5. **Reviewer** - Final quality check

**Output Structure:**
```
projects/2025-10-14/ai_agents_blog/
├── FINAL_OUTPUT.md              # Polished blog post
├── workflow_summary.json
└── task_results/
    ├── task_1_researcher.md     # Research findings
    ├── task_2_analyst.md        # Content structure
    ├── task_3_writer.md         # Draft content
    ├── task_4_writer.md         # Examples and formatting
    └── task_5_reviewer.md       # Final review notes
```

### Example 3: Data Analysis Pipeline

**Request:**
```json
{
  "user_request": "Analyze sales data and create a dashboard with insights and recommendations",
  "metadata": {
    "project_name": "sales_dashboard",
    "complexity": "high",
    "priority": "urgent"
  }
}
```

**Expected Workflow:**
1. **Researcher** - Understand data sources and requirements
2. **Analyst** - Perform statistical analysis
3. **Analyst** - Identify trends and patterns
4. **Developer** - Build dashboard visualization
5. **Writer** - Document findings and recommendations
6. **Reviewer** - Validate analysis methodology

**Output Structure:**
```
projects/2025-10-14/sales_dashboard/
├── FINAL_OUTPUT.md              # Complete analysis report
├── workflow_summary.json
└── task_results/
    ├── task_1_researcher.md     # Data understanding
    ├── task_2_analyst.md        # Statistical analysis
    ├── task_3_analyst.md        # Trend identification
    ├── task_4_developer.md      # Dashboard code
    ├── task_5_writer.md         # Executive summary
    └── task_6_reviewer.md       # Validation report
```

## Without Project Name

If you don't specify a project name, the workflow ID is used:

**Request:**
```json
{
  "user_request": "Explain quantum computing in simple terms"
}
```

**Output Location:**
```
projects/2025-10-14/wf_20251014_xyz789/
├── FINAL_OUTPUT.md
├── workflow_summary.json
└── task_results/
    └── ...
```

## Browsing Historical Projects

### By Date
```bash
# List all projects from today
ls projects/2025-10-14/

# List all projects from October 2025
ls projects/2025-10-*/

# Find specific project
find projects/ -name "calculator"
```

### By Content
```bash
# Search for projects mentioning "Python"
grep -r "Python" projects/*/FINAL_OUTPUT.md

# Find projects by agent type
grep -l "developer" projects/*/workflow_summary.json
```

## Workflow Summary Analysis

Each project includes a `workflow_summary.json` with metrics:

```json
{
  "workflow_id": "wf_20251014_abc123",
  "created_at": "2025-10-14T12:00:00.123456",
  "total_tasks": 5,
  "total_execution_time": 67.89,
  "agents_used": ["architect", "developer", "tester", "writer"],
  "task_count_by_agent": {
    "architect": 1,
    "developer": 2,
    "tester": 1,
    "writer": 1
  }
}
```

**Use Cases:**
- **Performance Analysis**: Compare execution times across projects
- **Agent Utilization**: See which agents are used most
- **Complexity Assessment**: Correlate task count with project complexity
- **Cost Tracking**: Calculate LLM API costs based on agent usage

## Best Practices

### 1. Use Descriptive Project Names
✅ Good: `ecommerce_api`, `customer_analytics`, `blog_automation`  
❌ Bad: `project1`, `test`, `temp`

### 2. Organize by Business Logic
```
projects/
├── 2025-10-14/
│   ├── client_acme/
│   │   ├── website_redesign/
│   │   └── api_integration/
│   └── internal/
│       ├── sales_report/
│       └── hr_automation/
```

### 3. Archive Old Projects
```bash
# Archive projects older than 30 days
tar -czf archive_2025-09.tar.gz projects/2025-09-*/
rm -rf projects/2025-09-*/
```

### 4. Backup Strategy
```bash
# Daily backup of projects folder
rsync -av projects/ /backup/agentmanager/projects/

# Or use cloud storage
aws s3 sync projects/ s3://my-bucket/agentmanager/projects/
```

### 5. Review Task Results
Don't just read `FINAL_OUTPUT.md` - review individual task results to:
- Understand agent reasoning
- Identify potential issues
- Learn from agent approaches
- Validate intermediate outputs

## Integration Examples

### Python Script
```python
import requests
import json
from pathlib import Path

def create_project(name: str, request: str):
    """Submit a task and track project creation."""
    
    response = requests.post(
        "http://localhost:8001/v1/tasks",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer your_token"
        },
        json={
            "user_request": request,
            "metadata": {"project_name": name}
        }
    )
    
    workflow_id = response.json()["workflow_id"]
    
    # Wait for completion
    while True:
        status = requests.get(
            f"http://localhost:8001/v1/workflows/{workflow_id}/status",
            headers={"Authorization": "Bearer your_token"}
        ).json()
        
        if status["status"] == "completed":
            break
        
        time.sleep(5)
    
    # Read results
    today = datetime.now().strftime("%Y-%m-%d")
    project_path = Path(f"projects/{today}/{name}")
    
    with open(project_path / "FINAL_OUTPUT.md") as f:
        final_output = f.read()
    
    return final_output

# Usage
result = create_project(
    name="calculator",
    request="Create a Python calculator with tests"
)
print(result)
```

### Shell Script Automation
```bash
#!/bin/bash
# submit_project.sh

PROJECT_NAME=$1
USER_REQUEST=$2

# Submit task
RESPONSE=$(curl -s -X POST http://localhost:8001/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  -d "{\"user_request\": \"$USER_REQUEST\", \"metadata\": {\"project_name\": \"$PROJECT_NAME\"}}")

WORKFLOW_ID=$(echo $RESPONSE | jq -r '.workflow_id')
echo "Created workflow: $WORKFLOW_ID"

# Monitor progress
while true; do
  STATUS=$(curl -s http://localhost:8001/v1/workflows/$WORKFLOW_ID/status \
    -H "Authorization: Bearer $API_TOKEN" | jq -r '.status')
  
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  
  sleep 5
done

# Show results location
TODAY=$(date +%Y-%m-%d)
echo "Results saved to: projects/$TODAY/$PROJECT_NAME/"
cat "projects/$TODAY/$PROJECT_NAME/FINAL_OUTPUT.md"
```

## Troubleshooting

### Project Folder Not Created
**Issue**: Workflow completes but no project folder appears

**Solutions:**
1. Check volume mounting in docker-compose.yml
2. Verify file permissions on projects/ directory
3. Check agent-manager logs: `docker logs agentmanager-agent-manager-1`

### Incomplete Results
**Issue**: Some task results are missing

**Solutions:**
1. Check workflow status - may not be fully completed
2. Review audit reports for failed tasks
3. Check individual task logs in database

### Large Project Folders
**Issue**: Projects folder consuming too much disk space

**Solutions:**
1. Implement archival strategy for old projects
2. Compress dated folders: `tar -czf 2025-09.tar.gz projects/2025-09-*/`
3. Add cleanup job to remove projects older than N days

## Next Steps

- Learn about [Audit Workflows](audit-workflow.md)
- Explore [API Documentation](http://localhost:8001/docs)
- Review [Architecture Overview](../docs/architecture.md)

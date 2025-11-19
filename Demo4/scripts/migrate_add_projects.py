"""
Quick migration to create projects from existing workflows
"""
import subprocess

# SQL to create a project for each workflow and link them
migration_sql = """
-- Create a project for each existing workflow
INSERT INTO projects (project_id, project_name, project_path, created_at, updated_at)
SELECT 
    'PROJECT-' || TO_CHAR(created_at, 'YYYYMMDD') || '-' || LPAD(ROW_NUMBER() OVER (PARTITION BY DATE(created_at) ORDER BY created_at)::TEXT, 3, '0') as project_id,
    COALESCE(NULLIF(workflow_name, ''), SUBSTRING(user_request, 1, 50), 'Untitled Project') as project_name,
    'projects/' || TO_CHAR(created_at, 'YYYY-MM-DD') || '/' || 
        REGEXP_REPLACE(
            LOWER(COALESCE(NULLIF(workflow_name, ''), SUBSTRING(user_request, 1, 30), 'project')),
            '[^a-z0-9_]', '_', 'g'
        ) as project_path,
    created_at,
    created_at as updated_at
FROM task_graphs
WHERE workflow_id NOT IN (
    SELECT tg.workflow_id 
    FROM task_graphs tg 
    JOIN projects p ON tg.project_id = p.id
);

-- Link workflows to their corresponding projects
UPDATE task_graphs tg
SET project_id = p.id
FROM projects p
WHERE tg.project_id IS NULL
AND p.project_name = COALESCE(NULLIF(tg.workflow_name, ''), SUBSTRING(tg.user_request, 1, 50), 'Untitled Project')
AND DATE(p.created_at) = DATE(tg.created_at);
"""

print("🔄 Running project migration...")
print("=" * 60)

result = subprocess.run(
    ['docker', 'exec', 'agentmanager-postgres-1',
     'psql', '-U', 'postgres', '-d', 'agent_manager', '-c', migration_sql],
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)

print("\n✅ Migration complete!")
print("=" * 60)

# Verify the results
verify_sql = """
SELECT 
    COUNT(DISTINCT p.id) as total_projects,
    COUNT(tg.id) as total_workflows,
    COUNT(tg.id) FILTER (WHERE tg.project_id IS NOT NULL) as linked_workflows
FROM task_graphs tg
LEFT JOIN projects p ON tg.project_id = p.id;
"""

print("\n📊 Verification:")
result = subprocess.run(
    ['docker', 'exec', 'agentmanager-postgres-1',
     'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c', verify_sql],
    capture_output=True,
    text=True
)

print(result.stdout)

"""
Delete workflows with no progress (no completed tasks)
This removes workflows where all tasks are still pending/in-progress
"""
import subprocess
import sys

def delete_no_progress_workflows():
    """Delete workflows with 0% progress from PostgreSQL"""
    
    print("\n🔍 Finding workflows with no progress...")
    
    # Find workflows where no tasks are completed
    check_cmd = [
        "docker", "exec", "agentmanager-postgres-1",
        "psql", "-U", "postgres", "-d", "agent_manager",
        "-t", "-c",
        """SELECT COUNT(DISTINCT tg.workflow_id) 
           FROM task_graphs tg
           WHERE NOT EXISTS (
               SELECT 1 FROM task_steps ts 
               WHERE ts.workflow_id = tg.workflow_id 
               AND ts.status = 'COMPLETED'
           );"""
    ]
    
    try:
        result = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        count = result.stdout.strip()
        print(f"   Found {count} workflows with no completed tasks")
        
        if int(count) == 0:
            print("✅ No workflows with zero progress to delete!")
            return
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking workflows: {e.stderr}")
        return
    
    # Show which workflows will be deleted
    print("\n📋 Workflows to be deleted (0% progress):")
    sample_cmd = [
        "docker", "exec", "agentmanager-postgres-1",
        "psql", "-U", "postgres", "-d", "agent_manager",
        "-c",
        """SELECT tg.workflow_id, 
                  tg.workflow_name, 
                  LEFT(tg.user_request, 40) as request,
                  COUNT(ts.id) as total_tasks,
                  tg.created_at
           FROM task_graphs tg
           LEFT JOIN task_steps ts ON ts.workflow_id = tg.workflow_id
           WHERE NOT EXISTS (
               SELECT 1 FROM task_steps ts2 
               WHERE ts2.workflow_id = tg.workflow_id 
               AND ts2.status = 'COMPLETED'
           )
           GROUP BY tg.workflow_id, tg.workflow_name, tg.user_request, tg.created_at
           ORDER BY tg.created_at DESC;"""
    ]
    
    try:
        result = subprocess.run(
            sample_cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        print(result.stdout)
    except:
        pass
    
    print(f"⚠️  This will delete {count} workflows and their associated:")
    print("   - Tasks (none completed)")
    print("   - Results")
    print("   - Audit reports")
    print("\n🚀 Proceeding with deletion...")
    
    # Auto-confirm for this operation
    
    print("\n🗑️  Deleting workflows with no progress...")
    
    # Delete in correct order due to foreign keys
    sql_commands = [
        ("audit_reports", """DELETE FROM audit_reports 
                            WHERE workflow_id::text IN (
                                SELECT workflow_id FROM task_graphs tg
                                WHERE NOT EXISTS (
                                    SELECT 1 FROM task_steps ts 
                                    WHERE ts.workflow_id = tg.workflow_id 
                                    AND ts.status = 'COMPLETED'
                                )
                            );"""),
        ("results", """DELETE FROM results 
                      WHERE task_step_id IN (
                          SELECT id FROM task_steps ts
                          WHERE workflow_id IN (
                              SELECT workflow_id FROM task_graphs tg
                              WHERE NOT EXISTS (
                                  SELECT 1 FROM task_steps ts2 
                                  WHERE ts2.workflow_id = tg.workflow_id 
                                  AND ts2.status = 'COMPLETED'
                              )
                          )
                      );"""),
        ("task_steps", """DELETE FROM task_steps 
                         WHERE workflow_id IN (
                             SELECT workflow_id FROM task_graphs tg
                             WHERE NOT EXISTS (
                                 SELECT 1 FROM task_steps ts 
                                 WHERE ts.workflow_id = tg.workflow_id 
                                 AND ts.status = 'COMPLETED'
                             )
                         );"""),
        ("task_graphs", """DELETE FROM task_graphs tg
                          WHERE NOT EXISTS (
                              SELECT 1 FROM task_steps ts 
                              WHERE ts.workflow_id = tg.workflow_id 
                              AND ts.status = 'COMPLETED'
                          );"""),
    ]
    
    for table, sql in sql_commands:
        print(f"   Deleting from {table}...")
        
        cmd = [
            "docker", "exec", "agentmanager-postgres-1",
            "psql", "-U", "postgres", "-d", "agent_manager",
            "-c", sql
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            print(f"   ✅ {table} cleaned")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error deleting from {table}: {e.stderr}")
            return
    
    print(f"\n✅ Successfully deleted {count} workflows with no progress!")
    print("💡 Workflows with completed tasks were preserved.")
    print("\n🔄 Refresh your dashboard to see the updated list!")

if __name__ == "__main__":
    delete_no_progress_workflows()

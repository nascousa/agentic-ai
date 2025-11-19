"""
Delete workflows with NULL or empty workflow_name from PostgreSQL
This removes test/unnamed workflows while keeping named ones
"""
import subprocess
import sys

def delete_unnamed_workflows():
    """Delete workflows without proper names from PostgreSQL"""
    
    print("\n🔍 Finding workflows without names...")
    
    # Check how many workflows will be deleted
    check_cmd = [
        "docker", "exec", "agentmanager-postgres-1",
        "psql", "-U", "postgres", "-d", "agent_manager",
        "-t", "-c",
        "SELECT COUNT(*) FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '';"
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
        print(f"   Found {count} workflows without names")
        
        if int(count) == 0:
            print("✅ No unnamed workflows to delete!")
            return
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking workflows: {e.stderr}")
        return
    
    # Show sample of what will be deleted
    print("\n📋 Workflows to be deleted:")
    sample_cmd = [
        "docker", "exec", "agentmanager-postgres-1",
        "psql", "-U", "postgres", "-d", "agent_manager",
        "-c",
        "SELECT workflow_id, LEFT(user_request, 50) as request, created_at FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '' ORDER BY created_at DESC LIMIT 10;"
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
    print("   - Tasks")
    print("   - Results")
    print("   - Audit reports")
    print("\n🚀 Proceeding with deletion...")
    
    # Auto-confirm for this operation
    # confirm = input("\nProceed? (yes/no): ")
    # if confirm.lower() != "yes":
    #     print("❌ Cancelled. No data was deleted.")
    #     return
    
    print("\n🗑️  Deleting unnamed workflows...")
    
    # Delete in correct order due to foreign keys
    sql_commands = [
        ("audit_reports", "DELETE FROM audit_reports WHERE workflow_id::text IN (SELECT workflow_id FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '');"),
        ("results", "DELETE FROM results WHERE task_step_id IN (SELECT id FROM task_steps WHERE workflow_id IN (SELECT workflow_id FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = ''));"),
        ("task_steps", "DELETE FROM task_steps WHERE workflow_id IN (SELECT workflow_id FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '');"),
        ("task_graphs", "DELETE FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '';"),
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
    
    print(f"\n✅ Successfully deleted {count} unnamed workflows!")
    print("💡 Named workflows were preserved.")
    print("\n🔄 Refresh your dashboard to see the updated list!")

if __name__ == "__main__":
    delete_unnamed_workflows()

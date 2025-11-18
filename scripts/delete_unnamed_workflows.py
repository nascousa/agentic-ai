"""
Delete workflows with NULL or empty workflow_name
This removes test/unnamed workflows while keeping named ones
"""
import subprocess
import sys

def delete_unnamed_workflows():
    """Delete workflows without proper names from PostgreSQL"""
    
    print("\n🔍 Finding workflows without names...")
    
    # First, check how many workflows will be deleted
    check_cmd = [
        "docker", "exec", "-i", "agentmanager-postgres-1",
        "psql", "-U", "agentmanager", "-d", "agentmanager",
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
    
    print(f"\n⚠️  This will delete {count} workflows and their associated:")
    print("   - Tasks")
    print("   - Results")
    print("   - Audit reports")
    
    confirm = input("\nProceed? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("❌ Cancelled. No data was deleted.")
        return
    
    print("\n🗑️  Deleting unnamed workflows...")
    
    # Delete in correct order due to foreign keys
    # First, get the IDs of workflows to delete
    get_ids_cmd = [
        "docker", "exec", "-i", "agentmanager-postgres-1",
        "psql", "-U", "agentmanager", "-d", "agentmanager",
        "-t", "-c",
        "SELECT id FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '';"
    ]
    
    try:
        result = subprocess.run(
            get_ids_cmd,
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        workflow_ids = [id.strip() for id in result.stdout.strip().split('\n') if id.strip()]
        
        if not workflow_ids:
            print("✅ No workflows to delete!")
            return
            
        # Convert to SQL array format
        id_list = "', '".join(workflow_ids)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting workflow IDs: {e.stderr}")
        return
    
    # SQL commands to delete data (in correct order)
    sql_commands = [
        f"DELETE FROM audit_reports WHERE workflow_id IN (SELECT id FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '');",
        f"DELETE FROM results WHERE task_step_id IN (SELECT id FROM task_steps WHERE workflow_id IN (SELECT id FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = ''));",
        f"DELETE FROM task_steps WHERE workflow_id IN (SELECT id FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '');",
        f"DELETE FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '';",
    ]
    
    tables = ["audit_reports", "results", "task_steps", "task_graphs"]
    
    for sql, table in zip(sql_commands, tables):
        print(f"   Deleting from {table}...")
        
        cmd = [
            "docker", "exec", "-i", "agentmanager-postgres-1",
            "psql", "-U", "agentmanager", "-d", "agentmanager",
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

if __name__ == "__main__":
    delete_unnamed_workflows()

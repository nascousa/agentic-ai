"""
Delete all workflows from the database
WARNING: This will delete ALL workflows, tasks, results, and projects!
"""
import subprocess
import sys

def delete_all_workflows():
    """Delete all workflows and related data from PostgreSQL"""
    
    print("\n⚠️  WARNING: This will delete ALL data from the database!")
    print("   - All projects")
    print("   - All workflows") 
    print("   - All tasks")
    print("   - All results")
    print("   - All audit reports")
    
    confirm = input("\nAre you sure? Type 'DELETE ALL' to confirm: ")
    
    if confirm != "DELETE ALL":
        print("❌ Cancelled. No data was deleted.")
        return
    
    print("\n🗑️  Deleting all data...")
    
    # SQL commands to delete all data (in correct order due to foreign keys)
    sql_commands = [
        "DELETE FROM audit_reports;",
        "DELETE FROM results;", 
        "DELETE FROM task_steps;",
        "DELETE FROM task_graphs;",
        "DELETE FROM projects;",
    ]
    
    for sql in sql_commands:
        table = sql.split("FROM ")[1].split(";")[0]
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
            print(f"   ✅ {table} cleared")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error deleting from {table}: {e.stderr}")
            return
    
    print("\n✅ All data deleted successfully!")
    print("\n💡 The database is now empty and ready for fresh workflows.")

if __name__ == "__main__":
    delete_all_workflows()

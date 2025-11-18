"""
Delete workflows with NULL or empty workflow_name from SQLite
This removes test/unnamed workflows while keeping named ones
"""
import sqlite3

def delete_unnamed_workflows():
    """Delete workflows without proper names from SQLite"""
    
    conn = sqlite3.connect('agent_manager.db')
    cur = conn.cursor()
    
    print("\n🔍 Finding workflows without names...")
    
    # Check how many workflows will be deleted
    result = cur.execute(
        "SELECT COUNT(*) FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = ''"
    ).fetchone()
    count = result[0]
    
    print(f"   Found {count} workflows without names")
    
    if count == 0:
        print("✅ No unnamed workflows to delete!")
        conn.close()
        return
    
    # Show sample of what will be deleted
    print("\n📋 Sample workflows to be deleted:")
    samples = cur.execute(
        "SELECT workflow_id, user_request, created_at FROM task_graphs WHERE workflow_name IS NULL OR workflow_name = '' LIMIT 5"
    ).fetchall()
    
    for wf_id, request, created in samples:
        request_preview = request[:60] + "..." if len(request) > 60 else request
        print(f"   • {wf_id}: {request_preview}")
    
    if count > 5:
        print(f"   ... and {count - 5} more")
    
    print(f"\n⚠️  This will delete {count} workflows and their associated:")
    print("   - Tasks")
    print("   - Results")
    print("   - Audit reports")
    
    confirm = input("\nProceed? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("❌ Cancelled. No data was deleted.")
        conn.close()
        return
    
    print("\n🗑️  Deleting unnamed workflows...")
    
    try:
        # Delete in correct order due to foreign keys
        print("   Deleting audit reports...")
        cur.execute("""
            DELETE FROM audit_reports 
            WHERE workflow_id IN (
                SELECT id FROM task_graphs 
                WHERE workflow_name IS NULL OR workflow_name = ''
            )
        """)
        
        print("   Deleting results...")
        cur.execute("""
            DELETE FROM results 
            WHERE task_step_id IN (
                SELECT id FROM task_steps 
                WHERE workflow_id IN (
                    SELECT id FROM task_graphs 
                    WHERE workflow_name IS NULL OR workflow_name = ''
                )
            )
        """)
        
        print("   Deleting task steps...")
        cur.execute("""
            DELETE FROM task_steps 
            WHERE workflow_id IN (
                SELECT id FROM task_graphs 
                WHERE workflow_name IS NULL OR workflow_name = ''
            )
        """)
        
        print("   Deleting task graphs...")
        cur.execute("""
            DELETE FROM task_graphs 
            WHERE workflow_name IS NULL OR workflow_name = ''
        """)
        
        conn.commit()
        print(f"\n✅ Successfully deleted {count} unnamed workflows!")
        print("💡 Named workflows were preserved.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during deletion: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    delete_unnamed_workflows()

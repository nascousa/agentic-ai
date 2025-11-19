"""
Show all workflows in the database
"""
import sqlite3
from datetime import datetime

def show_all_workflows():
    """Display all workflows in SQLite"""
    
    conn = sqlite3.connect('agent_manager.db')
    cur = conn.cursor()
    
    # Get all workflows
    workflows = cur.execute("""
        SELECT workflow_id, workflow_name, user_request, status, created_at 
        FROM task_graphs 
        ORDER BY created_at DESC
    """).fetchall()
    
    print(f"\n📊 Total workflows in database: {len(workflows)}\n")
    print("=" * 120)
    
    for i, (wf_id, wf_name, request, status, created) in enumerate(workflows, 1):
        wf_name_display = wf_name if wf_name else "N/A"
        request_preview = request[:70] + "..." if len(request) > 70 else request
        print(f"{i}. {wf_id}")
        print(f"   Name: {wf_name_display}")
        print(f"   Request: {request_preview}")
        print(f"   Status: {status} | Created: {created}")
        print("-" * 120)
    
    conn.close()

if __name__ == "__main__":
    show_all_workflows()

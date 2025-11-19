"""
Migration script to add workflow_name column to task_graphs table.

Run this script to update an existing AgentManager database.
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str = "agent_manager.db"):
    """Add workflow_name column to task_graphs table."""
    
    print(f"[MIGRATION] Connecting to database: {db_path}")
    
    if not Path(db_path).exists():
        print(f"[ERROR] Database file not found: {db_path}")
        sys.exit(1)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(task_graphs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "workflow_name" in columns:
            print("[INFO] Column 'workflow_name' already exists. No migration needed.")
            conn.close()
            return
        
        print("[MIGRATION] Adding 'workflow_name' column to task_graphs table...")
        
        # Add the new column with a default value
        cursor.execute("""
            ALTER TABLE task_graphs 
            ADD COLUMN workflow_name VARCHAR(255) NOT NULL DEFAULT 'Untitled Workflow'
        """)
        
        # Update existing rows to have descriptive names based on user_request
        cursor.execute("""
            UPDATE task_graphs 
            SET workflow_name = CASE 
                WHEN LENGTH(user_request) > 50 
                THEN SUBSTR(user_request, 1, 50) || '...'
                ELSE user_request
            END
            WHERE workflow_name = 'Untitled Workflow'
        """)
        
        conn.commit()
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM task_graphs")
        count = cursor.fetchone()[0]
        
        print(f"[SUCCESS] Migration completed successfully!")
        print(f"[INFO] Updated {count} existing workflow(s)")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "agent_manager.db"
    migrate_database(db_path)

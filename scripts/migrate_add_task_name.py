"""
Migration script to add task_name column to task_steps table.

This migration adds the AI-generated task name field to support
better human-readable task identification in the dashboard.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from agent_manager.db import create_database_engine


async def migrate_add_task_name():
    """Add task_name column to task_steps table."""
    engine = create_database_engine()
    
    try:
        async with engine.begin() as conn:
            print("🔍 Checking if task_name column exists...")
            
            # Check if column already exists
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'task_steps' 
                AND column_name = 'task_name';
            """))
            
            existing = result.fetchone()
            
            if existing:
                print("✅ Column task_name already exists. Migration not needed.")
                return
            
            print("📝 Adding task_name column to task_steps table...")
            
            # Add task_name column with default value
            await conn.execute(text("""
                ALTER TABLE task_steps
                ADD COLUMN task_name VARCHAR(255) NOT NULL DEFAULT 'Untitled Task';
            """))
            
            print("✅ Successfully added task_name column!")
            
            # Update existing rows to have meaningful task names based on step_id
            print("📝 Updating existing task names from step_id...")
            await conn.execute(text("""
                UPDATE task_steps
                SET task_name = CASE
                    WHEN step_id ~ '^TID[0-9]+$' THEN 'Task ' || substring(step_id from 4)
                    ELSE substring(step_id from 1 for 50)
                END
                WHERE task_name = 'Untitled Task';
            """))
            
            print("✅ Updated existing task names!")
            
            # Show sample of updated data
            result = await conn.execute(text("""
                SELECT step_id, task_name, assigned_agent
                FROM task_steps
                LIMIT 5;
            """))
            
            print("\n📊 Sample of updated tasks:")
            rows = result.fetchall()
            for row in rows:
                print(f"  {row[0]}: {row[1]} ({row[2]})")
            
            print(f"\n✅ Migration completed successfully!")
            print(f"   - Added task_name column to task_steps")
            print(f"   - Updated {len(rows)} existing tasks")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("  Add task_name Column Migration")
    print("=" * 60)
    print()
    
    asyncio.run(migrate_add_task_name())
    
    print()
    print("=" * 60)

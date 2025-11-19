"""
Migration script to add status column to projects table.

This script adds the 'status' column to the projects table with default value 'IN_PROGRESS'.
Run this after updating the ORM model and before starting the server.
"""

import asyncio
from sqlalchemy import text
from agent_manager.db import get_engine


async def migrate_add_project_status():
    """Add status column to projects table."""
    engine = get_engine()
    
    async with engine.begin() as conn:
        # Check if we're using SQLite or PostgreSQL
        dialect_name = engine.dialect.name
        
        # Check if column already exists (different queries for different databases)
        if dialect_name == 'sqlite':
            check_query = text("PRAGMA table_info(projects)")
            result = await conn.execute(check_query)
            columns = [row[1] for row in result.fetchall()]
            column_exists = 'status' in columns
        else:  # PostgreSQL
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'projects' 
                AND column_name = 'status'
            """)
            result = await conn.execute(check_query)
            column_exists = result.fetchone() is not None
        
        if column_exists:
            print("✅ Status column already exists in projects table")
            return
        
        # Add status column
        print("➡️  Adding status column to projects table...")
        add_column_query = text("""
            ALTER TABLE projects 
            ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS'
        """)
        await conn.execute(add_column_query)
        
        # Add index for performance (SQLite and PostgreSQL both support CREATE INDEX IF NOT EXISTS)
        print("➡️  Creating index on status column...")
        add_index_query = text("""
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)
        """)
        await conn.execute(add_index_query)
        
        print("✅ Successfully added status column to projects table")


if __name__ == "__main__":
    print("=" * 60)
    print("Project Status Migration Script")
    print("=" * 60)
    asyncio.run(migrate_add_project_status())
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)

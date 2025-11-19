"""
Database migration script to add id_counters table for sequential ID generation.

Run this script to add the new id_counters table to your existing database.
"""
import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_manager.orm import Base, IDCounterORM
from dotenv import load_dotenv

load_dotenv()


async def run_migration():
    """Add id_counters table to existing database."""
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5433/agent_manager")
    
    print(f"🔧 Connecting to database...")
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        print(f"📊 Creating id_counters table...")
        
        # Create only the id_counters table
        await conn.run_sync(IDCounterORM.__table__.create, checkfirst=True)
        
        print(f"✅ id_counters table created successfully!")
        
        # Initialize counters
        print(f"🔢 Initializing counters...")
        
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Check existing max IDs and initialize counters
            # For project IDs
            result = await session.execute(
                text("SELECT project_id FROM projects WHERE project_id LIKE 'PID%' ORDER BY created_at DESC LIMIT 1")
            )
            last_project = result.scalar_one_or_none()
            project_start = 0
            if last_project and last_project.startswith("PID"):
                try:
                    project_start = int(last_project[3:])
                except ValueError:
                    pass
            
            # For workflow IDs
            result = await session.execute(
                text("SELECT workflow_id FROM task_graphs WHERE workflow_id LIKE 'WID%' ORDER BY created_at DESC LIMIT 1")
            )
            last_workflow = result.scalar_one_or_none()
            workflow_start = 0
            if last_workflow and last_workflow.startswith("WID"):
                try:
                    workflow_start = int(last_workflow[3:])
                except ValueError:
                    pass
            
            # For task IDs
            result = await session.execute(
                text("SELECT step_id FROM task_steps WHERE step_id LIKE 'TID%' ORDER BY created_at DESC LIMIT 1")
            )
            last_task = result.scalar_one_or_none()
            task_start = 0
            if last_task and last_task.startswith("TID"):
                try:
                    task_start = int(last_task[3:])
                except ValueError:
                    pass
            
            # Insert initial counter values
            await session.execute(
                text("INSERT INTO id_counters (id, counter_type, current_value, created_at, updated_at) "
                     "VALUES (gen_random_uuid(), 'project', :val, NOW(), NOW()) "
                     "ON CONFLICT (counter_type) DO NOTHING"),
                {"val": project_start}
            )
            
            await session.execute(
                text("INSERT INTO id_counters (id, counter_type, current_value, created_at, updated_at) "
                     "VALUES (gen_random_uuid(), 'workflow', :val, NOW(), NOW()) "
                     "ON CONFLICT (counter_type) DO NOTHING"),
                {"val": workflow_start}
            )
            
            await session.execute(
                text("INSERT INTO id_counters (id, counter_type, current_value, created_at, updated_at) "
                     "VALUES (gen_random_uuid(), 'task', :val, NOW(), NOW()) "
                     "ON CONFLICT (counter_type) DO NOTHING"),
                {"val": task_start}
            )
            
            await session.commit()
            
            print(f"✅ Counters initialized:")
            print(f"   - Project counter: {project_start}")
            print(f"   - Workflow counter: {workflow_start}")
            print(f"   - Task counter: {task_start}")
    
    await engine.dispose()
    print(f"\n✅ Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())

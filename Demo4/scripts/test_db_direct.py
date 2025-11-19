"""Test database persistence directly."""
import asyncio
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from agent_manager.orm import Base, TaskGraphORM, TaskStepORM

async def test_direct_save():
    """Test saving directly to database."""
    # Create engine
    engine = create_async_engine("sqlite+aiosqlite:///agent_manager.db", echo=True)
    
    # Create session factory
    SessionFactory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with SessionFactory() as session:
        try:
            # Create test workflow
            workflow_id = str(uuid4())
            print(f"\n[TEST] Creating workflow: {workflow_id}")
            
            task_graph_orm = TaskGraphORM(
                workflow_id=workflow_id,
                user_request="TEST: Direct database save",
                workflow_metadata={"test": True},
                status="IN_PROGRESS",
                created_at=datetime.utcnow()
            )
            
            session.add(task_graph_orm)
            await session.flush()
            
            # Create test task
            task_step_orm = TaskStepORM(
                step_id="test_step_1",
                workflow_id=workflow_id,
                task_description="Test task",
                assigned_agent="analyst",
                dependencies=[],
                file_dependencies=[],
                file_access_types={},
                status="READY",
                created_at=datetime.utcnow()
            )
            
            session.add(task_step_orm)
            
            # COMMIT
            print("[TEST] Committing to database...")
            await session.commit()
            print("[TEST] ✅ Commit successful!")
            
            # Verify it was saved
            from sqlalchemy import select
            stmt = select(TaskGraphORM).where(TaskGraphORM.workflow_id == workflow_id)
            result = await session.execute(stmt)
            saved = result.scalar_one_or_none()
            
            if saved:
                print(f"[TEST] ✅ Workflow found in database: {saved.workflow_id}")
                print(f"[TEST] User request: {saved.user_request}")
            else:
                print("[TEST] ❌ Workflow NOT found in database!")
                
        except Exception as e:
            print(f"[TEST] ❌ Error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

if __name__ == "__main__":
    asyncio.run(test_direct_save())

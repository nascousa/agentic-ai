"""Check recent projects created in the database"""
import asyncio
from agent_manager.db import get_database_session
from agent_manager.orm import ProjectORM, TaskGraphORM
from sqlalchemy import select

async def check_projects():
    """Query recent projects from the database"""
    async for session in get_database_session():
        try:
            # Get recent projects
            stmt = select(ProjectORM).order_by(ProjectORM.created_at.desc()).limit(5)
            result = await session.execute(stmt)
            projects = result.scalars().all()
            
            print("\n📁 Recent Projects:")
            print("=" * 80)
            for p in projects:
                print(f"\nProject Name: {p.project_name}")
                print(f"Project Path: {p.project_path}")
                print(f"Status: {p.status}")
                print(f"Created: {p.created_at}")
                
                # Get workflows for this project
                workflows_stmt = select(TaskGraphORM).where(TaskGraphORM.project_id == p.id)
                workflows_result = await session.execute(workflows_stmt)
                workflows = workflows_result.scalars().all()
                print(f"Workflows: {len(workflows)}")
                for w in workflows:
                    print(f"  - {w.workflow_name or 'Unnamed'} ({w.status})")
                print("-" * 80)
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_projects())

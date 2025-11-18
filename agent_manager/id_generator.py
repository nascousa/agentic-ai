"""
Sequential ID Generator with Database Persistence

Generates sequential IDs with prefixes (PID, WID, TID) stored in database
to ensure uniqueness across server restarts and distributed workers.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from agent_manager.orm import IDCounterORM


class SequentialIDGenerator:
    """Thread-safe sequential ID generator with database persistence."""
    
    @staticmethod
    async def get_next_project_id(session: AsyncSession) -> str:
        """Generate next project ID: PID000001, PID000002, etc."""
        return await SequentialIDGenerator._get_next_id(session, "project", "PID", 6)
    
    @staticmethod
    async def get_next_workflow_id(session: AsyncSession) -> str:
        """Generate next workflow ID: WID00000001, WID00000002, etc."""
        return await SequentialIDGenerator._get_next_id(session, "workflow", "WID", 8)
    
    @staticmethod
    async def get_next_task_id(session: AsyncSession) -> str:
        """Generate next task ID: TID0000000001, TID0000000002, etc."""
        return await SequentialIDGenerator._get_next_id(session, "task", "TID", 10)
    
    @staticmethod
    async def _get_next_id(
        session: AsyncSession,
        counter_type: str,
        prefix: str,
        padding: int
    ) -> str:
        """
        Get next sequential ID from database counter.
        
        Args:
            session: Database session
            counter_type: Type of counter (project/workflow/task)
            prefix: ID prefix (PID/WID/TID)
            padding: Number of digits for zero-padding
            
        Returns:
            Formatted sequential ID
        """
        # Query for existing counter
        stmt = select(IDCounterORM).where(
            IDCounterORM.counter_type == counter_type
        ).with_for_update()
        
        result = await session.execute(stmt)
        counter = result.scalar_one_or_none()
        
        if counter is None:
            # Create new counter starting at 1
            counter = IDCounterORM(
                counter_type=counter_type,
                current_value=1
            )
            session.add(counter)
            await session.flush()
            next_value = 1
        else:
            # Increment existing counter
            next_value = counter.current_value + 1
            counter.current_value = next_value
            await session.flush()
        
        # Format with zero-padding
        return f"{prefix}{next_value:0{padding}d}"


# Synchronous wrapper functions for use in Pydantic default_factory
# These will be replaced with async calls at the service layer

def generate_project_id_sync() -> str:
    """Placeholder for project ID - will be replaced by service layer."""
    return "PID_PENDING"


def generate_workflow_id_sync() -> str:
    """Placeholder for workflow ID - will be replaced by service layer."""
    return "WID_PENDING"


def generate_task_id_sync() -> str:
    """Placeholder for task ID - will be replaced by service layer."""
    return "TID_PENDING"

# Test database initialization and ORM models
import asyncio
import sys
from agent_manager.db import create_database_tables, get_database_session
from agent_manager.orm import TaskGraphORM, TaskStepORM, ResultORM, AuditReportORM
from sqlalchemy import text

async def test_database():
    print("Testing Database Initialization...")
    
    try:
        # Initialize database tables
        await create_database_tables()
        
        # Test database session and table creation
        async for session in get_database_session():
            print("Database session created successfully")
            
            # Check table creation
            tables_query = text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables_result = await session.execute(tables_query)
            tables = [row[0] for row in tables_result.fetchall()]
            
            expected_tables = ['audit_reports', 'results', 'task_graphs', 'task_steps']
            print(f"Created tables: {tables}")
            
            for table in expected_tables:
                if table in tables:
                    print(f"[OK] Table '{table}' exists")
                else:
                    print(f"[FAIL] Table '{table}' missing")
            
            # Test basic operations
            print("\nTesting basic ORM operations...")
            
            # Test count queries on each table
            for model, table_name in [
                (TaskGraphORM, 'task_graphs'),
                (TaskStepORM, 'task_steps'), 
                (ResultORM, 'results'),
                (AuditReportORM, 'audit_reports')
            ]:
                try:
                    count_result = await session.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    )
                    count = count_result.scalar()
                    print(f"[OK] {model.__name__}: {count} records")
                except Exception as e:
                    print(f"[FAIL] {model.__name__} query failed: {e}")
            
            break  # Exit the async generator loop
        
        print("Database initialization test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database())
    sys.exit(0 if success else 1)
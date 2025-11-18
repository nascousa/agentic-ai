"""
Integration tests for file access coordination and concurrent worker safety.

This module tests the file locking mechanisms, database coordination,
and worker-level file safety to ensure no conflicts occur when multiple
agents access the same files.
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from agent_manager.core.models import TaskStep, TaskStatus, RAHistory
from agent_manager.core.worker import WorkerAgent
from agent_manager.core.file_lock import (
    FileAccessManager,
    file_lock,
    extract_file_paths_from_action,
    classify_file_access_type,
    FileLockError,
    FileLockTimeout
)
from agent_manager.service import DatabaseService
from agent_manager.orm import FileAccessORM


class TestFileAccessManager:
    """Test the file access manager coordination."""
    
    @pytest.fixture
    def file_manager(self):
        """Create fresh file manager for each test."""
        return FileAccessManager()
    
    @pytest.fixture
    def temp_file(self):
        """Create temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass
    
    @pytest.mark.asyncio
    async def test_single_read_lock(self, file_manager, temp_file):
        """Test acquiring a single read lock."""
        async with file_manager.acquire_file_lock(
            temp_file, "read", client_id="test_client"
        ) as handle:
            assert handle is not None
            assert file_manager.is_file_locked(temp_file)
            
            # Verify lock is registered
            locks = file_manager.get_active_locks()
            assert temp_file in locks
            assert locks[temp_file]['access_type'] == 'read'
            assert locks[temp_file]['client_id'] == 'test_client'
        
        # After context, lock should be released
        assert not file_manager.is_file_locked(temp_file)
    
    @pytest.mark.asyncio
    async def test_multiple_read_locks(self, file_manager, temp_file):
        """Test that multiple read locks can coexist."""
        async def acquire_read_lock(client_id: str):
            async with file_manager.acquire_file_lock(
                temp_file, "read", client_id=client_id
            ) as handle:
                await asyncio.sleep(0.1)  # Hold lock briefly
                return True
        
        # Run multiple read locks concurrently
        results = await asyncio.gather(
            acquire_read_lock("client_1"),
            acquire_read_lock("client_2"),
            acquire_read_lock("client_3")
        )
        
        # All should succeed
        assert all(results)
    
    @pytest.mark.asyncio
    async def test_exclusive_lock_blocks_others(self, file_manager, temp_file):
        """Test that exclusive locks block all other access."""
        # Acquire exclusive lock in background
        async def hold_exclusive_lock():
            async with file_manager.acquire_file_lock(
                temp_file, "exclusive", client_id="exclusive_client"
            ):
                await asyncio.sleep(0.2)
        
        # Try to acquire read lock while exclusive is held
        async def try_read_lock():
            try:
                async with file_manager.acquire_file_lock(
                    temp_file, "read", timeout_seconds=0.1, client_id="read_client"
                ):
                    return True
            except FileLockTimeout:
                return False
        
        # Start exclusive lock
        exclusive_task = asyncio.create_task(hold_exclusive_lock())
        await asyncio.sleep(0.05)  # Let exclusive lock acquire
        
        # Try read lock (should fail)
        read_result = await try_read_lock()
        
        await exclusive_task
        
        assert not read_result
    
    @pytest.mark.asyncio
    async def test_write_lock_exclusivity(self, file_manager, temp_file):
        """Test that write locks are exclusive."""
        lock_acquired = []
        
        async def acquire_write_lock(client_id: str):
            try:
                async with file_manager.acquire_file_lock(
                    temp_file, "write", timeout_seconds=0.1, client_id=client_id
                ):
                    lock_acquired.append(client_id)
                    await asyncio.sleep(0.1)
                return True
            except FileLockTimeout:
                return False
        
        # Try multiple write locks simultaneously
        results = await asyncio.gather(
            acquire_write_lock("writer_1"),
            acquire_write_lock("writer_2"),
            return_exceptions=True
        )
        
        # Only one should succeed
        successful_locks = sum(1 for r in results if r is True)
        assert successful_locks == 1
        assert len(lock_acquired) == 1


class TestFilePathExtraction:
    """Test file path extraction and classification."""
    
    def test_extract_absolute_paths(self):
        """Test extraction of absolute file paths."""
        # Windows path
        action_win = "Edit file C:\\Users\\test\\document.txt and save changes"
        paths_win = extract_file_paths_from_action(action_win)
        assert any("document.txt" in path for path in paths_win)
        
        # Unix path
        action_unix = "Read /home/user/config.json and update settings"
        paths_unix = extract_file_paths_from_action(action_unix)
        assert any("config.json" in path for path in paths_unix)
    
    def test_extract_relative_paths(self):
        """Test extraction of relative file paths."""
        action = "Modify ./src/main.py and ../tests/test_main.py"
        paths = extract_file_paths_from_action(action)
        
        assert len(paths) >= 2
        assert any("main.py" in path for path in paths)
        assert any("test_main.py" in path for path in paths)
    
    def test_extract_quoted_paths(self):
        """Test extraction of quoted file paths."""
        action = 'Update "file with spaces.txt" and \'another-file.json\''
        paths = extract_file_paths_from_action(action)
        
        assert any("file with spaces.txt" in path for path in paths)
        assert any("another-file.json" in path for path in paths)
    
    def test_classify_read_access(self):
        """Test classification of read access."""
        action = "Read the configuration file and analyze its contents"
        access_type = classify_file_access_type(action, "config.txt")
        assert access_type == "read"
    
    def test_classify_write_access(self):
        """Test classification of write access."""
        action = "Write new data to the output file"
        access_type = classify_file_access_type(action, "output.txt")
        assert access_type == "write"
        
        action2 = "Edit the source code and save changes"
        access_type2 = classify_file_access_type(action2, "source.py")
        assert access_type2 == "write"
    
    def test_classify_exclusive_access(self):
        """Test classification of exclusive access."""
        action = "Delete the temporary file and clean up"
        access_type = classify_file_access_type(action, "temp.txt")
        assert access_type == "exclusive"
        
        action2 = "Rename the backup file to the main file"
        access_type2 = classify_file_access_type(action2, "backup.txt")
        assert access_type2 == "exclusive"


class TestDatabaseFileCoordination:
    """Test database-level file coordination."""
    
    @pytest.fixture
    async def db_service(self):
        """Create database service with mocked session."""
        session = AsyncMock()
        return DatabaseService(session)
    
    @pytest.mark.asyncio
    async def test_acquire_file_lock_success(self, db_service):
        """Test successful file lock acquisition."""
        # Mock successful lock acquisition
        db_service.session.add = AsyncMock()
        db_service.session.commit = AsyncMock()
        db_service._can_acquire_file_lock = AsyncMock(return_value=True)
        
        result = await db_service.acquire_file_lock(
            file_path="/test/file.txt",
            client_id="test_client",
            access_type="write"
        )
        
        assert result is True
        db_service.session.add.assert_called_once()
        db_service.session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_acquire_file_lock_conflict(self, db_service):
        """Test file lock acquisition with conflict."""
        # Mock conflicting lock
        db_service._can_acquire_file_lock = AsyncMock(return_value=False)
        
        result = await db_service.acquire_file_lock(
            file_path="/test/file.txt",
            client_id="test_client",
            access_type="write"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_release_file_lock(self, db_service):
        """Test file lock release."""
        # Mock successful release
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        db_service.session.execute = AsyncMock(return_value=mock_result)
        db_service.session.commit = AsyncMock()
        
        result = await db_service.release_file_lock(
            file_path="/test/file.txt",
            client_id="test_client"
        )
        
        assert result is True
        db_service.session.execute.assert_called_once()
        db_service.session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_locks(self, db_service):
        """Test cleanup of expired file locks."""
        # Mock cleanup operation
        mock_result = AsyncMock()
        mock_result.rowcount = 3
        db_service.session.execute = AsyncMock(return_value=mock_result)
        db_service.session.commit = AsyncMock()
        
        cleaned_count = await db_service.cleanup_expired_file_locks()
        
        assert cleaned_count == 3
        db_service.session.execute.assert_called_once()
        db_service.session.commit.assert_called_once()


class TestWorkerAgentFileSafety:
    """Test WorkerAgent integration with file safety."""
    
    @pytest.fixture
    def sample_task(self):
        """Create sample task with file dependencies."""
        return TaskStep(
            step_id="test_task_1",
            workflow_id="test_workflow",
            task_description="Process data files and generate report",
            assigned_agent="analyst",
            file_dependencies=[
                "/data/input.csv",
                "/output/report.txt"
            ],
            file_access_types={
                "/data/input.csv": "read",
                "/output/report.txt": "write"
            }
        )
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock()
        client.run_prompt_for_json = AsyncMock()
        client.run_simple_prompt = AsyncMock(return_value="Task completed successfully")
        return client
    
    @pytest.mark.asyncio
    async def test_worker_with_file_dependencies(self, sample_task, mock_llm_client):
        """Test worker execution with declared file dependencies."""
        # Mock LLM responses
        mock_thought_action = AsyncMock()
        mock_thought_action.thought = "I need to process the data files"
        mock_thought_action.action = "Read input data and generate analysis report"
        mock_thought_action.iteration_number = 1
        mock_thought_action.observation = None
        mock_llm_client.run_prompt_for_json.return_value = mock_thought_action
        
        # Create worker with mocked LLM
        worker = WorkerAgent(
            name="TestAnalyst",
            role="analyst",
            llm_client=mock_llm_client,
            client_id="test_worker_1"
        )
        
        # Mock file lock context managers
        with patch('agent_manager.core.worker.file_lock') as mock_file_lock:
            mock_file_lock.return_value.__aenter__ = AsyncMock()
            mock_file_lock.return_value.__aexit__ = AsyncMock()
            
            # Execute task
            result = await worker.execute_task(sample_task)
            
            # Verify result structure
            assert isinstance(result, RAHistory)
            assert result.source_agent == "analyst"
            assert result.client_id == "test_worker_1"
            assert len(result.iterations) > 0
    
    @pytest.mark.asyncio
    async def test_worker_file_lock_timeout_handling(self, sample_task, mock_llm_client):
        """Test worker handling of file lock timeouts."""
        mock_thought_action = AsyncMock()
        mock_thought_action.thought = "Processing with file operations"
        mock_thought_action.action = "Write results to /output/report.txt"
        mock_thought_action.iteration_number = 1
        mock_llm_client.run_prompt_for_json.return_value = mock_thought_action
        
        worker = WorkerAgent(
            name="TestWorker",
            role="writer",
            llm_client=mock_llm_client
        )
        
        # Mock file lock timeout
        with patch('agent_manager.core.worker.file_lock') as mock_file_lock:
            mock_file_lock.side_effect = FileLockTimeout("Lock timeout")
            
            # Should handle timeout gracefully
            result = await worker.execute_task(sample_task)
            assert isinstance(result, RAHistory)
    
    @pytest.mark.asyncio
    async def test_action_file_path_extraction(self, mock_llm_client):
        """Test automatic file path extraction from actions."""
        task = TaskStep(
            step_id="extract_test",
            workflow_id="test_workflow", 
            task_description="Test file path extraction",
            assigned_agent="tester"
        )
        
        # Mock action with file paths
        mock_thought_action = AsyncMock()
        mock_thought_action.thought = "I need to work with files"
        mock_thought_action.action = "Edit /path/to/source.py and save to ./output/result.txt"
        mock_thought_action.iteration_number = 1
        mock_llm_client.run_prompt_for_json.return_value = mock_thought_action
        
        worker = WorkerAgent(
            name="TestExtractor",
            role="tester",
            llm_client=mock_llm_client
        )
        
        with patch('agent_manager.core.worker.extract_file_paths_from_action') as mock_extract:
            mock_extract.return_value = {"/path/to/source.py", "./output/result.txt"}
            
            with patch('agent_manager.core.worker.file_lock') as mock_file_lock:
                mock_file_lock.return_value.__aenter__ = AsyncMock()
                mock_file_lock.return_value.__aexit__ = AsyncMock()
                
                result = await worker.execute_task(task)
                
                # Verify file path extraction was called
                mock_extract.assert_called()
                assert isinstance(result, RAHistory)


class TestConcurrentFileAccess:
    """Test concurrent file access scenarios."""
    
    @pytest.mark.asyncio
    async def test_multiple_workers_same_file_read(self):
        """Test multiple workers reading the same file concurrently."""
        temp_file = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write("shared test content")
                temp_file = f.name
            
            async def worker_read_task(worker_id: str):
                async with file_lock(temp_file, "read", client_id=worker_id):
                    await asyncio.sleep(0.1)  # Simulate work
                    return f"worker_{worker_id}_success"
            
            # Run multiple workers concurrently
            results = await asyncio.gather(
                worker_read_task("1"),
                worker_read_task("2"),
                worker_read_task("3")
            )
            
            # All should succeed
            assert len(results) == 3
            assert all("success" in result for result in results)
            
        finally:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_writer_blocks_readers(self):
        """Test that a writer blocks concurrent readers."""
        temp_file = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write("test content for writer test")
                temp_file = f.name
            
            write_started = asyncio.Event()
            write_completed = asyncio.Event()
            
            async def writer_task():
                async with file_lock(temp_file, "write", client_id="writer"):
                    write_started.set()
                    await asyncio.sleep(0.2)  # Hold write lock
                    write_completed.set()
                return "write_success"
            
            async def reader_task(reader_id: str):
                # Wait for writer to start
                await write_started.wait()
                
                try:
                    async with file_lock(temp_file, "read", timeout_seconds=0.1, client_id=reader_id):
                        return f"read_{reader_id}_success"
                except FileLockTimeout:
                    return f"read_{reader_id}_blocked"
            
            # Start writer
            writer_future = asyncio.create_task(writer_task())
            
            # Start readers after writer begins
            await write_started.wait()
            reader_results = await asyncio.gather(
                reader_task("1"),
                reader_task("2"),
                return_exceptions=True
            )
            
            # Wait for writer to complete
            writer_result = await writer_future
            
            # Writer should succeed, readers should be blocked
            assert writer_result == "write_success"
            assert all("blocked" in str(result) for result in reader_results)
            
        finally:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)


@pytest.mark.integration
class TestEndToEndFileCoordination:
    """End-to-end integration tests for file coordination."""
    
    @pytest.mark.asyncio
    async def test_workflow_with_file_dependencies(self):
        """Test complete workflow with file dependencies."""
        # This would be a comprehensive test integrating:
        # 1. Task creation with file dependencies
        # 2. Worker coordination through database
        # 3. File lock acquisition and release
        # 4. Successful workflow completion
        
        # For now, this is a placeholder for the complete integration test
        # that would require full database setup and multiple worker simulation
        pass


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "not integration"  # Skip integration tests by default
    ])
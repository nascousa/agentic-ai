"""
Cross-platform file locking utilities for concurrent worker coordination.

This module provides safe file access mechanisms that work across Windows
and Unix-like systems, preventing file access conflicts when multiple
agent workers need to access the same files.
"""

import os
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Set, Any
from pathlib import Path
from datetime import datetime, timedelta

# Platform-specific imports
try:
    import fcntl  # Unix/Linux file locking
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt  # Windows file locking
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


class FileLockError(Exception):
    """Exception raised when file locking operations fail."""
    pass


class FileLockTimeout(FileLockError):
    """Exception raised when file lock acquisition times out."""
    pass


class FileAccessManager:
    """
    Cross-platform file access coordination manager.
    
    Provides both OS-level file locking and application-level
    coordination for safe concurrent file access.
    """
    
    def __init__(self):
        """Initialize file access manager."""
        self._active_locks: Dict[str, Dict[str, Any]] = {}
        self._lock_registry: Set[str] = set()
    
    @asynccontextmanager
    async def acquire_file_lock(
        self,
        file_path: str,
        access_type: str = "read",
        timeout_seconds: float = 30.0,
        client_id: Optional[str] = None
    ):
        """
        Acquire cross-platform file lock with timeout.
        
        Args:
            file_path: Absolute path to file to lock
            access_type: Type of access ('read', 'write', 'exclusive')
            timeout_seconds: Maximum time to wait for lock
            client_id: Identifier for the client acquiring the lock
            
        Yields:
            File handle with acquired lock
            
        Raises:
            FileLockTimeout: If lock cannot be acquired within timeout
            FileLockError: If lock operation fails
        """
        normalized_path = os.path.abspath(file_path)
        lock_key = f"{normalized_path}:{access_type}"
        
        # Check for conflicting locks
        if not self._can_acquire_lock(normalized_path, access_type):
            raise FileLockError(
                f"Cannot acquire {access_type} lock on {file_path}: conflicting lock exists"
            )
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(normalized_path), exist_ok=True)
        
        # Determine file mode based on access type
        file_mode = self._get_file_mode(access_type)
        
        file_handle = None
        start_time = time.time()
        
        try:
            # Try to acquire lock with timeout
            while time.time() - start_time < timeout_seconds:
                try:
                    file_handle = open(normalized_path, file_mode)
                    
                    # Apply OS-level lock
                    if HAS_FCNTL and os.name != 'nt':
                        # Unix/Linux locking
                        lock_type = self._get_fcntl_lock_type(access_type)
                        fcntl.flock(file_handle.fileno(), lock_type)
                    elif HAS_MSVCRT and os.name == 'nt':
                        # Windows locking
                        lock_type = self._get_msvcrt_lock_type(access_type)
                        msvcrt.locking(file_handle.fileno(), lock_type, 1)
                    
                    # Register application-level lock
                    self._register_lock(normalized_path, access_type, client_id)
                    
                    break
                    
                except (OSError, IOError):
                    if file_handle:
                        file_handle.close()
                        file_handle = None
                    
                    # Wait before retry
                    await asyncio.sleep(0.1)
            
            if file_handle is None:
                raise FileLockTimeout(
                    f"Failed to acquire {access_type} lock on {file_path} within {timeout_seconds} seconds"
                )
            
            # Yield the locked file handle
            yield file_handle
            
        finally:
            # Always release lock and close file
            if file_handle:
                try:
                    # Release OS-level lock
                    if HAS_FCNTL and os.name != 'nt':
                        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
                    elif HAS_MSVCRT and os.name == 'nt':
                        msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                except (OSError, IOError):
                    pass  # Lock might already be released
                
                file_handle.close()
            
            # Unregister application-level lock
            self._unregister_lock(normalized_path, access_type)
    
    def _can_acquire_lock(self, file_path: str, access_type: str) -> bool:
        """
        Check if lock can be acquired without conflicts.
        
        Lock compatibility matrix:
        - Multiple 'read' locks are allowed
        - 'write' locks are exclusive
        - 'exclusive' locks block everything
        """
        for existing_path, lock_info in self._active_locks.items():
            if existing_path == file_path:
                existing_type = lock_info['access_type']
                
                # Exclusive locks block everything
                if existing_type == 'exclusive' or access_type == 'exclusive':
                    return False
                
                # Write locks are exclusive
                if existing_type == 'write' or access_type == 'write':
                    return False
                
                # Multiple read locks are OK
                if existing_type == 'read' and access_type == 'read':
                    continue
        
        return True
    
    def _get_file_mode(self, access_type: str) -> str:
        """Get appropriate file mode for access type."""
        if access_type in ('write', 'exclusive'):
            return 'a+'  # Append mode to avoid truncating
        else:
            return 'r'   # Read-only mode
    
    def _get_fcntl_lock_type(self, access_type: str) -> int:
        """Get fcntl lock type for Unix systems."""
        if not HAS_FCNTL:
            raise FileLockError("fcntl not available on this platform")
        
        if access_type == 'read':
            return fcntl.LOCK_SH  # Shared lock
        else:
            return fcntl.LOCK_EX  # Exclusive lock
    
    def _get_msvcrt_lock_type(self, access_type: str) -> int:
        """Get msvcrt lock type for Windows systems."""
        if not HAS_MSVCRT:
            raise FileLockError("msvcrt not available on this platform")
        
        if access_type == 'read':
            return msvcrt.LK_LOCK   # Standard lock
        else:
            return msvcrt.LK_LOCK   # Windows doesn't distinguish shared/exclusive at this level
    
    def _register_lock(self, file_path: str, access_type: str, client_id: Optional[str]):
        """Register lock in application-level registry."""
        self._active_locks[file_path] = {
            'access_type': access_type,
            'client_id': client_id,
            'acquired_at': datetime.utcnow(),
        }
        self._lock_registry.add(f"{file_path}:{access_type}")
    
    def _unregister_lock(self, file_path: str, access_type: str):
        """Unregister lock from application-level registry."""
        if file_path in self._active_locks:
            del self._active_locks[file_path]
        
        lock_key = f"{file_path}:{access_type}"
        if lock_key in self._lock_registry:
            self._lock_registry.remove(lock_key)
    
    def get_active_locks(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active locks."""
        return self._active_locks.copy()
    
    def is_file_locked(self, file_path: str) -> bool:
        """Check if a file is currently locked."""
        normalized_path = os.path.abspath(file_path)
        return normalized_path in self._active_locks
    
    def cleanup_expired_locks(self, max_age_hours: float = 24.0):
        """Clean up locks that are older than specified age."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_paths = []
        
        for file_path, lock_info in self._active_locks.items():
            if lock_info['acquired_at'] < cutoff_time:
                expired_paths.append(file_path)
        
        for path in expired_paths:
            lock_info = self._active_locks[path]
            self._unregister_lock(path, lock_info['access_type'])


# Global file access manager instance
_global_file_manager = FileAccessManager()


@asynccontextmanager
async def file_lock(
    file_path: str,
    access_type: str = "read",
    timeout_seconds: float = 30.0,
    client_id: Optional[str] = None
):
    """
    Convenience function for acquiring file locks.
    
    Args:
        file_path: Path to file to lock
        access_type: Type of access ('read', 'write', 'exclusive')
        timeout_seconds: Maximum wait time for lock
        client_id: Client identifier
        
    Yields:
        File handle with acquired lock
    """
    async with _global_file_manager.acquire_file_lock(
        file_path, access_type, timeout_seconds, client_id
    ) as handle:
        yield handle


def get_file_access_manager() -> FileAccessManager:
    """Get the global file access manager instance."""
    return _global_file_manager


# Utility functions for file path extraction
def extract_file_paths_from_action(action: str) -> Set[str]:
    """
    Extract potential file paths from action description.
    
    Args:
        action: Action description text
        
    Returns:
        Set of potential file paths found in the action
    """
    import re
    
    # Common file path patterns
    patterns = [
        # Absolute paths (Windows and Unix)
        r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*',
        r'/(?:[^/\0]+/)*[^/\0]*',
        
        # Relative paths with common extensions
        r'(?:\./)?(?:[^/\\:*?"<>|\r\n\s]+/)*[^/\\:*?"<>|\r\n\s]*\.[a-zA-Z0-9]+',
        
        # Quoted file paths
        r'"([^"]*\.[a-zA-Z0-9]+)"',
        r"'([^']*\.[a-zA-Z0-9]+)'",
    ]
    
    file_paths = set()
    
    for pattern in patterns:
        matches = re.findall(pattern, action)
        for match in matches:
            # Handle tuple results from groups
            if isinstance(match, tuple):
                match = match[0] if match[0] else match[1]
            
            # Basic validation
            if match and len(match) > 1:
                # Convert to absolute path if possible
                try:
                    abs_path = os.path.abspath(match)
                    file_paths.add(abs_path)
                except (OSError, ValueError):
                    # Keep original if conversion fails
                    file_paths.add(match)
    
    return file_paths


def classify_file_access_type(action: str, file_path: str) -> str:
    """
    Classify the type of file access based on action description.
    
    Args:
        action: Action description
        file_path: Path to the file
        
    Returns:
        Access type: 'read', 'write', or 'exclusive'
    """
    action_lower = action.lower()
    
    # Exclusive access indicators
    exclusive_words = ['delete', 'remove', 'rename', 'move', 'replace']
    if any(word in action_lower for word in exclusive_words):
        return 'exclusive'
    
    # Write access indicators
    write_words = ['write', 'edit', 'modify', 'update', 'create', 'save', 'append']
    if any(word in action_lower for word in write_words):
        return 'write'
    
    # Default to read access
    return 'read'
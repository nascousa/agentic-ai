"""
Custom exception classes for Agent Manager.
"""


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class WorkflowError(Exception):
    """Raised when workflow operations fail."""
    pass
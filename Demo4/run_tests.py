#!/usr/bin/env python3
"""
Test runner script for AM (AgentManager) MCP Server.

Provides convenient commands for running different test suites
with proper configuration and reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="AM MCP Server Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    
    args = parser.parse_args()
    
    # Set up test environment
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    
    # Base pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]
    
    if args.verbose:
        pytest_cmd.append("-v")
    
    if args.coverage:
        pytest_cmd.extend(["--cov=agent_manager", "--cov-report=html", "--cov-report=term"])
    
    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])
    
    # Determine which tests to run
    if args.unit:
        pytest_cmd.extend(["-m", "unit", "tests/test_api_endpoints.py"])
        run_command(pytest_cmd, "Running unit tests")
    elif args.integration:
        pytest_cmd.extend(["-m", "integration", "tests/test_integration.py", "tests/test_database_service.py"])
        run_command(pytest_cmd, "Running integration tests")
    else:
        # Run all tests
        pytest_cmd.append("tests/")
        success = run_command(pytest_cmd, "Running all tests")
        
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
    
    # Generate coverage report if requested
    if args.coverage:
        print("\n📊 Coverage report generated in htmlcov/index.html")


if __name__ == "__main__":
    main()
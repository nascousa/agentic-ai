#!/usr/bin/env python3
"""
Environment check script for AgentManager project.
Verifies that the virtual environment is properly set up and all dependencies are available.
"""

import sys
import subprocess
from pathlib import Path

def check_virtual_environment():
    """Check if we're running in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    print("🔍 Virtual Environment Check")
    print(f"  Python executable: {sys.executable}")
    print(f"  Virtual environment: {'✅ Active' if in_venv else '❌ Not active'}")
    print(f"  Python version: {sys.version}")
    
    if in_venv:
        venv_path = Path(sys.executable).parent.parent
        print(f"  Environment path: {venv_path}")
    
    return in_venv

def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = [
        'fastapi',
        'uvicorn', 
        'sqlalchemy',
        'pydantic',
        'openai',
        'httpx',
        'pytest',
        'black',
        'mypy'
    ]
    
    print("\n📦 Package Dependencies Check")
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (missing)")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def check_agent_manager():
    """Check if AgentManager package is properly installed."""
    print("\n🤖 AgentManager Package Check")
    
    try:
        from agent_manager.api.main import create_application
        from agent_manager.service import DatabaseService
        from agent_manager.core.manager import AgentManager
        from agent_manager.core.worker import WorkerAgent
        from agent_manager.core.auditor import AuditorAgent
        from agent_manager.core.llm_client import LLMClient
        print("  ✅ All core modules import successfully")
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def check_database():
    """Check if database can be initialized."""
    print("\n🗄️  Database Check")
    
    try:
        from agent_manager.orm import Base, TaskGraphORM, TaskStepORM
        print("  ✅ ORM models import successfully")
        return True
    except Exception as e:
        print(f"  ❌ Database check failed: {e}")
        return False

def main():
    """Run all environment checks."""
    print("🚀 AgentManager Environment Verification")
    print("=" * 50)
    
    checks = [
        ("Virtual Environment", check_virtual_environment()),
        ("Dependencies", check_dependencies()),
        ("AgentManager Package", check_agent_manager()),
        ("Database Setup", check_database())
    ]
    
    print("\n📊 Summary")
    print("-" * 30)
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 Environment is ready for development!")
        print("\nNext steps:")
        print("  1. Create .env file with API keys")
        print("  2. Run tests: pytest tests/ -v")
        print("  3. Start server: uvicorn agent_manager.api.main:app --reload")
    else:
        print("⚠️  Environment setup incomplete. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
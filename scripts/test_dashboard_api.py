#!/usr/bin/env python3
"""Test script to verify dashboard API calls"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from api_client import AgentManagerClient

def test_worker_status():
    """Test worker status API endpoint"""
    print("Testing Worker Status API...")
    print("=" * 60)
    
    client = AgentManagerClient(
        server_url="http://localhost:8001",
        auth_token="am_server_30j_MNJFG086I8kh2fdsAU_aA7ggR4OTv5iR-tYcuyQ"
    )
    
    # Get Docker workers
    print("\n1. Docker Workers:")
    print("-" * 60)
    workers = client.get_docker_workers()
    for worker in workers:
        print(f"  - {worker['name']:20} | Role: {worker['role']:12} | Status: {worker['status']}")
    
    # Get worker status from API
    print("\n2. Worker Status API Response:")
    print("-" * 60)
    worker_status = client.get_worker_status()
    print(f"  Total Active: {worker_status.get('total_active', 0)}")
    print(f"  Worker Tasks:")
    worker_tasks = worker_status.get('worker_tasks', {})
    if worker_tasks:
        for worker_id, task_info in worker_tasks.items():
            print(f"    - {worker_id:20} -> {task_info['task_name']}")
    else:
        print("    (No active tasks)")
    
    # Test the matching logic
    print("\n3. Matching Test:")
    print("-" * 60)
    worker_dict = {w['name']: w for w in workers}
    
    # Simulate what dashboard does
    for worker_name in [w['name'] for w in workers]:
        task_info = worker_tasks.get(worker_name)
        if task_info:
            print(f"  ✓ {worker_name:20} -> EXECUTING: {task_info['task_name']}")
        else:
            print(f"  ✗ {worker_name:20} -> IDLE (no task)")
    
    print("\n" + "=" * 60)
    print("Test Complete!")

if __name__ == '__main__':
    test_worker_status()

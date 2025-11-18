"""Test worker status endpoint"""
import requests
import json

SERVER_URL = "http://localhost:8001"

def test_worker_status():
    """Test the worker status endpoint"""
    try:
        # Submit a workflow
        print("Submitting test workflow...")
        response = requests.post(
            f"{SERVER_URL}/v1/submit_task",
            json={
                "user_request": "Create a simple calculator application",
                "workflow_name": "Calculator",
                "metadata": {}
            },
            timeout=30
        )
        
        if response.status_code == 201:
            workflow = response.json()
            print(f"✅ Workflow created: {workflow['workflow_id']}")
            print(f"   Tasks: {len(workflow['tasks'])}")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return
        
        # Wait a moment for workers to pick up tasks
        import time
        print("\nWaiting 3 seconds for workers to start...")
        time.sleep(3)
        
        # Check worker status
        print("\nChecking worker status...")
        response = requests.get(f"{SERVER_URL}/v1/workers/status")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Worker status retrieved")
            print(f"   Active workers: {data['total_active']}")
            
            if data['worker_tasks']:
                print("\n   Currently executing tasks:")
                for worker_id, task_info in data['worker_tasks'].items():
                    print(f"   - {worker_id}:")
                    print(f"     Task: {task_info['task_name']}")
                    print(f"     ID: {task_info['task_id']}")
            else:
                print("   No tasks currently executing")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_worker_status()

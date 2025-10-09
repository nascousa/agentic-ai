import asyncio
import httpx
import json

async def test_api_endpoints():
    """Test all AgentManager API endpoints"""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing AgentManager API Endpoints...")
    print(f"Base URL: {base_url}")
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Health check
        print("\n1. Testing health check endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: OpenAPI docs endpoint
        print("\n2. Testing OpenAPI docs...")
        try:
            response = await client.get(f"{base_url}/docs")
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 3: Submit task endpoint
        print("\n3. Testing task submission...")
        try:
            task_request = {
                "user_request": "Test workflow: create a simple Python script that prints hello world",
                "metadata": {"priority": "high", "test": True}
            }
            response = await client.post(
                f"{base_url}/v1/submit_task",
                json=task_request
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                task_response = response.json()
                print(f"   Workflow ID: {task_response.get('workflow_id')}")
                print(f"   Number of tasks: {len(task_response.get('tasks', []))}")
                
                # Store workflow_id for further tests
                workflow_id = task_response.get('workflow_id')
                
                # Test 4: Check workflow status
                print("\n4. Testing workflow status...")
                status_response = await client.get(f"{base_url}/v1/workflows/{workflow_id}/status")
                print(f"   Status: {status_response.status_code}")
                print(f"   Response: {status_response.json()}")
                
                # Test 5: Poll for ready tasks
                print("\n5. Testing task polling...")
                poll_response = await client.get(f"{base_url}/v1/tasks/developer/ready")
                print(f"   Status: {poll_response.status_code}")
                if poll_response.status_code == 200:
                    task = poll_response.json()
                    print(f"   Task ID: {task.get('step_id')}")
                    print(f"   Description: {task.get('task_description', '')[:100]}...")
                elif poll_response.status_code == 204:
                    print("   No ready tasks available (expected)")
                else:
                    print(f"   Response: {poll_response.json()}")
                    
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 6: Report result endpoint (with dummy data)
        print("\n6. Testing result reporting...")
        try:
            result_data = {
                "step_id": "test-step-1",
                "workflow_id": "test-workflow",
                "iterations": [
                    {
                        "thought": "I need to create a hello world script",
                        "action": "CREATE_FILE",
                        "action_input": {"filename": "hello.py", "content": "print('Hello, World!')"}
                    }
                ],
                "final_result": "Created hello.py with greeting message",
                "source_agent": "developer",
                "client_id": "test-client",
                "execution_time": 1.5
            }
            response = await client.post(
                f"{base_url}/v1/report_result",
                json=result_data
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\nAPI endpoint testing completed!")

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
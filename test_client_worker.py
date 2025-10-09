# Quick test of client worker functionality
import asyncio
import sys
import json
import httpx
import os
from datetime import datetime
from pathlib import Path

# Add the agent_manager package to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent_manager.core.models import TaskResult, RAHistory
from agent_manager.core.worker import WorkerAgent

class SimpleWorkerClient:
    def __init__(self, role: str, server_url: str):
        self.role = role
        self.server_url = server_url
        self.client_id = f"test-{role}-{datetime.now().strftime('%H%M%S')}"
        self.worker = WorkerAgent(role=role)
        
    async def poll_and_execute_once(self):
        """Poll for one task and execute it"""
        print(f"[{self.client_id}] Polling for {self.role} tasks...")
        
        # Get auth token
        token = os.getenv("SERVER_API_TOKEN")
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            # Poll for ready task
            response = await client.get(
                f"{self.server_url}/v1/tasks/ready",
                headers=headers,
                params={"role": self.role}
            )
            
            if response.status_code == 200:
                task_data = response.json()
                print(f"[{self.client_id}] Got task: {task_data['step_id']}")
                print(f"Description: {task_data['task_description']}")
                
                # Execute task
                result = await self.worker.execute_task(task_data)
                print(f"[{self.client_id}] Executed task. Result: {result.final_result[:100]}...")
                
                # Report result back
                report_response = await client.post(
                    f"{self.server_url}/v1/results",
                    headers=headers,
                    json=result.model_dump()
                )
                print(f"[{self.client_id}] Reported result: {report_response.status_code}")
                
                return True
                
            elif response.status_code == 204:
                print(f"[{self.client_id}] No ready tasks available")
                return False
            else:
                print(f"[{self.client_id}] Error polling: {response.status_code} - {response.text}")
                return False

async def test_client_worker():
    """Test the client worker with researcher role"""
    print("Testing External Client Worker...")
    
    # Load env variables for auth
    from dotenv import load_dotenv
    load_dotenv()
    
    # Create worker for researcher tasks
    worker = SimpleWorkerClient(role="researcher", server_url="http://127.0.0.1:8001")
    
    # Try to poll and execute a task
    success = await worker.poll_and_execute_once()
    
    if success:
        print("✅ Client worker test successful!")
    else:
        print("ℹ️ No tasks available or error occurred")

if __name__ == "__main__":
    asyncio.run(test_client_worker())
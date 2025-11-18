#!/usr/bin/env python3
"""
Monitor AgentManager task execution
"""
import asyncio
import httpx
import json
import time

async def monitor_workflow(workflow_id):
    """Monitor the workflow progress"""
    
    # API configuration
    base_url = "http://localhost:8001"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer am_server_30j_MNJFG086I8kh2fdsAU_aA7ggR4OTv5iR-tYcuyQ"
    }
    
    print(f"🔍 Monitoring Workflow: {workflow_id}")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                # Check workflow status
                response = await client.get(
                    f"{base_url}/v1/workflows/{workflow_id}/status",
                    headers=headers
                )
                
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"⏰ {time.strftime('%H:%M:%S')} - Workflow Status: {status_data.get('status', 'UNKNOWN')}")
                    
                    # Check for ready tasks for any agent type
                    agent_types = ['analyst', 'writer', 'researcher', 'developer', 'tester', 'architect', 'planner', 'reviewer']
                    
                    for agent_type in agent_types:
                        task_response = await client.get(
                            f"{base_url}/v1/tasks/ready?agent_id=monitor_{agent_type}&agent_capabilities={agent_type}",
                            headers=headers
                        )
                        
                        if task_response.status_code == 200 and task_response.text.strip() != 'null':
                            task_data = task_response.json()
                            if task_data:
                                print(f"🎯 Ready task for {agent_type}:")
                                print(f"   Step ID: {task_data.get('step_id')}")
                                print(f"   Description: {task_data.get('task_description', '')[:100]}...")
                                break
                    else:
                        print("📝 No ready tasks found for any agent type")
                    
                    # Check if workflow is complete
                    if status_data.get('status') in ['COMPLETED', 'FAILED']:
                        print(f"✅ Workflow {status_data.get('status')}!")
                        break
                
                else:
                    print(f"❌ Error checking workflow: {response.status_code}")
                
                # Wait before next check
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    workflow_id = "8adcd71d-8a71-4d35-bdb2-84966b3c5a29"  # Replace with actual workflow ID
    asyncio.run(monitor_workflow(workflow_id))
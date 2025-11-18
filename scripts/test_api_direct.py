"""Test API call with detailed logging."""
import requests
import json

def test_api():
    url = "http://localhost:8001/v1/tasks"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer am_server_30j_MNJFG086I8kh2fdsAU_aA7ggR4OTv5iR-tYcuyQ"
    }
    data = {
        "user_request": "TEST: Create a simple hello world script",
        "metadata": {
            "project_name": "test_hello",
            "test_mode": True
        }
    }
    
    print(f"[TEST] Calling POST {url}")
    print(f"[TEST] Request: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data, headers=headers, timeout=60)
    
    print(f"\n[TEST] Response Status: {response.status_code}")
    print(f"[TEST] Response Headers: {dict(response.headers)}")
    print(f"[TEST] Response Body:\n{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        workflow_id = response.json()["workflow_id"]
        print(f"\n[TEST] ✅ Workflow created: {workflow_id}")
        return workflow_id
    else:
        print(f"\n[TEST] ❌ Failed with status {response.status_code}")
        return None

if __name__ == "__main__":
    workflow_id = test_api()
    
    if workflow_id:
        # Check database
        import sqlite3
        conn = sqlite3.connect("agent_manager.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT workflow_id, user_request, status FROM task_graphs WHERE workflow_id = ?", (workflow_id,))
        result = cursor.fetchone()
        
        if result:
            print(f"\n[TEST] ✅ Found in database: {result}")
        else:
            print(f"\n[TEST] ❌ NOT found in database!")
            
        conn.close()

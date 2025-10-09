#!/usr/bin/env python3
"""
External worker client for MCP server coordination.

This client polls the FastAPI server for ready tasks, executes them locally
using the WorkerAgent, and reports results back to the server.

Usage:
    python client_worker.py --config mcp_client_config.json
    python client_worker.py --agent-id research_worker --capabilities researcher,analyst
"""

import asyncio
import json
import logging
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

# Add the agent_manager package to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent_manager.core.models import (
    TaskStep,
    TaskResult,
    RAHistory,
    ClientPollRequest,
    TaskGraphRequest,
)
from agent_manager.core.worker import WorkerAgent


class ClientConfig(BaseModel):
    """Configuration for the external worker client."""
    client_id: str = Field(..., description="Unique client identifier")
    server_url: str = Field(..., description="Base URL of the MCP server")
    auth_token: str = Field(..., description="Authentication token for API access")
    poll_interval_sec: int = Field(default=5, description="Polling interval in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts for failed requests")
    timeout_sec: int = Field(default=30, description="Request timeout in seconds")
    agent_capabilities: List[str] = Field(..., description="Agent types this client can handle")
    log_level: str = Field(default="INFO", description="Logging level")


class MCPWorkerClient:
    """
    External worker client for MCP server coordination.
    
    Implements the polling pattern for task coordination with proper
    error handling, retry logic, and graceful shutdown.
    
    Go/No-Go Checkpoint: Client demonstrates full polling → execution → reporting cycle
    """
    
    def __init__(self, config: ClientConfig):
        """
        Initialize the worker client.
        
        Args:
            config: Client configuration
        """
        self.config = config
        self.client_id = config.client_id
        self.is_running = False
        
        # Setup logging
        self._setup_logging()
        
        # HTTP client for server communication
        self.http_client = httpx.AsyncClient(
            base_url=config.server_url,
            timeout=config.timeout_sec,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.auth_token}"
            }
        )
        
        # Worker agent for task execution (will be instantiated per task)
        self.worker_agent = None
        
        self.logger.info(f"🤖 Initialized MCP Worker Client {self.client_id}")
        self.logger.info(f"📡 Server: {config.server_url}")
        self.logger.info(f"🎯 Capabilities: {config.agent_capabilities}")
    
    def _setup_logging(self) -> None:
        """Configure logging for the client."""
        self.logger = logging.getLogger(f"mcp_client_{self.client_id}")
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    async def start(self) -> None:
        """
        Start the client polling loop.
        
        Runs continuously until stopped, polling for tasks and executing them.
        
        Go/No-Go Checkpoint: Client polls server and processes tasks continuously
        """
        self.is_running = True
        self.logger.info("🚀 Starting MCP Worker Client polling loop")
        
        try:
            await self._polling_loop()
        except KeyboardInterrupt:
            self.logger.info("⏹️ Received shutdown signal")
        except Exception as e:
            self.logger.error(f"❌ Critical error in polling loop: {str(e)}")
            raise
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Gracefully stop the client."""
        self.is_running = False
        await self.http_client.aclose()
        self.logger.info("🔴 MCP Worker Client stopped")
    
    async def _polling_loop(self) -> None:
        """Main polling loop for task coordination."""
        while self.is_running:
            try:
                # Poll for ready tasks
                task = await self._poll_for_task()
                
                if task:
                    # Execute the task
                    await self._execute_and_report_task(task)
                else:
                    # No tasks available, wait before next poll
                    await asyncio.sleep(self.config.poll_interval_sec)
                    
            except Exception as e:
                self.logger.error(f"❌ Error in polling loop: {str(e)}")
                await asyncio.sleep(self.config.poll_interval_sec)
    
    async def _poll_for_task(self) -> Optional[TaskStep]:
        """
        Poll the server for ready tasks.
        
        Returns:
            TaskStep: Ready task or None if no tasks available
        """
        try:
            # Use GET request with query parameters for /v1/tasks/ready
            params = {
                "agent_id": self.client_id,
                "agent_capabilities": self.config.agent_capabilities
            }
            
            response = await self.http_client.get(
                "/v1/tasks/ready",
                params=params
            )
            
            if response.status_code == 200:
                task_data = response.json()
                if task_data:
                    task = TaskStep.model_validate(task_data)
                    self.logger.info(f"🎯 Claimed task {task.step_id} for {task.assigned_agent}")
                    return task
                else:
                    self.logger.debug("📭 No tasks available")
                    return None
            elif response.status_code == 204:
                self.logger.debug("📭 No tasks available (204)")
                return None
            else:
                self.logger.warning(f"⚠️ Unexpected poll response: {response.status_code}")
                return None
                
        except httpx.TimeoutException:
            self.logger.warning("⏰ Poll request timed out")
            return None
        except Exception as e:
            self.logger.error(f"❌ Poll request failed: {str(e)}")
            return None
    
    async def _execute_and_report_task(self, task: TaskStep) -> None:
        """
        Execute a task and report the results.
        
        Args:
            task: Task to execute
            
        Go/No-Go Checkpoint: Task execution produces RAHistory with proper result reporting
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"🔥 Executing task {task.step_id}: {task.task_description[:100]}...")
            
            # Create WorkerAgent for this task
            worker_agent = WorkerAgent(
                name=f"Worker_{self.client_id}",
                role=task.assigned_agent
            )
            
            # Execute the task using WorkerAgent
            ra_history = await worker_agent.execute_task(task)
            
            # Add client_id to the history
            ra_history.client_id = self.client_id
            
            # Create task result
            task_result = TaskResult(
                workflow_id=task.workflow_id,
                task_id=task.step_id,
                ra_history=ra_history,
                completed_at=datetime.utcnow()
            )
            
            # Report result to server
            success = await self._report_result(task_result)
            
            if success:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                self.logger.info(f"✅ Completed task {task.step_id} in {execution_time:.2f}s")
            else:
                self.logger.error(f"❌ Failed to report result for task {task.step_id}")
                
        except Exception as e:
            self.logger.error(f"❌ Task execution failed {task.step_id}: {str(e)}")
            # Could implement failure reporting here
    
    async def _report_result(self, task_result: TaskResult) -> bool:
        """
        Report task completion to the server.
        
        Args:
            task_result: Complete task execution result
            
        Returns:
            bool: True if reported successfully
        """
        for attempt in range(self.config.max_retries):
            try:
                response = await self.http_client.post(
                    "/v1/results",
                    json=task_result.model_dump(mode="json")
                )
                
                if response.status_code == 204:
                    self.logger.debug(f"📤 Result reported for task {task_result.task_id}")
                    return True
                else:
                    self.logger.warning(f"⚠️ Unexpected result response: {response.status_code}")
                    
            except Exception as e:
                self.logger.error(f"❌ Report attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    async def submit_task(self, user_request: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Submit a new task to the server (convenience method).
        
        Args:
            user_request: User's task description
            metadata: Optional task metadata
            
        Returns:
            str: Workflow ID if successful, None otherwise
        """
        try:
            task_request = TaskGraphRequest(
                user_request=user_request,
                metadata=metadata or {}
            )
            
            response = await self.http_client.post(
                "/v1/tasks",
                json=task_request.model_dump()
            )
            
            if response.status_code == 201:
                result = response.json()
                workflow_id = result.get("workflow_id")
                self.logger.info(f"📝 Submitted task, workflow_id: {workflow_id}")
                return workflow_id
            else:
                self.logger.error(f"❌ Task submission failed: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Task submission error: {str(e)}")
            return None


def load_config(config_path: str) -> ClientConfig:
    """
    Load client configuration from JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        ClientConfig: Loaded configuration
    """
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    return ClientConfig.model_validate(config_data)


def create_default_config(config_path: str) -> None:
    """
    Create a default configuration file.
    
    Args:
        config_path: Path where to create the config file
    """
    default_config = {
        "client_id": f"worker_{uuid4().hex[:8]}",
        "server_url": "http://localhost:8000",
        "poll_interval_sec": 5,
        "max_retries": 3,
        "timeout_sec": 30,
        "agent_capabilities": ["researcher", "analyst", "coder"],
        "log_level": "INFO"
    }
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"✅ Created default configuration: {config_path}")
    print("📝 Please edit the configuration file to match your setup")


async def main():
    """Main entry point for the worker client."""
    parser = argparse.ArgumentParser(description="MCP Worker Client")
    parser.add_argument(
        "--config",
        default="mcp_client_config.json",
        help="Path to client configuration file"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default configuration file and exit"
    )
    parser.add_argument(
        "--submit-task",
        help="Submit a task and exit (for testing)"
    )
    parser.add_argument(
        "--client-id",
        help="Override client ID from config"
    )
    parser.add_argument(
        "--capabilities",
        nargs="+",
        help="Override agent capabilities (space-separated list)"
    )
    
    args = parser.parse_args()
    
    # Create default config if requested
    if args.create_config:
        create_default_config(args.config)
        return
    
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"❌ Configuration file not found: {args.config}")
        print(f"💡 Run with --create-config to create a default configuration")
        return
    
    # Load configuration
    try:
        config = load_config(args.config)
        
        # Apply environment variable overrides
        worker_id = os.getenv('WORKER_ID')
        worker_role = os.getenv('WORKER_ROLE')
        
        if worker_id:
            config.client_id = worker_id
        if worker_role:
            config.agent_capabilities = [worker_role]
        
        # Apply command line overrides (highest priority)
        if args.client_id:
            config.client_id = args.client_id
        if args.capabilities:
            config.agent_capabilities = args.capabilities
            
    except Exception as e:
        print(f"❌ Failed to load configuration: {str(e)}")
        return
    
    # Create and start client
    client = MCPWorkerClient(config)
    
    try:
        if args.submit_task:
            # Submit a task and exit
            workflow_id = await client.submit_task(args.submit_task)
            if workflow_id:
                print(f"✅ Task submitted successfully: {workflow_id}")
            else:
                print("❌ Task submission failed")
        else:
            # Start polling loop
            await client.start()
            
    except KeyboardInterrupt:
        print("\n⏹️ Shutting down...")
    except Exception as e:
        print(f"❌ Client error: {str(e)}")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
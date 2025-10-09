#!/usr/bin/env python3
"""
Command-line interface for AM (AgentManager) MCP Server.

Provides convenient commands for server management, database operations,
and client coordination tasks.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click
import uvicorn
from rich.console import Console
from rich.table import Table

# Add the agent_manager package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="agent-manager")
def cli():
    """AM (AgentManager) MCP Server CLI."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--log-level", default="info", help="Log level")
def start_server(host: str, port: int, reload: bool, log_level: str):
    """Start the MCP server."""
    console.print(f"🚀 Starting AM MCP Server on {host}:{port}", style="green")
    
    uvicorn.run(
        "agent_manager.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )


@cli.command()
@click.option("--url", help="Database URL (default from .env)")
def init_db(url: Optional[str]):
    """Initialize the database with tables."""
    async def _init_db():
        if url:
            os.environ["DATABASE_URL"] = url
        
        from agent_manager.db import create_database_tables, check_database_connection
        
        console.print("🔧 Initializing database...", style="blue")
        
        if await check_database_connection():
            console.print("✅ Database connection successful", style="green")
            await create_database_tables()
            console.print("✅ Database tables created", style="green")
        else:
            console.print("❌ Database connection failed", style="red")
            sys.exit(1)
    
    asyncio.run(_init_db())


@cli.command()
@click.option("--client-id", help="Client ID for the worker")
@click.option("--capabilities", multiple=True, help="Agent capabilities")
@click.option("--server-url", default="http://localhost:8000", help="Server URL")
def start_worker(client_id: Optional[str], capabilities: tuple, server_url: str):
    """Start a worker client."""
    import tempfile
    import json
    from uuid import uuid4
    
    # Create temporary config
    if not client_id:
        client_id = f"cli_worker_{uuid4().hex[:8]}"
    
    if not capabilities:
        capabilities = ["researcher", "analyst", "coder"]
    
    config = {
        "client_id": client_id,
        "server_url": server_url,
        "agent_capabilities": list(capabilities),
        "poll_interval_sec": 5,
        "log_level": "INFO"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name
    
    console.print(f"🤖 Starting worker client {client_id}", style="green")
    console.print(f"🎯 Capabilities: {list(capabilities)}", style="blue")
    
    try:
        os.system(f"python client_worker.py --config {config_path}")
    finally:
        os.unlink(config_path)


@cli.command()
@click.argument("task")
@click.option("--server-url", default="http://localhost:8000", help="Server URL")
def submit_task(task: str, server_url: str):
    """Submit a task to the server."""
    import httpx
    import json
    
    async def _submit():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{server_url}/v1/submit_task",
                    json={"user_request": task, "metadata": {}},
                    timeout=30
                )
                
                if response.status_code == 201:
                    result = response.json()
                    workflow_id = result.get("workflow_id")
                    console.print(f"✅ Task submitted: {workflow_id}", style="green")
                    console.print(f"📋 Total tasks: {result.get('total_tasks', 0)}", style="blue")
                else:
                    console.print(f"❌ Task submission failed: {response.status_code}", style="red")
                    console.print(response.text, style="red")
                    
            except Exception as e:
                console.print(f"❌ Error: {str(e)}", style="red")
    
    asyncio.run(_submit())


@cli.command()
@click.argument("workflow_id")
@click.option("--server-url", default="http://localhost:8000", help="Server URL")
def status(workflow_id: str, server_url: str):
    """Get workflow status."""
    import httpx
    
    async def _status():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{server_url}/v1/workflows/{workflow_id}/status",
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    table = Table(title=f"Workflow Status: {workflow_id}")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    
                    table.add_row("Total Tasks", str(data.get("total_tasks", 0)))
                    table.add_row("Completed", str(data.get("completed_tasks", 0)))
                    table.add_row("In Progress", str(data.get("in_progress_tasks", 0)))
                    table.add_row("Pending", str(data.get("pending_tasks", 0)))
                    table.add_row("Complete", "✅" if data.get("is_complete") else "⏳")
                    
                    console.print(table)
                else:
                    console.print(f"❌ Status check failed: {response.status_code}", style="red")
                    
            except Exception as e:
                console.print(f"❌ Error: {str(e)}", style="red")
    
    asyncio.run(_status())


@cli.command()
@click.argument("workflow_id")
@click.option("--server-url", default="http://localhost:8000", help="Server URL")
def result(workflow_id: str, server_url: str):
    """Get workflow final result."""
    import httpx
    
    async def _result():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{server_url}/v1/workflows/{workflow_id}/result",
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result:
                        console.print("📄 Final Result:", style="green bold")
                        console.print(result, style="white")
                    else:
                        console.print("⏳ Workflow not yet complete", style="yellow")
                else:
                    console.print(f"❌ Result retrieval failed: {response.status_code}", style="red")
                    
            except Exception as e:
                console.print(f"❌ Error: {str(e)}", style="red")
    
    asyncio.run(_result())


@cli.command()
def health():
    """Check server health."""
    import httpx
    
    async def _health():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8000/health", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    console.print("✅ Server is healthy", style="green")
                    console.print(f"📊 Status: {data.get('status')}", style="blue")
                    console.print(f"🕐 Timestamp: {data.get('timestamp')}", style="blue")
                else:
                    console.print("❌ Server health check failed", style="red")
                    
            except Exception as e:
                console.print(f"❌ Cannot reach server: {str(e)}", style="red")
    
    asyncio.run(_health())


@cli.command()
def create_config():
    """Create default configuration files."""
    import shutil
    
    console.print("🔧 Creating default configuration files...", style="blue")
    
    # Copy .env template if .env doesn't exist
    if not os.path.exists(".env") and os.path.exists(".env.template"):
        shutil.copy(".env.template", ".env")
        console.print("✅ Created .env from template", style="green")
    
    # Create client config if it doesn't exist
    if not os.path.exists("mcp_client_config.json"):
        os.system("python client_worker.py --create-config")
        console.print("✅ Created mcp_client_config.json", style="green")
    
    console.print("📝 Please edit configuration files for your setup", style="yellow")


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
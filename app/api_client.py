"""
API Client for AgentManager Dashboard
"""
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

# Windows-specific subprocess flag to hide console windows
if sys.platform == 'win32':
    import subprocess
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0


class AgentManagerClient:
    """Client for interacting with AgentManager API"""
    
    def __init__(self, server_url: str, auth_token: str):
        self.server_url = server_url.rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        self._session = requests.Session()
        self._session.headers.update(self.headers)
    
    def check_health(self) -> Dict[str, Any]:
        """Check server health status"""
        try:
            response = self._session.get(
                f"{self.server_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'details': response.json() if response.text else {}
                }
            else:
                return {
                    'status': 'unhealthy',
                    'timestamp': datetime.now().isoformat(),
                    'error': f"Status code: {response.status_code}"
                }
        except Exception as e:
            return {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_docker_workers(self) -> List[Dict[str, Any]]:
        """Get worker status from Docker containers"""
        try:
            # Get ALL agentmanager containers (workers, server, database, cache)
            result = subprocess.run(
                ['docker', 'ps', '--filter', 'name=agentmanager-', '--format', 
                 '{{.Names}}\t{{.Status}}\t{{.State}}'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            workers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        full_name = parts[0]
                        status = parts[1]
                        state = parts[2]
                        
                        # Parse different container types:
                        # agentmanager-worker-analyst-1-1 -> analyst-1
                        # agentmanager-agent-manager-1 -> agent-manager
                        # agentmanager-postgres-1 -> postgres
                        # agentmanager-redis-1 -> redis
                        
                        name = full_name.replace('agentmanager-', '', 1)
                        
                        # Remove the trailing -1 (docker compose replica suffix)
                        if name.endswith('-1'):
                            name = name[:-2]
                        
                        # For worker containers, remove the "worker-" prefix
                        if name.startswith('worker-'):
                            name = name.replace('worker-', '', 1)
                        
                        # Extract role
                        if name in ['agent-manager', 'postgres', 'redis']:
                            role = {'agent-manager': 'server', 'postgres': 'database', 'redis': 'cache'}[name]
                        else:
                            # Extract role (e.g., "analyst" from "analyst-1")
                            role = name.rsplit('-', 1)[0] if '-' in name else name
                        
                        workers.append({
                            'name': name,
                            'role': role,
                            'status': state,
                            'health': 'healthy' if 'healthy' in status.lower() else 'unhealthy',
                            'uptime': self._extract_uptime(status),
                            'last_update': datetime.now().isoformat()
                        })
            
            return workers
        except Exception as e:
            logger.error(f"Error getting docker workers: {e}")
            return []
    
    def _extract_uptime(self, status: str) -> str:
        """Extract uptime from Docker status string"""
        if 'Up' in status:
            parts = status.split('Up')
            if len(parts) > 1:
                return parts[1].split('(')[0].strip()
        return 'Unknown'
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of all projects with workflow counts and status"""
        try:
            # Query projects with aggregated workflow statistics
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-postgres-1', 
                 'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c',
                 """SELECT 
                        p.project_id,
                        p.project_name,
                        p.project_path,
                        p.created_at,
                        COUNT(tg.id) as workflow_count,
                        COUNT(tg.id) FILTER (WHERE tg.status = 'COMPLETED') as completed,
                        COUNT(tg.id) FILTER (WHERE tg.status = 'IN_PROGRESS') as in_progress,
                        COUNT(tg.id) FILTER (WHERE tg.status = 'FAILED') as failed,
                        CASE 
                            WHEN COUNT(tg.id) FILTER (WHERE tg.status = 'FAILED') > 0 THEN 'FAILED'
                            WHEN COUNT(tg.id) FILTER (WHERE tg.status = 'IN_PROGRESS') > 0 THEN 'IN_PROGRESS'
                            WHEN COUNT(tg.id) = COUNT(tg.id) FILTER (WHERE tg.status = 'COMPLETED') THEN 'COMPLETED'
                            ELSE 'PENDING'
                        END as overall_status,
                        ROUND(100.0 * COUNT(tg.id) FILTER (WHERE tg.status = 'COMPLETED') / NULLIF(COUNT(tg.id), 0), 1) as progress_pct
                    FROM projects p
                    LEFT JOIN task_graphs tg ON tg.project_id = p.id
                    GROUP BY p.id, p.project_id, p.project_name, p.project_path, p.created_at
                    ORDER BY p.created_at DESC
                    LIMIT 50;"""],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            projects = []
            for line in result.stdout.strip().split('\n'):
                if line.strip() and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 10:
                        # Convert created_at to PST format
                        created_at = parts[3]
                        if created_at:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                from timezone_utils import format_pst_timestamp
                                created_at_pst = format_pst_timestamp(dt)
                            except:
                                created_at_pst = created_at
                        else:
                            created_at_pst = 'N/A'
                        
                        workflow_count = int(parts[4]) if parts[4] else 0
                        completed = int(parts[5]) if parts[5] else 0
                        in_progress = int(parts[6]) if parts[6] else 0
                        failed = int(parts[7]) if parts[7] else 0
                        progress_pct = float(parts[9]) if parts[9] else 0.0
                        
                        projects.append({
                            'project_id': parts[0],
                            'project_name': parts[1],
                            'project_path': parts[2],
                            'created_at': created_at_pst,
                            'workflow_count': workflow_count,
                            'completed_workflows': completed,
                            'in_progress_workflows': in_progress,
                            'failed_workflows': failed,
                            'overall_status': parts[8],
                            'progress_percentage': progress_pct
                        })
            
            return projects
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []
    
    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get list of all workflows (including completed) in descending order"""
        try:
            # Query database for all workflows - get id separately
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-postgres-1', 
                 'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c',
                 """SELECT tg.id, tg.workflow_id, tg.workflow_name, tg.user_request, tg.status, tg.created_at, p.project_id 
                    FROM task_graphs tg
                    LEFT JOIN projects p ON tg.project_id = p.id
                    ORDER BY tg.created_at DESC 
                    LIMIT 50;"""],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            workflows = []
            for line in result.stdout.strip().split('\n'):
                if line.strip() and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 6:
                        workflows.append({
                            'id': parts[1],  # Sequential workflow ID (WID00000001)
                            'workflow_id': parts[1],  # Generated workflow ID
                            'workflow_name': parts[2],  # Actual workflow name from database
                            'description': parts[3],  # Full description without truncation
                            'status': parts[4],
                            'created_at': parts[5],
                            'project_id': parts[6] if len(parts) > 6 else 'N/A'  # Project ID
                        })
            
            return workflows
        except Exception as e:
            logger.error(f"Error getting active workflows: {e}")
            return []
    
    def get_workflow_progress(self, workflow_id: str) -> Dict[str, Any]:
        """Get progress for a specific workflow"""
        try:
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-postgres-1',
                 'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c',
                 f"""SELECT status, COUNT(*) 
                     FROM task_steps 
                     WHERE workflow_id='{workflow_id}' 
                     GROUP BY status;"""],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            stats = {
                'READY': 0,
                'IN_PROGRESS': 0,
                'COMPLETED': 0,
                'FAILED': 0
            }
            
            for line in result.stdout.strip().split('\n'):
                if line.strip() and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 2:
                        status = parts[0]
                        count = int(parts[1])
                        stats[status] = count
            
            total = sum(stats.values())
            completed = stats['COMPLETED']
            
            return {
                'total_tasks': total,
                'completed': completed,
                'in_progress': stats['IN_PROGRESS'],
                'pending': stats['READY'],
                'failed': stats['FAILED'],
                'progress_percent': (completed / total * 100) if total > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting workflow progress: {e}")
            return {'total_tasks': 0, 'completed': 0, 'progress_percent': 0}
    
    def get_all_workflow_progress(self) -> Dict[str, Dict[str, Any]]:
        """Get progress for all workflows in a single query (much faster than individual queries)"""
        try:
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-postgres-1',
                 'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c',
                 """SELECT workflow_id, status, COUNT(*) 
                     FROM task_steps 
                     GROUP BY workflow_id, status;"""],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=SUBPROCESS_FLAGS
            )
            
            # Build progress dict: {workflow_id: {status: count}}
            workflow_progress = {}
            
            for line in result.stdout.strip().split('\n'):
                if line.strip() and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        workflow_id = parts[0]
                        status = parts[1]
                        count = int(parts[2])
                        
                        if workflow_id not in workflow_progress:
                            workflow_progress[workflow_id] = {
                                'READY': 0,
                                'IN_PROGRESS': 0,
                                'COMPLETED': 0,
                                'FAILED': 0,
                                'PENDING': 0
                            }
                        
                        workflow_progress[workflow_id][status] = count
            
            # Calculate totals and percentages
            for workflow_id, stats in workflow_progress.items():
                total = sum(stats.values())
                completed = stats['COMPLETED']
                stats['total_tasks'] = total
                stats['completed'] = completed
                stats['in_progress'] = stats['IN_PROGRESS']
                stats['pending'] = stats['READY']
                stats['failed'] = stats['FAILED']
                stats['progress_percent'] = (completed / total * 100) if total > 0 else 0
            
            return workflow_progress
            
        except Exception as e:
            logger.error(f"Error getting all workflow progress: {e}")
            return {}
    
    def get_recent_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent tasks with their status"""
        try:
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-postgres-1',
                 'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c',
                 f"""SELECT id, step_id, workflow_id, assigned_agent, status, 
                            task_description,
                            updated_at
                     FROM task_steps 
                     ORDER BY updated_at DESC 
                     LIMIT {limit};"""],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=SUBPROCESS_FLAGS
            )
            
            tasks = []
            for line in result.stdout.strip().split('\n'):
                if line.strip() and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 7:
                        tasks.append({
                            'task_id': parts[1],  # Sequential step_id (TID0000000001)
                            'task_name': parts[1],  # step_id (readable name)
                            'workflow_id': parts[2],
                            'agent': parts[3],
                            'status': parts[4],
                            'description': parts[5],
                            'updated_at': parts[6]
                        })
            
            return tasks
        except Exception as e:
            logger.error(f"Error getting recent tasks: {e}")
            return []
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        try:
            # Get task counts
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-postgres-1',
                 'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c',
                 """SELECT status, COUNT(*) 
                    FROM task_steps 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY status;"""],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            task_stats = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip() and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 2:
                        task_stats[parts[0]] = int(parts[1])
            
            # Get workflow counts
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-postgres-1',
                 'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c',
                 """SELECT COUNT(*) 
                    FROM task_graphs 
                    WHERE created_at > NOW() - INTERVAL '24 hours';"""],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            workflow_count = int(result.stdout.strip()) if result.stdout.strip() else 0
            
            return {
                'tasks_24h': sum(task_stats.values()),
                'tasks_completed_24h': task_stats.get('COMPLETED', 0),
                'tasks_failed_24h': task_stats.get('FAILED', 0),
                'workflows_24h': workflow_count,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
    
    def get_database_status(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-postgres-1',
                 'psql', '-U', 'postgres', '-d', 'agent_manager', '-t', '-c',
                 'SELECT 1;'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            if result.returncode == 0:
                return {
                    'status': 'connected',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'error': result.stderr,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_redis_status(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            result = subprocess.run(
                ['docker', 'exec', 'agentmanager-redis-1',
                 'redis-cli', 'PING'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            if result.returncode == 0 and 'PONG' in result.stdout:
                return {
                    'status': 'connected',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'error': 'No PONG response',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get worker status with current task assignments from API"""
        try:
            response = requests.get(
                f"{self.server_url}/v1/workers/status",
                headers=self.headers,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting worker status: {e}")
            return {
                'worker_tasks': {},
                'total_active': 0,
                'error': str(e)
            }

"""
Prometheus Monitoring for AgentManager

Comprehensive metrics collection for workflows, tasks, agents, and system performance.
"""
from prometheus_client import Counter, Gauge, Histogram, Summary, Info
from prometheus_client import generate_latest, REGISTRY
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Workflow Metrics
# ============================================================================

workflow_requests_total = Counter(
    'agentmanager_workflow_requests_total',
    'Total number of workflow requests received',
    ['status']
)

workflow_tasks_total = Counter(
    'agentmanager_workflow_tasks_total',
    'Total number of tasks created across all workflows',
    ['workflow_id', 'assigned_agent']
)

workflow_duration_seconds = Histogram(
    'agentmanager_workflow_duration_seconds',
    'Time taken to complete workflows',
    ['workflow_id', 'status'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

active_workflows = Gauge(
    'agentmanager_active_workflows',
    'Number of currently active workflows'
)

# ============================================================================
# Task Metrics
# ============================================================================

task_status_total = Counter(
    'agentmanager_task_status_total',
    'Total task status transitions',
    ['from_status', 'to_status', 'assigned_agent']
)

task_execution_duration_seconds = Histogram(
    'agentmanager_task_execution_duration_seconds',
    'Time taken to execute tasks',
    ['assigned_agent', 'status'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)

task_queue_depth = Gauge(
    'agentmanager_task_queue_depth',
    'Number of tasks waiting in ready state',
    ['assigned_agent']
)

task_retry_total = Counter(
    'agentmanager_task_retry_total',
    'Total number of task retries',
    ['assigned_agent', 'reason']
)

# ============================================================================
# Agent/Worker Metrics
# ============================================================================

worker_poll_requests_total = Counter(
    'agentmanager_worker_poll_requests_total',
    'Total number of worker poll requests',
    ['worker_role', 'result']
)

worker_active = Gauge(
    'agentmanager_worker_active',
    'Number of active workers by role',
    ['worker_role']
)

worker_task_processing_seconds = Summary(
    'agentmanager_worker_task_processing_seconds',
    'Time spent processing tasks by workers',
    ['worker_role']
)

# ============================================================================
# LLM API Metrics
# ============================================================================

llm_requests_total = Counter(
    'agentmanager_llm_requests_total',
    'Total number of LLM API requests',
    ['model', 'status']
)

llm_tokens_total = Counter(
    'agentmanager_llm_tokens_total',
    'Total number of tokens used',
    ['model', 'type']  # type: prompt, completion
)

llm_request_duration_seconds = Histogram(
    'agentmanager_llm_request_duration_seconds',
    'Time taken for LLM API requests',
    ['model'],
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60]
)

llm_cost_usd = Counter(
    'agentmanager_llm_cost_usd',
    'Estimated cost of LLM API usage in USD',
    ['model']
)

# ============================================================================
# Database Metrics
# ============================================================================

db_query_duration_seconds = Histogram(
    'agentmanager_db_query_duration_seconds',
    'Time taken for database queries',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
)

db_connections_active = Gauge(
    'agentmanager_db_connections_active',
    'Number of active database connections'
)

db_operations_total = Counter(
    'agentmanager_db_operations_total',
    'Total number of database operations',
    ['operation', 'table', 'status']
)

# ============================================================================
# Cache Metrics (Redis)
# ============================================================================

cache_operations_total = Counter(
    'agentmanager_cache_operations_total',
    'Total number of cache operations',
    ['operation', 'status']  # operation: get, set, delete
)

cache_hit_ratio = Gauge(
    'agentmanager_cache_hit_ratio',
    'Cache hit ratio (0-1)'
)

cache_keys_total = Gauge(
    'agentmanager_cache_keys_total',
    'Total number of keys in cache',
    ['key_type']  # task, workflow, result
)

# ============================================================================
# Audit Metrics
# ============================================================================

audit_reports_total = Counter(
    'agentmanager_audit_reports_total',
    'Total number of audit reports generated',
    ['is_successful']
)

audit_rework_cycles_total = Counter(
    'agentmanager_audit_rework_cycles_total',
    'Total number of rework cycles triggered',
    ['workflow_id']
)

audit_confidence_score = Histogram(
    'agentmanager_audit_confidence_score',
    'Confidence scores from audit reports',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# ============================================================================
# System Metrics
# ============================================================================

api_request_duration_seconds = Histogram(
    'agentmanager_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5]
)

api_requests_total = Counter(
    'agentmanager_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

system_errors_total = Counter(
    'agentmanager_system_errors_total',
    'Total number of system errors',
    ['component', 'error_type']
)

# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    'agentmanager_app',
    'AgentManager application information'
)

# Set application info
app_info.info({
    'version': '1.2.0',
    'name': 'AgentManager',
    'description': 'Multi-Agent Coordination Server'
})

# ============================================================================
# Decorators for automatic metric collection
# ============================================================================

def track_workflow_duration(func):
    """Decorator to track workflow execution duration"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status = 'success'
        workflow_id = 'unknown'
        
        try:
            result = await func(*args, **kwargs)
            if hasattr(result, 'workflow_id'):
                workflow_id = result.workflow_id
            return result
        except Exception as e:
            status = 'error'
            logger.error(f"Workflow execution failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            workflow_duration_seconds.labels(
                workflow_id=workflow_id,
                status=status
            ).observe(duration)
    
    return wrapper

def track_task_execution(func):
    """Decorator to track task execution duration"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status = 'completed'
        assigned_agent = 'unknown'
        
        try:
            result = await func(*args, **kwargs)
            if hasattr(result, 'source_agent'):
                assigned_agent = result.source_agent
            return result
        except Exception as e:
            status = 'failed'
            logger.error(f"Task execution failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            task_execution_duration_seconds.labels(
                assigned_agent=assigned_agent,
                status=status
            ).observe(duration)
    
    return wrapper

def track_llm_request(func):
    """Decorator to track LLM API requests"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        model = kwargs.get('model', 'unknown')
        status = 'success'
        
        try:
            result = await func(*args, **kwargs)
            
            # Track token usage if available
            if hasattr(result, 'usage'):
                llm_tokens_total.labels(model=model, type='prompt').inc(
                    result.usage.prompt_tokens
                )
                llm_tokens_total.labels(model=model, type='completion').inc(
                    result.usage.completion_tokens
                )
            
            llm_requests_total.labels(model=model, status=status).inc()
            return result
        except Exception as e:
            status = 'error'
            llm_requests_total.labels(model=model, status=status).inc()
            logger.error(f"LLM request failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            llm_request_duration_seconds.labels(model=model).observe(duration)
    
    return wrapper

def track_db_operation(operation: str, table: str):
    """Decorator to track database operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                db_operations_total.labels(
                    operation=operation,
                    table=table,
                    status=status
                ).inc()
                return result
            except Exception as e:
                status = 'error'
                db_operations_total.labels(
                    operation=operation,
                    table=table,
                    status=status
                ).inc()
                logger.error(f"Database operation failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                db_query_duration_seconds.labels(
                    operation=operation,
                    table=table
                ).observe(duration)
        
        return wrapper
    return decorator

def track_api_request(func):
    """Decorator to track API request duration and count"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        method = kwargs.get('method', 'unknown')
        endpoint = kwargs.get('endpoint', 'unknown')
        status_code = 200
        
        try:
            result = await func(*args, **kwargs)
            if hasattr(result, 'status_code'):
                status_code = result.status_code
            return result
        except Exception as e:
            status_code = 500
            logger.error(f"API request failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            api_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).observe(duration)
            api_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
    
    return wrapper

# ============================================================================
# Helper Functions
# ============================================================================

def update_active_workflows(count: int):
    """Update the gauge for active workflows"""
    active_workflows.set(count)

def update_task_queue_depth(agent_role: str, count: int):
    """Update task queue depth for specific agent role"""
    task_queue_depth.labels(assigned_agent=agent_role).set(count)

def update_worker_active(role: str, count: int):
    """Update active worker count for specific role"""
    worker_active.labels(worker_role=role).set(count)

def update_cache_hit_ratio(hits: int, total: int):
    """Update cache hit ratio"""
    if total > 0:
        ratio = hits / total
        cache_hit_ratio.set(ratio)

def update_db_connections(count: int):
    """Update active database connection count"""
    db_connections_active.set(count)

def record_workflow_request(status: str):
    """Record a workflow request"""
    workflow_requests_total.labels(status=status).inc()

def record_task_status_change(from_status: str, to_status: str, agent: str):
    """Record a task status transition"""
    task_status_total.labels(
        from_status=from_status,
        to_status=to_status,
        assigned_agent=agent
    ).inc()

def record_audit_report(is_successful: bool, confidence: float):
    """Record an audit report"""
    audit_reports_total.labels(is_successful=str(is_successful).lower()).inc()
    audit_confidence_score.observe(confidence)

def record_system_error(component: str, error_type: str):
    """Record a system error"""
    system_errors_total.labels(
        component=component,
        error_type=error_type
    ).inc()

def get_metrics():
    """Get current metrics in Prometheus format"""
    return generate_latest(REGISTRY)

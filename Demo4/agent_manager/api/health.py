"""
Health Check and Monitoring Endpoints

Provides comprehensive health checks and Prometheus metrics endpoint.
"""
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text
from datetime import datetime
import psutil
import logging

from agent_manager.db import get_database_session
from agent_manager.monitoring import get_metrics, update_db_connections
from agent_manager.exceptions import DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["monitoring"])

# ============================================================================
# Health Check Endpoints
# ============================================================================

@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "agentmanager"
    }

@router.get("/liveness", status_code=status.HTTP_200_OK)
async def liveness():
    """
    Kubernetes liveness probe endpoint
    
    Returns:
        dict: Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/readiness")
async def readiness():
    """
    Kubernetes readiness probe endpoint
    
    Checks:
    - Database connectivity
    - Redis connectivity (if configured)
    
    Returns:
        JSONResponse: Readiness status with details
    """
    checks = {
        "database": False,
        "redis": False,
        "overall": False
    }
    
    # Check database
    try:
        async with get_database_session() as db:
            await db.execute(text("SELECT 1"))
            checks["database"] = True
            logger.debug("Database health check: OK")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = False
    
    # Check Redis (optional - graceful degradation)
    try:
        # Import here to avoid circular dependency
        from agent_manager.core.redis_client import RedisClient
        redis_client = RedisClient()
        if redis_client:
            await redis_client.ping()
            checks["redis"] = True
            logger.debug("Redis health check: OK")
        else:
            checks["redis"] = True  # Optional component
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        checks["redis"] = True  # Graceful degradation - not critical
    
    # Overall status
    checks["overall"] = checks["database"]  # Database is critical
    
    status_code = status.HTTP_200_OK if checks["overall"] else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if checks["overall"] else "not_ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@router.get("/detailed")
async def detailed_health():
    """
    Detailed health check with system metrics
    
    Returns:
        dict: Comprehensive health information
    """
    health_info = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "agentmanager",
        "version": "1.2.0",
        "components": {},
        "system": {}
    }
    
    # Database check
    try:
        async with get_database_session() as db:
            result = await db.execute(text("SELECT COUNT(*) FROM task_graphs"))
            workflow_count = result.scalar()
            
            result = await db.execute(text("SELECT COUNT(*) FROM task_steps"))
            task_count = result.scalar()
            
            health_info["components"]["database"] = {
                "status": "healthy",
                "workflows": workflow_count,
                "tasks": task_count
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_info["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_info["status"] = "degraded"
    
    # Redis check
    try:
        from agent_manager.core.redis_client import RedisClient
        redis_client = RedisClient()
        if redis_client:
            await redis_client.ping()
            info = await redis_client.info()
            health_info["components"]["redis"] = {
                "status": "healthy",
                "keys": info.get("db0", {}).get("keys", 0),
                "memory_used": info.get("used_memory_human", "N/A")
            }
        else:
            health_info["components"]["redis"] = {
                "status": "not_configured"
            }
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_info["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # System metrics
    try:
        health_info["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids())
        }
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        health_info["system"] = {"error": str(e)}
    
    return health_info

# ============================================================================
# Metrics Endpoint
# ============================================================================

@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint
    
    Returns:
        PlainTextResponse: Metrics in Prometheus format
    """
    try:
        # Update database connection gauge
        try:
            async with get_database_session() as db:
                result = await db.execute(text(
                    "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'agent_manager'"
                ))
                connection_count = result.scalar()
                update_db_connections(connection_count)
        except Exception as e:
            logger.warning(f"Failed to update DB connection metric: {e}")
        
        # Generate and return metrics
        metrics_data = get_metrics()
        return PlainTextResponse(content=metrics_data.decode('utf-8'))
    
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return PlainTextResponse(
            content=f"# Error generating metrics: {str(e)}\n",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ============================================================================
# Status Dashboard Endpoint
# ============================================================================

@router.get("/dashboard")
async def monitoring_dashboard():
    """
    Human-readable monitoring dashboard
    
    Returns:
        dict: Dashboard data with metrics and health status
    """
    dashboard = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AgentManager v1.2.0",
        "health": {},
        "workflows": {},
        "tasks": {},
        "workers": {},
        "system": {}
    }
    
    # Health status
    try:
        async with get_database_session() as db:
            # Workflows by status
            result = await db.execute(text("""
                SELECT status, COUNT(*) as count
                FROM task_graphs
                GROUP BY status
            """))
            workflow_stats = {row.status: row.count for row in result}
            
            # Tasks by status
            result = await db.execute(text("""
                SELECT status, COUNT(*) as count
                FROM task_steps
                GROUP BY status
            """))
            task_stats = {row.status: row.count for row in result}
            
            # Tasks by agent
            result = await db.execute(text("""
                SELECT assigned_agent, status, COUNT(*) as count
                FROM task_steps
                GROUP BY assigned_agent, status
            """))
            agent_stats = {}
            for row in result:
                if row.assigned_agent not in agent_stats:
                    agent_stats[row.assigned_agent] = {}
                agent_stats[row.assigned_agent][row.status] = row.count
            
            dashboard["health"]["database"] = "connected"
            dashboard["workflows"] = {
                "total": sum(workflow_stats.values()),
                "by_status": workflow_stats
            }
            dashboard["tasks"] = {
                "total": sum(task_stats.values()),
                "by_status": task_stats
            }
            dashboard["workers"] = agent_stats
            
    except Exception as e:
        logger.error(f"Dashboard data collection failed: {e}")
        dashboard["health"]["database"] = f"error: {str(e)}"
    
    # System metrics
    try:
        dashboard["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "uptime_seconds": psutil.boot_time()
        }
    except Exception as e:
        logger.error(f"System metrics failed: {e}")
    
    return dashboard

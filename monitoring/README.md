# AgentManager Monitoring

Comprehensive monitoring solution using Prometheus for metrics collection and Grafana for visualization.

## Overview

The monitoring stack provides:

- **Prometheus**: Time-series metrics collection and storage
- **Grafana**: Real-time dashboards and visualization
- **Node Exporter**: System-level metrics (CPU, memory, disk)
- **Postgres Exporter**: Database performance metrics
- **Redis Exporter**: Cache performance metrics
- **Custom Metrics**: Application-specific metrics from AgentManager

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start monitoring containers
docker-compose -f docker-compose.monitoring.yml up -d

# Verify all containers are running
docker ps | grep agentmanager
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
  - Pre-configured dashboard: "AgentManager Overview"

- **Prometheus**: http://localhost:9090
  - Query interface for raw metrics
  - Targets status: http://localhost:9090/targets

### 3. Health Endpoints

AgentManager exposes several monitoring endpoints:

```bash
# Basic health check
curl http://localhost:8001/health

# Detailed health with system metrics
curl http://localhost:8001/health/detailed

# Kubernetes readiness probe
curl http://localhost:8001/health/readiness

# Prometheus metrics
curl http://localhost:8001/health/metrics

# Monitoring dashboard (JSON)
curl http://localhost:8001/health/dashboard
```

## Metrics Categories

### 1. Workflow Metrics

- `agentmanager_workflow_requests_total`: Total workflow submissions
- `agentmanager_workflow_tasks_total`: Tasks created per workflow
- `agentmanager_workflow_duration_seconds`: Workflow completion time
- `agentmanager_active_workflows`: Currently executing workflows

### 2. Task Metrics

- `agentmanager_task_status_total`: Task status transitions
- `agentmanager_task_execution_duration_seconds`: Task execution time
- `agentmanager_task_queue_depth`: Tasks waiting by agent type
- `agentmanager_task_retry_total`: Task retry count

### 3. Worker Metrics

- `agentmanager_worker_poll_requests_total`: Worker polling activity
- `agentmanager_worker_active`: Active workers by role
- `agentmanager_worker_task_processing_seconds`: Worker processing time

### 4. LLM API Metrics

- `agentmanager_llm_requests_total`: LLM API call count
- `agentmanager_llm_tokens_total`: Token usage (prompt/completion)
- `agentmanager_llm_request_duration_seconds`: LLM API latency
- `agentmanager_llm_cost_usd`: Estimated API costs

### 5. Database Metrics

- `agentmanager_db_query_duration_seconds`: Query execution time
- `agentmanager_db_connections_active`: Active database connections
- `agentmanager_db_operations_total`: Database operation count

### 6. Cache Metrics (Redis)

- `agentmanager_cache_operations_total`: Cache operations
- `agentmanager_cache_hit_ratio`: Cache hit rate (0-1)
- `agentmanager_cache_keys_total`: Total cached keys

### 7. Audit Metrics

- `agentmanager_audit_reports_total`: Audit report count
- `agentmanager_audit_rework_cycles_total`: Rework cycles triggered
- `agentmanager_audit_confidence_score`: Audit confidence distribution

### 8. API Metrics

- `agentmanager_api_request_duration_seconds`: API response time
- `agentmanager_api_requests_total`: API request count
- `agentmanager_system_errors_total`: Error count by type

## Grafana Dashboard

The pre-configured "AgentManager Overview" dashboard includes:

### Row 1: Workflow Overview
- Workflow request rate over time
- Active workflow count
- Task queue depth by agent type

### Row 2: Performance
- API request duration (p95)
- LLM request rate
- LLM token usage

### Row 3: Database & Errors
- Database query duration (p95)
- Error rate by component
- Worker activity levels

### Row 4: System Health
- Cache hit ratio
- Audit success rate
- System CPU/memory usage
- Database connection count

## Custom Queries

### Example Prometheus Queries

```promql
# Average workflow duration
avg(agentmanager_workflow_duration_seconds)

# Task completion rate
rate(agentmanager_task_status_total{to_status="COMPLETED"}[5m])

# Error rate percentage
100 * (rate(agentmanager_system_errors_total[5m]) / rate(agentmanager_api_requests_total[5m]))

# Top 5 slowest endpoints (p95)
topk(5, histogram_quantile(0.95, rate(agentmanager_api_request_duration_seconds_bucket[5m])))

# LLM cost per hour
rate(agentmanager_llm_cost_usd[1h]) * 3600

# Cache efficiency
agentmanager_cache_hit_ratio > 0.8
```

## Alerting (Optional)

Create alert rules in `monitoring/prometheus/alerts/`:

```yaml
# Example: High error rate alert
groups:
  - name: agentmanager
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(agentmanager_system_errors_total[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"
```

## Troubleshooting

### Metrics Not Showing

1. Verify AgentManager is exposing metrics:
   ```bash
   curl http://localhost:8001/health/metrics
   ```

2. Check Prometheus targets:
   - Visit http://localhost:9090/targets
   - Ensure `agentmanager-api` target is UP

3. Check Prometheus logs:
   ```bash
   docker logs agentmanager-prometheus
   ```

### Grafana Dashboard Issues

1. Verify datasource connection:
   - Settings → Data Sources → Prometheus
   - Click "Test" button

2. Check dashboard queries:
   - Edit panel → Query inspector
   - Verify Prometheus queries return data

### High Resource Usage

Monitor exporters and adjust scrape intervals:

```yaml
# In prometheus.yml
scrape_interval: 30s  # Increase from 15s
```

## Production Recommendations

### 1. Security

- Change default Grafana password
- Enable authentication on Prometheus
- Use TLS for all connections
- Restrict network access with firewall rules

### 2. Retention

Configure Prometheus data retention:

```yaml
# In docker-compose.monitoring.yml
command:
  - '--storage.tsdb.retention.time=30d'
  - '--storage.tsdb.retention.size=50GB'
```

### 3. Performance

- Use remote write for long-term storage
- Enable recording rules for expensive queries
- Scale Prometheus horizontally if needed

### 4. Backup

```bash
# Backup Grafana dashboards
docker exec agentmanager-grafana grafana-cli admin export-dashboard

# Backup Prometheus data
docker run --rm -v prometheus-data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz /data
```

## Integration with CI/CD

### Health Check in Deployment

```yaml
# Example Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health/readiness
    port: 8001
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Metrics-Based Autoscaling

```yaml
# Example HPA based on custom metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agentmanager-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agentmanager
  metrics:
  - type: Pods
    pods:
      metric:
        name: agentmanager_task_queue_depth
      target:
        type: AverageValue
        averageValue: "100"
```

## Support

For issues or questions:
- Check logs: `docker logs agentmanager-prometheus`
- Review Prometheus documentation: https://prometheus.io/docs/
- Review Grafana documentation: https://grafana.com/docs/

## Version

- Monitoring Stack Version: 1.0.0
- AgentManager Version: 1.2.0
- Last Updated: 2025-10-14

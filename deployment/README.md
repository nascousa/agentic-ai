# AgentManager Deployment Documentation

## Overview

This deployment folder contains all the necessary files and scripts to deploy the AgentManager Multi-Agent Coordination/Planning (MCP) Server in production environments.

## Architecture

### Server Components
- **FastAPI Server**: Main coordination server
- **PostgreSQL**: Primary database for workflow persistence
- **Redis**: Caching and session storage
- **Nginx**: Reverse proxy and load balancer

### Worker Components
- **Researcher Worker**: Data gathering and analysis
- **Analyst Worker**: Pattern analysis and insights
- **Writer Worker**: Content generation and documentation
- **Multi-role Worker**: Combined capabilities in one container

## Quick Start

### Windows Deployment

#### Option 1: Batch Script (Recommended for beginners)
```batch
cd deployment
scripts\deploy.bat
```

#### Option 2: PowerShell Script (Recommended for advanced users)
```powershell
cd deployment
.\scripts\deploy.ps1
```

#### Option 3: PowerShell with Parameters
```powershell
# Deploy only server
.\scripts\deploy.ps1 -SkipWorkerDeploy

# Deploy only workers
.\scripts\deploy.ps1 -SkipServerDeploy

# Deploy with multi-role workers
.\scripts\deploy.ps1 -WorkerMode "multi-role"

# Silent deployment (no interactive prompts)
.\scripts\deploy.ps1 -Mode "silent" -WorkerMode "both"
```

### Linux/macOS Deployment

```bash
cd deployment
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

## Manual Deployment

### 1. Environment Setup

Copy the environment template:
```bash
cp .env.template .env
```

Edit `.env` and configure:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `AUTH_TOKEN`: Secure token for worker authentication
- `SECRET_KEY`: Flask secret key

### 2. Server Deployment

```bash
cd server
docker-compose up -d --build
```

### 3. Worker Deployment

```bash
cd worker

# Individual workers
docker-compose up -d --build worker-researcher worker-analyst writer-writer

# Multi-role worker
docker-compose --profile multi-worker up -d --build worker-multi

# All workers
docker-compose --profile multi-worker up -d --build
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | Yes |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://...` | No |
| `REDIS_URL` | Redis connection | `redis://...` | No |
| `AUTH_TOKEN` | Worker auth token | Auto-generated | No |
| `SECRET_KEY` | App secret key | Auto-generated | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `WORKER_POLL_INTERVAL` | Worker polling frequency | `5` | No |

### Worker Configuration

Edit `worker/worker_config.template.json` to customize:
- Worker roles and capabilities
- Polling intervals
- Retry logic
- Resource limits

### Server Configuration

Server settings are configured via environment variables and Docker Compose. Key settings:

- **Database**: PostgreSQL with automatic migrations
- **Caching**: Redis for session and task caching
- **API**: FastAPI with automatic documentation
- **Security**: Bearer token authentication
- **Monitoring**: Health checks and metrics endpoints

## Monitoring and Management

### Health Checks

- **Server Health**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs`
- **Worker Metrics**: 
  - Researcher: `http://localhost:8081`
  - Analyst: `http://localhost:8082`
  - Writer: `http://localhost:8083`
  - Multi-role: `http://localhost:8084`

### Container Management

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# Restart services
docker-compose restart [service-name]

# Update and restart
docker-compose up -d --build [service-name]

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Database Management

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U agentmanager -d agentmanager

# Backup database
docker-compose exec postgres pg_dump -U agentmanager agentmanager > backup.sql

# Restore database
docker-compose exec -T postgres psql -U agentmanager agentmanager < backup.sql
```

## Scaling

### Horizontal Scaling

To scale workers:
```bash
# Scale specific worker type
docker-compose up -d --scale worker-researcher=3

# Scale all workers
docker-compose up -d --scale worker-researcher=2 --scale worker-analyst=2 --scale worker-writer=2
```

### Load Balancing

The Nginx configuration in `server/nginx.conf` provides:
- Load balancing across server instances
- SSL termination (configure certificates)
- Rate limiting
- Request routing

## Security Considerations

### Production Hardening

1. **API Keys**: Store in secure key management system
2. **Database**: Use strong passwords and SSL connections
3. **Network**: Configure firewalls and VPNs
4. **Certificates**: Enable HTTPS with valid SSL certificates
5. **Access Control**: Implement proper authentication and authorization

### Security Checklist

- [ ] Strong passwords for all services
- [ ] SSL/TLS encryption enabled
- [ ] Network access restricted
- [ ] Regular security updates
- [ ] Backup and disaster recovery plan
- [ ] Monitoring and alerting configured

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Check if ports 8000, 5432, 6379 are available
2. **Permission Errors**: Ensure Docker has proper permissions
3. **Memory Issues**: Increase Docker memory limits
4. **Network Issues**: Check firewall and network configuration

### Debugging

```bash
# Check container logs
docker-compose logs [service-name]

# Interactive shell
docker-compose exec [service-name] /bin/bash

# Check resource usage
docker stats

# Check network connectivity
docker-compose exec worker-researcher curl http://server:8000/health
```

### Log Locations

- **Server Logs**: `logs/server/`
- **Worker Logs**: `logs/workers/`
- **Database Logs**: Docker container logs
- **Nginx Logs**: Docker container logs

## Backup and Recovery

### Automated Backups

Add to crontab for regular backups:
```bash
# Daily database backup at 2 AM
0 2 * * * cd /path/to/deployment && docker-compose exec postgres pg_dump -U agentmanager agentmanager > backups/backup-$(date +\%Y\%m\%d).sql
```

### Recovery Procedure

1. Stop all services
2. Restore database from backup
3. Restart services
4. Verify functionality

## Performance Tuning

### Database Optimization

- Configure PostgreSQL connection pooling
- Tune memory settings
- Add appropriate indexes
- Monitor query performance

### Worker Optimization

- Adjust polling intervals
- Configure resource limits
- Optimize task distribution
- Monitor worker utilization

## Production Deployment

### Prerequisites

- Docker and Docker Compose
- Minimum 4GB RAM
- 20GB disk space
- Network access to OpenAI API

### Deployment Steps

1. Prepare environment configuration
2. Deploy infrastructure (database, cache)
3. Deploy server components
4. Deploy and scale workers
5. Configure monitoring and alerting
6. Test functionality
7. Set up backups and maintenance

### Maintenance

- Regular updates and security patches
- Database maintenance and optimization
- Log rotation and cleanup
- Performance monitoring and tuning
- Backup verification and testing

## Support

For issues and questions:
- Check troubleshooting section
- Review container logs
- Consult API documentation at `/docs`
- Create GitHub issues for bugs and feature requests
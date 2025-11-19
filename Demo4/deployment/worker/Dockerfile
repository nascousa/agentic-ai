# =============================================================================
# AgentManager Worker Client - Production Dockerfile
# =============================================================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY deployment/worker/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agent_manager/ ./agent_manager/
COPY client_worker.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash worker
RUN chown -R worker:worker /app
USER worker

# Create directories for logs and config
RUN mkdir -p /app/logs /app/config

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Default command - can be overridden with docker run
CMD ["python", "client_worker.py", "--config", "/app/config/worker_config.json"]
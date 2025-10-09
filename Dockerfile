# Docker configuration for AM (AgentManager) MCP Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and application code
COPY pyproject.toml ./
COPY README.md ./
COPY agent_manager/ ./agent_manager/
COPY client_worker.py ./
COPY logging_config.yaml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the server
CMD ["uvicorn", "agent_manager.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
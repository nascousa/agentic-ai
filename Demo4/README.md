# AM (AgentManager) - Multi-Agent Coordination/Planning Server

A sophisticated **FastAPI-based MCP server** that orchestrates distributed task execution through HTTP API coordination with persistent SQLAlchemy ORM state management.

## 🏗️ Architecture Overview

- **Centralized HTTP Coordination**: FastAPI server managing all task distribution via REST endpoints
- **Persistent ORM State Management**: SQLAlchemy models with SQLite/PostgreSQL support
- **External Client Coordination**: Worker clients polling for tasks and reporting results
- **Server-Side Quality Control**: Centralized audit logic with database-driven rework cycles
- **Production-Ready Deployment**: PostgreSQL migration readiness with robust API security

## 📋 Phase 1 Implementation Status

✅ **Completed Components:**
- Project structure with proper Python package layout
- Complete Pydantic models for API communication (`TaskGraph`, `TaskStep`, `RAHistory`, etc.)
- FastAPI application with middleware and error handling
- Core API endpoints: `POST /v1/tasks`, `GET /v1/tasks/ready`, `POST /v1/results`
- Environment configuration with database and LLM settings
- Client configuration contract (`mcp_client_config.json`)

🚧 **Next Steps (Phase 2):**
- SQLAlchemy ORM implementation with database models
- LLM client integration for structured output
- Worker and Auditor agent core logic
- Database session management and dependency injection

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -e .
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run the Server
```bash
python -m agent_manager.api.main
```

### 4. Access API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📊 API Endpoints

### Core MCP Server Endpoints

| Endpoint | Method | Description | Status |
|----------|--------|-------------|---------|
| `/v1/tasks` | POST | Submit new task for processing | ✅ Phase 1 |
| `/v1/tasks/ready` | GET | Poll for ready tasks by agent type | ✅ Phase 1 |
| `/v1/results` | POST | Report completed task results | ✅ Phase 1 |
| `/v1/workflows/{id}/status` | GET | Get workflow status | ✅ Phase 1 |
| `/health` | GET | Health check endpoint | ✅ Phase 1 |

### Authentication
All endpoints require Bearer token authentication:
```bash
curl -H "Authorization: Bearer your_token_here" http://localhost:8000/v1/tasks/ready
```

## 🏗️ Development Phases

### Phase 1: Data Contracts and API Definitions ✅
- [x] Pydantic schemas for all API communication
- [x] FastAPI application with middleware setup
- [x] Core API endpoints with proper validation
- [x] Authentication framework
- [x] Environment configuration

**Go/No-Go Checkpoints:**
- ✅ All API endpoints accept required Pydantic data structures
- ✅ Auth token validation working across all endpoints
- ✅ Task polling endpoint structure ready for database integration

### Phase 2: Agent Core Logic (RA & Decoupling) 🚧
- [ ] Worker RA implementation with structured `ThoughtAction` output
- [ ] Auditor logic with critical system prompt
- [ ] LLM client with strict Pydantic enforcement
- [ ] SQLAlchemy ORM models and database setup

### Phase 3: Manager Orchestration and Control
- [ ] Database-driven planning and persistence
- [ ] Dependency scheduling with atomic updates
- [ ] Audit control loop with rework coordination

### Phase 4: Client Simulation and Production Readiness
- [ ] External worker client implementation
- [ ] Concurrency validation and resilience testing
- [ ] Full end-to-end workflow validation

## 🔧 Configuration

### Server Configuration (.env)
```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./agent_manager.db

# Security
SERVER_API_TOKEN=your_secure_token
SECRET_KEY=your_jwt_secret

# LLM
OPENAI_API_KEY=your_openai_key
LLM_MODEL=gpt-4
```

### Client Configuration (mcp_client_config.json)
```json
{
  "client_agent_id": "worker_001",
  "server_url": "http://localhost:8000",
  "auth_token": "your_token",
  "polling_interval_sec": 5,
  "agent_capabilities": ["researcher", "writer"]
}
```

## 📖 Documentation

- **CCS Documentation**: See `.context/` directory for comprehensive technical documentation
- **Development Guide**: `docs/development-phases-guide.md`
- **Project Roadmap**: `docs/project-roadmap.md`
- **API Documentation**: Available at `/docs` when server is running

## 🧪 Testing

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests (when implemented)
pytest

# Run linting
black agent_manager/
isort agent_manager/
mypy agent_manager/
```

## 🚀 Deployment

The MCP server is designed for production deployment with:
- PostgreSQL database support
- Docker containerization (coming in Phase 4)
- Load balancing and scaling capabilities
- Comprehensive monitoring and logging

---

**Status**: Phase 1 Complete ✅ | Ready for Phase 2 Implementation 🚀
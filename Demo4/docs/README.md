# AgentManager Documentation Index

Welcome to the AgentManager documentation! This index helps you find the right documentation for your needs.

## 📚 Documentation Overview

All documentation is organized in the `docs/` folder for easy access and maintenance.

## 🚀 Getting Started

### New Users Start Here

1. **[Project Usage Guide](project-usage-guide.md)** ⭐ **START HERE**
   - Quick start with practical examples
   - Real-world project scenarios
   - Integration patterns
   - Troubleshooting tips

2. **[Project Folder Structure](project-folder-structure.md)**
   - Understanding the dated folder system
   - File organization and naming
   - Automatic result saving
   - Configuration options

3. **[API Documentation](http://localhost:8001/docs)** (Interactive)
   - Complete REST API reference
   - Try endpoints in browser
   - Request/response schemas
   - Authentication details

## 📖 Complete Documentation

### Core Concepts

| Document | Description | Audience |
|----------|-------------|----------|
| [Project Usage Guide](project-usage-guide.md) | Practical examples and tutorials | All users |
| [Project Folder Structure](project-folder-structure.md) | Architecture and organization | Developers, DevOps |
| [Project Structure Update](PROJECT_STRUCTURE_UPDATE.md) | v1.2.0 changes and migration guide | All users |
| [Request JSON Implementation](REQUEST_JSON_IMPLEMENTATION.md) | Workflow request tracking and traceability | Developers, operators |
| [Documentation Updates](DOCUMENTATION_UPDATE.md) | Recent changes and migration | Existing users |
| [Project Status](PROJECT_STATUS.md) | Current system status and health dashboard | All users, operators |
| [Cleanup Summary](CLEANUP_SUMMARY.md) | Project cleanup record and organization | Developers, maintainers |

### Setup & Environment

| Document | Description | Audience |
|----------|-------------|----------|
| [Virtual Environment Setup](VENV_README.md) | Python virtual environment configuration | Developers |
| [Development Phases Guide](development-phases-guide.md) | Step-by-step development instructions | Developers |

### Planning & Roadmap

| Document | Description | Audience |
|----------|-------------|----------|
| [Project Roadmap](project-roadmap.md) | Future features and timeline | Product managers, stakeholders |

### Technical Reference

| Resource | Description | Access |
|----------|-------------|--------|
| [API Docs](http://localhost:8001/docs) | Interactive REST API reference | http://localhost:8001/docs |
| [Health Check](http://localhost:8001/health) | Server status endpoint | http://localhost:8001/health |

## 🎯 Documentation by Use Case

### I want to...

#### Submit My First Task
→ Start with [Project Usage Guide](project-usage-guide.md#quick-start-guide)

#### Understand the Project Structure
→ Read [Project Folder Structure](project-folder-structure.md#directory-layout)

#### Learn About Recent Updates
→ Check [Documentation Updates](DOCUMENTATION_UPDATE.md)

#### Plan Future Features
→ Review [Project Roadmap](project-roadmap.md)

#### Test the API
→ Visit [Interactive API Docs](http://localhost:8001/docs)

#### Troubleshoot Issues
→ See [Project Usage Guide - Troubleshooting](project-usage-guide.md#troubleshooting)

#### Integrate with My App
→ Follow [Project Usage Guide - Integration Examples](project-usage-guide.md#integration-examples)

#### Understand Agent Roles
→ Read [Project Usage Guide - Example Projects](project-usage-guide.md#example-projects)

## 🔧 Quick Reference

### Common Commands

```bash
# Submit a task
curl -X POST http://localhost:8001/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "user_request": "Your task here",
    "metadata": {"project_name": "my_project"}
  }'

# Check workflow status
curl http://localhost:8001/v1/workflows/{workflow_id}/status \
  -H "Authorization: Bearer your_token"

# View today's projects
ls -la projects/$(date +%Y-%m-%d)/

# Check server health
curl http://localhost:8001/health
```

### Project Structure Quick View

```
projects/
└── 2025-10-14/                    # Today's date
    └── project_name/              # Your project
        ├── FINAL_OUTPUT.md        # ⭐ Main deliverable
        ├── workflow_summary.json  # Workflow stats
        └── task_results/          # Individual tasks
            ├── task_1_agent.md
            ├── task_2_agent.md
            └── ...
```

### Available Agent Types

- **researcher** - Information gathering, fact checking
- **writer** - Content creation, documentation
- **analyst** - Data analysis, evaluation, insights
- **developer** - Software development, coding
- **tester** - Testing, quality assurance
- **architect** - System design, architecture
- **planner** - Planning, strategy, coordination
- **reviewer** - Quality control, validation

## 📝 Documentation Standards

### For Contributors

When adding new documentation:

1. **Location**: All docs go in `docs/` folder
2. **Format**: Use Markdown (.md)
3. **Naming**: Use kebab-case (e.g., `my-guide.md`)
4. **Structure**: 
   - Clear title (# Level 1)
   - Table of contents for long docs
   - Code examples where relevant
   - Links to related docs
5. **Update**: Add to this index after creating

### Documentation Template

```markdown
# Document Title

## Overview
Brief description of what this document covers.

## Prerequisites
What users should know/have before reading.

## Main Content
Core information organized in sections.

## Examples
Practical code examples.

## Troubleshooting
Common issues and solutions.

## Next Steps
Links to related documentation.
```

## 🔄 Recent Updates

**2025-10-14**: Major documentation update
- ✅ Added project folder structure documentation
- ✅ Created comprehensive usage guide
- ✅ Centralized all documentation in `docs/`
- ✅ Added dated project folder system
- ✅ Enhanced agent capabilities

See [DOCUMENTATION_UPDATE.md](DOCUMENTATION_UPDATE.md) for full details.

## 🎓 Learning Path

### Beginner Track
1. Read Quick Start in [Usage Guide](project-usage-guide.md)
2. Try Example 1 (Calculator Project)
3. Explore your project folder
4. Review workflow summary

### Intermediate Track
1. Study [Project Folder Structure](project-folder-structure.md)
2. Try all examples in [Usage Guide](project-usage-guide.md)
3. Integrate with your application
4. Configure custom settings

### Advanced Track
1. Deep dive into agent capabilities
2. Optimize workflow planning
3. Implement automation scripts
4. Contribute to documentation

## 🛠️ Tools & Resources

### Development
- **API Testing**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health
- **Docker Logs**: `docker-compose logs -f agent-manager`

### Monitoring
- **Project Folders**: `ls -la projects/$(date +%Y-%m-%d)/`
- **Database**: PostgreSQL at localhost:5433
- **Redis Cache**: localhost:6380

### Utilities
```bash
# View all documentation
ls -la docs/

# Search documentation
grep -r "keyword" docs/

# View recent projects
ls -lt projects/*/

# Count workflows today
ls -1 projects/$(date +%Y-%m-%d)/ | wc -l
```

## 📧 Support & Feedback

### Need Help?
1. Check this index for relevant documentation
2. Review troubleshooting sections
3. Check API docs for endpoint details
4. Inspect container logs for errors

### Found an Issue?
- Documentation unclear? Open an issue
- Found a bug? Report with details
- Have a suggestion? Create a feature request

### Contributing
- Improve existing docs
- Add new examples
- Create tutorials
- Share best practices

## 🔗 External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM Guide](https://docs.sqlalchemy.org/en/14/orm/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)

---

## Navigation

| Previous | Home | Next |
|----------|------|------|
| - | **📍 You Are Here** | [Usage Guide →](project-usage-guide.md) |

---

**Last Updated**: 2025-10-14  
**Version**: 0.2.0  
**Maintained by**: AgentManager Team

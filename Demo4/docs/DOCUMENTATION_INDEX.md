# AgentManager Documentation Index

**Last Updated**: October 15, 2025 PST  
**Documentation Version**: 2.0

---

## 📋 Quick Navigation

### 🚀 Getting Started
1. **[Project Usage Guide](./guides/project-usage-guide.md)** - How to use AgentManager
2. **[Project Roadmap](./guides/project-roadmap.md)** - Development timeline and milestones
3. **[Virtual Environment Setup](./guides/VENV_README.md)** - Python environment configuration

### 🎯 Dashboard Documentation
1. **[Dashboard Enhancement Summary](./dashboard/dashboard-enhancement-summary.md)** - ⭐ Latest updates (Oct 15, 2025)
   - Projects tab implementation
   - PST timezone consistency
   - Clean worker cards
2. **[UUID and Worker Fixes](./dashboard/uuid-and-worker-fixes.md)** - Full UUID display and container detection
3. **[Dashboard Display Improvements](./dashboard/dashboard-display-improvements.md)** - UI/UX enhancements
4. **[Workers Scrollbar Fix](./dashboard/workers-scrollbar-fix.md)** - Scrollable workers tab
5. **[Dashboard Workflow Updates](./dashboard/dashboard-workflow-updates.md)** - Workflow management
6. **[Build Dashboard Guide](./dashboard/BUILD_DASHBOARD.md)** - Executable build instructions

### 🏗️ Architecture & Data Model
1. **[Project-Workflow-Task Analysis](./architecture/project-workflow-task-analysis.md)** - ⭐ Data model relationships
   - 2-tier vs 3-tier hierarchy
   - Project → Workflows → Tasks structure
   - PST timezone requirements
2. **[Data Model Analysis](./architecture/data-model-analysis.md)** - Database schema and ORM design
3. **[Project Folder Structure](./architecture/project-folder-structure.md)** - Codebase organization

### 📚 Guides & Tutorials
1. **[Project Usage Guide](./guides/project-usage-guide.md)** - Complete usage instructions
2. **[Monitoring Implementation](./guides/monitoring-implementation-summary.md)** - Prometheus + Grafana
3. **[Development Phases Guide](./guides/development-phases-guide.md)** - Implementation phases
4. **[Build Configuration](./guides/build-config-update.md)** - PyInstaller setup
5. **[Request JSON Implementation](./guides/REQUEST_JSON_IMPLEMENTATION.md)** - API handling

---

## 🗂️ Documentation Structure

```
docs/
├── README.md (YOU ARE HERE)                 # Documentation index and navigation
│
├── dashboard/                               # Dashboard-specific documentation
│   ├── dashboard-enhancement-summary.md     # ⭐ Latest enhancements (Oct 15, 2025)
│   ├── uuid-and-worker-fixes.md            # UUID display & worker detection fixes
│   ├── dashboard-display-improvements.md    # UI/UX improvements
│   ├── workers-scrollbar-fix.md            # Vertical scrollbar implementation
│   ├── dashboard-workflow-updates.md       # Workflow management features
│   └── BUILD_DASHBOARD.md                  # Build instructions and configuration
│
├── architecture/                            # System architecture & design
│   ├── project-workflow-task-analysis.md   # ⭐ Data model relationships & hierarchy
│   ├── data-model-analysis.md              # Database schema and ORM models
│   └── project-folder-structure.md         # Codebase organization structure
│
├── guides/                                  # How-to guides & tutorials
│   ├── project-usage-guide.md              # Complete usage instructions
│   ├── project-roadmap.md                  # Development roadmap and timeline
│   ├── VENV_README.md                      # Virtual environment setup
│   ├── monitoring-implementation-summary.md # Prometheus + Grafana setup
│   ├── development-phases-guide.md         # Implementation phases & checkpoints
│   ├── build-config-update.md              # PyInstaller build configuration
│   └── REQUEST_JSON_IMPLEMENTATION.md      # API request/response handling
│
├── archive/                                 # Historical documentation
│   ├── DOCUMENTATION_REORGANIZATION.md     # Previous reorganization
│   └── DOCUMENTATION_UPDATE.md             # Old documentation changelog
│
├── PROJECT_STATUS.md                        # ⭐ Current project implementation status
├── CLEANUP_SUMMARY.md                       # Recent cleanup activities
└── PROJECT_STRUCTURE_UPDATE.md              # Project structure changes
```

---

## 🎯 Documentation by Use Case

### "I want to use AgentManager"
→ Start with [Project Usage Guide](./guides/project-usage-guide.md)

### "I want to build the dashboard"
→ See [Build Dashboard Guide](./dashboard/BUILD_DASHBOARD.md)

### "I want to understand the data model"
→ Read [Project-Workflow-Task Analysis](./architecture/project-workflow-task-analysis.md)

### "I want to see recent changes"
→ Check [Dashboard Enhancement Summary](./dashboard/dashboard-enhancement-summary.md)

### "I want to set up monitoring"
→ Follow [Monitoring Implementation](./guides/monitoring-implementation-summary.md)

### "I want to understand the codebase"
→ Review [Project Folder Structure](./architecture/project-folder-structure.md)

---

## 🔍 Recent Major Updates

### ⭐ October 15, 2025 - Dashboard Enhancements & Data Model Analysis
- ✅ **Projects Tab Added** - New top-level organization tab
- ✅ **PST Timezone Consistency** - All timestamps display in PST format
- ✅ **Clean Worker Cards** - Removed verbose job descriptions
- ✅ **Data Model Analysis** - Comprehensive 2-tier vs 3-tier hierarchy documentation
- ✅ **Documentation Organized** - New folder structure for better navigation

### October 14, 2025 - Dashboard Improvements
- ✅ **Full UUID Display** - Complete workflow and task IDs (no truncation)
- ✅ **Worker Detection Fixed** - All 13 containers now visible
- ✅ **4-Column Layout** - Workers displayed in 4-per-row grid
- ✅ **Scrollbar Added** - Vertical scrolling for workers tab
- ✅ **Build Configuration** - Updated PyInstaller setup

### Earlier Updates
- Monitoring implementation (Prometheus + Grafana)
- Virtual environment configuration
- Request/response JSON handling
- Development phases documentation

---

## 📊 Dashboard Features Reference

### Current Dashboard Tabs
| Tab | Purpose | Key Features |
|-----|---------|--------------|
| 🎯 **Projects** | Project-level organization | Placeholder for 3-tier data model, PST timestamps |
| 📊 **Workflows** | TaskGraph records | PST timestamps, full UUIDs, status colors |
| 📋 **Tasks** | TaskStep records | PST timestamps, full UUIDs, agent assignment |
| 👷 **Workers** | Container monitoring | 13 workers, 4-column grid, clean cards |
| 📈 **Metrics** | System performance | 24-hour statistics, success rates |

### Timezone Standard
- **Format**: `YYYY-MM-DD HH:MM:SS PST`
- **Implementation**: `app/timezone_utils.py`
- **Applied to**: All timestamps across all dashboard tabs

### Data Model Hierarchy
```
Current Implementation (2-tier):
  TaskGraphORM (Workflow) → TaskStepORM (Task) → ResultORM

Recommended Future (3-tier):
  ProjectORM → TaskGraphORM (Workflow) → TaskStepORM (Task) → ResultORM
```

---

## 🏗️ Technical Reference

### Key System Components
- **FastAPI Server**: HTTP API server (port 8001)
- **PostgreSQL Database**: Persistent storage (port 5433)
- **Redis Cache**: Performance optimization (port 6380)
- **Docker Containers**: 13 total (1 server + 2 infrastructure + 10 workers)
- **Dashboard**: Tkinter GUI with real-time monitoring

### Worker Types
- **Infrastructure**: agent-manager (server), postgres (database), redis (cache)
- **Analysts**: 2 workers (analyst-1, analyst-2)
- **Writers**: 2 workers (writer-1, writer-2)
- **Researchers**: 2 workers (researcher-1, researcher-2)
- **Developers**: 2 workers (developer-1, developer-2)
- **Tester**: 1 worker (tester-1)
- **Architect**: 1 worker (architect-1)

---

## 📖 Documentation Conventions

### File Naming Standards
- **Feature docs**: `feature-name-description.md` (lowercase with hyphens)
- **Status docs**: `PROJECT_STATUS.md` (uppercase with underscores)
- **Guides**: `topic-guide.md` or `TOPIC_README.md`

### Content Structure
1. **Header**: Title, date, version (if applicable)
2. **Summary**: TL;DR or executive summary
3. **Body**: Well-organized with clear headers and sections
4. **Conclusion**: Status, next steps, or recommendations
5. **References**: Links to related documentation

### Status Indicators
- ✅ **Completed** - Feature/task finished
- 🚧 **In Progress** - Currently being developed
- ❌ **Blocked/Issue** - Problem preventing progress
- 📋 **Planned** - Scheduled for future development
- 🔄 **Updated** - Recently modified
- ⭐ **Important** - Key documentation or feature

---

## 🔗 External Resources

### Project Context
- **Codebase Context**: `.context/index.md` (CCS v1.1 specification)
- **Copilot Instructions**: `.github/copilot-instructions.md`
- **Environment Configuration**: `.env` file

### Related Documentation
- **Docker Compose**: `docker-compose.yml` (infrastructure setup)
- **Agent Manager Core**: `agent_manager/` (Python source code)
- **Dashboard App**: `app/` (dashboard source code)

---

## 📞 Support & Contribution

### Getting Help
1. Check [Project Status](./PROJECT_STATUS.md) for current development state
2. Review [Project Usage Guide](./guides/project-usage-guide.md) for usage instructions
3. See [Development Phases Guide](./guides/development-phases-guide.md) for development workflow

### Finding Information
- **Dashboard issues**: Check `docs/dashboard/` folder
- **Data model questions**: See `docs/architecture/` folder
- **Setup problems**: Review `docs/guides/` folder
- **Historical context**: Browse `docs/archive/` folder

---

## 📝 Documentation Maintenance

### Last Major Reorganization
**Date**: October 15, 2025 PST  
**Changes**:
- Created organized folder structure (dashboard, architecture, guides, archive)
- Moved files to appropriate categories
- Created comprehensive README with navigation
- Updated cross-references and links

### Documentation Ownership
**Maintained By**: AgentManager Development Team  
**Review Cycle**: As needed with major updates  
**Feedback**: Submit via project issues or pull requests

---

**Quick Links**: [Status](./PROJECT_STATUS.md) | [Usage](./guides/project-usage-guide.md) | [Build](./dashboard/BUILD_DASHBOARD.md) | [Architecture](./architecture/project-workflow-task-analysis.md)
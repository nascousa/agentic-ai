# AgentManager Dashboard

Real-time monitoring desktop application for AgentManager workflows and workers.

## Features

- **Real-time Worker Status**: Monitor all 10 workers with live health status
- **Active Workflows**: Track running workflows and their progress
- **Task Queue**: View pending, in-progress, and completed tasks
- **Performance Metrics**: Execution times, success rates, and throughput
- **System Health**: Server, database, and Redis connection status
- **Auto-refresh**: Configurable refresh intervals

## Installation

```bash
# Install dependencies (tkinter usually comes pre-installed on Windows)
pip install -r requirements.txt
```

## Usage

### Option 1: Using the Batch Launcher (Recommended for Windows)
```bash
# Double-click run_dashboard.bat or run from terminal
.\run_dashboard.bat
```

The batch launcher will:
- Check Python installation
- Verify tkinter availability
- Auto-install missing dependencies
- Launch the dashboard

### Option 2: Using Python Directly
```bash
# Run from project root
python run_dashboard.py

# Or run directly from app folder
cd app
python dashboard.py
```

## Configuration

Edit `app/config.py` to change:
- Server URL (default: http://localhost:8001)
- Auth token
- Refresh interval (default: 2 seconds)
- Display options

## Requirements

- Python 3.8+
- Running AgentManager server
- Network access to server

## Architecture

```
app/
├── dashboard.py          # Main GUI application
├── config.py            # Configuration settings
├── api_client.py        # AgentManager API client
├── widgets/
│   ├── worker_panel.py  # Worker status display
│   ├── workflow_panel.py # Workflow monitoring
│   └── metrics_panel.py # Performance metrics
└── utils/
    ├── colors.py        # Color schemes
    └── formatters.py    # Data formatting utilities
```

## Screenshots

The dashboard includes:
- Worker grid showing all 10 workers with health indicators
- Active workflows with real-time progress bars
- Task queue with status badges
- Performance charts and metrics
- System health indicators

## Troubleshooting

**Connection Issues**:
- Verify server is running: `docker-compose ps`
- Check auth token in config.py
- Ensure firewall allows port 8001

**Display Issues**:
- Requires tkinter (comes with Python on Windows)
- High DPI displays: Adjust font sizes in config.py

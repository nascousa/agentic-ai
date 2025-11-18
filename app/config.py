"""
AgentManager Dashboard Configuration
"""

# Server Configuration
SERVER_URL = "http://localhost:8001"
AUTH_TOKEN = "am_server_30j_MNJFG086I8kh2fdsAU_aA7ggR4OTv5iR-tYcuyQ"

# Refresh Intervals (seconds)
WORKER_REFRESH_INTERVAL = 2
WORKFLOW_REFRESH_INTERVAL = 3
METRICS_REFRESH_INTERVAL = 5

# Display Settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_TITLE = "AgentManager Dashboard"

# Worker Configuration - Includes all containers
WORKERS = [
    # Infrastructure
    {"name": "agent-manager", "role": "server"},
    {"name": "postgres", "role": "database"},
    {"name": "redis", "role": "cache"},
    # Workers
    {"name": "analyst-1", "role": "analyst"},
    {"name": "analyst-2", "role": "analyst"},
    {"name": "writer-1", "role": "writer"},
    {"name": "writer-2", "role": "writer"},
    {"name": "researcher-1", "role": "researcher"},
    {"name": "researcher-2", "role": "researcher"},
    {"name": "developer-1", "role": "developer"},
    {"name": "developer-2", "role": "developer"},
    {"name": "tester-1", "role": "tester"},
    {"name": "architect-1", "role": "architect"},
]

# Color Scheme
COLORS = {
    'bg_dark': '#1e1e1e',
    'bg_medium': '#2d2d2d',
    'bg_light': '#3d3d3d',
    'text_primary': '#ffffff',
    'text_secondary': '#b0b0b0',
    'accent_blue': '#007acc',
    'accent_green': '#4ec9b0',
    'accent_orange': '#ce9178',
    'accent_red': '#f48771',
    'success': '#4caf50',
    'warning': '#ff9800',
    'error': '#f44336',
    'info': '#2196f3',
    'healthy': '#00c851',
    'unhealthy': '#ff4444',
    'idle': '#ffbb33',
    'running': '#00c851',  # Same as healthy/active
    'active': '#00c851',
}

# Font Settings
FONTS = {
    'title': ('Segoe UI', 16, 'bold'),
    'heading': ('Segoe UI', 12, 'bold'),
    'body': ('Segoe UI', 10),
    'small': ('Segoe UI', 9),
    'mono': ('Consolas', 10),
}

# Status Indicators
STATUS_COLORS = {
    'READY': COLORS['info'],
    'IN_PROGRESS': COLORS['active'],
    'COMPLETED': COLORS['success'],
    'FAILED': COLORS['error'],
    'PENDING': COLORS['idle'],
}

# Worker Role Colors
ROLE_COLORS = {
    # Infrastructure
    'server': '#e74c3c',       # Red - Core server
    'database': '#3498db',     # Blue - Database
    'cache': '#e67e22',        # Orange - Cache/Redis
    # Workers
    'analyst': '#007acc',      # Blue - Analysis work
    'writer': '#4ec9b0',       # Cyan - Creative writing
    'researcher': '#ce9178',   # Orange - Information gathering
    'developer': '#4caf50',    # Green - Code development
    'tester': '#ff9800',       # Amber - Testing
    'architect': '#9c27b0',    # Purple - Design/Architecture
}

# Worker Role Descriptions
ROLE_DESCRIPTIONS = {
    # Infrastructure
    'server': 'AgentManager core server - coordinates workflows and manages task distribution',
    'database': 'PostgreSQL database - stores workflows, tasks, results, and audit reports',
    'cache': 'Redis cache - provides fast data access and improves system performance',
    # Workers
    'analyst': 'Analyzes requirements, evaluates solutions, and provides strategic recommendations',
    'writer': 'Creates documentation, technical content, and user-facing materials',
    'researcher': 'Gathers information, conducts research, and compiles knowledge resources',
    'developer': 'Writes code, implements features, and builds software solutions',
    'tester': 'Tests functionality, validates quality, and ensures reliability',
    'architect': 'Designs system architecture, defines patterns, and ensures scalability',
}

# API Endpoints
ENDPOINTS = {
    'health': '/health',
    'tasks': '/v1/tasks',
    'workflows': '/v1/workflows',
    'workers': '/v1/workers',
    'metrics': '/v1/metrics',
}

# Dashboard Panels
SHOW_WORKER_PANEL = True
SHOW_WORKFLOW_PANEL = True
SHOW_METRICS_PANEL = True
SHOW_SYSTEM_PANEL = True

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'app/dashboard.log'

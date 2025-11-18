"""
AgentManager Dashboard - Main Application

Real-time monitoring dashboard for agentManager workers, workflows, and tasks.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime, timezone, timedelta
import threading
import time
import logging
import os
import sys
import tempfile
import json

# Import timezone utilities
from timezone_utils import format_pst_timestamp, format_current_pst

from config import *
from api_client import AgentManagerClient

# Setup logging with proper path handling
def setup_logging():
    """Setup logging with fallback to temp directory"""
    try:
        # Try to use the configured log file path
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        log_file = LOG_FILE
    except (OSError, PermissionError):
        # Fallback to temp directory if can't create log in app dir
        log_file = os.path.join(tempfile.gettempdir(), 'agentmanager_dashboard.log')
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Persistence file for last project inputs
PERSISTENCE_FILE = os.path.join(os.path.dirname(__file__), '.dashboard_state.json')


class AgentManagerDashboard:
    """Main dashboard application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=COLORS['bg_dark'])
        
        # Initialize API client
        self.client = AgentManagerClient(SERVER_URL, AUTH_TOKEN)
        
        # State tracking
        self.running = True
        self.refresh_threads = []
        
        # Load persisted state
        self.last_project_name = ""
        self.last_project_desc = ""
        self.load_persisted_state()
        
        # Setup UI
        self.setup_ui()
        
        # Start refresh threads
        self.start_refresh_threads()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Setup the main UI layout"""
        # Header
        self.create_header()
        
        # Main content area with notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create tabs
        self.create_prompt_tab()
        self.create_projects_tab()
        self.create_workflows_tab()
        self.create_tasks_tab()
        self.create_workers_tab()
        self.create_metrics_tab()
        
        # Status bar
        self.create_status_bar()
    
    def create_header(self):
        """Create header with title and system status"""
        header_frame = tk.Frame(self.root, bg=COLORS['bg_dark'], height=80)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="🚀 AgentManager Dashboard",
            font=FONTS['title'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        title_label.pack(side='left', padx=10)
        
        # System status indicators
        status_frame = tk.Frame(header_frame, bg=COLORS['bg_dark'])
        status_frame.pack(side='right', padx=10)
        
        self.server_status = self.create_status_indicator(status_frame, "Server", 0)
        self.db_status = self.create_status_indicator(status_frame, "Database", 1)
        self.redis_status = self.create_status_indicator(status_frame, "Redis", 2)
    
    def create_status_indicator(self, parent, label, col):
        """Create a status indicator"""
        frame = tk.Frame(parent, bg=COLORS['bg_dark'])
        frame.grid(row=0, column=col, sticky='e', padx=10)
        
        label_widget = tk.Label(
            frame,
            text=f"{label}:",
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_dark']
        )
        label_widget.pack(side='left', padx=(0, 5))
        
        status_widget = tk.Label(
            frame,
            text="●",
            font=FONTS['heading'],
            fg=COLORS['idle'],
            bg=COLORS['bg_dark']
        )
        status_widget.pack(side='left')
        
        return status_widget
    
    def create_prompt_tab(self):
        """Create prompt input tab for submitting new workflows"""
        prompt_frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(prompt_frame, text='✨ Prompt')
        
        # Header
        header = tk.Label(
            prompt_frame,
            text="Submit New Project Request",
            font=FONTS['heading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        header.pack(pady=10)
        
        # Main container with padding
        container = tk.Frame(prompt_frame, bg=COLORS['bg_dark'])
        container.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Project Name
        name_label = tk.Label(
            container,
            text="Project Name:",
            font=FONTS['body'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        name_label.pack(anchor='w', pady=(0, 5))
        
        self.project_name_entry = tk.Entry(
            container,
            font=FONTS['body'],
            bg=COLORS['bg_medium'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary']
        )
        self.project_name_entry.pack(fill='x', pady=(0, 15))
        
        # Project Description
        desc_label = tk.Label(
            container,
            text="Project Description:",
            font=FONTS['body'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        desc_label.pack(anchor='w', pady=(0, 5))
        
        # Text area with scrollbar
        text_frame = tk.Frame(container, bg=COLORS['bg_dark'])
        text_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        self.project_desc_text = scrolledtext.ScrolledText(
            text_frame,
            font=FONTS['body'],
            bg=COLORS['bg_medium'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'],
            wrap=tk.WORD,
            height=15
        )
        self.project_desc_text.pack(fill='both', expand=True)
        
        # Restore last values if available
        if self.last_project_name:
            self.project_name_entry.insert(0, self.last_project_name)
        if self.last_project_desc:
            self.project_desc_text.insert('1.0', self.last_project_desc)
        
        # Fast Mode checkbox
        fast_mode_frame = tk.Frame(container, bg=COLORS['bg_dark'])
        fast_mode_frame.pack(fill='x', pady=(10, 5))
        
        self.fast_mode_var = tk.BooleanVar(value=False)
        fast_mode_check = tk.Checkbutton(
            fast_mode_frame,
            text="⚡ Fast Mode (reduces iterations from 10→2, ~50% faster)",
            variable=self.fast_mode_var,
            font=FONTS['body'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark'],
            selectcolor=COLORS['bg_medium'],
            activebackground=COLORS['bg_dark'],
            activeforeground=COLORS['text_primary']
        )
        fast_mode_check.pack(anchor='w')
        
        # Button frame
        button_frame = tk.Frame(container, bg=COLORS['bg_dark'])
        button_frame.pack(fill='x', pady=10)
        
        # Submit button
        submit_btn = tk.Button(
            button_frame,
            text="Generate & Submit Project Request",
            font=FONTS['body'],
            bg=COLORS['success'],
            fg='white',
            command=self.submit_workflow,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        submit_btn.pack(side='left', padx=(0, 10))
        
        # Clear button
        clear_btn = tk.Button(
            button_frame,
            text="Clear",
            font=FONTS['body'],
            bg=COLORS['bg_medium'],
            fg=COLORS['text_primary'],
            command=self.clear_prompt,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        clear_btn.pack(side='left')
        
        # Status label
        self.prompt_status = tk.Label(
            container,
            text="",
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_dark']
        )
        self.prompt_status.pack(anchor='w', pady=(10, 0))
    
    def create_workers_tab(self):
        """Create workers monitoring tab"""
        workers_frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(workers_frame, text='👷 Workers')
        
        # Loading indicator
        self.workers_loading = tk.Label(
            workers_frame,
            text="⏳ Loading workers...",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_dark']
        )
        self.workers_loading.place(relx=0.5, rely=0.5, anchor='center')
        
        # Header
        header = tk.Label(
            workers_frame,
            text="Worker Status",
            font=FONTS['heading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        header.pack(pady=10)
        
        # Workers list with scrollbar
        list_frame = tk.Frame(workers_frame, bg=COLORS['bg_dark'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create treeview for workers - matching tasks tab format
        columns = ('Worker Name', 'Role', 'Status', 'Current Task', 'Uptime', 'Container ID')
        self.workers_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            height=20
        )
        
        # Define headings
        self.workers_tree.heading('Worker Name', text='Worker Name')
        self.workers_tree.heading('Role', text='Role')
        self.workers_tree.heading('Status', text='Status')
        self.workers_tree.heading('Current Task', text='Current Task')
        self.workers_tree.heading('Uptime', text='Uptime')
        self.workers_tree.heading('Container ID', text='Container ID')
        
        # Define column widths
        self.workers_tree.column('Worker Name', width=180)
        self.workers_tree.column('Role', width=100)
        self.workers_tree.column('Status', width=100)
        self.workers_tree.column('Current Task', width=450)
        self.workers_tree.column('Uptime', width=120)
        self.workers_tree.column('Container ID', width=100)
        
        # Configure tags for status colors
        self.workers_tree.tag_configure('EXECUTING', foreground=COLORS['warning'])  # Yellow - actively executing task
        self.workers_tree.tag_configure('IDLE', foreground=COLORS['success'])  # Green - idle/available
        self.workers_tree.tag_configure('ERROR', foreground=COLORS['error'])  # Red - error/unhealthy
        self.workers_tree.tag_configure('NOT_FOUND', foreground=COLORS['error'])  # Red - not found/unknown
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.workers_tree.yview)
        self.workers_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.workers_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Store worker items mapping
        self.worker_items = {}
        
        # Insert initial worker rows with updated format
        for worker in WORKERS:
            item = self.workers_tree.insert('', 'end', values=(
                worker['name'],
                worker['role'],
                'Checking...',
                'No task',
                'N/A',
                'N/A'
            ), tags=('IDLE',))
            self.worker_items[worker['name']] = item
    
    def create_projects_tab(self):
        """Create projects monitoring tab"""
        projects_frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(projects_frame, text='📁 Projects')
        
        # Loading indicator
        self.projects_loading = tk.Label(
            projects_frame,
            text="⏳ Loading projects...",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_dark']
        )
        self.projects_loading.place(relx=0.5, rely=0.5, anchor='center')
        
        # Header
        header = tk.Label(
            projects_frame,
            text="Recent Projects",
            font=FONTS['heading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        header.pack(pady=10)
        
        # Projects list
        list_frame = tk.Frame(projects_frame, bg=COLORS['bg_dark'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create treeview for projects
        columns = ('Created', 'Project ID', 'Name', 'Workflows', 'Status', 'Progress')
        self.projects_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        # Define headings
        self.projects_tree.heading('Created', text='Created At (PST)')
        self.projects_tree.heading('Project ID', text='Project ID')
        self.projects_tree.heading('Name', text='Project Name')
        self.projects_tree.heading('Workflows', text='Workflows Count')
        self.projects_tree.heading('Status', text='Status')
        self.projects_tree.heading('Progress', text='Progress')
        
        # Define column widths
        self.projects_tree.column('Created', width=150)
        self.projects_tree.column('Project ID', width=100)
        self.projects_tree.column('Name', width=200)
        self.projects_tree.column('Workflows', width=320)  # Wider for new format
        self.projects_tree.column('Status', width=100)
        self.projects_tree.column('Progress', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.projects_tree.yview)
        self.projects_tree.configure(yscrollcommand=scrollbar.set)
        
        # Configure tags for status colors (same as tasks)
        self.projects_tree.tag_configure('READY', foreground=STATUS_COLORS['READY'])
        self.projects_tree.tag_configure('IN_PROGRESS', foreground=STATUS_COLORS['IN_PROGRESS'])
        self.projects_tree.tag_configure('COMPLETED', foreground=STATUS_COLORS['COMPLETED'])
        self.projects_tree.tag_configure('FAILED', foreground=STATUS_COLORS['FAILED'])
        self.projects_tree.tag_configure('PENDING', foreground=STATUS_COLORS['PENDING'])
        
        # Pack
        self.projects_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_workflows_tab(self):
        """Create workflows monitoring tab"""
        workflows_frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(workflows_frame, text='📊 Workflows')
        
        # Loading indicator
        self.workflows_loading = tk.Label(
            workflows_frame,
            text="⏳ Loading workflows...",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_dark']
        )
        self.workflows_loading.place(relx=0.5, rely=0.5, anchor='center')
        
        # Header
        header = tk.Label(
            workflows_frame,
            text="Recent Workflows",
            font=FONTS['heading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        header.pack(pady=10)
        
        # Workflows list with scrollbar
        list_frame = tk.Frame(workflows_frame, bg=COLORS['bg_dark'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create treeview for workflows - reordered columns
        columns = ('Created', 'Project ID', 'ID', 'Description', 'Status', 'Progress')
        self.workflows_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        # Define headings
        self.workflows_tree.heading('Created', text='Created At (PST)')
        self.workflows_tree.heading('Project ID', text='Project ID')
        self.workflows_tree.heading('ID', text='Workflow ID')
        self.workflows_tree.heading('Description', text='Description')
        self.workflows_tree.heading('Status', text='Status')
        self.workflows_tree.heading('Progress', text='Progress')
        
        # Define column widths
        self.workflows_tree.column('Created', width=150)
        self.workflows_tree.column('Project ID', width=100)
        self.workflows_tree.column('ID', width=110)
        self.workflows_tree.column('Description', width=450)
        self.workflows_tree.column('Status', width=100)
        self.workflows_tree.column('Progress', width=100)
        
        # Configure tags for status color coding
        self.workflows_tree.tag_configure('READY', foreground=STATUS_COLORS['READY'])
        self.workflows_tree.tag_configure('IN_PROGRESS', foreground=STATUS_COLORS['IN_PROGRESS'])
        self.workflows_tree.tag_configure('COMPLETED', foreground=STATUS_COLORS['COMPLETED'])
        self.workflows_tree.tag_configure('FAILED', foreground=STATUS_COLORS['FAILED'])
        self.workflows_tree.tag_configure('PENDING', foreground=STATUS_COLORS['PENDING'])
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.workflows_tree.yview)
        self.workflows_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.workflows_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_tasks_tab(self):
        """Create tasks monitoring tab"""
        tasks_frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(tasks_frame, text='📝 Tasks')
        
        # Loading indicator
        self.tasks_loading = tk.Label(
            tasks_frame,
            text="⏳ Loading tasks...",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_dark']
        )
        self.tasks_loading.place(relx=0.5, rely=0.5, anchor='center')
        
        # Header
        header = tk.Label(
            tasks_frame,
            text="Recent Tasks",
            font=FONTS['heading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        header.pack(pady=10)
        
        # Tasks list with scrollbar
        list_frame = tk.Frame(tasks_frame, bg=COLORS['bg_dark'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create treeview for tasks - reordered columns with Last Updated first
        columns = ('Updated', 'Workflow ID', 'Task ID', 'Agent', 'Status', 'Description')
        self.tasks_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            height=20
        )
        
        # Define headings
        self.tasks_tree.heading('Updated', text='Last Updated (PST)')
        self.tasks_tree.heading('Workflow ID', text='Workflow ID')
        self.tasks_tree.heading('Task ID', text='Task ID')
        self.tasks_tree.heading('Agent', text='Agent')
        self.tasks_tree.heading('Status', text='Status')
        self.tasks_tree.heading('Description', text='Description')
        
        # Define column widths
        self.tasks_tree.column('Updated', width=140)
        self.tasks_tree.column('Workflow ID', width=110)
        self.tasks_tree.column('Task ID', width=110)
        self.tasks_tree.column('Agent', width=120)
        self.tasks_tree.column('Status', width=120)
        self.tasks_tree.column('Description', width=500)
        
        # Configure tags for status color coding
        self.tasks_tree.tag_configure('READY', foreground=STATUS_COLORS['READY'])
        self.tasks_tree.tag_configure('IN_PROGRESS', foreground=STATUS_COLORS['IN_PROGRESS'])
        self.tasks_tree.tag_configure('COMPLETED', foreground=STATUS_COLORS['COMPLETED'])
        self.tasks_tree.tag_configure('FAILED', foreground=STATUS_COLORS['FAILED'])
        self.tasks_tree.tag_configure('PENDING', foreground=STATUS_COLORS['PENDING'])
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.tasks_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_metrics_tab(self):
        """Create metrics and statistics tab"""
        metrics_frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(metrics_frame, text='📈 Metrics')
        
        # Loading indicator
        self.metrics_loading = tk.Label(
            metrics_frame,
            text="⏳ Loading metrics...",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_dark']
        )
        self.metrics_loading.place(relx=0.5, rely=0.5, anchor='center')
        
        # Header
        header = tk.Label(
            metrics_frame,
            text="System Metrics",
            font=FONTS['heading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_dark']
        )
        header.pack(pady=10)
        
        # Metrics grid
        grid = tk.Frame(metrics_frame, bg=COLORS['bg_dark'])
        grid.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create metric cards
        self.metric_cards = {}
        metrics = [
            ('total_tasks', 'Total Tasks', '0'),
            ('completed_tasks', 'Completed Tasks', '0'),
            ('failed_tasks', 'Failed Tasks', '0'),
            ('workflows', 'Workflows', '0'),
            ('success_rate', 'Success Rate', '0%'),
            ('avg_time', 'Avg Execution', '0s'),
        ]
        
        for i, (key, label, initial) in enumerate(metrics):
            row = i // 3
            col = i % 3
            card = self.create_metric_card(grid, label, initial)
            card.grid(row=row, column=col, padx=10, pady=10, sticky='ew')
            self.metric_cards[key] = card
        
        # Configure grid weights
        for i in range(3):
            grid.grid_columnconfigure(i, weight=1)
    
    def create_metric_card(self, parent, label, value):
        """Create a metric display card"""
        card = tk.Frame(parent, bg=COLORS['bg_medium'], relief='raised', bd=2)
        card.pack_propagate(False)
        card.configure(height=100)
        
        label_widget = tk.Label(
            card,
            text=label,
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_medium']
        )
        label_widget.pack(pady=(15, 5))
        
        value_widget = tk.Label(
            card,
            text=value,
            font=FONTS['title'],
            fg=COLORS['accent_blue'],
            bg=COLORS['bg_medium']
        )
        value_widget.pack()
        
        # Store reference for updates
        card.value_label = value_widget
        
        return card
    
    def create_status_bar(self):
        """Create bottom status bar"""
        status_frame = tk.Frame(self.root, bg=COLORS['bg_medium'], height=30)
        status_frame.pack(side='bottom', fill='x')
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready",
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_medium']
        )
        self.status_label.pack(side='left', padx=10)
        
        self.time_label = tk.Label(
            status_frame,
            text=(datetime.now(timezone.utc) - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S PST'),
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_medium']
        )
        self.time_label.pack(side='right', padx=10)
    
    def start_refresh_threads(self):
        """Start background refresh threads"""
        # Projects refresh
        thread = threading.Thread(target=self.refresh_projects_loop, daemon=True)
        thread.start()
        self.refresh_threads.append(thread)
        
        # Workers refresh
        thread = threading.Thread(target=self.refresh_workers_loop, daemon=True)
        thread.start()
        self.refresh_threads.append(thread)
        
        # Workflows refresh
        thread = threading.Thread(target=self.refresh_workflows_loop, daemon=True)
        thread.start()
        self.refresh_threads.append(thread)
        
        # Tasks refresh
        thread = threading.Thread(target=self.refresh_tasks_loop, daemon=True)
        thread.start()
        self.refresh_threads.append(thread)
        
        # Metrics refresh
        thread = threading.Thread(target=self.refresh_metrics_loop, daemon=True)
        thread.start()
        self.refresh_threads.append(thread)
        
        # System status refresh
        thread = threading.Thread(target=self.refresh_system_status_loop, daemon=True)
        thread.start()
        self.refresh_threads.append(thread)
        
        # Time update
        thread = threading.Thread(target=self.update_time_loop, daemon=True)
        thread.start()
        self.refresh_threads.append(thread)
    
    def refresh_projects_loop(self):
        """Background loop to refresh projects"""
        while self.running:
            try:
                projects = self.client.get_projects()
                self.root.after(0, self.update_projects_ui, projects)
            except Exception as e:
                logger.error(f"Error refreshing projects: {e}")
            time.sleep(WORKFLOW_REFRESH_INTERVAL)
    
    def update_projects_ui(self, projects):
        """Update projects UI with new data"""
        # Hide loading indicator
        if hasattr(self, 'projects_loading'):
            self.projects_loading.place_forget()
        
        # Clear existing items
        for item in self.projects_tree.get_children():
            self.projects_tree.delete(item)
        
        # Add new items
        for project in projects:
            workflow_count = project.get('workflow_count', 0)
            completed = project.get('completed_workflows', 0)
            in_progress = project.get('in_progress_workflows', 0)
            failed = project.get('failed_workflows', 0)
            progress_pct = project.get('progress_percentage', 0.0)
            
            # Format workflow count with breakdown: [ X ] Completed | [ Y ] In Progress | [ Z ] Failed
            workflow_text = f"[ {completed} ] Completed | [ {in_progress} ] In Progress | [ {failed} ] Failed"
            
            # Format progress
            progress_text = f"{progress_pct:.0f}%"
            
            # Get status for color coding
            status = project.get('overall_status', 'PENDING')
            
            # Insert with status tag for color coding
            self.projects_tree.insert('', 'end', values=(
                project.get('created_at', 'N/A'),
                project.get('project_id', 'N/A'),
                project.get('project_name', 'N/A'),
                workflow_text,
                status,
                progress_text
            ), tags=(status,))
    
    def refresh_workers_loop(self):
        """Background loop to refresh worker status"""
        while self.running:
            try:
                workers = self.client.get_docker_workers()
                worker_status = self.client.get_worker_status()
                self.root.after(0, self.update_workers_ui, workers, worker_status)
            except Exception as e:
                logger.error(f"Error refreshing workers: {e}")
            time.sleep(WORKER_REFRESH_INTERVAL)
    
    def update_workers_ui(self, workers, worker_status):
        """Update workers UI with new data including current tasks"""
        worker_dict = {w['name']: w for w in workers}
        worker_tasks = worker_status.get('worker_tasks', {})
        
        for name, item in self.worker_items.items():
            if name in worker_dict:
                worker = worker_dict[name]
                status = worker['status']
                health = worker['health']
                role = worker.get('role', 'unknown')
                uptime = worker.get('uptime', 'N/A')
                container_id = worker.get('id', 'N/A')[:12] if worker.get('id') else 'N/A'  # Shortened container ID
                
                # Check if worker has a current task
                task_info = worker_tasks.get(name)
                if task_info:
                    current_task = f"{task_info['task_name']} ({task_info['task_id'][:15]}...)"
                    status_text = "● Executing"
                    status_tag = 'EXECUTING'
                else:
                    current_task = "No task"
                    # Determine status color and text
                    if health == 'healthy':
                        status_text = "● Idle"
                        status_tag = 'IDLE'
                    else:
                        status_text = "● Unhealthy"
                        status_tag = 'ERROR'
                
                # Update the row with new column structure
                self.workers_tree.item(item, values=(
                    name,
                    role,
                    status_text,
                    current_task,
                    uptime,
                    container_id
                ), tags=(status_tag,))
            else:
                # Worker not found
                role = WORKERS[[w['name'] for w in WORKERS].index(name)]['role'] if name in [w['name'] for w in WORKERS] else 'unknown'
                self.workers_tree.item(item, values=(
                    name,
                    role,
                    "● Not found",
                    "Container not running",
                    "N/A",
                    "N/A"
                ), tags=('NOT_FOUND',))
    
    def refresh_workflows_loop(self):
        """Background loop to refresh workflows"""
        while self.running:
            try:
                workflows = self.client.get_active_workflows()
                
                # Get progress for ALL workflows in a single query (much faster!)
                all_progress = self.client.get_all_workflow_progress()
                
                # Attach progress to each workflow
                for workflow in workflows:
                    workflow_id = workflow['workflow_id']
                    workflow['progress'] = all_progress.get(workflow_id, {
                        'total_tasks': 0,
                        'completed': 0,
                        'in_progress': 0,
                        'pending': 0,
                        'failed': 0,
                        'progress_percent': 0
                    })
                
                self.root.after(0, self.update_workflows_ui, workflows)
            except Exception as e:
                logger.error(f"Error refreshing workflows: {e}")
            time.sleep(WORKFLOW_REFRESH_INTERVAL)
    
    def update_workflows_ui(self, workflows):
        """Update workflows UI with new data"""
        # Hide loading indicator
        if hasattr(self, 'workflows_loading'):
            self.workflows_loading.place_forget()
        
        # Clear existing items
        for item in self.workflows_tree.get_children():
            self.workflows_tree.delete(item)
        
        # Add new items - filter out invalid/empty workflows
        for workflow in workflows:
            # Skip workflows without proper ID or name
            if not workflow.get('workflow_id') or not workflow.get('workflow_name'):
                continue
            progress = workflow.get('progress', {})
            progress_text = f"{progress.get('completed', 0)}/{progress.get('total_tasks', 0)}"
            
            # Use full ID
            workflow_id = workflow.get('id', '')
            
            # Get status for color coding
            status = workflow.get('status', '')
            
            # Convert created_at to PST format
            created_at = workflow.get('created_at', '')
            if created_at:
                try:
                    # Parse the timestamp and convert to PST
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at_pst = format_pst_timestamp(dt)
                except:
                    created_at_pst = created_at  # Fallback to original
            else:
                created_at_pst = 'N/A'
            
            # Database returns workflows in DESC order, insert at end to maintain that order
            self.workflows_tree.insert('', 'end', values=(
                created_at_pst,
                workflow.get('project_id', 'N/A'),
                workflow_id,
                workflow.get('description', ''),
                status,
                progress_text
            ), tags=(status,))
    
    def refresh_tasks_loop(self):
        """Background loop to refresh tasks"""
        while self.running:
            try:
                tasks = self.client.get_recent_tasks(limit=50)
                self.root.after(0, self.update_tasks_ui, tasks)
            except Exception as e:
                logger.error(f"Error refreshing tasks: {e}")
            time.sleep(WORKFLOW_REFRESH_INTERVAL)
    
    def update_tasks_ui(self, tasks):
        """Update tasks UI with new data"""
        # Hide loading indicator
        if hasattr(self, 'tasks_loading'):
            self.tasks_loading.place_forget()
        
        # Clear existing items
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        
        # Add new items with reordered columns: Updated, Task ID, Task Name, Agent, Status, Description
        for task in tasks:
            # Use full ID
            task_id = task.get('task_id', '')
            
            # Get status for color coding
            status = task.get('status', '')
            
            # Convert updated_at to PST format
            updated_at = task.get('updated_at', '')
            if updated_at:
                try:
                    # Parse the timestamp and convert to PST
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    updated_at_pst = format_pst_timestamp(dt)
                except:
                    updated_at_pst = updated_at  # Fallback to original
            else:
                updated_at_pst = 'N/A'
            
            # Insert with status tag for color coding
            self.tasks_tree.insert('', 'end', values=(
                updated_at_pst,
                task.get('workflow_id', 'N/A'),
                task_id,
                task.get('agent', ''),
                status,
                task.get('description', '')
            ), tags=(status,))
    
    def refresh_metrics_loop(self):
        """Background loop to refresh metrics"""
        while self.running:
            try:
                metrics = self.client.get_system_metrics()
                self.root.after(0, self.update_metrics_ui, metrics)
            except Exception as e:
                logger.error(f"Error refreshing metrics: {e}")
            time.sleep(METRICS_REFRESH_INTERVAL)
    
    def update_metrics_ui(self, metrics):
        """Update metrics UI with new data"""
        # Hide loading indicator
        if hasattr(self, 'metrics_loading'):
            self.metrics_loading.place_forget()
        
        total = metrics.get('tasks_24h', 0)
        completed = metrics.get('tasks_completed_24h', 0)
        failed = metrics.get('tasks_failed_24h', 0)
        workflows = metrics.get('workflows_24h', 0)
        
        success_rate = (completed / total * 100) if total > 0 else 0
        
        self.metric_cards['total_tasks'].value_label.config(text=str(total))
        self.metric_cards['completed_tasks'].value_label.config(text=str(completed))
        self.metric_cards['failed_tasks'].value_label.config(text=str(failed))
        self.metric_cards['workflows'].value_label.config(text=str(workflows))
        self.metric_cards['success_rate'].value_label.config(text=f"{success_rate:.1f}%")
    
    def refresh_system_status_loop(self):
        """Background loop to refresh system status"""
        while self.running:
            try:
                # Check server health
                health = self.client.check_health()
                server_color = COLORS['healthy'] if health['status'] == 'healthy' else COLORS['unhealthy']
                self.root.after(0, lambda: self.server_status.config(fg=server_color))
                
                # Check database
                db_status = self.client.get_database_status()
                db_color = COLORS['healthy'] if db_status['status'] == 'connected' else COLORS['unhealthy']
                self.root.after(0, lambda: self.db_status.config(fg=db_color))
                
                # Check Redis
                redis_status = self.client.get_redis_status()
                redis_color = COLORS['healthy'] if redis_status['status'] == 'connected' else COLORS['unhealthy']
                self.root.after(0, lambda: self.redis_status.config(fg=redis_color))
                
            except Exception as e:
                logger.error(f"Error refreshing system status: {e}")
            time.sleep(METRICS_REFRESH_INTERVAL)
    
    def update_time_loop(self):
        """Background loop to update time"""
        while self.running:
            current_time = (datetime.now(timezone.utc) - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S PST')
            self.root.after(0, lambda: self.time_label.config(text=current_time))
            time.sleep(1)
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        logger.info("Shutting down dashboard...")
        time.sleep(0.5)  # Give threads time to finish
        self.root.destroy()
    
    def load_persisted_state(self):
        """Load last project name and description from file"""
        try:
            if os.path.exists(PERSISTENCE_FILE):
                with open(PERSISTENCE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.last_project_name = state.get('project_name', '')
                    self.last_project_desc = state.get('project_desc', '')
                    logger.info("Loaded persisted state")
        except Exception as e:
            logger.warning(f"Could not load persisted state: {e}")
    
    def save_persisted_state(self):
        """Save current project name and description to file"""
        try:
            state = {
                'project_name': self.project_name_entry.get().strip(),
                'project_desc': self.project_desc_text.get('1.0', tk.END).strip()
            }
            with open(PERSISTENCE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            logger.debug("Saved persisted state")
        except Exception as e:
            logger.warning(f"Could not save persisted state: {e}")
    
    def clear_prompt(self):
        """Clear the prompt input fields"""
        self.project_name_entry.delete(0, tk.END)
        self.project_desc_text.delete('1.0', tk.END)
        self.prompt_status.config(text="")
    
    def manual_refresh_projects(self):
        """Manually trigger projects refresh"""
        try:
            projects = self.client.get_projects()
            self.update_projects_ui(projects)
            logger.debug("Manual projects refresh triggered")
        except Exception as e:
            logger.error(f"Error in manual projects refresh: {e}")
    
    def manual_refresh_workflows(self):
        """Manually trigger workflows refresh"""
        try:
            workflows = self.client.get_active_workflows()
            self.update_workflows_ui(workflows)
            logger.debug("Manual workflows refresh triggered")
        except Exception as e:
            logger.error(f"Error in manual workflows refresh: {e}")
    
    def submit_workflow(self):
        """Generate script and submit workflow"""
        import subprocess
        import os
        from datetime import datetime
        
        # Get input values
        project_name = self.project_name_entry.get().strip()
        description = self.project_desc_text.get('1.0', tk.END).strip()
        fast_mode = self.fast_mode_var.get()
        
        # Validate input
        if not project_name:
            self.prompt_status.config(text="[ERROR] Project name is required", fg=COLORS['error'])
            return
        
        if not description:
            self.prompt_status.config(text="[ERROR] Project description is required", fg=COLORS['error'])
            return
        
        # Update status
        self.prompt_status.config(text="[PROCESSING] Generating script and submitting workflow...", fg=COLORS['text_secondary'])
        self.root.update()
        
        try:
            # Generate timestamp for unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            script_name = f"submit_{project_name.lower().replace(' ', '_')}_{timestamp}.py"
            script_path = os.path.join('projects', 'submission', script_name)
            
            # Generate script content
            script_content = f'''"""
Auto-generated workflow submission script
Project: {project_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
import requests
import os
from datetime import datetime

# Configuration
SERVER_URL = "http://localhost:8001"
API_KEY = "am_server_30j_MNJFG086I8kh2fdsAU_aA7ggR4OTv5iR-tYcuyQ"

# Project details
PROJECT_NAME = "{project_name}"
USER_REQUEST = """{description}"""
FAST_MODE = {str(fast_mode)}

def submit_workflow():
    """Submit workflow to AgentManager"""
    
    headers = {{
        "Authorization": f"Bearer {{API_KEY}}",
        "Content-Type": "application/json"
    }}
    
    payload = {{
        "user_request": USER_REQUEST,
        "project_name": PROJECT_NAME,
        "fast_mode": FAST_MODE
    }}
    
    print(">> Submitting Workflow to AgentManager")
    print("=" * 70)
    print(f"Project: {{PROJECT_NAME}}")
    print(f"Server: {{SERVER_URL}}")
    print("=" * 70)
    
    try:
        response = requests.post(
            f"{{SERVER_URL}}/v1/tasks",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 201:
            result = response.json()
            print("\\n[SUCCESS] Workflow Submitted Successfully!")
            print(f"\\nWorkflow ID: {{result.get('workflow_id', 'N/A')}}")
            print(f"Status: {{result.get('status', 'N/A')}}")
            return result
        else:
            print(f"\\n[ERROR] Status Code: {{response.status_code}}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"\\n[ERROR] Exception: {{str(e)}}")
        return None

if __name__ == "__main__":
    submit_workflow()
'''
            
            # Write script to file
            os.makedirs(os.path.join('projects', 'submission'), exist_ok=True)
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Execute the script
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Save state before clearing
                self.save_persisted_state()
                
                self.prompt_status.config(
                    text=f"[SUCCESS] Workflow submitted! Script: {script_path}",
                    fg=COLORS['success']
                )
                logger.info(f"Workflow submitted via script: {script_path}")
                
                # Trigger immediate refresh of projects and workflows
                self.root.after(500, self.manual_refresh_projects)
                self.root.after(500, self.manual_refresh_workflows)
                
                # Clear inputs after successful submission
                self.root.after(2000, self.clear_prompt)
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.prompt_status.config(
                    text=f"[ERROR] Submission failed: {error_msg[:100]}",
                    fg=COLORS['error']
                )
                logger.error(f"Workflow submission failed: {error_msg}")
                
        except Exception as e:
            self.prompt_status.config(
                text=f"[ERROR] {str(e)[:100]}",
                fg=COLORS['error']
            )
            logger.error(f"Error submitting workflow: {e}")


def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Configure ttk style for dark theme
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configure treeview colors
    style.configure('Treeview',
                    background=COLORS['bg_medium'],
                    foreground=COLORS['text_primary'],
                    fieldbackground=COLORS['bg_medium'],
                    borderwidth=0)
    style.configure('Treeview.Heading',
                    background=COLORS['bg_light'],
                    foreground=COLORS['text_primary'],
                    borderwidth=1)
    style.map('Treeview', background=[('selected', COLORS['accent_blue'])])
    
    app = AgentManagerDashboard(root)
    logger.info("Dashboard started successfully")
    root.mainloop()


if __name__ == "__main__":
    main()

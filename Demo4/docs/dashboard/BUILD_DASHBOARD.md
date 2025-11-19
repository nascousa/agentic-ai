# Building AgentManager Dashboard to EXE

This guide explains how to build the AgentManager Dashboard into a standalone Windows executable.

## Quick Build (Recommended)

### Option 1: Using Batch Script
```bash
# Run the automated build script
.\build_dashboard.bat
```

This will:
1. Check Python installation
2. Install PyInstaller and dependencies
3. Build the executable
4. Output to `dist/AgentManagerDashboard.exe`

### Option 2: Using Python Script
```bash
# Run the Python build script
python build_dashboard.py
```

## Manual Build

If you prefer to build manually:

### 1. Install PyInstaller
```bash
pip install pyinstaller
```

### 2. Install Dependencies
```bash
pip install -r app/requirements.txt
```

### 3. Build Executable
```bash
pyinstaller --name="AgentManagerDashboard" \
    --onefile \
    --windowed \
    --add-data="app;app" \
    --hidden-import=tkinter \
    --hidden-import=tkinter.ttk \
    --hidden-import=PIL \
    --hidden-import=PIL._tkinter_finder \
    --hidden-import=requests \
    --clean \
    run_dashboard.py
```

## Build Options Explained

- `--onefile`: Package everything into a single executable
- `--windowed`: No console window (GUI only)
- `--add-data="app;app"`: Include the app folder with Python modules
- `--hidden-import`: Explicitly include required modules
- `--clean`: Clean PyInstaller cache before building
- `--name`: Set the executable name

## Output

After successful build:
```
dist/
└── AgentManagerDashboard.exe  (Standalone executable ~20-40MB)
```

## Running the Executable

### Requirements
- Windows OS
- Docker Desktop running
- AgentManager containers active

### Launch
```bash
# Double-click or run from terminal
.\dist\AgentManagerDashboard.exe
```

## Distribution

The generated `.exe` file is standalone and can be distributed to other Windows machines. Recipients need:
1. Docker Desktop installed and running
2. AgentManager containers running
3. Network access to localhost:8001

## Troubleshooting

### Build Errors

**"PyInstaller not found"**
```bash
pip install pyinstaller
```

**"Module not found during build"**
Add the module to `--hidden-import` list

**"tkinter import error"**
Ensure Python includes tkinter (should be built-in on Windows)

### Runtime Errors

**"Failed to connect to server"**
- Ensure Docker containers are running
- Check server is accessible at http://localhost:8001
- Run: `docker-compose ps` to verify

**"Missing DLL errors"**
- Rebuild with `--onefile` option
- Install Visual C++ Redistributable

**"Slow startup"**
- First run may be slow due to unpacking
- Subsequent runs will be faster

## Advanced Options

### Add Icon
```bash
pyinstaller --icon=app_icon.ico ...
```

### Console Mode (for debugging)
Remove `--windowed` flag to see console output

### Smaller Executable
```bash
# Use --onedir instead of --onefile
pyinstaller --onedir ...
# Creates dist/AgentManagerDashboard/ folder with executable
```

### Custom Spec File
After first build, edit `dashboard.spec` for advanced customization:
```python
# dashboard.spec
a = Analysis(
    ['run_dashboard.py'],
    datas=[('app', 'app')],
    hiddenimports=['tkinter', 'requests', 'PIL'],
    # ... more options
)
```

Then build with:
```bash
pyinstaller dashboard.spec
```

## Build Time

Expected build times:
- First build: 2-5 minutes
- Subsequent builds: 1-3 minutes

## File Sizes

Typical executable sizes:
- `--onefile`: 25-40 MB (single .exe)
- `--onedir`: 40-60 MB (folder with dependencies)

## CI/CD Integration

For automated builds, use:
```bash
# In CI pipeline
python build_dashboard.py
# Upload dist/AgentManagerDashboard.exe as artifact
```

## Notes

- The executable includes all Python dependencies
- No Python installation needed on target machine
- Config can be edited by modifying `app/config.py` before build
- For updates, rebuild the executable with new code

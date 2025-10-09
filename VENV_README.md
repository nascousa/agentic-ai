# AgentManager Virtual Environment

This project uses a Python virtual environment to manage dependencies and ensure consistent development experience.

## Quick Start

### Windows (PowerShell)
```powershell
# Activate virtual environment
.\activate.ps1

# Or manually:
.\.venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)
```cmd
# Activate virtual environment
activate.bat

# Or manually:
.venv\Scripts\activate.bat
```

## Virtual Environment Status

✅ **Virtual Environment Created**: `.venv/` directory
✅ **Dependencies Installed**: All packages from `pyproject.toml`
✅ **Project Installed**: AgentManager installed in editable mode
✅ **Development Tools**: pytest, black, mypy, flake8, isort

## Package List

**Production Dependencies:**
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- sqlalchemy[asyncio]>=2.0.0
- pydantic>=2.4.0
- openai>=1.3.0
- python-dotenv>=1.0.0
- psycopg2-binary>=2.9.0
- aiosqlite>=0.19.0
- httpx>=0.25.0
- python-multipart>=0.0.6

**Development Dependencies:**
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- black>=23.0.0
- isort>=5.12.0
- mypy>=1.5.0
- flake8>=6.0.0
- pre-commit>=3.4.0

## Common Commands

```bash
# Run tests
pytest tests/ -v

# Start development server
uvicorn agent_manager.api.main:app --reload

# Format code
black agent_manager/
isort agent_manager/

# Type checking
mypy agent_manager/

# Install new package
pip install <package-name>

# Update requirements
pip freeze > requirements.txt
```

## Environment Information

- **Python Version**: 3.13.7
- **Environment Type**: Virtual Environment
- **Location**: `D:/Repos/AgentManager/.venv/`
- **Python Executable**: `D:/Repos/AgentManager/.venv/Scripts/python.exe`

## Verification

To verify the virtual environment is working:

```python
import sys
print("Python executable:", sys.executable)
print("Virtual env active:", hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))
```

Expected output:
```
Python executable: D:\Repos\AgentManager\.venv\Scripts\python.exe
Virtual env active: True
```
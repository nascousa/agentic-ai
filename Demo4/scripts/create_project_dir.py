"""
Create Project Directory Script

Creates a project directory under projects/<today's date>/<project_name>
Automatically handles name conflicts by appending numbers (e.g., project_1, project_2)

Usage:
    python scripts/create_project_dir.py <project_name>
    python scripts/create_project_dir.py "My Calculator App"
"""

import sys
from pathlib import Path
from datetime import datetime


def create_project_directory(project_name: str, base_path: Path = None) -> Path:
    """
    Create a project directory with automatic conflict resolution.
    
    Args:
        project_name: Name of the project
        base_path: Base path for projects (defaults to ./projects)
        
    Returns:
        Path to the created project directory
    """
    if base_path is None:
        base_path = Path(__file__).parent.parent / "projects"
    
    # Get today's date in YYYY-MM-DD format
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = base_path / today
    
    # Create date directory if it doesn't exist
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize project name (replace spaces with underscores, remove special chars)
    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in project_name)
    safe_name = safe_name.strip('_')
    
    # Check if directory exists, if so, append number
    project_dir = date_dir / safe_name
    
    if not project_dir.exists():
        # Directory doesn't exist, create it
        project_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created project directory: {project_dir}")
        return project_dir
    
    # Directory exists, find next available number
    counter = 1
    while True:
        numbered_name = f"{safe_name}_{counter}"
        project_dir = date_dir / numbered_name
        
        if not project_dir.exists():
            project_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created project directory: {project_dir}")
            print(f"   (Original name '{safe_name}' already exists)")
            return project_dir
        
        counter += 1
        
        # Safety check to avoid infinite loop
        if counter > 1000:
            raise ValueError(f"Too many projects with similar names (>{counter})")


def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/create_project_dir.py <project_name>")
        print("Example: python scripts/create_project_dir.py 'Calculator App'")
        sys.exit(1)
    
    project_name = " ".join(sys.argv[1:])
    
    try:
        project_dir = create_project_directory(project_name)
        print(f"\n📁 Project directory ready at:")
        print(f"   {project_dir.absolute()}")
        
        # Create a README.md in the project directory
        readme_path = project_dir / "README.md"
        readme_path.write_text(f"# {project_name}\n\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        print(f"\n📝 Created README.md")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Build AgentManager Dashboard to standalone Windows executable
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print("✅ PyInstaller is installed")
        return True
    except ImportError:
        print("❌ PyInstaller not found")
        print("📦 Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True

def create_spec_file():
    """Create PyInstaller spec file"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run_dashboard.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/config.py', 'app'),
        ('app/api_client.py', 'app'),
        ('app/dashboard.py', 'app'),
        ('app/timezone_utils.py', 'app'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'PIL',
        'PIL._tkinter_finder',
        'requests',
        'datetime',
        'threading',
        'subprocess',
        'json',
        'logging',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AgentManagerDashboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if you have one
)
"""
    
    with open('dashboard.spec', 'w') as f:
        f.write(spec_content)
    
    print("✅ Created dashboard.spec")

def build_executable():
    """Build the executable using PyInstaller"""
    print("\n" + "="*60)
    print("🔨 BUILDING AGENTMANAGER DASHBOARD EXECUTABLE")
    print("="*60 + "\n")
    
    # Check PyInstaller
    check_pyinstaller()
    
    # Create spec file
    create_spec_file()
    
    # Clean previous builds
    if os.path.exists('build'):
        print("🧹 Cleaning build directory...")
        shutil.rmtree('build')
    
    if os.path.exists('dist'):
        print("🧹 Cleaning dist directory...")
        shutil.rmtree('dist')
    
    # Build executable
    print("\n🔨 Building executable (this may take a few minutes)...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "dashboard.spec", "--clean"],
        check=False
    )
    
    if result.returncode == 0:
        print("\n" + "="*60)
        print("✅ BUILD SUCCESSFUL!")
        print("="*60)
        print(f"\n📦 Executable location: dist/AgentManagerDashboard.exe")
        print(f"   Size: {os.path.getsize('dist/AgentManagerDashboard.exe') / (1024*1024):.1f} MB")
        print("\n💡 Usage:")
        print("   1. Double-click dist/AgentManagerDashboard.exe to run")
        print("   2. Or run from terminal: .\\dist\\AgentManagerDashboard.exe")
        print("\n⚠️  Note: Make sure Docker containers are running before launching")
        print("="*60)
        return True
    else:
        print("\n❌ BUILD FAILED")
        print("Check the error messages above for details")
        return False

if __name__ == '__main__':
    try:
        success = build_executable()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

# -*- mode: python ; coding: utf-8 -*-

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

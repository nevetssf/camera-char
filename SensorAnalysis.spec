# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Sensor Analysis macOS app.

Build with:
    pyinstaller SensorAnalysis.spec --noconfirm --clean
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect plotly data files (templates, etc.) but NOT all 12K+ validator submodules
plotly_datas = collect_data_files('plotly')

# Collect exiftool Python package submodules
exiftool_hiddenimports = collect_submodules('exiftool')

# ExifTool Perl binary paths
exiftool_bin = '/usr/local/bin/exiftool'
exiftool_lib = '/usr/local/bin/lib'

# Verify exiftool exists
if not os.path.exists(exiftool_bin):
    print(f"ERROR: ExifTool not found at {exiftool_bin}")
    print("Install with: brew install exiftool")
    sys.exit(1)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # ExifTool: Perl script + Perl library tree
        # Put in 'exiftool_perl/' to avoid name collision with Python exiftool package
        (exiftool_bin, 'exiftool_perl'),
        (exiftool_lib, 'exiftool_perl/lib'),
        # sensor_camera module (imported dynamically)
        ('sensor_camera.py', '.'),
    ] + plotly_datas,
    hiddenimports=[
        # Qt WebEngine (often missed)
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebChannel',
        # macOS integration
        'AppKit',
        'Foundation',
        # Raw image processing
        'rawpy',
        'rawpy._rawpy',
        # Scientific computing
        'scipy',
        'scipy.stats',
        # Matplotlib backend
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        # Plotly — full submodule collection needed (validators required at runtime)
        *collect_submodules('plotly'),
        # PyExifTool Python package
        *exiftool_hiddenimports,
        # Other dependencies
        'PIL',
        'tqdm',
        'pandas',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'cupy',
        'torch',
        'torchvision',
        'torchaudio',
        'jupyter',
        'notebook',
        'IPython',
        'jupyterlab',
        'nbconvert',
        'nbformat',
        'ipykernel',
        'ipywidgets',
        'pytest',
        'pydantic',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SensorAnalysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch='arm64',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='SensorAnalysis',
)

# Icon path (generate first with: python scripts/create_icns.py)
icon_path = 'resources/SensorAnalysis.icns'
if not os.path.exists(icon_path):
    icon_path = None
    print("WARNING: Icon not found at resources/SensorAnalysis.icns")
    print("Run: python scripts/create_icns.py")

app = BUNDLE(
    coll,
    name='Sensor Analysis.app',
    icon=icon_path,
    bundle_identifier='com.sensoranalysis.app',
    info_plist={
        'CFBundleName': 'Sensor Analysis',
        'CFBundleDisplayName': 'Sensor Analysis',
        'CFBundleShortVersionString': '0.1',
        'CFBundleVersion': '0.1.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '12.0',
        'NSRequiresAquaSystemAppearance': False,
    },
)

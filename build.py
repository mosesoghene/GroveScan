#!/usr/bin/env python3
"""
Build script for GroveScan Application.

This script creates a Windows executable using PyInstaller and
optionally builds an installer using Inno Setup.
"""

import sys
import os
import shutil
import subprocess
import argparse
from pathlib import Path


def find_iscc():
    """Find the Inno Setup Compiler executable on Windows."""
    # First try using shutil.which (more reliable than subprocess on Windows)
    iscc_path = shutil.which('iscc')
    if iscc_path:
        print(f"Found iscc via shutil.which: {iscc_path}")
        return iscc_path

    # Try the exact path we know exists
    known_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if Path(known_path).exists():
        print(f"Found iscc at known location: {known_path}")
        return known_path

    # Try other common paths
    common_paths = [
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]

    for path in common_paths:
        if Path(path).exists():
            print(f"Found iscc at: {path}")
            return path

    return None


def test_iscc_executable(iscc_path):
    """Test if the ISCC executable works."""
    try:
        result = subprocess.run([iscc_path], capture_output=True, text=True, timeout=10)
        output_text = (result.stdout or '') + (result.stderr or '')

        if 'Inno Setup' in output_text and result.returncode == 1:
            print("✓ ISCC executable works correctly")
            return True
        else:
            print(f"✗ ISCC test failed - Return code: {result.returncode}")
            return False
    except Exception as e:
        print(f"✗ Error testing ISCC: {e}")
        return False


def run_command(cmd, check=True, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def clean_build_dirs():
    """Clean previous build directories."""
    dirs_to_clean = ['build', 'dist', '__pycache__']

    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)

    # Clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))


def check_dependencies():
    """Check if required tools are available."""
    missing = []

    # Check PyInstaller
    try:
        result = subprocess.run(['pyinstaller', '--version'], capture_output=True, check=True, timeout=10)
        print("✓ Found pyinstaller")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("✗ Missing pyinstaller")
        missing.append("pyinstaller: PyInstaller (pip install pyinstaller)")

    # Check ISCC (Inno Setup Compiler) - Windows-specific approach
    iscc_path = find_iscc()
    if iscc_path and test_iscc_executable(iscc_path):
        print("✓ Found and verified ISCC")
        # Store the path for later use
        globals()['ISCC_PATH'] = iscc_path
    else:
        print("✗ ISCC not found or not working")
        missing.append("iscc: Inno Setup Compiler (Download from https://jrsoftware.org/isinfo.php)")

    return missing


def create_spec_file():
    """Create PyInstaller spec file with custom configuration."""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Get the project root directory
project_root = Path.cwd()

block_cipher = None

# Define data files to include
datas = []

# Add assets if they exist
if (project_root / 'assets').exists():
    datas.append((str(project_root / 'assets'), 'assets'))

# Define hidden imports - be more specific about what we need
hiddenimports = [
    # PySide6 core
    'PySide6.QtCore',
    'PySide6.QtWidgets', 
    'PySide6.QtGui',

    # PIL/Pillow
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageTk',
    'PIL.ImageOps',

    # Standard library modules that might not be auto-detected
    'json',
    'tempfile', 
    'uuid',
    'datetime',
    'os',
    'sys',
    'pathlib',
    'threading',
    'queue',
    'gc',
    'platform',
    'subprocess',
    'shutil',
    'logging',
    'traceback',
    're',
    'time',
    'hashlib',
    'collections',
    'dataclasses',
    'enum',
    'typing',

    # Our application modules
    'src',
    'src.models',
    'src.views', 
    'src.controllers',
    'src.utils',
]

# Add optional dependencies if available
try:
    import pyinsane2
    hiddenimports.append('pyinsane2')
except ImportError:
    print("PyInsane2 not available - using mock scanner")

try:
    import reportlab
    hiddenimports.extend([
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.utils',
        'reportlab.lib.units'
    ])
except ImportError:
    print("ReportLab not available - PDF features will be limited")

try:
    import psutil
    hiddenimports.append('psutil')
except ImportError:
    print("PSUtil not available - performance monitoring disabled")

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'cv2',
        'sklearn',
        'tensorflow',
        'torch',
        'jupyter',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out excluded modules from binaries and data
excluded_keywords = ['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'cv2', 'sklearn']
a.binaries = [x for x in a.binaries if not any(exc in x[0].lower() for exc in excluded_keywords)]
a.datas = [x for x in a.datas if not any(exc in x[0].lower() for exc in excluded_keywords)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GroveScan',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windows app, not console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'assets' / 'icon.ico') if (project_root / 'assets' / 'icon.ico').exists() else None,
    version='version_info.txt'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GroveScan',
)
'''

    with open('GroveScan.spec', 'w') as f:
        f.write(spec_content.strip())


def create_version_info():
    """Create version info file for Windows executable."""
    version_info = '''
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'GroveScan Solutions'),
        StringStruct(u'FileDescription', u'GroveScan - Document Indexing System'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'GroveScan'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2024 Scanner Solutions'),
        StringStruct(u'OriginalFilename', u'GroveScan.exe'),
        StringStruct(u'ProductName', u'GroveScan'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

    with open('version_info.txt', 'w') as f:
        f.write(version_info.strip())


def build_executable(debug=False):
    """Build the executable using PyInstaller."""
    print("Building executable...")

    # Create spec file and version info
    create_spec_file()
    create_version_info()

    # Build command
    cmd = ['pyinstaller', 'GroveScan.spec']
    if not debug:
        cmd.extend(['--clean', '--noconfirm'])

    try:
        run_command(cmd)
        print("✓ Executable built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to build executable: {e}")
        return False


def create_default_settings():
    """Create default settings template."""
    settings_template = {
        "ui": {
            "window_geometry": [100, 100, 1400, 900],
            "window_maximized": False,
            "splitter_sizes": {
                "main_splitter": [350, 1050],
                "assignment_splitter": [400, 300, 300]
            },
            "current_tab": 0,
            "show_tooltips": True,
            "theme": "default",
            "font_size": 10
        },
        "scanner": {
            "default_resolution": 300,
            "default_color_mode": "Color",
            "default_format": "TIFF",
            "default_quality": 95,
            "auto_detect_devices": True,
            "device_timeout": 30
        },
        "export": {
            "default_output_dir": "",
            "remember_last_directory": True,
            "default_template": "High Quality PDF",
            "confirm_overwrite": True,
            "show_progress_details": True,
            "auto_cleanup_temp": True
        },
        "general": {
            "auto_save_profiles": True,
            "backup_profiles": True,
            "max_recent_profiles": 10,
            "startup_check_updates": False,
            "crash_reporting": True,
            "log_level": "INFO"
        },
        "advanced": {
            "memory_limit_mb": 512,
            "temp_directory": "",
            "max_undo_levels": 10,
            "enable_debug_mode": False,
            "parallel_export": True,
            "cache_thumbnails": True
        }
    }

    import json
    with open('default_settings.json', 'w', encoding='utf-8') as f:
        json.dump(settings_template, f, indent=4)

    print("✓ Created default settings template")


def create_readme():
    """Create a README file for distribution."""
    readme_content = '''GroveScan v1.0.0
=======================

A powerful document scanning and indexing application for organizing your scanned documents with custom metadata.

INSTALLATION
------------
Run the installer as Administrator to install to Program Files.

FIRST RUN
---------
1. Start the application
2. Create or load a scanning profile
3. Connect your scanner device (or use mock scanner for testing)
4. Scan your documents
5. Assign pages with index values
6. Export organized documents

FEATURES
--------
- Dynamic indexing with custom field structures
- Support for folder hierarchy and filename generation
- Batch document scanning with page assignment
- Multiple export formats (PDF, TIFF, PNG, JPEG)
- Advanced PDF generation with ReportLab
- Profile-based workflows for different document types
- Performance optimization for large document batches
- Comprehensive help system and tooltips

SCANNER SUPPORT
---------------
- Real scanner support via PyInsane2 (Windows Image Acquisition)
- Mock scanner for testing and development
- Auto-detection of connected devices
- Configurable resolution, color modes, and formats

SYSTEM REQUIREMENTS
-------------------
- Windows 10 version 1809 (build 17763) or later
- Scanner device with Windows drivers (optional - mock mode available)
- Administrative privileges for installation
- Minimum 4GB RAM (8GB recommended for large batches)
- 1GB free disk space

PROFILES AND DATA
-----------------
User data is stored in:
- Profiles: %USERPROFILE%\\Documents\\GroveScan\\Profiles
- Settings: %APPDATA%\\GroveScan\\settings.json
- Logs: %LOCALAPPDATA%\\GroveScan\\Logs
- Temp files: System temp directory (auto-cleaned)

PROFILE TEMPLATES
-----------------
The application includes quick-start templates for:
- Legal Documents (Client/Case/Document structure)
- Medical Records (Department/Year/Patient organization)
- Invoice Processing (Vendor/Year/Month filing)
- Archive Documents (Category/Year/Description)
- Custom profiles for any workflow

EXPORT TEMPLATES
----------------
Pre-configured export templates:
- High Quality PDF (ReportLab engine, professional output)
- Fast PDF (PIL engine, quick processing)
- Archive TIFF (multi-page, lossless compression)
- Web Images (PNG format for online use)
- Letter/A4 PDF (standard page sizes with margins)
- Email Friendly (compressed, timestamp-enabled)

TROUBLESHOOTING
---------------
Scanner Issues:
- Ensure scanner drivers are installed
- Check Windows Image Acquisition service is running
- Try refreshing device list
- Use mock scanner mode for testing without hardware

Performance:
- Reduce memory limit in Advanced settings for low-RAM systems
- Process smaller batches if experiencing memory issues
- Clear thumbnail cache if storage space is low
- Enable parallel export for faster processing

Export Problems:
- Check output directory permissions
- Ensure sufficient disk space
- Verify all pages are assigned before export
- Try different export templates

KEYBOARD SHORTCUTS
------------------
- Ctrl+N: New Profile
- Ctrl+O: Load Profile
- Ctrl+S: Save Profile
- Ctrl+E: Export Documents
- Ctrl+Shift+S: Start Scanning
- F1: Help (context-sensitive)

SUPPORT
-------
For support, feature requests, or bug reports, please contact Scanner Solutions.

Copyright (C) 2024 GroveScan Solutions
'''

    with open('README.txt', 'w') as f:
        f.write(readme_content.strip())


def create_license():
    """Create a basic license file."""
    license_content = '''MIT License

Copyright (c) 2024 GroveScan Solutions

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

    with open('LICENSE.txt', 'w') as f:
        f.write(license_content.strip())


def create_assets_directory():
    """Create assets directory with placeholder icon if it doesn't exist."""
    assets_dir = Path('assets')
    assets_dir.mkdir(exist_ok=True)

    # Create a simple placeholder icon file info
    icon_info = assets_dir / 'icon_info.txt'
    if not icon_info.exists():
        with open(icon_info, 'w') as f:
            f.write("""Icon file information:

Place your application icon as 'icon.ico' in this directory.

The icon should be:
- ICO format with multiple sizes (16x16, 32x32, 48x48, 256x256)
- Windows-compatible format
- Professional appearance representing document scanning

If no icon.ico is provided, the application will use the default Windows icon.
""")
        print("✓ Created assets directory with icon instructions")


def build_installer():
    """Build the installer using Inno Setup."""
    print("Building installer...")

    # Use the stored ISCC path or find it again
    iscc_path = globals().get('ISCC_PATH') or find_iscc()

    if not iscc_path:
        print("✗ Inno Setup Compiler not found.")
        print("  Make sure Inno Setup is installed and ISCC.exe is accessible")
        return False

    # Create supporting files
    create_default_settings()
    create_readme()
    create_license()
    create_assets_directory()

    # Ensure installer directory exists
    os.makedirs('dist/installer', exist_ok=True)

    try:
        print(f"Using ISCC at: {iscc_path}")
        result = run_command([iscc_path, 'installer.iss'], check=False)

        if result.returncode == 0:
            print("✓ Installer built successfully!")

            # Find and report the installer location
            installer_files = list(Path('dist/installer').glob('*.exe'))
            if installer_files:
                print(f"✓ Installer created: {installer_files[0]}")

            return True
        else:
            print(f"✗ Inno Setup failed with return code: {result.returncode}")
            print("\nInno Setup error details:")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            print("\nPossible solutions:")
            print("1. Check that installer.iss syntax is correct")
            print("2. Verify all source files exist (dist/GroveScan/)")
            print("3. Check file paths in the [Files] section")
            print("4. Make sure LICENSE.txt and README.txt were created")

            return False

    except Exception as e:
        print(f"✗ Failed to run Inno Setup: {e}")
        return False


def main():
    """Main build function."""
    parser = argparse.ArgumentParser(description='Build GroveScan Application')
    parser.add_argument('--clean', action='store_true', help='Clean build directories first')
    parser.add_argument('--debug', action='store_true', help='Build in debug mode')
    parser.add_argument('--no-installer', action='store_true', help='Skip installer creation')
    parser.add_argument('--installer-only', action='store_true', help='Only build installer (skip executable)')

    args = parser.parse_args()

    # Change to script directory
    os.chdir(Path(__file__).parent)

    print("GroveScan Build Script")
    print("=" * 40)

    # Clean if requested
    if args.clean:
        clean_build_dirs()

    # Check dependencies
    missing_deps = check_dependencies()
    if len(missing_deps) > 0:
        print("✗ Missing required tools:")
        for dep in missing_deps:
            print(f"  - {dep}")
        return 1

    success = True

    # Build executable unless installer-only
    if not args.installer_only:
        success = build_executable(debug=args.debug)

    # Build installer if executable succeeded and not disabled
    if success and not args.no_installer:
        # Check if executable exists (either just built or from previous build)
        exe_path = Path('dist/GroveScan/GroveScan.exe')
        if exe_path.exists():
            success = build_installer()
        else:
            print("✗ Executable not found. Cannot build installer.")
            success = False

    print("\n" + "=" * 40)
    if success:
        print("✓ Build completed successfully!")

        # Show what was built
        if Path('dist/GroveScan/GroveScan.exe').exists():
            print(f"✓ Executable: dist/GroveScan/GroveScan.exe")

        installer_files = list(Path('dist/installer').glob('*.exe'))
        if installer_files:
            print(f"✓ Installer: {installer_files[0]}")
    else:
        print("✗ Build failed!")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
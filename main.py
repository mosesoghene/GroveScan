#!/usr/bin/env python3
"""
Dynamic Scanner Application Startup Script

This script initializes and runs the Dynamic Scanner application.
Make sure you have all dependencies installed:
- PySide6
- Pillow (PIL)
- PyInsane2 (for real scanner support)
"""

import sys
import os
from pathlib import Path
import platform

# Add src directory to Python path if running from project root
project_root = Path(__file__).parent
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(project_root))


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    optional_deps = []
    scanner_status = None

    print("Checking dependencies...")

    # Check PySide6
    try:
        import PySide6
        print(f"✓ PySide6 {PySide6.__version__} - GUI framework")
    except ImportError:
        missing_deps.append("PySide6")
        print("✗ PySide6 - GUI framework (REQUIRED)")

    # Check Pillow
    try:
        from PIL import Image
        import PIL
        print(f"✓ Pillow {PIL.__version__} - Image processing")
    except ImportError:
        missing_deps.append("Pillow")
        print("✗ Pillow - Image processing (REQUIRED)")

    # Check PyInsane2 (scanner support)
    try:
        import pyinsane2
        # Test initialization
        pyinsane2.init()
        devices = pyinsane2.get_devices()
        pyinsane2.exit()

        scanner_status = {
            'available': True,
            'backend': 'pyinsane2',
            'device_count': len(devices),
            'platform': platform.system()
        }

        print(f"✓ PyInsane2 - Scanner support ({len(devices)} devices found)")
        if devices:
            print("  Scanner devices detected:")
            for device_info in devices[:3]:  # Show first 3 devices
                device_id = device_info[0]
                device_name = device_info[1] if len(device_info) > 1 else device_id
                print(f"    - {device_name}")
            if len(devices) > 3:
                print(f"    ... and {len(devices) - 3} more devices")
        else:
            print("  No scanner devices found (but PyInsane2 is working)")

    except ImportError:
        scanner_status = {
            'available': False,
            'backend': 'mock',
            'reason': 'not_installed',
            'platform': platform.system()
        }
        print("⚠ PyInsane2 - Scanner support (NOT INSTALLED)")
        print("  App will use mock scanners for testing")
        print("  Install with: pip install pyinsane2")

    except Exception as e:
        scanner_status = {
            'available': False,
            'backend': 'mock',
            'reason': 'init_failed',
            'error': str(e),
            'platform': platform.system()
        }
        print(f"⚠ PyInsane2 - Scanner support (INITIALIZATION FAILED)")
        print(f"  Error: {e}")
        print("  App will use mock scanners for testing")

    # Check optional dependencies
    print("\nOptional dependencies:")

    # ReportLab for advanced PDF features
    try:
        import reportlab
        print(f"✓ ReportLab {reportlab.Version} - Advanced PDF generation")
    except ImportError:
        optional_deps.append("reportlab")
        print("- ReportLab - Advanced PDF features")

    # PSUtil for performance monitoring
    try:
        import psutil
        print(f"✓ PSUtil {psutil.__version__} - System monitoring")
    except ImportError:
        optional_deps.append("psutil")
        print("- PSUtil - Performance monitoring")

    # Pydantic for data validation
    try:
        import pydantic
        print(f"✓ Pydantic {pydantic.version.VERSION} - Data validation")
    except ImportError:
        optional_deps.append("pydantic")
        print("- Pydantic - Data validation")

    # Report missing dependencies
    if missing_deps:
        print(f"\n❌ Missing required dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print(f"\nInstall missing dependencies with:")
        print(f"   pip install {' '.join(missing_deps)}")
        return False

    if optional_deps:
        print(f"\n💡 Optional dependencies not found (features may be limited):")
        for dep in optional_deps:
            print(f"   - {dep}")
        print(f"\nInstall optional dependencies with:")
        print(f"   pip install {' '.join(optional_deps)}")

    # Platform-specific scanner setup info
    if not scanner_status['available']:
        print(f"\n📋 Scanner Setup for {platform.system()}:")
        if platform.system() == "Linux":
            print("   1. Install system packages:")
            print("      sudo apt-get install libsane-dev python3-dev  # Ubuntu/Debian")
            print("      sudo yum install sane-backends-devel python3-devel  # CentOS/RHEL")
            print("   2. Install PyInsane2:")
            print("      pip install pyinsane2")
            print("   3. Add user to scanner group:")
            print("      sudo usermod -a -G scanner $USER")
        elif platform.system() == "Windows":
            print("   1. Install PyInsane2:")
            print("      pip install pyinsane2")
            print("   2. Ensure scanner drivers are installed")
            print("   3. Check Windows Image Acquisition service is running")
        elif platform.system() == "Darwin":
            print("   1. Install SANE via Homebrew:")
            print("      brew install sane-backends")
            print("   2. Install PyInsane2:")
            print("      pip install pyinsane2")

    return True


def create_required_directories():
    """Create required directories if they don't exist"""
    directories = [
        "profiles",
        "temp",
        "exports",
        "export_templates"
    ]

    created_dirs = []
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            created_dirs.append(directory)

    if created_dirs:
        print(f"\nCreated directories: {', '.join(created_dirs)}")


def show_startup_info():
    """Show application startup information"""
    print("=" * 60)
    print("🔍 DYNAMIC SCANNER - Document Indexing System")
    print("=" * 60)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Working Directory: {os.getcwd()}")
    print()


def main():
    """Main application entry point"""
    show_startup_info()

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Cannot start application due to missing required dependencies.")
        input("Press Enter to exit...")
        sys.exit(1)

    print("\n" + "=" * 60)

    # Create required directories
    create_required_directories()

    # Import and run the application
    try:
        from PySide6.QtWidgets import QApplication
        from src.views.main_window import MainWindow

        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("Dynamic Scanner")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Scanner Solutions")
        app.setOrganizationDomain("scanner-solutions.local")

        # Set application style
        app.setStyle('Fusion')  # Use Fusion style for consistent look

        print("🚀 Starting Dynamic Scanner application...")

        # Create and show main window
        window = MainWindow()
        window.show()

        # Show scanner status in window title
        try:
            from src.models.scanner_interface import get_scanner_backend_info
            backend_info = get_scanner_backend_info()

            if backend_info['backend'] == 'pyinsane2':
                window.setWindowTitle("Dynamic Scanner - Real Scanner Support")
            else:
                window.setWindowTitle("Dynamic Scanner - Mock Scanner Mode")

        except Exception:
            pass

        print("✅ Application started successfully!")

        # Show usage hints
        if len(sys.argv) == 1:  # No command line args
            print("\n💡 Getting Started:")
            print("   1. Create or load a scanning profile")
            print("   2. Connect to your scanner device")
            print("   3. Scan your documents")
            print("   4. Assign pages to organize documents")
            print("   5. Export your organized files")
            print("\n   Press F1 in the application for detailed help")

        print("\n" + "=" * 60)

        # Run application event loop
        sys.exit(app.exec())

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure you're running from the project root directory")
        print("and all source files are in the 'src' directory.")
        input("Press Enter to exit...")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
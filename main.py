#!/usr/bin/env python3
"""
Dynamic Scanner Application Startup Script

This script initializes and runs the Dynamic Scanner application.
Make sure you have all dependencies installed:
- PySide6
- Pillow (PIL)
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path if running from project root
project_root = Path(__file__).parent
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(project_root))


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    optional_deps = []

    try:
        import PySide6
    except ImportError:
        missing_deps.append("PySide6")

    try:
        from PIL import Image
    except ImportError:
        missing_deps.append("Pillow")

    # Check optional dependencies
    try:
        import reportlab
    except ImportError:
        optional_deps.append("reportlab")

    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall missing dependencies with:")
        print(f"  pip install {' '.join(missing_deps)}")
        return False

    if optional_deps:
        print("Optional dependencies not found (advanced features may be limited):")
        for dep in optional_deps:
            print(f"  - {dep}")
        print("\nInstall optional dependencies with:")
        print(f"  pip install {' '.join(optional_deps)}")
        print("Note: ReportLab provides advanced PDF features\n")

    return True


def create_required_directories():
    """Create required directories if they don't exist"""
    directories = [
        "profiles",
        "temp",
        "exports"
    ]

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"Created directory: {directory}")


def main():
    """Main application entry point"""
    print("Starting Dynamic Scanner Application...")

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

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

        # Set application style
        app.setStyle('Fusion')  # Use Fusion style for consistent look

        # Create and show main window
        window = MainWindow()
        window.show()

        print("Application started successfully!")
        print("Create or load a profile to begin scanning documents.")

        # Run application event loop
        sys.exit(app.exec())

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running from the project root directory")
        print("and all source files are in the 'src' directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
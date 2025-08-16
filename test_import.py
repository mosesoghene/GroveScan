#!/usr/bin/env python3
"""
Test imports for Dynamic Scanner before building

This script tests that all required modules can be imported correctly
before attempting to build the executable.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(project_root))

def test_basic_imports():
    """Test basic Python imports"""
    print("Testing basic Python imports...")
    
    try:
        import json
        import os
        import sys
        import pathlib
        import tempfile
        import datetime
        import uuid
        import threading
        import queue
        import gc
        import platform
        import subprocess
        import shutil
        import logging
        import traceback
        import re
        import time
        print("✓ Basic Python modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import basic modules: {e}")
        return False

def test_required_imports():
    """Test required third-party imports"""
    print("Testing required third-party imports...")
    
    # Test PySide6
    try:
        from PySide6.QtWidgets import QApplication, QMainWindow
        from PySide6.QtCore import Qt, Signal, QObject
        from PySide6.QtGui import QFont, QColor
        print("✓ PySide6 imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import PySide6: {e}")
        print("  Install with: pip install PySide6")
        return False
    
    # Test PIL/Pillow
    try:
        from PIL import Image, ImageDraw, ImageTk, ImageOps
        print("✓ Pillow imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Pillow: {e}")
        print("  Install with: pip install Pillow")
        return False
    
    return True

def test_optional_imports():
    """Test optional imports"""
    print("Testing optional imports...")
    
    optional_modules = []
    
    # Test PyInsane2
    try:
        import pyinsane2
        print("✓ PyInsane2 available (real scanner support)")
        optional_modules.append("pyinsane2")
    except ImportError:
        print("⚠ PyInsane2 not available (will use mock scanner)")
    
    # Test ReportLab
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        print("✓ ReportLab available (advanced PDF features)")
        optional_modules.append("reportlab")
    except ImportError:
        print("⚠ ReportLab not available (basic PDF only)")
    
    # Test PSUtil
    try:
        import psutil
        print("✓ PSUtil available (performance monitoring)")
        optional_modules.append("psutil")
    except ImportError:
        print("⚠ PSUtil not available (no performance monitoring)")
    
    return optional_modules

def test_application_imports():
    """Test application-specific imports"""
    print("Testing application imports...")
    
    try:
        # Test main application structure
        import src
        print("✓ src package imported")
        
        # Test models
        from src.models import ScanProfile, ScannedPage, DocumentBatch
        from src.models.dynamic_index_schema import DynamicIndexSchema
        from src.models.index_field import IndexField, IndexFieldType
        print("✓ Models imported")
        
        # Test controllers
        from src.controllers.app_controller import ApplicationController
        print("✓ Controllers imported")
        
        # Test views
        from src.views.main_window import MainWindow
        print("✓ Views imported")
        
        # Test utils
        from src.utils.settings_manager import SettingsManager
        from src.utils.error_handling import ErrorHandler
        print("✓ Utils imported")
        
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import application modules: {e}")
        print("Make sure you're running from the project root directory")
        return False

def test_main_module():
    """Test that main.py can be imported without running"""
    print("Testing main.py import...")
    
    try:
        # Add main.py directory to path if needed
        main_path = project_root / "main.py"
        if not main_path.exists():
            print("✗ main.py not found in project root")
            return False
        
        # Try to compile the main.py file
        with open(main_path, 'r') as f:
            source_code = f.read()
        
        try:
            compile(source_code, 'main.py', 'exec')
            print("✓ main.py compiles successfully")
            return True
        except SyntaxError as e:
            print(f"✗ Syntax error in main.py: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing main.py: {e}")
        return False

def main():
    """Main test function"""
    print("Dynamic Scanner - Import Test")
    print("=" * 40)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    all_passed = True
    
    # Run all tests
    all_passed &= test_basic_imports()
    print()
    
    all_passed &= test_required_imports()
    print()
    
    optional_modules = test_optional_imports()
    print()
    
    all_passed &= test_application_imports()
    print()
    
    all_passed &= test_main_module()
    
    print("\n" + "=" * 40)
    
    if all_passed:
        print("✓ All required imports successful!")
        print("You should be able to build the application.")
        
        if optional_modules:
            print(f"\nOptional features available: {', '.join(optional_modules)}")
        
        print("\nNext steps:")
        print("1. Run: python build.py --clean")
        print("2. If build fails, try: python build.py --debug")
        
        return 0
    else:
        print("✗ Some imports failed!")
        print("\nPlease fix the import issues before building.")
        print("Common fixes:")
        print("- Install missing packages with pip")
        print("- Check that you're in the correct directory")
        print("- Verify your Python environment is activated")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())

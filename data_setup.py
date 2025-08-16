#!/usr/bin/env python3
"""
Application Data Setup for Dynamic Scanner

This script sets up the proper user data directories and initial configuration
for the Dynamic Scanner application on first run.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime


def setup_user_data_directories():
    """Set up all required user data directories"""
    
    app_name = "Dynamic Scanner"
    
    # Define directory paths based on platform
    if os.name == 'nt':  # Windows
        documents_base = Path.home() / "Documents" / app_name
        appdata_base = Path(os.environ.get('APPDATA', Path.home() / "AppData" / "Roaming")) / app_name
        localappdata_base = Path(os.environ.get('LOCALAPPDATA', Path.home() / "AppData" / "Local")) / app_name
    else:  # Linux/Mac
        documents_base = Path.home() / f".{app_name.lower().replace(' ', '_')}"
        appdata_base = Path.home() / f".config" / app_name.lower().replace(" ", "_")
        localappdata_base = Path.home() / f".cache" / app_name.lower().replace(" ", "_")
    
    # Directory structure
    directories = {
        'profiles': documents_base / "Profiles",
        'export_templates': documents_base / "Export Templates",
        'settings': appdata_base,
        'logs': localappdata_base / "Logs",
        'temp': localappdata_base / "Temp"
    }
    
    print(f"Setting up user data directories for {app_name}...")
    
    # Create all directories
    for dir_name, dir_path in directories.items():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created {dir_name}: {dir_path}")
        except Exception as e:
            print(f"✗ Failed to create {dir_name}: {e}")
    
    return directories


def create_default_settings(settings_dir: Path):
    """Create default settings file"""
    
    default_settings = {
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
            "default_output_dir": str(Path.home() / "Documents" / "Scanner Exports"),
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
    
    settings_file = settings_dir / "settings.json"
    
    try:
        if not settings_file.exists():
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, indent=2, ensure_ascii=False)
            print(f"✓ Created default settings: {settings_file}")
        else:
            print(f"⚠ Settings file already exists: {settings_file}")
    except Exception as e:
        print(f"✗ Failed to create settings file: {e}")


def create_readme_files(directories: dict):
    """Create README files in user directories"""
    
    # Profiles README
    profiles_readme = directories['profiles'] / "README.txt"
    profiles_content = f"""Dynamic Scanner Profiles
========================

This folder contains your scanning profiles.
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

What are profiles?
Profiles define how your scanned documents will be organized:
- Index fields (what information to track)
- Folder structure (how to organize files)
- Filename patterns (how to name documents)
- Scanner settings (resolution, color mode, etc.)
- Export preferences (PDF quality, compression, etc.)

Getting started:
1. Launch Dynamic Scanner
2. Create a new profile or use a quick template
3. Define your index fields (Client, Date, Document Type, etc.)
4. Start scanning and organizing your documents

Profile files are saved as JSON and can be:
- Shared between computers
- Backed up safely
- Imported/exported for collaboration

For help, press F1 in the application or visit the Help menu.
"""
    
    # Export Templates README
    templates_readme = directories['export_templates'] / "README.txt"
    templates_content = f"""Dynamic Scanner Export Templates
================================

This folder contains your custom export templates.
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

What are export templates?
Templates define how your scanned documents are saved:
- Output format (PDF, TIFF, PNG, JPEG)
- Quality settings and compression
- Page sizing and margins
- File naming options
- Folder creation preferences

Built-in templates include:
- High Quality PDF (ReportLab engine, professional output)
- Fast PDF (PIL engine, quick processing)
- Archive TIFF (multi-page, lossless compression)
- Web Images (PNG format for online use)
- Letter/A4 PDF (standard page sizes with margins)
- Email Friendly (compressed, timestamp-enabled)

You can:
- Create custom templates in the application
- Import/export templates as JSON files
- Modify existing templates to suit your needs

Templates are automatically saved here when you create them.
"""
    
    # Create README files
    try:
        if not profiles_readme.exists():
            with open(profiles_readme, 'w', encoding='utf-8') as f:
                f.write(profiles_content)
            print(f"✓ Created profiles README: {profiles_readme}")
            
        if not templates_readme.exists():
            with open(templates_readme, 'w', encoding='utf-8') as f:
                f.write(templates_content)
            print(f"✓ Created templates README: {templates_readme}")
            
    except Exception as e:
        print(f"✗ Failed to create README files: {e}")


def create_sample_profile(profiles_dir: Path):
    """Create a sample profile to help users get started"""
    
    sample_profile = {
        "name": "Legal Documents Sample",
        "description": "Sample profile for organizing legal documents by client and case type",
        "schema": {
            "fields": [
                {
                    "name": "Client",
                    "field_type": "folder",
                    "order": 0,
                    "default_value": "",
                    "is_required": True,
                    "validation_rules": {
                        "pattern": None,
                        "allowed_values": None,
                        "min_length": 1,
                        "max_length": 50,
                        "required": True
                    }
                },
                {
                    "name": "Case Type",
                    "field_type": "folder",
                    "order": 1,
                    "default_value": "",
                    "is_required": True,
                    "validation_rules": {
                        "pattern": None,
                        "allowed_values": ["Contract", "Divorce", "Real Estate", "Personal Injury", "Other"],
                        "min_length": None,
                        "max_length": None,
                        "required": True
                    }
                },
                {
                    "name": "Document Type",
                    "field_type": "filename",
                    "order": 2,
                    "default_value": "",
                    "is_required": True,
                    "validation_rules": {
                        "pattern": None,
                        "allowed_values": None,
                        "min_length": 1,
                        "max_length": 30,
                        "required": True
                    }
                },
                {
                    "name": "Date",
                    "field_type": "filename",
                    "order": 3,
                    "default_value": "",
                    "is_required": False,
                    "validation_rules": {
                        "pattern": "\\d{4}-\\d{2}-\\d{2}",
                        "allowed_values": None,
                        "min_length": None,
                        "max_length": None,
                        "required": False
                    }
                }
            ],
            "separator": "_"
        },
        "filled_values": {},
        "scanner_settings": {
            "device_name": "",
            "resolution": 300,
            "color_mode": "Color",
            "format": "TIFF",
            "quality": 95
        },
        "export_settings": {
            "output_format": "PDF",
            "pdf_quality": 95,
            "create_folders": True,
            "overwrite_existing": False
        },
        "created_date": datetime.now().isoformat(),
        "modified_date": datetime.now().isoformat()
    }
    
    sample_file = profiles_dir / "Legal_Documents_Sample.json"
    
    try:
        if not sample_file.exists():
            with open(sample_file, 'w', encoding='utf-8') as f:
                json.dump(sample_profile, f, indent=2, ensure_ascii=False)
            print(f"✓ Created sample profile: {sample_file}")
        else:
            print(f"⚠ Sample profile already exists: {sample_file}")
    except Exception as e:
        print(f"✗ Failed to create sample profile: {e}")


def setup_application_shortcuts():
    """Set up application shortcuts and associations (Windows only)"""
    if os.name != 'nt':
        return
    
    try:
        # This would be handled by the installer
        # Just print info for now
        print("ℹ Application shortcuts will be created by installer")
        print("  - Start Menu shortcut")
        print("  - Desktop shortcut (optional)")
        print("  - File associations for .dsprofile files")
    except Exception as e:
        print(f"✗ Error setting up shortcuts: {e}")


def main():
    """Main setup function"""
    print("Dynamic Scanner - Application Data Setup")
    print("=" * 45)
    
    # Set up directories
    directories = setup_user_data_directories()
    
    print("\n" + "=" * 45)
    
    # Create configuration files
    create_default_settings(directories['settings'])
    create_readme_files(directories)
    create_sample_profile(directories['profiles'])
    
    # Platform-specific setup
    setup_application_shortcuts()
    
    print("\n" + "=" * 45)
    print("Setup completed successfully!")
    
    print(f"\nYour Dynamic Scanner data is stored in:")
    print(f"📁 Profiles: {directories['profiles']}")
    print(f"📁 Settings: {directories['settings']}")
    print(f"📁 Export Templates: {directories['export_templates']}")
    print(f"📁 Logs: {directories['logs']}")
    
    print(f"\nNext steps:")
    print("1. Launch Dynamic Scanner")
    print("2. Try the sample Legal Documents profile")
    print("3. Create your own profiles for your workflow")
    print("4. Start scanning and organizing documents")
    
    return directories


if __name__ == "__main__":
    main()

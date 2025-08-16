import json
import os
from typing import Any, Dict, Optional
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QSettings, QStandardPaths
from PySide6.QtWidgets import QApplication
from dataclasses import dataclass, asdict
from enum import Enum
import platform


class SettingsCategory(Enum):
    GENERAL = "general"
    UI = "ui"
    SCANNER = "scanner"
    EXPORT = "export"
    ADVANCED = "advanced"


@dataclass
class UISettings:
    window_geometry: tuple = (100, 100, 1400, 900)  # x, y, width, height
    window_maximized: bool = False
    splitter_sizes: Dict[str, list] = None
    current_tab: int = 0
    show_tooltips: bool = True
    theme: str = "default"  # default, dark, light
    font_size: int = 10

    def __post_init__(self):
        if self.splitter_sizes is None:
            self.splitter_sizes = {
                'main_splitter': [350, 1050],
                'assignment_splitter': [400, 300, 300]
            }


@dataclass
class ScannerSettings:
    default_resolution: int = 300
    default_color_mode: str = "Color"
    default_format: str = "TIFF"
    default_quality: int = 95
    auto_detect_devices: bool = True
    device_timeout: int = 30


@dataclass
class ExportSettings:
    default_output_dir: str = ""
    remember_last_directory: bool = True
    default_template: str = "High Quality PDF"
    confirm_overwrite: bool = True
    show_progress_details: bool = True
    auto_cleanup_temp: bool = True


@dataclass
class GeneralSettings:
    auto_save_profiles: bool = True
    backup_profiles: bool = True
    max_recent_profiles: int = 10
    startup_check_updates: bool = False
    crash_reporting: bool = True
    log_level: str = "INFO"


@dataclass
class AdvancedSettings:
    memory_limit_mb: int = 512
    temp_directory: str = ""
    max_undo_levels: int = 10
    enable_debug_mode: bool = False
    parallel_export: bool = True
    cache_thumbnails: bool = True


class UserDataManager:
    """Manages user data directory paths for the application"""

    def __init__(self):
        self.app_name = "Dynamic Scanner"
        self._init_directories()

    def _init_directories(self):
        """Initialize and create necessary user directories"""
        # Create all required directories
        directories = [
            self.get_profiles_dir(),
            self.get_settings_dir(),
            self.get_logs_dir(),
            self.get_export_templates_dir(),
            self.get_temp_dir()
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_profiles_dir(self) -> Path:
        """Get the profiles directory in user's Documents"""
        if platform.system() == "Windows":
            documents_path = Path.home() / "Documents" / self.app_name / "Profiles"
        else:
            # For Linux/Mac, use a dot directory in home
            documents_path = Path.home() / f".{self.app_name.lower().replace(' ', '_')}" / "profiles"

        return documents_path

    def get_settings_dir(self) -> Path:
        """Get the settings directory in AppData/Roaming"""
        if platform.system() == "Windows":
            return Path(os.environ.get('APPDATA', Path.home() / "AppData" / "Roaming")) / self.app_name
        else:
            return Path.home() / f".config" / self.app_name.lower().replace(" ", "_")

    def get_logs_dir(self) -> Path:
        """Get the logs directory in LocalAppData"""
        if platform.system() == "Windows":
            return Path(os.environ.get('LOCALAPPDATA', Path.home() / "AppData" / "Local")) / self.app_name / "Logs"
        else:
            return Path.home() / f".cache" / self.app_name.lower().replace(" ", "_") / "logs"

    def get_export_templates_dir(self) -> Path:
        """Get the export templates directory in user's Documents"""
        if platform.system() == "Windows":
            return Path.home() / "Documents" / self.app_name / "Export Templates"
        else:
            return Path.home() / f".{self.app_name.lower().replace(' ', '_')}" / "export_templates"

    def get_temp_dir(self) -> Path:
        """Get the temporary files directory"""
        import tempfile
        return Path(tempfile.gettempdir()) / f"{self.app_name.replace(' ', '_')}_temp"

    def get_settings_file(self) -> Path:
        """Get the main settings file path"""
        return self.get_settings_dir() / "settings.json"

    def get_recent_files_file(self) -> Path:
        """Get the recent files list path"""
        return self.get_settings_dir() / "recent_files.json"

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        temp_dir = self.get_temp_dir()
        if temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(temp_dir)
                temp_dir.mkdir(parents=True, exist_ok=True)
                print(f"Cleaned temporary directory: {temp_dir}")
            except Exception as e:
                print(f"Warning: Could not clean temp directory: {e}")

    def get_data_usage_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about data usage in user directories"""

        def get_dir_info(path: Path) -> Dict[str, Any]:
            if not path.exists():
                return {"exists": False, "size_mb": 0, "file_count": 0}

            total_size = 0
            file_count = 0

            try:
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1

                return {
                    "exists": True,
                    "path": str(path),
                    "size_mb": round(total_size / (1024 * 1024), 2),
                    "file_count": file_count
                }
            except Exception:
                return {"exists": True, "path": str(path), "size_mb": 0, "file_count": 0, "error": True}

        return {
            "profiles": get_dir_info(self.get_profiles_dir()),
            "settings": get_dir_info(self.get_settings_dir()),
            "logs": get_dir_info(self.get_logs_dir()),
            "export_templates": get_dir_info(self.get_export_templates_dir()),
            "temp": get_dir_info(self.get_temp_dir())
        }


class SettingsManager(QObject):
    """Enhanced settings manager with proper user data directory handling"""

    settings_changed = Signal(str, str, object)  # category, key, value

    def __init__(self):
        super().__init__()

        # Initialize user data manager
        self.user_data = UserDataManager()

        # Use Qt's settings system for registry/plist storage on each platform
        self.qt_settings = QSettings("Scanner Solutions", "Dynamic Scanner")

        # Application settings stored in user AppData
        self.app_settings = {
            SettingsCategory.UI: UISettings(),
            SettingsCategory.SCANNER: ScannerSettings(),
            SettingsCategory.EXPORT: ExportSettings(),
            SettingsCategory.GENERAL: GeneralSettings(),
            SettingsCategory.ADVANCED: AdvancedSettings()
        }

        self.load_settings()

    def load_settings(self):
        """Load settings from user data directory"""
        settings_file = self.user_data.get_settings_file()

        try:
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)

                # Update dataclass instances with loaded data
                for category in SettingsCategory:
                    category_data = settings_data.get(category.value, {})
                    if category_data:
                        current_settings = self.app_settings[category]

                        # Update each field individually to preserve dataclass structure
                        for key, value in category_data.items():
                            if hasattr(current_settings, key):
                                setattr(current_settings, key, value)

        except Exception as e:
            print(f"Error loading settings from {settings_file}: {e}")
            print("Using default settings")

    def save_settings(self):
        """Save settings to user data directory"""
        settings_file = self.user_data.get_settings_file()

        try:
            # Convert all settings to dictionary format
            settings_data = {}
            for category, settings_obj in self.app_settings.items():
                settings_data[category.value] = asdict(settings_obj)

            # Write to file
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving settings to {settings_file}: {e}")

    def get(self, category: SettingsCategory, key: str, default=None):
        """Get a specific setting value"""
        settings_obj = self.app_settings.get(category)
        if settings_obj and hasattr(settings_obj, key):
            return getattr(settings_obj, key)
        return default

    def set(self, category: SettingsCategory, key: str, value: Any):
        """Set a specific setting value"""
        settings_obj = self.app_settings.get(category)
        if settings_obj and hasattr(settings_obj, key):
            setattr(settings_obj, key, value)
            self.settings_changed.emit(category.value, key, value)
            self.save_settings()

    def get_ui_settings(self) -> UISettings:
        return self.app_settings[SettingsCategory.UI]

    def get_scanner_settings(self) -> ScannerSettings:
        return self.app_settings[SettingsCategory.SCANNER]

    def get_export_settings(self) -> ExportSettings:
        return self.app_settings[SettingsCategory.EXPORT]

    def get_general_settings(self) -> GeneralSettings:
        return self.app_settings[SettingsCategory.GENERAL]

    def get_advanced_settings(self) -> AdvancedSettings:
        return self.app_settings[SettingsCategory.ADVANCED]

    def reset_to_defaults(self, category: Optional[SettingsCategory] = None):
        """Reset settings to defaults"""
        if category:
            # Reset specific category
            if category == SettingsCategory.UI:
                self.app_settings[category] = UISettings()
            elif category == SettingsCategory.SCANNER:
                self.app_settings[category] = ScannerSettings()
            elif category == SettingsCategory.EXPORT:
                self.app_settings[category] = ExportSettings()
            elif category == SettingsCategory.GENERAL:
                self.app_settings[category] = GeneralSettings()
            elif category == SettingsCategory.ADVANCED:
                self.app_settings[category] = AdvancedSettings()
        else:
            # Reset all categories
            self.app_settings = {
                SettingsCategory.UI: UISettings(),
                SettingsCategory.SCANNER: ScannerSettings(),
                SettingsCategory.EXPORT: ExportSettings(),
                SettingsCategory.GENERAL: GeneralSettings(),
                SettingsCategory.ADVANCED: AdvancedSettings()
            }
        self.save_settings()

    def get_user_data_info(self) -> Dict[str, Any]:
        """Get information about user data directories and usage"""
        return {
            "directories": {
                "profiles": str(self.user_data.get_profiles_dir()),
                "settings": str(self.user_data.get_settings_dir()),
                "logs": str(self.user_data.get_logs_dir()),
                "export_templates": str(self.user_data.get_export_templates_dir()),
                "temp": str(self.user_data.get_temp_dir())
            },
            "usage": self.user_data.get_data_usage_info()
        }

    def cleanup_user_data(self):
        """Clean up temporary files and old logs"""
        self.user_data.cleanup_temp_files()

        # Clean old log files (keep last 10)
        logs_dir = self.user_data.get_logs_dir()
        if logs_dir.exists():
            try:
                log_files = sorted([f for f in logs_dir.glob("*.log")],
                                   key=lambda x: x.stat().st_mtime, reverse=True)

                # Remove old log files beyond the limit
                for old_log in log_files[10:]:
                    try:
                        old_log.unlink()
                        print(f"Removed old log file: {old_log}")
                    except Exception as e:
                        print(f"Could not remove log file {old_log}: {e}")

            except Exception as e:
                print(f"Error cleaning log files: {e}")

    def export_settings(self, file_path: str) -> bool:
        """Export all settings to a file"""
        try:
            settings_data = {}
            for category, settings_obj in self.app_settings.items():
                settings_data[category.value] = asdict(settings_obj)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False

    def import_settings(self, file_path: str) -> bool:
        """Import settings from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)

            # Validate and import settings
            for category in SettingsCategory:
                if category.value in settings_data:
                    category_data = settings_data[category.value]
                    settings_obj = self.app_settings[category]

                    for key, value in category_data.items():
                        if hasattr(settings_obj, key):
                            setattr(settings_obj, key, value)

            self.save_settings()
            return True

        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
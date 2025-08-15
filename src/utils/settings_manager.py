import json
import os
from typing import Any, Dict, Optional
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtWidgets import QApplication
from dataclasses import dataclass, asdict
from enum import Enum


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


class SettingsManager(QObject):
    settings_changed = Signal(str, str, object)  # category, key, value

    def __init__(self):
        super().__init__()
        self.settings = QSettings("ScannerSolutions", "DynamicScanner")
        self.app_settings = {
            SettingsCategory.UI: UISettings(),
            SettingsCategory.SCANNER: ScannerSettings(),
            SettingsCategory.EXPORT: ExportSettings(),
            SettingsCategory.GENERAL: GeneralSettings(),
            SettingsCategory.ADVANCED: AdvancedSettings()
        }
        self.load_settings()

    def load_settings(self):
        """Load settings from persistent storage"""
        try:
            for category in SettingsCategory:
                category_data = self.settings.value(category.value, {})
                if isinstance(category_data, dict) and category_data:
                    # Update dataclass with saved values
                    current_settings = self.app_settings[category]
                    for key, value in category_data.items():
                        if hasattr(current_settings, key):
                            setattr(current_settings, key, value)

        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Save settings to persistent storage"""
        try:
            for category, settings_obj in self.app_settings.items():
                self.settings.setValue(category.value, asdict(settings_obj))
            self.settings.sync()

        except Exception as e:
            print(f"Error saving settings: {e}")

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


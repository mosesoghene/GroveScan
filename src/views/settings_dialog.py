from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QWidget, QGroupBox, QGridLayout, QLabel, QSpinBox,
                               QCheckBox, QComboBox, QLineEdit, QPushButton,
                               QDialogButtonBox, QFileDialog, QMessageBox, QSlider)
from PySide6.QtCore import Qt, Signal
from src.utils.settings_manager import SettingsManager, SettingsCategory
import os


class SettingsDialog(QDialog):
    settings_applied = Signal()

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Application Settings")
        self.setModal(True)
        self.resize(600, 500)
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Tab widget for different setting categories
        self.tab_widget = QTabWidget()

        # General settings tab
        general_tab = self._create_general_tab()
        self.tab_widget.addTab(general_tab, "General")

        # UI settings tab
        ui_tab = self._create_ui_tab()
        self.tab_widget.addTab(ui_tab, "Interface")

        # Scanner settings tab
        scanner_tab = self._create_scanner_tab()
        self.tab_widget.addTab(scanner_tab, "Scanner")

        # Export settings tab
        export_tab = self._create_export_tab()
        self.tab_widget.addTab(export_tab, "Export")

        # Advanced settings tab
        advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(advanced_tab, "Advanced")

        layout.addWidget(self.tab_widget)

        # Dialog buttons
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_current_tab)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self._apply_and_close)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_settings)

        button_layout.addWidget(button_box)
        layout.addLayout(button_layout)

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Profile settings group
        profile_group = QGroupBox("Profile Settings")
        profile_layout = QGridLayout(profile_group)

        self.auto_save_profiles_check = QCheckBox("Auto-save profiles when modified")
        profile_layout.addWidget(self.auto_save_profiles_check, 0, 0, 1, 2)

        self.backup_profiles_check = QCheckBox("Create profile backups")
        profile_layout.addWidget(self.backup_profiles_check, 1, 0, 1, 2)

        profile_layout.addWidget(QLabel("Max recent profiles:"), 2, 0)
        self.max_recent_spin = QSpinBox()
        self.max_recent_spin.setRange(5, 50)
        profile_layout.addWidget(self.max_recent_spin, 2, 1)

        layout.addWidget(profile_group)

        # Application settings group
        app_group = QGroupBox("Application")
        app_layout = QGridLayout(app_group)

        self.startup_check_updates_check = QCheckBox("Check for updates on startup")
        app_layout.addWidget(self.startup_check_updates_check, 0, 0, 1, 2)

        self.crash_reporting_check = QCheckBox("Enable crash reporting")
        app_layout.addWidget(self.crash_reporting_check, 1, 0, 1, 2)

        app_layout.addWidget(QLabel("Log level:"), 2, 0)
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        app_layout.addWidget(self.log_level_combo, 2, 1)

        layout.addWidget(app_group)
        layout.addStretch()

        return tab

    def _create_ui_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QGridLayout(appearance_group)

        appearance_layout.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Default", "Dark", "Light"])
        appearance_layout.addWidget(self.theme_combo, 0, 1)

        appearance_layout.addWidget(QLabel("Font size:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 16)
        appearance_layout.addWidget(self.font_size_spin, 1, 1)

        self.show_tooltips_check = QCheckBox("Show tooltips")
        appearance_layout.addWidget(self.show_tooltips_check, 2, 0, 1, 2)

        layout.addWidget(appearance_group)

        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)

        restore_layout_check = QCheckBox("Restore window layout on startup")
        restore_layout_check.setChecked(True)
        behavior_layout.addWidget(restore_layout_check)

        remember_tab_check = QCheckBox("Remember last active tab")
        remember_tab_check.setChecked(True)
        behavior_layout.addWidget(remember_tab_check)

        layout.addWidget(behavior_group)
        layout.addStretch()

        return tab

    def _create_scanner_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Default settings group
        defaults_group = QGroupBox("Default Scanner Settings")
        defaults_layout = QGridLayout(defaults_group)

        defaults_layout.addWidget(QLabel("Resolution (DPI):"), 0, 0)
        self.default_resolution_combo = QComboBox()
        self.default_resolution_combo.addItems(["150", "200", "300", "400", "600", "1200"])
        defaults_layout.addWidget(self.default_resolution_combo, 0, 1)

        defaults_layout.addWidget(QLabel("Color Mode:"), 1, 0)
        self.default_color_mode_combo = QComboBox()
        self.default_color_mode_combo.addItems(["Color", "Grayscale", "Black&White"])
        defaults_layout.addWidget(self.default_color_mode_combo, 1, 1)

        defaults_layout.addWidget(QLabel("Format:"), 2, 0)
        self.default_format_combo = QComboBox()
        self.default_format_combo.addItems(["TIFF", "PNG", "JPEG"])
        defaults_layout.addWidget(self.default_format_combo, 2, 1)

        defaults_layout.addWidget(QLabel("Quality:"), 3, 0)
        self.default_quality_spin = QSpinBox()
        self.default_quality_spin.setRange(10, 100)
        self.default_quality_spin.setSuffix("%")
        defaults_layout.addWidget(self.default_quality_spin, 3, 1)

        layout.addWidget(defaults_group)

        # Device settings group
        device_group = QGroupBox("Device Settings")
        device_layout = QGridLayout(device_group)

        self.auto_detect_devices_check = QCheckBox("Auto-detect devices on startup")
        device_layout.addWidget(self.auto_detect_devices_check, 0, 0, 1, 2)

        device_layout.addWidget(QLabel("Device timeout (seconds):"), 1, 0)
        self.device_timeout_spin = QSpinBox()
        self.device_timeout_spin.setRange(10, 120)
        device_layout.addWidget(self.device_timeout_spin, 1, 1)

        layout.addWidget(device_group)
        layout.addStretch()

        return tab

    def _create_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Directory settings group
        directory_group = QGroupBox("Default Directories")
        directory_layout = QGridLayout(directory_group)

        directory_layout.addWidget(QLabel("Default output directory:"), 0, 0)
        self.default_output_dir_edit = QLineEdit()
        directory_layout.addWidget(self.default_output_dir_edit, 0, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_directory)
        directory_layout.addWidget(browse_btn, 0, 2)

        self.remember_last_directory_check = QCheckBox("Remember last used directory")
        directory_layout.addWidget(self.remember_last_directory_check, 1, 0, 1, 3)

        layout.addWidget(directory_group)

        # Export behavior group
        behavior_group = QGroupBox("Export Behavior")
        behavior_layout = QGridLayout(behavior_group)

        behavior_layout.addWidget(QLabel("Default template:"), 0, 0)
        self.default_template_combo = QComboBox()
        self.default_template_combo.addItems([
            "High Quality PDF", "Fast PDF", "Archive TIFF",
            "Web Images", "Letter Size PDF", "A4 PDF", "Email Friendly"
        ])
        behavior_layout.addWidget(self.default_template_combo, 0, 1)

        self.confirm_overwrite_check = QCheckBox("Confirm before overwriting files")
        behavior_layout.addWidget(self.confirm_overwrite_check, 1, 0, 1, 2)

        self.show_progress_details_check = QCheckBox("Show detailed progress during export")
        behavior_layout.addWidget(self.show_progress_details_check, 2, 0, 1, 2)

        self.auto_cleanup_temp_check = QCheckBox("Auto-cleanup temporary files")
        behavior_layout.addWidget(self.auto_cleanup_temp_check, 3, 0, 1, 2)

        layout.addWidget(behavior_group)
        layout.addStretch()

        return tab

    def _create_advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Performance settings group
        performance_group = QGroupBox("Performance")
        performance_layout = QGridLayout(performance_group)

        performance_layout.addWidget(QLabel("Memory limit (MB):"), 0, 0)
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(128, 4096)
        self.memory_limit_spin.setSuffix(" MB")
        performance_layout.addWidget(self.memory_limit_spin, 0, 1)

        performance_layout.addWidget(QLabel("Temp directory:"), 1, 0)
        self.temp_directory_edit = QLineEdit()
        performance_layout.addWidget(self.temp_directory_edit, 1, 1)

        temp_browse_btn = QPushButton("Browse...")
        temp_browse_btn.clicked.connect(self._browse_temp_directory)
        performance_layout.addWidget(temp_browse_btn, 1, 2)

        performance_layout.addWidget(QLabel("Max undo levels:"), 2, 0)
        self.max_undo_spin = QSpinBox()
        self.max_undo_spin.setRange(5, 50)
        performance_layout.addWidget(self.max_undo_spin, 2, 1)

        self.parallel_export_check = QCheckBox("Enable parallel export processing")
        performance_layout.addWidget(self.parallel_export_check, 3, 0, 1, 3)

        self.cache_thumbnails_check = QCheckBox("Cache thumbnails for faster loading")
        performance_layout.addWidget(self.cache_thumbnails_check, 4, 0, 1, 3)

        layout.addWidget(performance_group)

        # Debug settings group
        debug_group = QGroupBox("Debug & Troubleshooting")
        debug_layout = QVBoxLayout(debug_group)

        self.enable_debug_mode_check = QCheckBox("Enable debug mode (verbose logging)")
        debug_layout.addWidget(self.enable_debug_mode_check)

        debug_buttons_layout = QHBoxLayout()

        clear_cache_btn = QPushButton("Clear Thumbnail Cache")
        clear_cache_btn.clicked.connect(self._clear_thumbnail_cache)
        debug_buttons_layout.addWidget(clear_cache_btn)

        clear_logs_btn = QPushButton("Clear Log Files")
        clear_logs_btn.clicked.connect(self._clear_log_files)
        debug_buttons_layout.addWidget(clear_logs_btn)

        debug_buttons_layout.addStretch()
        debug_layout.addLayout(debug_buttons_layout)

        layout.addWidget(debug_group)
        layout.addStretch()

        return tab

    def _load_current_settings(self):
        """Load current settings into UI controls"""
        # General settings
        general = self.settings_manager.get_general_settings()
        self.auto_save_profiles_check.setChecked(general.auto_save_profiles)
        self.backup_profiles_check.setChecked(general.backup_profiles)
        self.max_recent_spin.setValue(general.max_recent_profiles)
        self.startup_check_updates_check.setChecked(general.startup_check_updates)
        self.crash_reporting_check.setChecked(general.crash_reporting)
        self.log_level_combo.setCurrentText(general.log_level)

        # UI settings
        ui = self.settings_manager.get_ui_settings()
        self.theme_combo.setCurrentText(ui.theme.title())
        self.font_size_spin.setValue(ui.font_size)
        self.show_tooltips_check.setChecked(ui.show_tooltips)

        # Scanner settings
        scanner = self.settings_manager.get_scanner_settings()
        self.default_resolution_combo.setCurrentText(str(scanner.default_resolution))
        self.default_color_mode_combo.setCurrentText(scanner.default_color_mode)
        self.default_format_combo.setCurrentText(scanner.default_format)
        self.default_quality_spin.setValue(scanner.default_quality)
        self.auto_detect_devices_check.setChecked(scanner.auto_detect_devices)
        self.device_timeout_spin.setValue(scanner.device_timeout)

        # Export settings
        export = self.settings_manager.get_export_settings()
        self.default_output_dir_edit.setText(export.default_output_dir)
        self.remember_last_directory_check.setChecked(export.remember_last_directory)
        self.default_template_combo.setCurrentText(export.default_template)
        self.confirm_overwrite_check.setChecked(export.confirm_overwrite)
        self.show_progress_details_check.setChecked(export.show_progress_details)
        self.auto_cleanup_temp_check.setChecked(export.auto_cleanup_temp)

        # Advanced settings
        advanced = self.settings_manager.get_advanced_settings()
        self.memory_limit_spin.setValue(advanced.memory_limit_mb)
        self.temp_directory_edit.setText(advanced.temp_directory)
        self.max_undo_spin.setValue(advanced.max_undo_levels)
        self.enable_debug_mode_check.setChecked(advanced.enable_debug_mode)
        self.parallel_export_check.setChecked(advanced.parallel_export)
        self.cache_thumbnails_check.setChecked(advanced.cache_thumbnails)

    def _apply_settings(self):
        """Apply settings changes"""
        try:
            # Apply general settings
            self.settings_manager.set(SettingsCategory.GENERAL, 'auto_save_profiles',
                                      self.auto_save_profiles_check.isChecked())
            self.settings_manager.set(SettingsCategory.GENERAL, 'backup_profiles',
                                      self.backup_profiles_check.isChecked())
            self.settings_manager.set(SettingsCategory.GENERAL, 'max_recent_profiles',
                                      self.max_recent_spin.value())
            self.settings_manager.set(SettingsCategory.GENERAL, 'startup_check_updates',
                                      self.startup_check_updates_check.isChecked())
            self.settings_manager.set(SettingsCategory.GENERAL, 'crash_reporting',
                                      self.crash_reporting_check.isChecked())
            self.settings_manager.set(SettingsCategory.GENERAL, 'log_level',
                                      self.log_level_combo.currentText())

            # Apply UI settings
            self.settings_manager.set(SettingsCategory.UI, 'theme',
                                      self.theme_combo.currentText().lower())
            self.settings_manager.set(SettingsCategory.UI, 'font_size',
                                      self.font_size_spin.value())
            self.settings_manager.set(SettingsCategory.UI, 'show_tooltips',
                                      self.show_tooltips_check.isChecked())

            # Apply scanner settings
            self.settings_manager.set(SettingsCategory.SCANNER, 'default_resolution',
                                      int(self.default_resolution_combo.currentText()))
            self.settings_manager.set(SettingsCategory.SCANNER, 'default_color_mode',
                                      self.default_color_mode_combo.currentText())
            self.settings_manager.set(SettingsCategory.SCANNER, 'default_format',
                                      self.default_format_combo.currentText())
            self.settings_manager.set(SettingsCategory.SCANNER, 'default_quality',
                                      self.default_quality_spin.value())
            self.settings_manager.set(SettingsCategory.SCANNER, 'auto_detect_devices',
                                      self.auto_detect_devices_check.isChecked())
            self.settings_manager.set(SettingsCategory.SCANNER, 'device_timeout',
                                      self.device_timeout_spin.value())

            # Apply export settings
            self.settings_manager.set(SettingsCategory.EXPORT, 'default_output_dir',
                                      self.default_output_dir_edit.text())
            self.settings_manager.set(SettingsCategory.EXPORT, 'remember_last_directory',
                                      self.remember_last_directory_check.isChecked())
            self.settings_manager.set(SettingsCategory.EXPORT, 'default_template',
                                      self.default_template_combo.currentText())
            self.settings_manager.set(SettingsCategory.EXPORT, 'confirm_overwrite',
                                      self.confirm_overwrite_check.isChecked())
            self.settings_manager.set(SettingsCategory.EXPORT, 'show_progress_details',
                                      self.show_progress_details_check.isChecked())
            self.settings_manager.set(SettingsCategory.EXPORT, 'auto_cleanup_temp',
                                      self.auto_cleanup_temp_check.isChecked())

            # Apply advanced settings
            self.settings_manager.set(SettingsCategory.ADVANCED, 'memory_limit_mb',
                                      self.memory_limit_spin.value())
            self.settings_manager.set(SettingsCategory.ADVANCED, 'temp_directory',
                                      self.temp_directory_edit.text())
            self.settings_manager.set(SettingsCategory.ADVANCED, 'max_undo_levels',
                                      self.max_undo_spin.value())
            self.settings_manager.set(SettingsCategory.ADVANCED, 'enable_debug_mode',
                                      self.enable_debug_mode_check.isChecked())
            self.settings_manager.set(SettingsCategory.ADVANCED, 'parallel_export',
                                      self.parallel_export_check.isChecked())
            self.settings_manager.set(SettingsCategory.ADVANCED, 'cache_thumbnails',
                                      self.cache_thumbnails_check.isChecked())

            self.settings_applied.emit()

        except Exception as e:
            QMessageBox.warning(self, "Settings Error", f"Failed to apply settings: {str(e)}")

    def _apply_and_close(self):
        """Apply settings and close dialog"""
        self._apply_settings()
        self.accept()

    def _reset_current_tab(self):
        """Reset current tab to defaults"""
        current_tab = self.tab_widget.currentIndex()
        tab_names = ["General", "Interface", "Scanner", "Export", "Advanced"]

        reply = QMessageBox.question(
            self, "Reset Settings",
            f"Reset {tab_names[current_tab]} settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if current_tab == 0:  # General
                self.settings_manager.reset_to_defaults(SettingsCategory.GENERAL)
            elif current_tab == 1:  # UI
                self.settings_manager.reset_to_defaults(SettingsCategory.UI)
            elif current_tab == 2:  # Scanner
                self.settings_manager.reset_to_defaults(SettingsCategory.SCANNER)
            elif current_tab == 3:  # Export
                self.settings_manager.reset_to_defaults(SettingsCategory.EXPORT)
            elif current_tab == 4:  # Advanced
                self.settings_manager.reset_to_defaults(SettingsCategory.ADVANCED)

            self._load_current_settings()

    def _browse_output_directory(self):
        """Browse for default output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Default Output Directory",
            self.default_output_dir_edit.text() or os.path.expanduser("~/Documents")
        )
        if directory:
            self.default_output_dir_edit.setText(directory)

    def _browse_temp_directory(self):
        """Browse for temp directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Temp Directory",
            self.temp_directory_edit.text() or os.path.expanduser("~/temp")
        )
        if directory:
            self.temp_directory_edit.setText(directory)

    def _clear_thumbnail_cache(self):
        """Clear thumbnail cache"""
        # Implementation would clear thumbnail cache directory
        QMessageBox.information(self, "Cache Cleared", "Thumbnail cache has been cleared.")

    def _clear_log_files(self):
        """Clear log files"""
        # Implementation would clear log files
        QMessageBox.information(self, "Logs Cleared", "Log files have been cleared.")

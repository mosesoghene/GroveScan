from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QTextEdit, QPushButton, QDialogButtonBox,
                               QGroupBox, QGridLayout, QComboBox, QSpinBox,
                               QCheckBox, QMessageBox, QListWidget, QListWidgetItem,
                               QSplitter, QFileDialog, QProgressBar, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from src.models.scan_profile import ScanProfile, ScannerSettings, ExportSettings
import json
import os
from typing import Optional, Dict, List


class ProfileInfoDialog(QDialog):
    """Dialog for editing profile basic information"""

    def __init__(self, parent=None, profile: ScanProfile = None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("Profile Information")
        self.setModal(True)
        self.resize(400, 300)
        self._setup_ui()

        if profile:
            self._load_profile_data(profile)

    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Basic Information
        info_group = QGroupBox("Profile Information")
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter profile name...")
        info_layout.addWidget(self.name_edit, 0, 1)

        info_layout.addWidget(QLabel("Description:"), 1, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlaceholderText("Optional description...")
        info_layout.addWidget(self.description_edit, 1, 1)

        layout.addWidget(info_group)

        # Scanner Settings
        scanner_group = QGroupBox("Default Scanner Settings")
        scanner_layout = QGridLayout(scanner_group)

        scanner_layout.addWidget(QLabel("Resolution:"), 0, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["150", "200", "300", "400", "600", "1200"])
        self.resolution_combo.setCurrentText("300")
        scanner_layout.addWidget(self.resolution_combo, 0, 1)

        scanner_layout.addWidget(QLabel("Color Mode:"), 1, 0)
        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItems(["Color", "Grayscale", "Black&White"])
        scanner_layout.addWidget(self.color_mode_combo, 1, 1)

        scanner_layout.addWidget(QLabel("Format:"), 2, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["TIFF", "PNG", "JPEG"])
        scanner_layout.addWidget(self.format_combo, 2, 1)

        layout.addWidget(scanner_group)

        # Export Settings
        export_group = QGroupBox("Default Export Settings")
        export_layout = QGridLayout(export_group)

        export_layout.addWidget(QLabel("Output Format:"), 0, 0)
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["PDF", "TIFF", "PNG", "JPEG"])
        export_layout.addWidget(self.output_format_combo, 0, 1)

        self.create_folders_check = QCheckBox("Create folder structure")
        self.create_folders_check.setChecked(True)
        export_layout.addWidget(self.create_folders_check, 1, 0, 1, 2)

        self.overwrite_check = QCheckBox("Overwrite existing files")
        export_layout.addWidget(self.overwrite_check, 2, 0, 1, 2)

        layout.addWidget(export_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_profile_data(self, profile: ScanProfile):
        """Load existing profile data"""
        self.name_edit.setText(profile.name)
        self.description_edit.setText(profile.description)

        # Scanner settings
        self.resolution_combo.setCurrentText(str(profile.scanner_settings.resolution))
        self.color_mode_combo.setCurrentText(profile.scanner_settings.color_mode)
        self.format_combo.setCurrentText(profile.scanner_settings.format)

        # Export settings
        self.output_format_combo.setCurrentText(profile.export_settings.output_format)
        self.create_folders_check.setChecked(profile.export_settings.create_folders)
        self.overwrite_check.setChecked(profile.export_settings.overwrite_existing)

    def _validate_and_accept(self):
        """Validate input and accept"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Profile name is required.")
            return

        self.accept()

    def get_profile_info(self) -> Dict:
        """Get the profile information"""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'scanner_settings': ScannerSettings(
                resolution=int(self.resolution_combo.currentText()),
                color_mode=self.color_mode_combo.currentText(),
                format=self.format_combo.currentText()
            ),
            'export_settings': ExportSettings(
                output_format=self.output_format_combo.currentText(),
                create_folders=self.create_folders_check.isChecked(),
                overwrite_existing=self.overwrite_check.isChecked()
            )
        }


class ProfileManagerDialog(QDialog):
    """Dialog for managing multiple profiles"""

    # Signals
    profile_selected = Signal(object)  # ScanProfile
    profile_deleted = Signal(str)  # profile_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_profiles = []
        self.profiles_dir = "profiles"

        self.setWindowTitle("Profile Manager")
        self.setModal(True)
        self.resize(700, 500)
        self._setup_ui()
        self._load_available_profiles()

    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Profile list
        left_panel = self._create_profile_list_panel()
        splitter.addWidget(left_panel)

        # Right panel - Profile details
        right_panel = self._create_profile_details_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 400])
        layout.addWidget(splitter)

        # Bottom buttons
        button_layout = QHBoxLayout()

        self.import_btn = QPushButton("Import Profile...")
        self.import_btn.clicked.connect(self._import_profile)
        button_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export Profile...")
        self.export_btn.clicked.connect(self._export_profile)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)

        button_layout.addStretch()

        self.load_btn = QPushButton("Load Profile")
        self.load_btn.clicked.connect(self._load_selected_profile)
        self.load_btn.setEnabled(False)
        button_layout.addWidget(self.load_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _create_profile_list_panel(self) -> QWidget:
        """Create profile list panel"""
        from PySide6.QtWidgets import QWidget

        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Available Profiles</b>"))
        header_layout.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_available_profiles)
        header_layout.addWidget(self.refresh_btn)

        layout.addLayout(header_layout)

        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        layout.addWidget(self.profile_list)

        # List buttons
        list_btn_layout = QHBoxLayout()

        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self._duplicate_profile)
        self.duplicate_btn.setEnabled(False)
        list_btn_layout.addWidget(self.duplicate_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_profile)
        self.delete_btn.setEnabled(False)
        list_btn_layout.addWidget(self.delete_btn)

        layout.addLayout(list_btn_layout)

        return panel

    def _create_profile_details_panel(self) -> QWidget:
        """Create profile details panel"""
        from PySide6.QtWidgets import QWidget, QScrollArea

        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Header
        layout.addWidget(QLabel("<b>Profile Details</b>"))

        # Scrollable details area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)

        # Initial empty state
        self.empty_label = QLabel("Select a profile to view details")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #888; font-style: italic;")
        self.details_layout.addWidget(self.empty_label)

        scroll_area.setWidget(self.details_widget)
        layout.addWidget(scroll_area)

        return panel

    def _load_available_profiles(self):
        """Load available profiles from directory"""
        self.profile_list.clear()
        self.available_profiles.clear()

        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)
            return

        try:
            for filename in os.listdir(self.profiles_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.profiles_dir, filename)
                    profile = self._load_profile_from_file(filepath)

                    if profile:
                        self.available_profiles.append(profile)

                        # Create list item
                        item = QListWidgetItem(profile.name)
                        item.setData(Qt.ItemDataRole.UserRole, profile)
                        self.profile_list.addItem(item)

        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Error loading profiles: {str(e)}")

    def _load_profile_from_file(self, filepath: str) -> Optional[ScanProfile]:
        """Load a single profile from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ScanProfile.from_dict(data)
        except Exception:
            return None

    def _on_profile_selected(self, current_item, previous_item):
        """Handle profile selection"""
        if current_item:
            profile = current_item.data(Qt.ItemDataRole.UserRole)
            self._display_profile_details(profile)
            self.load_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.duplicate_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        else:
            self._clear_profile_details()
            self.load_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.duplicate_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def _display_profile_details(self, profile: ScanProfile):
        """Display profile details in right panel"""
        # Clear existing details
        for i in reversed(range(self.details_layout.count())):
            child = self.details_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Profile info
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout(info_group)

        name_label = QLabel(f"<b>Name:</b> {profile.name}")
        info_layout.addWidget(name_label)

        if profile.description:
            desc_label = QLabel(f"<b>Description:</b> {profile.description}")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)

        created_label = QLabel(f"<b>Created:</b> {profile.created_date[:19].replace('T', ' ')}")
        info_layout.addWidget(created_label)

        modified_label = QLabel(f"<b>Modified:</b> {profile.modified_date[:19].replace('T', ' ')}")
        info_layout.addWidget(modified_label)

        self.details_layout.addWidget(info_group)

        # Schema info
        schema_group = QGroupBox("Index Schema")
        schema_layout = QVBoxLayout(schema_group)

        field_count_label = QLabel(f"<b>Fields:</b> {len(profile.schema.fields)}")
        schema_layout.addWidget(field_count_label)

        if profile.schema.fields:
            fields_text = ""
            folder_fields = profile.schema.get_folder_hierarchy()
            filename_fields = profile.schema.get_filename_components()
            metadata_fields = profile.schema.get_metadata_fields()

            if folder_fields:
                fields_text += "<b>Folder fields:</b><br>"
                for field in folder_fields:
                    fields_text += f"  • {field.name}<br>"

            if filename_fields:
                fields_text += "<b>Filename fields:</b><br>"
                for field in filename_fields:
                    fields_text += f"  • {field.name}<br>"

            if metadata_fields:
                fields_text += "<b>Metadata fields:</b><br>"
                for field in metadata_fields:
                    fields_text += f"  • {field.name}<br>"

            fields_label = QLabel(fields_text)
            fields_label.setWordWrap(True)
            schema_layout.addWidget(fields_label)

        self.details_layout.addWidget(schema_group)

        # Settings info
        settings_group = QGroupBox("Default Settings")
        settings_layout = QVBoxLayout(settings_group)

        scanner_text = f"<b>Scanner:</b> {profile.scanner_settings.resolution} DPI, {profile.scanner_settings.color_mode}, {profile.scanner_settings.format}"
        settings_layout.addWidget(QLabel(scanner_text))

        export_text = f"<b>Export:</b> {profile.export_settings.output_format}"
        if profile.export_settings.create_folders:
            export_text += ", Create folders"
        if profile.export_settings.overwrite_existing:
            export_text += ", Overwrite existing"

        settings_layout.addWidget(QLabel(export_text))

        self.details_layout.addWidget(settings_group)

        self.details_layout.addStretch()

    def _clear_profile_details(self):
        """Clear profile details display"""
        for i in reversed(range(self.details_layout.count())):
            child = self.details_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        self.details_layout.addWidget(self.empty_label)

    def _load_selected_profile(self):
        """Load the selected profile"""
        current_item = self.profile_list.currentItem()
        if current_item:
            profile = current_item.data(Qt.ItemDataRole.UserRole)
            self.profile_selected.emit(profile)
            self.accept()

    def _duplicate_profile(self):
        """Duplicate the selected profile"""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return

        profile = current_item.data(Qt.ItemDataRole.UserRole)

        # Get new name
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self,
            "Duplicate Profile",
            "Enter name for duplicated profile:",
            text=f"{profile.name} Copy"
        )

        if ok and new_name.strip():
            try:
                # Clone profile
                new_profile = profile.clone(new_name.strip())

                # Save to file
                filename = f"{new_name.strip().replace(' ', '_').lower()}.json"
                filepath = os.path.join(self.profiles_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(new_profile.to_dict(), f, indent=2, ensure_ascii=False)

                # Refresh list
                self._load_available_profiles()

                QMessageBox.information(self, "Profile Duplicated", f"Profile '{new_name}' created successfully!")

            except Exception as e:
                QMessageBox.critical(self, "Duplication Error", f"Failed to duplicate profile:\n{str(e)}")

    def _delete_profile(self):
        """Delete the selected profile"""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return

        profile = current_item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to delete profile '{profile.name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Find and delete the file
                for filename in os.listdir(self.profiles_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(self.profiles_dir, filename)
                        test_profile = self._load_profile_from_file(filepath)

                        if test_profile and test_profile.name == profile.name:
                            os.remove(filepath)
                            break

                # Refresh list
                self._load_available_profiles()
                self.profile_deleted.emit(profile.name)

                QMessageBox.information(self, "Profile Deleted", f"Profile '{profile.name}' deleted successfully!")

            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Failed to delete profile:\n{str(e)}")

    def _import_profile(self):
        """Import a profile from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profile",
            "",
            "Profile Files (*.json);;All Files (*)"
        )

        if file_path:
            profile = self._load_profile_from_file(file_path)
            if profile:
                try:
                    # Save to profiles directory
                    filename = f"{profile.name.replace(' ', '_').lower()}.json"
                    dest_path = os.path.join(self.profiles_dir, filename)

                    # Check if profile already exists
                    if os.path.exists(dest_path):
                        reply = QMessageBox.question(
                            self,
                            "Profile Exists",
                            f"A profile named '{profile.name}' already exists. Overwrite?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No
                        )

                        if reply != QMessageBox.StandardButton.Yes:
                            return

                    # Copy profile to profiles directory
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

                    # Refresh list
                    self._load_available_profiles()

                    QMessageBox.information(self, "Profile Imported",
                                            f"Profile '{profile.name}' imported successfully!")

                except Exception as e:
                    QMessageBox.critical(self, "Import Error", f"Failed to import profile:\n{str(e)}")
            else:
                QMessageBox.warning(self, "Import Error", "Failed to load profile from selected file.")

    def _export_profile(self):
        """Export selected profile to file"""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return

        profile = current_item.data(Qt.ItemDataRole.UserRole)

        default_filename = f"{profile.name.replace(' ', '_').lower()}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            default_filename,
            "Profile Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

                QMessageBox.information(self, "Profile Exported", f"Profile '{profile.name}' exported successfully!")

            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export profile:\n{str(e)}")

    def get_profile_info(self) -> Dict:
        """Get the profile information"""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'scanner_settings': ScannerSettings(
                resolution=int(self.resolution_combo.currentText()),
                color_mode=self.color_mode_combo.currentText(),
                format=self.format_combo.currentText()
            ),
            'export_settings': ExportSettings(
                output_format=self.output_format_combo.currentText(),
                create_folders=self.create_folders_check.isChecked(),
                overwrite_existing=self.overwrite_check.isChecked()
            )
        }

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QScrollArea, QLabel, QPushButton, QComboBox,
                               QLineEdit, QSpinBox, QCheckBox, QTextEdit,
                               QMessageBox, QDialog, QDialogButtonBox,
                               QGridLayout, QFrame, QSplitter)
from PySide6.QtCore import Signal, Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QPixmap
from src.models.dynamic_index_schema import DynamicIndexSchema
from src.models.index_field import IndexField, IndexFieldType, ValidationRule
from src.models.scan_profile import ScanProfile, ScannerSettings, ExportSettings
from .index_field_widget import IndexFieldWidget, FieldListWidget
from typing import List, Dict, Optional

from ..utils.help_system import HelpManager


class DynamicIndexEditor(QWidget):
    """Main editor for dynamic index schemas"""

    # Signals
    schema_changed = Signal(object)  # DynamicIndexSchema
    profile_changed = Signal(object)  # ScanProfile
    validation_error = Signal(str)  # error message

    def __init__(self):
        super().__init__()
        self.current_schema = DynamicIndexSchema()
        self.current_profile = None
        self._setup_ui()
        self._connect_signals()
        self.help_manager = HelpManager()
        self._setup_tooltips()

    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Field Management
        left_panel = self._create_field_management_panel()
        splitter.addWidget(left_panel)

        # Right panel - Preview and Values
        right_panel = self._create_preview_panel()
        splitter.addWidget(right_panel)

        # Set initial splitter sizes (60% left, 40% right)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)

        # Bottom panel - Profile Management
        profile_panel = self._create_profile_panel()
        layout.addWidget(profile_panel)

    def _create_field_management_panel(self) -> QWidget:
        """Create the field management panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Header with add field button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Index Fields</h3>"))
        header_layout.addStretch()

        self.add_field_btn = QPushButton("Add Field")
        self.add_field_btn.clicked.connect(self._add_new_field)
        header_layout.addWidget(self.add_field_btn)

        layout.addLayout(header_layout)

        # Field list with drag-and-drop support
        self.field_list = FieldListWidget()
        self.field_list.field_reordered.connect(self._on_field_reordered)
        self.field_list.field_edited.connect(self._on_field_edited)
        self.field_list.field_deleted.connect(self._on_field_deleted)
        layout.addWidget(self.field_list)

        # Schema settings
        settings_group = QGroupBox("Schema Settings")
        settings_layout = QGridLayout(settings_group)

        settings_layout.addWidget(QLabel("Field Separator:"), 0, 0)
        self.separator_edit = QLineEdit("_")
        self.separator_edit.setMaximumWidth(50)
        self.separator_edit.textChanged.connect(self._on_separator_changed)
        settings_layout.addWidget(self.separator_edit, 0, 1)

        layout.addWidget(settings_group)

        return panel

    def _create_preview_panel(self) -> QWidget:
        """Create the preview and values panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Structure Preview
        preview_group = QGroupBox("Structure Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.structure_preview = QTextEdit()
        self.structure_preview.setMaximumHeight(150)
        self.structure_preview.setReadOnly(True)
        self.structure_preview.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                background-color: #f5f5f5;
            }
        """)
        preview_layout.addWidget(self.structure_preview)

        layout.addWidget(preview_group)

        # Field Values
        values_group = QGroupBox("Field Values")
        values_layout = QVBoxLayout(values_group)

        # Scroll area for field values
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.values_widget = QWidget()
        self.values_layout = QVBoxLayout(self.values_widget)
        scroll_area.setWidget(self.values_widget)

        values_layout.addWidget(scroll_area)

        # Test buttons
        test_layout = QHBoxLayout()
        self.validate_btn = QPushButton("Validate All")
        self.validate_btn.clicked.connect(self._validate_all_fields)
        test_layout.addWidget(self.validate_btn)

        self.clear_values_btn = QPushButton("Clear Values")
        self.clear_values_btn.clicked.connect(self._clear_all_values)
        test_layout.addWidget(self.clear_values_btn)

        values_layout.addLayout(test_layout)
        layout.addWidget(values_group)

        return panel

    def _create_profile_panel(self) -> QWidget:
        """Create the profile management panel"""
        panel = QGroupBox("Profile Management")
        layout = QHBoxLayout(panel)

        # Profile info
        self.profile_label = QLabel("No profile loaded")
        self.profile_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.profile_label)

        layout.addStretch()

        # Profile buttons
        self.new_profile_btn = QPushButton("New Profile")
        self.new_profile_btn.clicked.connect(self._create_new_profile)
        layout.addWidget(self.new_profile_btn)

        self.save_profile_btn = QPushButton("Save Profile")
        self.save_profile_btn.clicked.connect(self._save_current_profile)
        self.save_profile_btn.setEnabled(False)
        layout.addWidget(self.save_profile_btn)

        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.clicked.connect(self._save_profile_as)
        layout.addWidget(self.save_as_btn)

        self.load_profile_btn = QPushButton("Load Profile")
        self.load_profile_btn.clicked.connect(self._load_profile)
        layout.addWidget(self.load_profile_btn)

        return panel

    def _connect_signals(self):
        """Connect internal signals"""
        pass

    def _add_new_field(self):
        """Add a new field to the schema"""
        dialog = FieldEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            field = dialog.get_field()
            try:
                self.current_schema.add_field(field)
                self._refresh_field_list()
                self._update_preview()
                self.schema_changed.emit(self.current_schema)
            except ValueError as e:
                QMessageBox.warning(self, "Field Error", str(e))

    def _on_field_reordered(self, field_name: str, new_position: int):
        """Handle field reordering"""
        success = self.current_schema.reorder_field(field_name, new_position)
        if success:
            self._refresh_field_list()
            self._update_preview()
            self.schema_changed.emit(self.current_schema)

    def _on_field_edited(self, field_name: str):
        """Handle field editing"""
        field = self.current_schema.get_field_by_name(field_name)
        if field:
            dialog = FieldEditorDialog(self, field)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_field = dialog.get_field()
                # Replace the field
                for i, f in enumerate(self.current_schema.fields):
                    if f.name == field_name:
                        self.current_schema.fields[i] = updated_field
                        break

                self._refresh_field_list()
                self._update_preview()
                self.schema_changed.emit(self.current_schema)

    def _on_field_deleted(self, field_name: str):
        """Handle field deletion"""
        reply = QMessageBox.question(
            self,
            "Delete Field",
            f"Are you sure you want to delete field '{field_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.current_schema.remove_field(field_name)
            if success:
                self._refresh_field_list()
                self._update_preview()
                self.schema_changed.emit(self.current_schema)

    def _on_separator_changed(self, text: str):
        """Handle separator change"""
        self.current_schema.separator = text or "_"
        self._update_preview()
        self.schema_changed.emit(self.current_schema)

    def _refresh_field_list(self):
        """Refresh the field list display"""
        self.field_list.set_fields(self.current_schema.fields)
        self._refresh_field_values()

    def _refresh_field_values(self):
        """Refresh the field values panel"""
        # Clear existing value widgets
        for i in reversed(range(self.values_layout.count())):
            child = self.values_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Add value editors for each field
        self.value_editors = {}
        for field in self.current_schema.fields:
            # Create value editor widget
            editor_widget = QWidget()
            editor_layout = QHBoxLayout(editor_widget)
            editor_layout.setContentsMargins(0, 0, 0, 0)

            # Field label with type indicator
            type_indicator = {
                IndexFieldType.FOLDER: "📁",
                IndexFieldType.FILENAME: "📄",
                IndexFieldType.METADATA: "🏷️"
            }

            label_text = f"{type_indicator.get(field.field_type, '')} {field.name}:"
            if field.is_required:
                label_text += " *"

            label = QLabel(label_text)
            label.setMinimumWidth(150)
            editor_layout.addWidget(label)

            # Value input
            value_edit = QLineEdit()
            value_edit.setText(field.default_value)
            value_edit.setPlaceholderText(f"Enter {field.name.lower()}...")
            value_edit.textChanged.connect(self._on_field_value_changed)

            self.value_editors[field.name] = value_edit
            editor_layout.addWidget(value_edit)

            self.values_layout.addWidget(editor_widget)

        # Add stretch to push everything up
        self.values_layout.addStretch()

    def _on_field_value_changed(self):
        """Handle field value changes"""
        self._update_preview()

    def _update_preview(self):
        """Update the structure preview"""
        # Get current values
        values = {}
        for field_name, editor in self.value_editors.items():
            values[field_name] = editor.text() or f"<{field_name.lower()}>"

        # Generate preview
        preview_text = self._generate_structure_preview(values)
        self.structure_preview.setText(preview_text)

    def _generate_structure_preview(self, values: Dict[str, str]) -> str:
        """Generate structure preview text"""
        lines = []
        lines.append("Folder Structure Preview:")
        lines.append("=" * 30)

        # Show folder hierarchy
        folder_path = self.current_schema.generate_folder_path(values)
        if folder_path:
            lines.append(f"Folder: /{folder_path}/")
        else:
            lines.append("Folder: /root/")

        # Show filename
        filename = self.current_schema.generate_filename(values)
        lines.append(f"File: {filename}")

        lines.append("")
        lines.append("Full Path Preview:")
        lines.append("-" * 20)
        full_path = f"/{folder_path}/{filename}" if folder_path else f"/{filename}"
        lines.append(full_path)

        # Show field assignments
        lines.append("")
        lines.append("Field Assignments:")
        lines.append("-" * 20)

        folder_fields = self.current_schema.get_folder_hierarchy()
        filename_fields = self.current_schema.get_filename_components()
        metadata_fields = self.current_schema.get_metadata_fields()

        if folder_fields:
            lines.append("Folder fields:")
            for field in folder_fields:
                lines.append(f"  • {field.name} = {values.get(field.name, '<empty>')}")

        if filename_fields:
            lines.append("Filename fields:")
            for field in filename_fields:
                lines.append(f"  • {field.name} = {values.get(field.name, '<empty>')}")

        if metadata_fields:
            lines.append("Metadata fields:")
            for field in metadata_fields:
                lines.append(f"  • {field.name} = {values.get(field.name, '<empty>')}")

        return "\n".join(lines)

    def _validate_all_fields(self):
        """Validate all field values"""
        values = {}
        for field_name, editor in self.value_editors.items():
            values[field_name] = editor.text()

        errors = self.current_schema.validate_all_values(values)

        if errors:
            error_msg = "Validation Errors:\n\n"
            for field_name, error in errors.items():
                error_msg += f"• {field_name}: {error}\n"

            QMessageBox.warning(self, "Validation Failed", error_msg)
            self.validation_error.emit("Field validation failed")
        else:
            QMessageBox.information(self, "Validation Success", "All fields are valid!")

    def _clear_all_values(self):
        """Clear all field values"""
        for editor in self.value_editors.values():
            editor.clear()
        self._update_preview()

    def _create_new_profile(self):
        """Create a new profile"""
        from .profile_dialog import ProfileInfoDialog

        dialog = ProfileInfoDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile_info = dialog.get_profile_info()

            self.current_profile = ScanProfile(
                name=profile_info['name'],
                description=profile_info['description'],
                schema=DynamicIndexSchema()
            )

            self.current_schema = self.current_profile.schema
            self._refresh_field_list()
            self._update_profile_display()
            self.save_profile_btn.setEnabled(True)

    def _save_current_profile(self):
        """Save the current profile"""
        if not self.current_profile:
            self._save_profile_as()
            return

        # Update profile with current schema and values
        self.current_profile.schema = self.current_schema

        # Save filled values
        values = {}
        for field_name, editor in self.value_editors.items():
            values[field_name] = editor.text()
        self.current_profile.filled_values = values

        self.current_profile.update_modified_date()

        # Save to file (implement file saving logic)
        success = self._save_profile_to_file(self.current_profile)
        if success:
            QMessageBox.information(self, "Profile Saved", f"Profile '{self.current_profile.name}' saved successfully!")
            self.profile_changed.emit(self.current_profile)
        else:
            QMessageBox.warning(self, "Save Failed", "Failed to save profile.")

    def _save_profile_as(self):
        """Save profile with new name"""
        from .profile_dialog import ProfileInfoDialog

        dialog = ProfileInfoDialog(self, self.current_profile)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile_info = dialog.get_profile_info()

            # Create new profile or update existing
            if not self.current_profile:
                self.current_profile = ScanProfile(
                    name=profile_info['name'],
                    description=profile_info['description'],
                    schema=self.current_schema
                )
            else:
                self.current_profile.name = profile_info['name']
                self.current_profile.description = profile_info['description']
                self.current_profile.schema = self.current_schema

            # Save values
            values = {}
            for field_name, editor in self.value_editors.items():
                values[field_name] = editor.text()
            self.current_profile.filled_values = values

            success = self._save_profile_to_file(self.current_profile)
            if success:
                self._update_profile_display()
                self.save_profile_btn.setEnabled(True)
                QMessageBox.information(self, "Profile Saved",
                                        f"Profile '{self.current_profile.name}' saved successfully!")
                self.profile_changed.emit(self.current_profile)

    def _load_profile(self):
        """Load an existing profile"""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Profile",
            "",
            "Profile Files (*.json);;All Files (*)"
        )

        if file_path:
            profile = self._load_profile_from_file(file_path)
            if profile:
                self.current_profile = profile
                self.current_schema = profile.schema
                self.separator_edit.setText(profile.schema.separator)
                self._refresh_field_list()

                # Load saved values
                for field_name, value in profile.filled_values.items():
                    if field_name in self.value_editors:
                        self.value_editors[field_name].setText(value)

                self._update_preview()
                self._update_profile_display()
                self.save_profile_btn.setEnabled(True)
                self.profile_changed.emit(self.current_profile)

    def _save_profile_to_file(self, profile: ScanProfile) -> bool:
        """Save profile to JSON file"""
        from PySide6.QtWidgets import QFileDialog
        import json
        import os

        # Create profiles directory if it doesn't exist
        profiles_dir = "profiles"
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)

        default_filename = f"{profile.name.replace(' ', '_').lower()}.json"
        default_path = os.path.join(profiles_dir, default_filename)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Profile",
            default_path,
            "Profile Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save profile:\n{str(e)}")
                return False

        return False

    def _load_profile_from_file(self, file_path: str) -> Optional[ScanProfile]:
        """Load profile from JSON file"""
        import json

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            profile = ScanProfile.from_dict(data)
            return profile

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load profile:\n{str(e)}")
            return None

    def _update_profile_display(self):
        """Update the profile display"""
        if self.current_profile:
            self.profile_label.setText(f"Profile: {self.current_profile.name}")
        else:
            self.profile_label.setText("No profile loaded")

    def set_schema(self, schema: DynamicIndexSchema):
        """Set the current schema"""
        self.current_schema = schema
        self.separator_edit.setText(schema.separator)
        self._refresh_field_list()
        self._update_preview()

    def get_schema(self) -> DynamicIndexSchema:
        """Get the current schema"""
        return self.current_schema

    def get_field_values(self) -> Dict[str, str]:
        """Get current field values"""
        values = {}
        for field_name, editor in self.value_editors.items():
            values[field_name] = editor.text()
        return values

    def _setup_tooltips(self):
        """Setup tooltips for UI elements"""
        self.add_field_btn.setToolTip(self.help_manager.get_tooltip("field_name"))
        self.separator_edit.setToolTip("Character used to separate filename components (default: _)")
        self.validate_btn.setToolTip("Check all field values for errors and conflicts")
        self.clear_values_btn.setToolTip("Clear all field values to start fresh")


class FieldEditorDialog(QDialog):
    """Dialog for editing field properties"""

    def __init__(self, parent=None, field: IndexField = None):
        super().__init__(parent)
        self.field = field
        self.setWindowTitle("Field Editor")
        self.setModal(True)
        self.resize(400, 500)
        self._setup_ui()

        self.help_manager = HelpManager()
        self._setup_field_help()

        if field:
            self._load_field_data(field)

    def _setup_field_help(self):
        """Setup help tooltips for field editor"""
        self.name_edit.setToolTip(self.help_manager.get_tooltip("field_name"))
        self.type_combo.setToolTip(self.help_manager.get_tooltip("field_type"))
        self.default_edit.setToolTip(self.help_manager.get_tooltip("field_default"))
        self.required_check.setToolTip(self.help_manager.get_tooltip("field_required"))
        self.pattern_edit.setToolTip("Regular expression pattern to validate field values (optional)")
        self.allowed_values_edit.setToolTip("List of allowed values, one per line (optional)")

    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Basic properties
        basic_group = QGroupBox("Basic Properties")
        basic_layout = QGridLayout(basic_group)

        basic_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter field name...")
        basic_layout.addWidget(self.name_edit, 0, 1)

        basic_layout.addWidget(QLabel("Type:"), 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItem("Folder", IndexFieldType.FOLDER)
        self.type_combo.addItem("Filename", IndexFieldType.FILENAME)
        self.type_combo.addItem("Metadata", IndexFieldType.METADATA)
        basic_layout.addWidget(self.type_combo, 1, 1)

        basic_layout.addWidget(QLabel("Default Value:"), 2, 0)
        self.default_edit = QLineEdit()
        self.default_edit.setPlaceholderText("Optional default value...")
        basic_layout.addWidget(self.default_edit, 2, 1)

        self.required_check = QCheckBox("Required Field")
        self.required_check.setChecked(True)
        basic_layout.addWidget(self.required_check, 3, 0, 1, 2)

        layout.addWidget(basic_group)

        # Validation rules
        validation_group = QGroupBox("Validation Rules")
        validation_layout = QGridLayout(validation_group)

        validation_layout.addWidget(QLabel("Pattern (RegEx):"), 0, 0)
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("Optional regex pattern...")
        validation_layout.addWidget(self.pattern_edit, 0, 1)

        validation_layout.addWidget(QLabel("Min Length:"), 1, 0)
        self.min_length_spin = QSpinBox()
        self.min_length_spin.setRange(0, 1000)
        self.min_length_spin.setSpecialValueText("No limit")
        validation_layout.addWidget(self.min_length_spin, 1, 1)

        validation_layout.addWidget(QLabel("Max Length:"), 2, 0)
        self.max_length_spin = QSpinBox()
        self.max_length_spin.setRange(0, 1000)
        self.max_length_spin.setSpecialValueText("No limit")
        validation_layout.addWidget(self.max_length_spin, 2, 1)

        validation_layout.addWidget(QLabel("Allowed Values:"), 3, 0)
        self.allowed_values_edit = QTextEdit()
        self.allowed_values_edit.setMaximumHeight(100)
        self.allowed_values_edit.setPlaceholderText("Enter allowed values, one per line (optional)")
        validation_layout.addWidget(self.allowed_values_edit, 3, 1)

        layout.addWidget(validation_group)

        help_btn = QPushButton("❓ Field Help")
        help_btn.clicked.connect(self._show_field_help)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        # Create a layout for the buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(help_btn)
        button_layout.addStretch()
        button_layout.addWidget(button_box)

        # Add button layout to main layout instead of button_box directly
        layout.addLayout(button_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _show_field_help(self):
        """Show field-specific help"""
        from src.utils.help_system import HelpDialog
        help_dialog = HelpDialog(self.help_manager, "profiles_overview", self)
        help_dialog.exec()

    def _load_field_data(self, field: IndexField):
        """Load existing field data into dialog"""
        self.name_edit.setText(field.name)
        self.type_combo.setCurrentText(field.field_type.value.title())
        self.default_edit.setText(field.default_value)
        self.required_check.setChecked(field.is_required)

        # Validation rules
        if field.validation_rules.pattern:
            self.pattern_edit.setText(field.validation_rules.pattern)

        if field.validation_rules.min_length:
            self.min_length_spin.setValue(field.validation_rules.min_length)

        if field.validation_rules.max_length:
            self.max_length_spin.setValue(field.validation_rules.max_length)

        if field.validation_rules.allowed_values:
            self.allowed_values_edit.setText("\n".join(field.validation_rules.allowed_values))

    def _validate_and_accept(self):
        """Validate field data and accept dialog"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Field name is required.")
            return

        # Check for valid field name (no special characters)
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_\s]*$', name):
            QMessageBox.warning(
                self,
                "Validation Error",
                "Field name must start with a letter and contain only letters, numbers, underscores, and spaces."
            )
            return

        self.accept()

    def get_field(self) -> IndexField:
        """Get the configured field"""
        # Get allowed values
        allowed_values = None
        allowed_text = self.allowed_values_edit.toPlainText().strip()
        if allowed_text:
            allowed_values = [line.strip() for line in allowed_text.split('\n') if line.strip()]

        # Create validation rules
        validation_rules = ValidationRule(
            pattern=self.pattern_edit.text().strip() or None,
            allowed_values=allowed_values,
            min_length=self.min_length_spin.value() if self.min_length_spin.value() > 0 else None,
            max_length=self.max_length_spin.value() if self.max_length_spin.value() > 0 else None,
            required=self.required_check.isChecked()
        )

        # Determine order (will be set by schema)
        order = self.field.order if self.field else 0

        return IndexField(
            name=self.name_edit.text().strip(),
            field_type=self.type_combo.currentData(),
            order=order,
            default_value=self.default_edit.text().strip(),
            is_required=self.required_check.isChecked(),
            validation_rules=validation_rules
        )


from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QListWidget, QListWidgetItem, QPushButton, QLabel,
                               QTreeWidget, QTreeWidgetItem, QSplitter, QLineEdit,
                               QGridLayout, QScrollArea, QFrame, QMessageBox,
                               QComboBox, QTextEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from src.models.page_assignment import PageAssignment, AssignmentConflict, ValidationError
from src.models.dynamic_index_schema import DynamicIndexSchema
from src.models.document_batch import DocumentBatch
from typing import List, Dict, Optional

from src.utils.help_system import HelpManager


class AssignmentWidget(QFrame):
    """Widget for displaying a single page assignment"""

    # Signals
    assignment_selected = Signal(str)  # assignment_id
    assignment_edited = Signal(str)  # assignment_id
    assignment_deleted = Signal(str)  # assignment_id

    def __init__(self, assignment: PageAssignment):
        super().__init__()
        self.assignment = assignment
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self):
        """Setup assignment widget UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setFixedHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header with assignment info
        header_layout = QHBoxLayout()

        # Assignment ID (shortened)
        id_label = QLabel(f"Assignment: {self.assignment.assignment_id[:8]}...")
        id_label.setStyleSheet("font-weight: bold; font-size: 9pt; color: #666;")
        header_layout.addWidget(id_label)

        header_layout.addStretch()

        # Page count
        page_count_label = QLabel(f"{len(self.assignment.page_ids)} pages")
        page_count_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        header_layout.addWidget(page_count_label)

        layout.addLayout(header_layout)

        # Preview info
        preview_layout = QVBoxLayout()
        preview_layout.setSpacing(2)

        # Folder preview
        if self.assignment.folder_path_preview:
            folder_label = QLabel(f"📁 {self.assignment.folder_path_preview}")
            folder_label.setStyleSheet("font-size: 9pt; color: #444;")
            preview_layout.addWidget(folder_label)

        # Filename preview
        if self.assignment.document_name_preview:
            file_label = QLabel(f"📄 {self.assignment.document_name_preview}")
            file_label.setStyleSheet("font-size: 9pt; color: #444;")
            preview_layout.addWidget(file_label)

        layout.addLayout(preview_layout)

        # Index values (abbreviated)
        if self.assignment.index_values:
            values_text = " | ".join([f"{k}: {v}" for k, v in list(self.assignment.index_values.items())[:3]])
            if len(self.assignment.index_values) > 3:
                values_text += "..."

            values_label = QLabel(values_text)
            values_label.setStyleSheet("font-size: 8pt; color: #888;")
            values_label.setWordWrap(True)
            layout.addWidget(values_label)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(50, 25)
        edit_btn.clicked.connect(self._on_edit_clicked)
        button_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(50, 25)
        delete_btn.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(delete_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _setup_style(self):
        """Setup widget styling"""
        self.setStyleSheet("""
            AssignmentWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            AssignmentWidget:hover {
                border: 2px solid #0078d4;
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 8pt;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

    def _on_edit_clicked(self):
        """Handle edit button click"""
        self.assignment_edited.emit(self.assignment.assignment_id)

    def _on_delete_clicked(self):
        """Handle delete button click"""
        self.assignment_deleted.emit(self.assignment.assignment_id)

    def mousePressEvent(self, event):
        """Handle mouse press for selection"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.assignment_selected.emit(self.assignment.assignment_id)
        super().mousePressEvent(event)

    def update_assignment(self, assignment: PageAssignment):
        """Update widget with new assignment data"""
        self.assignment = assignment
        # Clear and rebuild UI
        self.setParent(None)
        self._setup_ui()


class PageAssignmentView(QWidget):
    """Main view for page assignment operations"""

    # Signals
    assignment_requested = Signal(list, dict)  # page_ids, index_values
    assignment_updated = Signal(str, dict)  # assignment_id, index_values
    assignment_deleted = Signal(str)  # assignment_id
    pages_selected_for_assignment = Signal(list)  # page_ids

    def __init__(self):
        super().__init__()
        self.current_batch = None
        self.current_schema = None
        self.selected_assignment_id = None
        self.field_editors = {}  # field_name -> QLineEdit
        self.selected_page_ids = []
        self.assignment_widgets = {}  # assignment_id -> AssignmentWidget
        self._setup_ui()
        self._connect_signals()
        self.help_manager = HelpManager()
        self._setup_tooltips()

    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Current assignment editing
        left_panel = self._create_assignment_editor_panel()
        splitter.addWidget(left_panel)

        # Middle panel - Assignment list
        middle_panel = self._create_assignment_list_panel()
        splitter.addWidget(middle_panel)

        # Right panel - Structure preview
        right_panel = self._create_preview_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (40%, 30%, 30%)
        splitter.setSizes([400, 300, 300])
        layout.addWidget(splitter)

    def _setup_tooltips(self):
        """Setup tooltips for page assignment controls"""
        self.assign_btn.setToolTip(self.help_manager.get_tooltip("assign_pages"))
        self.clear_values_btn.setToolTip("Clear all field values to start over")

        self.pages_per_doc_spin.setToolTip(self.help_manager.get_tooltip("pages_per_doc"))
        self.auto_assign_btn.setToolTip(self.help_manager.get_tooltip("auto_assign"))

        self.validate_all_btn.setToolTip("Check all assignments for errors and missing required fields")
        self.clear_all_btn.setToolTip("Remove all page assignments (cannot be undone)")

        self.preview_tree.setToolTip("Preview of the folder structure and documents that will be created")


    def _create_assignment_editor_panel(self) -> QWidget:
        """Create assignment editing panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Assign Selected Pages</h3>"))
        header_layout.addStretch()

        self.selected_pages_label = QLabel("No pages selected")
        self.selected_pages_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.selected_pages_label)

        layout.addLayout(header_layout)

        # Index fields editor
        fields_group = QGroupBox("Index Values")
        fields_layout = QVBoxLayout(fields_group)

        # Scroll area for fields
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.fields_widget = QWidget()
        self.fields_layout = QVBoxLayout(self.fields_widget)
        scroll_area.setWidget(self.fields_widget)

        fields_layout.addWidget(scroll_area)
        layout.addWidget(fields_group)

        # Assignment actions
        actions_layout = QHBoxLayout()

        self.assign_btn = QPushButton("Assign Pages")
        self.assign_btn.setEnabled(False)
        self.assign_btn.clicked.connect(self._assign_selected_pages)
        actions_layout.addWidget(self.assign_btn)

        self.clear_values_btn = QPushButton("Clear Values")
        self.clear_values_btn.clicked.connect(self._clear_field_values)
        actions_layout.addWidget(self.clear_values_btn)

        layout.addLayout(actions_layout)

        # Auto-assignment section
        auto_group = QGroupBox("Auto Assignment")
        auto_layout = QGridLayout(auto_group)

        auto_layout.addWidget(QLabel("Pages per document:"), 0, 0)
        self.pages_per_doc_spin = QComboBox()
        self.pages_per_doc_spin.addItems(["1", "2", "3", "4", "5", "10", "20"])
        self.pages_per_doc_spin.setCurrentText("1")
        auto_layout.addWidget(self.pages_per_doc_spin, 0, 1)

        self.auto_assign_btn = QPushButton("Auto Assign All")
        self.auto_assign_btn.clicked.connect(self._auto_assign_pages)
        auto_layout.addWidget(self.auto_assign_btn, 1, 0, 1, 2)

        layout.addWidget(auto_group)

        return panel

    def _create_assignment_list_panel(self) -> QWidget:
        """Create assignment list panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Current Assignments</h3>"))
        header_layout.addStretch()

        self.assignments_count_label = QLabel("0 assignments")
        header_layout.addWidget(self.assignments_count_label)

        layout.addLayout(header_layout)

        # Assignment list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.assignments_widget = QWidget()
        self.assignments_layout = QVBoxLayout(self.assignments_widget)
        self.assignments_layout.addStretch()  # Push items to top

        scroll_area.setWidget(self.assignments_widget)
        layout.addWidget(scroll_area)

        # Assignment actions
        actions_layout = QHBoxLayout()

        self.validate_all_btn = QPushButton("Validate All")
        self.validate_all_btn.clicked.connect(self._validate_all_assignments)
        actions_layout.addWidget(self.validate_all_btn)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self._clear_all_assignments)
        actions_layout.addWidget(self.clear_all_btn)

        layout.addLayout(actions_layout)

        return panel

    def _create_preview_panel(self) -> QWidget:
        """Create structure preview panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Header
        layout.addWidget(QLabel("<h3>Export Preview</h3>"))

        # Tree widget for structure preview
        self.preview_tree = QTreeWidget()
        self.preview_tree.setHeaderLabels(["Structure", "Pages"])
        self.preview_tree.setRootIsDecorated(True)
        layout.addWidget(self.preview_tree)

        # Summary info
        self.summary_label = QLabel("No assignments")
        self.summary_label.setStyleSheet("color: #666; font-size: 9pt;")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # Refresh button
        refresh_btn = QPushButton("Refresh Preview")
        refresh_btn.clicked.connect(self._refresh_preview)
        layout.addWidget(refresh_btn)

        return panel

    def _connect_signals(self):
        """Connect internal signals"""
        pass

    def set_current_batch(self, batch: DocumentBatch):
        """Set current document batch"""
        self.current_batch = batch
        self._update_display()

    def set_current_schema(self, schema: DynamicIndexSchema):
        """Set current index schema"""
        self.current_schema = schema
        self._rebuild_field_editors()
        self._update_display()

    def set_selected_pages(self, page_ids: List[str]):
        """Set currently selected pages"""
        self.selected_page_ids = page_ids
        self.assign_btn.setEnabled(len(page_ids) > 0 and self.current_schema is not None)

        if page_ids:
            self.selected_pages_label.setText(f"{len(page_ids)} pages selected")
        else:
            self.selected_pages_label.setText("No pages selected")

    def update_assignments(self, assignments: List[PageAssignment]):
        """Update the assignments display"""
        # Clear existing assignment widgets
        for i in reversed(range(self.assignments_layout.count() - 1)):  # Keep stretch at end
            item = self.assignments_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        self.assignment_widgets.clear()

        # Add new assignment widgets
        for assignment in assignments:
            widget = AssignmentWidget(assignment)
            widget.assignment_selected.connect(self._on_assignment_selected)
            widget.assignment_edited.connect(self._on_assignment_edited)
            widget.assignment_deleted.connect(self._on_assignment_deleted)

            self.assignment_widgets[assignment.assignment_id] = widget
            self.assignments_layout.insertWidget(self.assignments_layout.count() - 1, widget)

        # Update count
        self.assignments_count_label.setText(f"{len(assignments)} assignments")

    def _rebuild_field_editors(self):
        """Rebuild field value editors based on current schema"""
        # Clear existing editors
        for i in reversed(range(self.fields_layout.count())):
            item = self.fields_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        self.field_editors.clear()

        if not self.current_schema:
            return

        # Create editors for each field
        for field in sorted(self.current_schema.fields, key=lambda x: x.order):
            editor_widget = QWidget()
            editor_layout = QHBoxLayout(editor_widget)
            editor_layout.setContentsMargins(0, 5, 0, 5)

            # Field label with type indicator
            type_indicators = {
                "folder": "📁",
                "filename": "📄",
                "metadata": "🏷️"
            }

            icon = type_indicators.get(field.field_type.value, "")
            label_text = f"{icon} {field.name}:"
            if field.is_required:
                label_text += " *"

            label = QLabel(label_text)
            label.setMinimumWidth(120)
            label.setStyleSheet("font-weight: bold;")
            editor_layout.addWidget(label)

            # Value editor
            editor = QLineEdit()
            editor.setText(field.default_value)
            editor.setPlaceholderText(f"Enter {field.name.lower()}...")
            editor.textChanged.connect(self._on_field_value_changed)

            # Add validation styling if field has validation rules
            if field.validation_rules.allowed_values:
                editor.setToolTip(f"Allowed values: {', '.join(field.validation_rules.allowed_values)}")

            self.field_editors[field.name] = editor
            editor_layout.addWidget(editor)

            self.fields_layout.addWidget(editor_widget)

    def _on_field_value_changed(self):
        """Handle field value changes"""
        # Enable assign button if we have pages selected and values filled
        has_values = any(editor.text().strip() for editor in self.field_editors.values())
        has_pages = len(self.selected_page_ids) > 0
        self.assign_btn.setEnabled(has_values and has_pages)

    def _assign_selected_pages(self):
        """Assign current field values to selected pages"""
        if not self.selected_page_ids or not self.current_schema:
            return

        # Collect field values
        values = {}
        for field_name, editor in self.field_editors.items():
            values[field_name] = editor.text().strip()

        # Emit signal for controller to handle
        self.assignment_requested.emit(self.selected_page_ids, values)

    def _clear_field_values(self):
        """Clear all field values"""
        for editor in self.field_editors.values():
            editor.clear()

    def _auto_assign_pages(self):
        """Auto-assign all pages with current values"""
        if not self.current_batch or not self.current_schema:
            QMessageBox.warning(self, "Auto Assignment", "No batch or schema loaded")
            return

        pages_per_doc = int(self.pages_per_doc_spin.currentText())

        # Get base values from current field editors
        base_values = {}
        for field_name, editor in self.field_editors.items():
            base_values[field_name] = editor.text().strip()

        # Check if we have any values
        if not any(base_values.values()):
            QMessageBox.warning(self, "Auto Assignment", "Please fill in at least one field value")
            return

        # Get all page IDs
        all_page_ids = [page.page_id for page in self.current_batch.scanned_pages]

        # Create assignments for each group
        for i in range(0, len(all_page_ids), pages_per_doc):
            page_group = all_page_ids[i:i + pages_per_doc]

            # Create values with document number for differentiation
            values = base_values.copy()
            doc_number = (i // pages_per_doc) + 1

            # Add document number to filename fields
            filename_fields = self.current_schema.get_filename_components()
            if filename_fields:
                # Add to first filename field
                first_field = filename_fields[0]
                current_value = values.get(first_field.name, "")
                if current_value:
                    values[first_field.name] = f"{current_value}_Doc{doc_number:03d}"
                else:
                    values[first_field.name] = f"Doc{doc_number:03d}"

            # Request assignment
            self.assignment_requested.emit(page_group, values)

    def _validate_all_assignments(self):
        """Validate all current assignments"""
        # This will be handled by the controller
        # For now, just show a message
        QMessageBox.information(self, "Validation", "Assignment validation requested")

    def _clear_all_assignments(self):
        """Clear all assignments"""
        reply = QMessageBox.question(
            self,
            "Clear All Assignments",
            "Are you sure you want to clear all page assignments?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Clear assignment widgets
            for widget in self.assignment_widgets.values():
                widget.setParent(None)
            self.assignment_widgets.clear()
            self.assignments_count_label.setText("0 assignments")

    def _on_assignment_selected(self, assignment_id: str):
        """Handle assignment selection"""
        self.selected_assignment_id = assignment_id
        # Could highlight related pages in grid view
        # This would need to be connected to the document grid

    def _on_assignment_edited(self, assignment_id: str):
        """Handle assignment edit request"""
        # Load assignment values into field editors for editing
        if assignment_id in self.assignment_widgets:
            assignment = self.assignment_widgets[assignment_id].assignment

            # Fill field editors with assignment values
            for field_name, value in assignment.index_values.items():
                if field_name in self.field_editors:
                    self.field_editors[field_name].setText(value)

            # Set selected pages to assignment pages
            self.set_selected_pages(assignment.page_ids)

            # Store for update instead of create
            self.selected_assignment_id = assignment_id

            # Change button text to indicate update mode
            self.assign_btn.setText("Update Assignment")
            self.assign_btn.clicked.disconnect()
            self.assign_btn.clicked.connect(self._update_selected_assignment)

    def _update_selected_assignment(self):
        """Update the currently selected assignment"""
        if not self.selected_assignment_id:
            return

        # Collect field values
        values = {}
        for field_name, editor in self.field_editors.items():
            values[field_name] = editor.text().strip()

        # Emit update signal
        self.assignment_updated.emit(self.selected_assignment_id, values)

        # Reset to create mode
        self._reset_to_create_mode()

    def _reset_to_create_mode(self):
        """Reset interface to create mode"""
        self.selected_assignment_id = None
        self.assign_btn.setText("Assign Pages")
        self.assign_btn.clicked.disconnect()
        self.assign_btn.clicked.connect(self._assign_selected_pages)

    def _on_assignment_deleted(self, assignment_id: str):
        """Handle assignment deletion"""
        reply = QMessageBox.question(
            self,
            "Delete Assignment",
            "Are you sure you want to delete this assignment?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.assignment_deleted.emit(assignment_id)

    def _refresh_preview(self):
        """Refresh the export structure preview"""
        if not self.current_schema or not self.assignment_widgets:
            self.preview_tree.clear()
            self.summary_label.setText("No assignments")
            return

        self.preview_tree.clear()

        # Group assignments by folder structure
        folder_groups = {}
        total_docs = 0
        total_pages = 0

        for widget in self.assignment_widgets.values():
            assignment = widget.assignment
            folder_path = assignment.folder_path_preview or "Root"

            if folder_path not in folder_groups:
                folder_groups[folder_path] = []

            folder_groups[folder_path].append(assignment)
            total_docs += 1
            total_pages += len(assignment.page_ids)

        # Populate tree
        for folder_path, assignments in folder_groups.items():
            # Create folder item
            folder_item = QTreeWidgetItem(self.preview_tree)
            folder_item.setText(0, f"📁 {folder_path}")
            folder_item.setText(1, f"{len(assignments)} docs")

            # Add document items
            for assignment in assignments:
                doc_item = QTreeWidgetItem(folder_item)
                doc_item.setText(0, f"📄 {assignment.document_name_preview}")
                doc_item.setText(1, f"{len(assignment.page_ids)} pages")

        # Expand all items
        self.preview_tree.expandAll()

        # Update summary
        self.summary_label.setText(
            f"Export will create {total_docs} documents from {total_pages} pages"
        )

    def _update_display(self):
        """Update the entire display"""
        self._rebuild_field_editors()
        self._refresh_preview()

    def show_validation_errors(self, errors: List[ValidationError]):
        """Show validation errors to user"""
        if not errors:
            return

        error_text = "Validation Errors:\n\n"
        for error in errors:
            error_text += f"• Assignment {error.assignment_id[:8]}...\n"
            error_text += f"  Field '{error.field_name}': {error.error_message}\n"
            error_text += f"  Pages: {len(error.page_ids)}\n\n"

        QMessageBox.warning(self, "Validation Errors", error_text)

    def show_assignment_conflicts(self, conflicts: List[AssignmentConflict]):
        """Show assignment conflicts to user"""
        if not conflicts:
            return

        conflict_text = "Assignment Conflicts:\n\n"
        for conflict in conflicts:
            conflict_text += f"• Page {conflict.page_id} is assigned to multiple documents\n"
            conflict_text += f"  Conflicting assignments: {len(conflict.conflicting_assignments)}\n\n"

        QMessageBox.warning(self, "Assignment Conflicts", conflict_text)

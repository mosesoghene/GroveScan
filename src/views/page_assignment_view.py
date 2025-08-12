from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QListWidget, QListWidgetItem, QPushButton, QLabel,
                               QTreeWidget, QTreeWidgetItem, QSplitter, QLineEdit,
                               QGridLayout, QScrollArea, QFrame, QMessageBox,
                               QComboBox, QTextEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from src.models.page_assignment import PageAssignment
from src.models.dynamic_index_schema import DynamicIndexSchema
from src.models.document_batch import DocumentBatch
from typing import List, Dict, Optional


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
        self._setup_ui()
        self._connect_signals()

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
        self._rebuild_field_
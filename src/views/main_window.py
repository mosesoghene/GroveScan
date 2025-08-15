from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QSplitter, QTabWidget, QStatusBar,
                               QMessageBox, QLabel, QTreeWidgetItem,
                               QDialogButtonBox, QTreeWidget, QDialog)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence

# Import our custom widgets and controllers
from src.controllers.app_controller import ApplicationController
from .enhanced_export_dialog import EnhancedExportPreviewDialog
from .export_dialog import ExportProgressDialog
from .settings_dialog import SettingsDialog
from .workflow_widget import WorkflowStatusWidget
from .dynamic_index_editor import DynamicIndexEditor
from .document_grid_view import DocumentGridView
from .page_assignment_view import PageAssignmentView
from .scanner_control_view import ScannerControlView
from .profile_dialog import ProfileManagerDialog, QuickProfileDialog
from src.models.scan_profile import ScanProfile, ExportSettings
from ..utils.error_handling import ErrorHandler
from ..utils.help_hints import HelpHintsManager
from ..utils.help_system import HelpManager, HelpDialog
from ..utils.settings_manager import SettingsManager, SettingsCategory


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Initialize application controller
        self.app_controller = ApplicationController()

        # UI components
        self.workflow_widget = None
        self.profile_editor = None
        self.document_grid = None
        self.assignment_view = None
        self.scanner_control = None

        # State tracking
        self.current_tab_index = 0

        self.error_handler = ErrorHandler()

        # Settings management
        self.settings_manager = SettingsManager()
        self.settings_manager.settings_changed.connect(self._on_settings_changed)

        self.help_manager = HelpManager()
        self.help_dialog = None

        self.help_hints_manager = HelpHintsManager()
        self.current_hint_widget = None

        self._setup_ui()
        self._connect_signals()
        self._setup_menu_and_toolbar()

        # Initialize with a timer to ensure everything is loaded
        QTimer.singleShot(100, self._initialize_application)

        self._restore_window_state()

    def _setup_ui(self):
        """Setup the main user interface"""
        self.setWindowTitle("Dynamic Scanner - Document Indexing System")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Central widget with splitter layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create main splitter (horizontal)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Workflow and controls
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)

        # Right panel - Main work area with tabs
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)

        # Set splitter proportions (25% left, 75% right)
        main_splitter.setSizes([350, 1050])
        layout.addWidget(main_splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Create or load a profile to begin")

    def _on_scan_error(self, error_message: str):
        """Handle scan errors"""
        self.scanner_control.show_error(error_message)
        self.status_bar.showMessage(f"Scan error: {error_message}")

    def _create_left_panel(self) -> QWidget:
        """Create the left control panel"""
        # Create scrollable left panel
        from PySide6.QtWidgets import QScrollArea

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Panel content widget
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)  # Add proper spacing
        layout.setContentsMargins(5, 5, 5, 5)

        # Workflow status widget
        self.workflow_widget = WorkflowStatusWidget()
        layout.addWidget(self.workflow_widget)

        # Scanner controls (initially hidden)
        self.scanner_control = ScannerControlView()
        self.scanner_control.setVisible(False)
        layout.addWidget(self.scanner_control)

        # Stretch to push everything up
        layout.addStretch()

        # Set panel as scroll area widget
        scroll_area.setWidget(panel)

        return scroll_area

    def _create_right_panel(self) -> QWidget:
        """Create the right main work area"""
        # Tab widget for different views
        self.tab_widget = QTabWidget()

        # Profile Editor Tab
        self.profile_editor = DynamicIndexEditor()
        self.tab_widget.addTab(self.profile_editor, "📋 Profile Editor")

        # Document Grid Tab
        self.document_grid = DocumentGridView()
        self.tab_widget.addTab(self.document_grid, "📄 Scanned Pages")

        # Page Assignment Tab
        self.assignment_view = PageAssignmentView()
        self.tab_widget.addTab(self.assignment_view, "🏷️ Page Assignment")

        # Connect tab changes
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        return self.tab_widget

    def _connect_signals(self):
        """Connect all signals between components"""

        # Application controller signals
        self.app_controller.application_state_changed.connect(self._on_application_state_changed)
        self.app_controller.workflow_step_completed.connect(self._on_workflow_step_completed)
        self.app_controller.critical_error.connect(self._on_critical_error)

        # Workflow widget signals
        self.workflow_widget.step_selected.connect(self._on_workflow_step_selected)
        self.workflow_widget.action_requested.connect(self._on_workflow_action_requested)

        # Profile editor signals
        self.profile_editor.profile_changed.connect(self._on_profile_changed)
        self.profile_editor.schema_changed.connect(self._on_schema_changed)

        # Scanner control signals
        self.scanner_control.device_selection_changed.connect(
            self.app_controller.scan_controller.connect_device
        )
        self.scanner_control.scan_requested.connect(
            self.app_controller.scan_controller.start_batch_scan
        )
        self.scanner_control.stop_scan_requested.connect(
            self.app_controller.scan_controller.stop_scanning
        )

        # Scanner controller signals
        self.app_controller.scan_controller.devices_discovered.connect(
            self.scanner_control.update_devices
        )
        self.app_controller.scan_controller.device_connected.connect(
            self.scanner_control.set_device_connected
        )
        self.app_controller.scan_controller.scan_progress.connect(
            self.scanner_control.update_scan_progress
        )
        self.app_controller.scan_controller.scan_completed.connect(
            self._on_scan_completed
        )
        self.app_controller.scan_controller.scan_error.connect(
            self._on_scan_error
        )
        self.app_controller.scan_controller.page_scanned.connect(
            self._on_page_scanned
        )

        # Document grid signals
        self.document_grid.page_selected.connect(self._on_pages_selected)
        self.document_grid.page_rotated.connect(
            self.app_controller.document_controller.rotate_page
        )
        self.document_grid.page_deleted.connect(
            self.app_controller.document_controller.delete_page
        )

        # Document controller signals
        self.app_controller.document_controller.batch_updated.connect(
            self._on_batch_updated
        )
        self.app_controller.document_controller.page_updated.connect(
            self.document_grid.refresh_page_display
        )

        # Page assignment signals
        self.assignment_view.assignment_requested.connect(
            self._on_assignment_requested
        )
        self.assignment_view.assignment_updated.connect(
            self._on_assignment_updated
        )
        self.assignment_view.assignment_deleted.connect(
            self._on_assignment_deleted
        )

        # Page assignment controller signals
        self.app_controller.page_assignment_controller.assignment_created.connect(
            lambda assignment: self.assignment_view.update_assignments(
                self.app_controller.page_assignment_controller.get_all_assignments()
            )
        )
        self.app_controller.page_assignment_controller.assignments_changed.connect(
            lambda: self.assignment_view.update_assignments(
                self.app_controller.page_assignment_controller.get_all_assignments()
            )
        )
        self.app_controller.page_assignment_controller.validation_errors.connect(
            self.assignment_view.show_validation_errors
        )

    def _setup_menu_and_toolbar(self):
        """Setup menu bar and toolbar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        new_profile_action = QAction("New Profile...", self)
        new_profile_action.setShortcut(QKeySequence.StandardKey.New)
        new_profile_action.triggered.connect(self._create_new_profile)
        file_menu.addAction(new_profile_action)

        load_profile_action = QAction("Load Profile...", self)
        load_profile_action.setShortcut(QKeySequence.StandardKey.Open)
        load_profile_action.triggered.connect(self._load_profile)
        file_menu.addAction(load_profile_action)

        file_menu.addSeparator()

        save_profile_action = QAction("Save Profile", self)
        save_profile_action.setShortcut(QKeySequence.StandardKey.Save)
        save_profile_action.triggered.connect(self._save_current_profile)
        file_menu.addAction(save_profile_action)

        file_menu.addSeparator()

        export_action = QAction("Export Documents...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_documents)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        clear_batch_action = QAction("Clear Current Batch", self)
        clear_batch_action.triggered.connect(self._clear_current_batch)
        edit_menu.addAction(clear_batch_action)

        clear_assignments_action = QAction("Clear All Assignments", self)
        clear_assignments_action.triggered.connect(self._clear_all_assignments)
        edit_menu.addAction(clear_assignments_action)

        # Scan menu
        scan_menu = menubar.addMenu("Scan")

        start_scan_action = QAction("Start Scanning", self)
        start_scan_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        start_scan_action.triggered.connect(self._start_scanning)
        scan_menu.addAction(start_scan_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        validate_action = QAction("Validate Assignments", self)
        validate_action.triggered.connect(self._validate_assignments)
        tools_menu.addAction(validate_action)

        preview_action = QAction("Preview Export Structure", self)
        preview_action.triggered.connect(self._preview_export_structure)

        tools_menu.addSeparator()

        preferences_action = QAction("Preferences...", self)
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        preferences_action.triggered.connect(self._show_preferences)
        tools_menu.addAction(preferences_action)

        tools_menu.addAction(preview_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        help_contents_action = QAction("Help Contents", self)
        help_contents_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_contents_action.triggered.connect(self._show_help)
        help_menu.addAction(help_contents_action)

        quick_start_action = QAction("Quick Start Guide", self)
        quick_start_action.triggered.connect(lambda: self._show_help("quick_start"))
        help_menu.addAction(quick_start_action)

        help_menu.addSeparator()

        context_help_action = QAction("Context Help", self)
        context_help_action.setShortcut(QKeySequence("F1"))
        context_help_action.triggered.connect(self._show_context_help)
        help_menu.addAction(context_help_action)

        help_menu.addSeparator()

        troubleshooting_action = QAction("Troubleshooting", self)
        troubleshooting_action.triggered.connect(lambda: self._show_help("troubleshooting_common"))
        help_menu.addAction(troubleshooting_action)

        help_menu.addSeparator()

        about_action = QAction("About Dynamic Scanner", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        about_action = QAction("About Dynamic Scanner", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _initialize_application(self):
        """Initialize application state"""
        # Start scanner device discovery
        self.app_controller.scan_controller.discover_devices()

        # Update initial state
        self._update_ui_state()

    def _on_application_state_changed(self, state_info: dict):
        """Handle application state changes"""
        # Update workflow widget
        self.workflow_widget.update_workflow_state(state_info)

        # Update UI based on state
        self._update_ui_state()

        # Update status bar
        self._update_status_bar(state_info)

        # Show contextual hints
        self._check_and_show_hints(state_info)

    def _check_and_show_hints(self, state_info: dict):
        """Check and show contextual help hints"""
        # Add scanner connection status to context
        context = state_info.copy()
        context["scanner_connected"] = len(self.app_controller.scan_controller.scanner_interface.discover_devices()) > 0

        # Check for hints to show
        hint_priorities = ["first_profile", "after_profile", "first_scan", "pages_scanned", "assignments_ready"]

        for hint_id in hint_priorities:
            if self.help_hints_manager.should_show_hint(hint_id, context):
                self._show_hint(hint_id)
                break  # Show only one hint at a time

    def _show_hint(self, hint_id: str):
        """Show a help hint"""
        # Remove existing hint
        if self.current_hint_widget:
            self.current_hint_widget.hide()
            self.current_hint_widget = None

        # Create and show new hint
        hint_widget = self.help_hints_manager.create_hint_widget(hint_id, self)
        if hint_widget:
            self.current_hint_widget = hint_widget

            # Position hint at top of window
            hint_widget.setParent(self)
            hint_widget.setGeometry(10, 80, self.width() - 20, 80)
            hint_widget.show_animated()

            # Auto-dismiss after 10 seconds
            QTimer.singleShot(10000, lambda: hint_widget._dismiss())


    def _on_workflow_step_completed(self, step_name: str):
        """Handle workflow step completion"""
        self.status_bar.showMessage(f"Completed: {step_name}", 3000)

    def _on_critical_error(self, error_message: str):
        """Handle critical errors"""
        # Log the error
        self.error_handler.logger.critical(f"Critical application error: {error_message}")

        # Show user-friendly message
        QMessageBox.critical(
            self,
            "Critical Error",
            f"A critical error has occurred:\n\n{error_message}\n\n" +
            "The application may need to be restarted. Please save any unsaved work."
        )
        self.status_bar.showMessage(f"Critical Error: {error_message}")

    def _on_workflow_step_selected(self, step_name: str):
        """Handle workflow step selection"""
        # Switch to appropriate tab based on step
        if step_name == "initial" or step_name == "profile_ready":
            self.tab_widget.setCurrentIndex(0)  # Profile Editor
        elif step_name == "scanned":
            self.tab_widget.setCurrentIndex(1)  # Document Grid
        elif step_name in ["assigned", "ready_to_export"]:
            self.tab_widget.setCurrentIndex(2)  # Page Assignment

    def _on_workflow_action_requested(self, action_name: str):
        """Handle workflow action requests"""
        action_handlers = {
            'create_profile': self._create_new_profile,
            'load_profile': self._load_profile,
            'start_scan': self._start_scanning,
            'edit_profile': lambda: self.tab_widget.setCurrentIndex(0),
            'assign_pages': lambda: self.tab_widget.setCurrentIndex(2),
            'validate_assignments': self._validate_assignments,
            'export_documents': self._export_documents,
            'preview_structure': self._preview_export_structure
        }

        handler = action_handlers.get(action_name)
        if handler:
            handler()

    def _on_profile_changed(self, profile: ScanProfile):
        """Handle profile changes"""
        # Update application controller
        self.app_controller.profile_controller.set_current_profile(profile)

        # Make sure assignment view has the schema
        self.assignment_view.set_current_schema(profile.schema)

        self.status_bar.showMessage(f"Profile '{profile.name}' loaded", 3000)

    def _on_schema_changed(self, schema):
        """Handle schema changes"""
        # Update assignment view with new schema
        self.assignment_view.set_current_schema(schema)

        # Also update the current profile's schema if we have one
        if self.app_controller.profile_controller.current_profile:
            self.app_controller.profile_controller.current_profile.schema = schema

    def _on_scan_completed(self, batch):
        """Handle scan completion"""
        self.scanner_control.finish_scan_feedback(True)
        self.status_bar.showMessage(f"Scan completed: {batch.batch_name} ({batch.total_pages} pages)", 5000)

        # Auto-switch to document grid tab
        self.tab_widget.setCurrentIndex(1)

    def _on_batch_updated(self, batch):
        """Handle batch updates"""
        # Update document grid
        self.document_grid.load_batch(batch)

        # Update assignment view with the batch
        self.assignment_view.set_current_batch(batch)

    def _on_assignment_requested(self, page_ids, index_values):
        """Handle assignment request from assignment view"""
        success = self.app_controller.page_assignment_controller.assign_pages_to_index(
            page_ids, index_values
        )
        if success:
            self.status_bar.showMessage(f"Assigned {len(page_ids)} pages to index values", 3000)
        else:
            self.status_bar.showMessage("Failed to assign pages", 3000)

    def _on_assignment_updated(self, assignment_id, index_values):
        """Handle assignment update from assignment view"""
        success = self.app_controller.page_assignment_controller.update_assignment_values(
            assignment_id, index_values
        )
        if success:
            self.status_bar.showMessage("Assignment updated successfully", 3000)
        else:
            self.status_bar.showMessage("Failed to update assignment", 3000)

    def _on_assignment_deleted(self, assignment_id):
        """Handle assignment deletion from assignment view"""
        success = self.app_controller.page_assignment_controller.remove_assignment(assignment_id)
        if success:
            self.status_bar.showMessage("Assignment deleted successfully", 3000)
        else:
            self.status_bar.showMessage("Failed to delete assignment", 3000)

    def _on_page_scanned(self, page):
        """Handle individual page scanned"""
        if self.app_controller.document_controller.current_batch:
            self.document_grid.add_page(page)

    def _on_pages_selected(self, page_ids):
        """Handle page selection in document grid"""
        self.assignment_view.set_selected_pages(page_ids)

        # Debug: Print page selection
        if page_ids:
            print(f"DEBUG: Selected {len(page_ids)} pages: {page_ids[:3]}...")  # Show first 3 IDs
        else:
            print("DEBUG: No pages selected")

    def _on_tab_changed(self, index):
        """Handle tab changes"""
        self.current_tab_index = index

        # Show/hide scanner controls based on tab
        if index == 1:  # Document Grid tab
            self.scanner_control.setVisible(True)
        else:
            self.scanner_control.setVisible(False)

    def _update_ui_state(self):
        """Update UI based on current application state"""
        state = self.app_controller.get_application_summary()

        # Enable/disable tabs based on workflow state
        has_profile = state['application_state'].get('has_profile', False)
        has_batch = state['application_state'].get('has_batch', False)

        # Document grid tab - only available after profile is loaded
        self.tab_widget.setTabEnabled(1, has_profile)

        # Assignment tab - only available after scanning
        self.tab_widget.setTabEnabled(2, has_profile and has_batch)

    def _update_status_bar(self, state_info: dict):
        """Update status bar with current state and help hints"""
        if state_info.get('ready_to_export', False):
            self.status_bar.showMessage("Ready to export documents • Press F1 for help")
        elif state_info.get('has_assignments', False):
            self.status_bar.showMessage("Pages assigned - validate and export • F1: Help")
        elif state_info.get('has_batch', False):
            self.status_bar.showMessage("Documents scanned - assign pages to index values • F1: Help")
        elif state_info.get('has_profile', False):
            self.status_bar.showMessage("Profile loaded - start scanning documents • F1: Help")
        else:
            self.status_bar.showMessage("Create or load a profile to begin • F1: Help")

    # Menu action handlers
    def _create_new_profile(self):
        """Create a new profile"""
        dialog = QuickProfileDialog(self)
        if dialog.exec() == QuickProfileDialog.DialogCode.Accepted:
            template_info = dialog.get_profile_template()

            # Create new profile with template
            from src.models.scan_profile import ScanProfile, ScannerSettings, ExportSettings
            profile = ScanProfile(
                name=template_info['name'],
                schema=template_info['schema'],
                scanner_settings=ScannerSettings(),
                export_settings=ExportSettings()
            )

            # Load into profile editor
            self.profile_editor.current_profile = profile
            self.profile_editor.set_schema(profile.schema)
            self.profile_editor._update_profile_display()

            # Switch to profile editor tab
            self.tab_widget.setCurrentIndex(0)

    def _load_profile(self):
        """Load an existing profile"""
        dialog = ProfileManagerDialog(self)
        dialog.profile_selected.connect(self._on_profile_loaded_from_manager)
        dialog.exec()

    def _on_profile_loaded_from_manager(self, profile: ScanProfile):
        """Handle profile loaded from manager"""
        # Load into profile editor
        self.profile_editor.current_profile = profile
        self.profile_editor.set_schema(profile.schema)
        self.profile_editor._update_profile_display()

        # Load saved field values
        if profile.filled_values:
            for field_name, value in profile.filled_values.items():
                if field_name in self.profile_editor.value_editors:
                    self.profile_editor.value_editors[field_name].setText(value)

        # Update preview
        self.profile_editor._update_preview()

        # Update assignment view with schema
        self.assignment_view.set_current_schema(profile.schema)

        # Notify application controller
        self.app_controller.profile_controller.set_current_profile(profile)

    def _save_current_profile(self):
        """Save the current profile"""
        if self.profile_editor.current_profile:
            success = self.app_controller.profile_controller.save_profile(
                self.profile_editor.current_profile
            )
            if success:
                QMessageBox.information(
                    self,
                    "Profile Saved",
                    f"Profile '{self.profile_editor.current_profile.name}' saved successfully!"
                )
        else:
            QMessageBox.warning(self, "No Profile", "No profile to save. Create a profile first.")

    def _start_scanning(self):
        """Start the scanning process"""
        if not self.app_controller.profile_controller.current_profile:
            QMessageBox.warning(self, "No Profile", "Please create or load a profile before scanning.")
            return

        # Show scanner controls and switch to document grid tab
        self.scanner_control.setVisible(True)
        self.tab_widget.setCurrentIndex(1)

        # Make sure scanner control buttons are in correct state
        # Don't start scan feedback until actual scan begins

    def _clear_current_batch(self):
        """Clear the current document batch"""
        reply = QMessageBox.question(
            self,
            "Clear Batch",
            "Are you sure you want to clear the current batch?\n\nThis will remove all scanned pages and assignments.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Reset application state
            self.app_controller.reset_application_state()

            # Clear UI components
            self.document_grid.load_batch(None)
            self.assignment_view.update_assignments([])

            self.status_bar.showMessage("Batch cleared", 3000)

    def _clear_all_assignments(self):
        """Clear all page assignments"""
        reply = QMessageBox.question(
            self,
            "Clear Assignments",
            "Are you sure you want to clear all page assignments?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.app_controller.page_assignment_controller.clear_all_assignments()
            self.status_bar.showMessage("All assignments cleared", 3000)

    def _validate_assignments(self):
        """Validate all current assignments"""
        errors = self.app_controller.page_assignment_controller.validate_all_assignments()

        if not errors:
            QMessageBox.information(
                self,
                "Validation Success",
                "All assignments are valid and ready for export!"
            )
        else:
            self.assignment_view.show_validation_errors(errors)

    def _preview_export_structure(self):
        """Preview the export structure"""
        can_export, message = self.app_controller.can_proceed_to_export()

        if not can_export:
            QMessageBox.warning(self, "Cannot Preview", message)
            return

        # Get export summary from controller
        assignments = self.app_controller.page_assignment_controller.get_all_assignments()
        export_controller = self.app_controller.get_export_controller()

        # Set up export controller
        # Set up export controller with default settings
        default_settings = ExportSettings()
        export_controller.set_export_settings(default_settings)
        export_controller.set_current_batch(self.app_controller.document_controller.current_batch)
        export_controller.set_current_schema(
            self.app_controller.profile_controller.current_profile.schema
        )


        default_settings = ExportSettings()
        export_controller.set_export_settings(default_settings)

        export_summary = export_controller.get_export_summary_for_assignments(assignments)
        preview = export_summary['preview']

        # Create simple preview dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Structure Preview")
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Structure", "Pages", "Size"])

        # Group by folders
        folder_groups = {}
        for group in preview['document_groups']:
            folder = group['folder_path'] or "Root"
            if folder not in folder_groups:
                folder_groups[folder] = []
            folder_groups[folder].append(group)

        # Populate tree
        for folder_path, groups in folder_groups.items():
            folder_item = QTreeWidgetItem(tree)
            folder_item.setText(0, f"📁 {folder_path}")
            folder_item.setText(1, f"{len(groups)} documents")

            total_pages = sum(g['page_count'] for g in groups)
            folder_item.setText(2, f"{total_pages} pages")

            for group in groups:
                doc_item = QTreeWidgetItem(folder_item)
                doc_item.setText(0, f"📄 {group['filename']}")
                doc_item.setText(1, f"{group['page_count']} pages")

                # Estimate size
                size_kb = group['page_count'] * 500
                size_text = f"{size_kb / 1024:.1f} MB" if size_kb > 1024 else f"{size_kb} KB"
                doc_item.setText(2, size_text)

        tree.expandAll()
        layout.addWidget(tree)

        # Summary label
        summary = QLabel(f"""Export Summary:
    - Total documents: {preview['total_documents']}
    - Total pages: {preview['total_pages']}
    - Folders to create: {preview['folder_structure']['total_folders']}
    - Estimated size: {export_summary.get('estimated_file_size_mb', 0):.1f} MB""")
        layout.addWidget(summary)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def _export_documents(self):
        """Export the organized documents with enhanced template support"""
        can_export, message = self.app_controller.can_proceed_to_export()

        if not can_export:
            QMessageBox.warning(self, "Cannot Export", message)
            return

        # Get export summary from controller
        assignments = self.app_controller.page_assignment_controller.get_all_assignments()

        # Use enhanced export controller
        from src.controllers.export_controller import DocumentExportController
        export_controller = DocumentExportController()

        # Set up export controller
        export_controller.set_current_batch(self.app_controller.document_controller.current_batch)
        export_controller.set_current_schema(
            self.app_controller.profile_controller.current_profile.schema
        )

        export_summary = export_controller.get_export_summary_for_assignments(assignments)

        # Show enhanced export preview dialog
        preview_dialog = EnhancedExportPreviewDialog(export_summary, self)
        preview_dialog.export_confirmed.connect(self._start_enhanced_export)
        preview_dialog.exec()

    def _start_enhanced_export(self, output_dir: str, template):
        """Start export with enhanced template support"""
        try:
            # Create enhanced export controller
            from src.controllers.export_controller import DocumentExportController, ExportWorker

            assignments = self.app_controller.page_assignment_controller.get_all_assignments()
            batch = self.app_controller.document_controller.current_batch

            # Generate export groups
            export_controller = DocumentExportController()
            export_controller.set_current_batch(batch)
            export_controller.set_current_schema(
                self.app_controller.profile_controller.current_profile.schema
            )

            export_groups = export_controller.generate_export_groups(assignments)

            if not export_groups:
                QMessageBox.warning(self, "Export Error", "No valid document groups to export.")
                return

            # Show progress dialog
            total_docs = len(export_groups)
            progress_dialog = ExportProgressDialog(total_docs, self)

            # Create enhanced export worker
            export_worker = ExportWorker(
                export_groups=export_groups,
                template=template,
                output_dir=output_dir,
                batch=batch
            )

            # Connect signals
            export_worker.export_progress.connect(progress_dialog.update_progress)
            export_worker.document_exported.connect(progress_dialog.document_exported)
            export_worker.export_error.connect(progress_dialog.export_error)
            export_worker.export_completed.connect(progress_dialog.export_completed)
            export_worker.export_completed.connect(self._on_enhanced_export_completed)
            export_worker.memory_warning.connect(self._on_export_memory_warning)

            # Connect cancel signal
            progress_dialog.export_cancelled.connect(export_worker.stop)

            # Start export
            export_worker.start()
            progress_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred during export:\n{str(e)}")

    def _on_enhanced_export_completed(self, success_count: int, total_count: int):
        """Handle enhanced export completion"""
        if success_count == total_count:
            self.status_bar.showMessage(f"Export completed successfully! {success_count} documents exported.", 5000)
        else:
            failed_count = total_count - success_count
            self.status_bar.showMessage(
                f"Export completed with issues. {success_count} successful, {failed_count} failed.", 5000)

    def _on_export_memory_warning(self, warning_message: str):
        """Handle export memory warnings"""
        print(f"Export memory warning: {warning_message}")
        self.status_bar.showMessage(f"Memory warning: {warning_message}", 3000)


    def _start_export_with_settings(self, output_dir: str, export_settings: dict):
        """Start export with specified settings"""
        try:
            # Start export process
            success = self.app_controller.start_export_process(output_dir, export_settings)

            if not success:
                QMessageBox.warning(self, "Export Error", "Failed to start export process.")
                return

            # Get assignments for progress tracking
            assignments = self.app_controller.page_assignment_controller.get_all_assignments()
            total_docs = len([a for a in assignments if a.page_ids])

            # Show progress dialog
            progress_dialog = ExportProgressDialog(total_docs, self)

            # Connect export controller signals to progress dialog
            export_controller = self.app_controller.get_export_controller()
            export_controller.export_progress.connect(progress_dialog.update_progress)
            export_controller.document_exported.connect(progress_dialog.document_exported)
            export_controller.export_error.connect(progress_dialog.export_error)
            export_controller.export_completed.connect(progress_dialog.export_completed)
            export_controller.export_completed.connect(self._on_export_process_completed)

            # Connect cancel signal
            progress_dialog.export_cancelled.connect(export_controller.stop_export)

            progress_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred during export:\n{str(e)}")

    def _on_export_process_completed(self, summary: dict):
        """Handle export process completion"""
        success_count = summary.get('successful_exports', 0)
        total_count = summary.get('total_documents', 0)

        if success_count == total_count:
            self.status_bar.showMessage(f"Export completed successfully! {success_count} documents exported.", 5000)
        else:
            failed_count = summary.get('failed_exports', 0)
            self.status_bar.showMessage(
                f"Export completed with issues. {success_count} successful, {failed_count} failed.", 5000)

    def _restore_window_state(self):
        """Restore window state from settings"""
        try:
            ui_settings = self.settings_manager.get_ui_settings()

            # Restore window geometry
            x, y, width, height = ui_settings.window_geometry
            self.setGeometry(x, y, width, height)

            if ui_settings.window_maximized:
                self.showMaximized()

            # Restore current tab
            if ui_settings.current_tab < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(ui_settings.current_tab)

        except Exception as e:
            self.error_handler.handle_error(e, "Restore window state")

    def _save_window_state(self):
        """Save current window state to settings"""
        try:
            # Save window geometry
            geometry = (self.x(), self.y(), self.width(), self.height())
            self.settings_manager.set(SettingsCategory.UI, 'window_geometry', geometry)

            # Save maximized state
            self.settings_manager.set(SettingsCategory.UI, 'window_maximized', self.isMaximized())

            # Save current tab
            self.settings_manager.set(SettingsCategory.UI, 'current_tab', self.tab_widget.currentIndex())

        except Exception as e:
            self.error_handler.handle_error(e, "Save window state")

    def _on_settings_changed(self, category: str, key: str, value):
        """Handle settings changes"""
        if category == "ui":
            self._apply_ui_settings()
        elif category == "scanner":
            self._apply_scanner_settings()
        elif category == "export":
            self._apply_export_settings()

    def _apply_ui_settings(self):
        """Apply UI settings changes"""
        ui_settings = self.settings_manager.get_ui_settings()

        # Apply theme changes
        if ui_settings.theme == "dark":
            self.setStyleSheet(self._get_dark_theme_stylesheet())
        elif ui_settings.theme == "light":
            self.setStyleSheet(self._get_light_theme_stylesheet())
        else:
            self.setStyleSheet("")

    def _get_dark_theme_stylesheet(self) -> str:
        """Get dark theme stylesheet"""
        return """
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QTabWidget::pane {
                background-color: #3c3c3c;
                border: 1px solid #555;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
        """

    def _show_preferences(self):
        """Show preferences dialog"""
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.settings_applied.connect(self._on_settings_applied)
        dialog.exec()

    def _on_settings_applied(self):
        """Handle settings being applied"""
        self.status_bar.showMessage("Settings applied successfully", 3000)

    def _show_help(self, topic_id: str = None):
        """Show help dialog"""
        if self.help_dialog is None:
            self.help_dialog = HelpDialog(self.help_manager, topic_id, self)
        else:
            if topic_id:
                self.help_dialog._show_topic(topic_id)

        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def _show_context_help(self):
        """Show context-sensitive help based on current tab"""
        current_tab = self.tab_widget.currentIndex()

        help_topics = {
            0: "profiles_overview",  # Profile Editor
            1: "scanning_tips",  # Scanned Pages
            2: "page_assignment_guide"  # Page Assignment
        }

        topic_id = help_topics.get(current_tab, "quick_start")
        self._show_help(topic_id)

    def keyPressEvent(self, event):
        """Handle global key presses"""
        if event.key() == Qt.Key.Key_F1:
            self._show_context_help()
            event.accept()
            return

        super().keyPressEvent(event)

    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Dynamic Scanner",
            """
            <h2>Dynamic Scanner v1.0</h2>
            <p>A batch document scanner application with dynamic indexing.</p>

            <p><b>Features:</b></p>
            <ul>
            <li>Flexible document indexing with custom fields</li>
            <li>Batch scanning with page assignment</li>
            <li>Automatic folder structure generation</li>
            <li>Profile-based workflows</li>
            </ul>

            <p>Built with PySide6 and Python</p>
            """
        )

    def closeEvent(self, event):
        """Handle application close"""
        # Clean up any temporary files
        if self.app_controller.document_controller.current_batch:
            self.app_controller.document_controller.current_batch.cleanup_all_files()

        self._save_window_state()
        event.accept()
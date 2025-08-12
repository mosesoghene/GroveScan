from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QMenuBar, QStatusBar, QToolBar, QSplitter,
                               QLabel, QProgressBar, QDockWidget, QTabWidget,
                               QMessageBox, QDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from .scanner_control_view import ScannerControlView
from .document_grid_view import DocumentGridView
from .dynamic_index_editor import DynamicIndexEditor
from .page_assignment_view import PageAssignmentView
from .profile_dialog import ProfileInfoDialog, ProfileManagerDialog, QuickProfileDialog
from ..controllers.scan_controller import ScanController
from ..controllers.document_controller import DocumentController
from ..controllers.profile_controller import ProfileController
from ..controllers.page_assignment_controller import PageAssignmentController


class MainWindow(QMainWindow):
    """Main application window with integrated Phase 3 functionality"""

    # Signals for communication between components
    profile_changed = Signal(object)  # ScanProfile
    scan_requested = Signal()
    export_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Scanner - Phase 3 Complete")
        self.setGeometry(100, 100, 1600, 1000)

        # Initialize controllers
        self.scan_controller = ScanController()
        self.document_controller = DocumentController()
        self.profile_controller = ProfileController()
        self.page_assignment_controller = PageAssignmentController()

        # Initialize UI components
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_dock_widgets()
        self._setup_status_bar()

        # Connect signals
        self._connect_signals()

        # Load available profiles on startup
        self.profile_controller.get_available_profiles()

    def _setup_central_widget(self):
        """Create main application layout with tabs"""
        # Create tab widget as central widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Document Grid Tab
        self.document_grid_view = DocumentGridView()
        self.tab_widget.addTab(self.document_grid_view, "📄 Document Pages")

        # Index Editor Tab
        self.index_editor = DynamicIndexEditor()
        self.tab_widget.addTab(self.index_editor, "⚙️ Index Configuration")

        # Page Assignment Tab
        self.page_assignment_view = PageAssignmentView()
        self.tab_widget.addTab(self.page_assignment_view, "🏷️ Page Assignment")

    def _setup_dock_widgets(self):
        """Setup dockable widgets"""
        # Scanner Control Dock
        scanner_dock = QDockWidget("Scanner Control", self)
        scanner_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self.scanner_control_view = ScannerControlView()
        scanner_dock.setWidget(self.scanner_control_view)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, scanner_dock)

    def _setup_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        self.new_profile_action = QAction("&New Profile...", self)
        self.new_profile_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_profile_action.triggered.connect(self._new_profile)
        file_menu.addAction(self.new_profile_action)

        self.quick_profile_action = QAction("&Quick Profile Setup...", self)
        self.quick_profile_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.quick_profile_action.triggered.connect(self._quick_profile_setup)
        file_menu.addAction(self.quick_profile_action)

        self.open_profile_action = QAction("&Open Profile...", self)
        self.open_profile_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_profile_action.triggered.connect(self._load_profile)
        file_menu.addAction(self.open_profile_action)

        self.save_profile_action = QAction("&Save Profile", self)
        self.save_profile_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_profile_action.triggered.connect(self._save_profile)
        self.save_profile_action.setEnabled(False)
        file_menu.addAction(self.save_profile_action)

        self.save_profile_as_action = QAction("Save Profile &As...", self)
        self.save_profile_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_profile_as_action.triggered.connect(self._save_profile_as)
        file_menu.addAction(self.save_profile_as_action)

        file_menu.addSeparator()

        self.manage_profiles_action = QAction("&Manage Profiles...", self)
        self.manage_profiles_action.triggered.connect(self._manage_profiles)
        file_menu.addAction(self.manage_profiles_action)

        file_menu.addSeparator()

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")

        self.add_field_action = QAction("&Add Index Field", self)
        self.add_field_action.setShortcut(QKeySequence("Ctrl+F"))
        self.add_field_action.triggered.connect(self._switch_to_index_editor)
        edit_menu.addAction(self.add_field_action)

        edit_menu.addSeparator()

        self.clear_assignments_action = QAction("&Clear All Assignments", self)
        self.clear_assignments_action.triggered.connect(self._clear_all_assignments)
        edit_menu.addAction(self.clear_assignments_action)

        # Scan Menu
        scan_menu = menubar.addMenu("&Scan")

        self.scan_action = QAction("&Start Scan", self)
        self.scan_action.setShortcut(QKeySequence("Ctrl+S"))
        self.scan_action.triggered.connect(self.scan_requested.emit)
        scan_menu.addAction(self.scan_action)

        self.stop_scan_action = QAction("S&top Scan", self)
        self.stop_scan_action.setShortcut(QKeySequence("Ctrl+T"))
        self.stop_scan_action.triggered.connect(self.scan_controller.stop_scanning)
        self.stop_scan_action.setEnabled(False)
        scan_menu.addAction(self.stop_scan_action)

        # Assignment Menu
        assignment_menu = menubar.addMenu("&Assignment")

        self.assign_pages_action = QAction("&Assign Selected Pages", self)
        self.assign_pages_action.setShortcut(QKeySequence("Ctrl+A"))
        self.assign_pages_action.triggered.connect(self._switch_to_assignment_view)
        assignment_menu.addAction(self.assign_pages_action)

        self.validate_assignments_action = QAction("&Validate All Assignments", self)
        self.validate_assignments_action.triggered.connect(self._validate_all_assignments)
        assignment_menu.addAction(self.validate_assignments_action)

        # Export Menu
        export_menu = menubar.addMenu("&Export")

        self.export_action = QAction("&Export Documents", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.triggered.connect(self.export_requested.emit)
        export_menu.addAction(self.export_action)

        self.preview_export_action = QAction("&Preview Export Structure", self)
        self.preview_export_action.triggered.connect(self._preview_export)
        export_menu.addAction(self.preview_export_action)

    def _setup_toolbar(self):
        """Create application toolbar"""
        toolbar = self.addToolBar("Main")

        toolbar.addAction(self.new_profile_action)
        toolbar.addAction(self.open_profile_action)
        toolbar.addAction(self.save_profile_action)
        toolbar.addSeparator()
        toolbar.addAction(self.add_field_action)
        toolbar.addAction(self.assign_pages_action)
        toolbar.addSeparator()
        toolbar.addAction(self.scan_action)
        toolbar.addAction(self.export_action)

    def _setup_status_bar(self):
        """Create status bar with indicators"""
        self.status_bar = self.statusBar()

        # Status message
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Current profile indicator
        self.profile_label = QLabel("No profile loaded")
        self.profile_label.setStyleSheet("QLabel { margin-left: 10px; }")
        self.status_bar.addPermanentWidget(self.profile_label)

        # Assignment summary
        self.assignment_summary_label = QLabel("No assignments")
        self.assignment_summary_label.setStyleSheet("QLabel { margin-left: 10px; }")
        self.status_bar.addPermanentWidget(self.assignment_summary_label)

    def _connect_signals(self):
        """Connect signals between components"""
        # Scanner Controller signals
        self.scan_controller.devices_discovered.connect(
            self.scanner_control_view.update_devices
        )
        self.scan_controller.device_connected.connect(
            self.scanner_control_view.set_device_connected
        )
        self.scan_controller.page_scanned.connect(
            self.document_grid_view.add_page
        )
        self.scan_controller.scan_progress.connect(
            self.scanner_control_view.update_scan_progress
        )
        self.scan_controller.scan_completed.connect(
            self._on_scan_completed
        )
        self.scan_controller.scan_error.connect(
            self.scanner_control_view.show_error
        )

        # Scanner Control View signals
        self.scanner_control_view.device_selection_changed.connect(
            self.scan_controller.connect_device
        )
        self.scanner_control_view.scan_requested.connect(
            self._on_scan_requested
        )
        self.scanner_control_view.stop_scan_requested.connect(
            self.scan_controller.stop_scanning
        )

        # Document Grid View signals
        self.document_grid_view.page_selected.connect(
            self.page_assignment_view.set_selected_pages
        )
        self.document_grid_view.page_rotated.connect(
            self.document_controller.rotate_page
        )
        self.document_grid_view.page_deleted.connect(
            self.document_controller.delete_page
        )
        self.document_grid_view.pages_reordered.connect(
            self.document_controller.reorder_pages
        )

        # Document Controller signals
        self.document_controller.batch_updated.connect(
            self._on_batch_updated
        )
        self.document_controller.page_updated.connect(
            self.document_grid_view.refresh_page_display
        )
        self.document_controller.operation_error.connect(
            self.show_status_message
        )

        # Index Editor signals
        self.index_editor.schema_changed.connect(
            self._on_schema_changed
        )
        self.index_editor.profile_changed.connect(
            self._on_profile_changed
        )
        self.index_editor.validation_error.connect(
            self.show_status_message
        )

        # Page Assignment View signals
        self.page_assignment_view.assignment_requested.connect(
            self._on_assignment_requested
        )
        self.page_assignment_view.assignment_updated.connect(
            self._on_assignment_updated
        )
        self.page_assignment_view.assignment_deleted.connect(
            self._on_assignment_deleted
        )

        # Page Assignment Controller signals
        self.page_assignment_controller.assignment_created.connect(
            self._on_assignment_created
        )
        self.page_assignment_controller.assignments_changed.connect(
            self._on_assignments_changed
        )
        self.page_assignment_controller.validation_errors.connect(
            self._on_validation_errors
        )
        self.page_assignment_controller.assignment_conflicts.connect(
            self._on_assignment_conflicts
        )
        self.page_assignment_controller.operation_error.connect(
            self.show_status_message
        )

        # Profile Controller signals
        self.profile_controller.profile_loaded.connect(
            self._on_profile_loaded
        )
        self.profile_controller.profile_saved.connect(
            self._on_profile_saved
        )
        self.profile_controller.operation_error.connect(
            self.show_status_message
        )
        self.profile_controller.validation_error.connect(
            self._on_profile_validation_error
        )

    def _on_scan_requested(self, settings, page_count, batch_name):
        """Handle scan request"""
        self.scanner_control_view.start_scan_feedback()
        self.show_progress(f"Starting scan of {page_count} pages...", page_count)
        self.scan_controller.start_batch_scan(settings, page_count, batch_name)
        self.stop_scan_action.setEnabled(True)
        self.scan_action.setEnabled(False)

    def _on_scan_completed(self, batch):
        """Handle scan completion"""
        self.scanner_control_view.finish_scan_feedback(True)
        self.hide_progress()

        # Set batch in controllers
        self.document_controller.set_current_batch(batch)
        self.page_assignment_controller.set_current_batch(batch)

        # Update assignment view
        self.page_assignment_view.set_current_batch(batch)

        self.show_status_message(f"Scan completed: {batch.total_pages} pages")
        self.stop_scan_action.setEnabled(False)
        self.scan_action.setEnabled(True)

        # Auto-switch to document grid view
        self.tab_widget.setCurrentIndex(0)

    def _on_batch_updated(self, batch):
        """Handle batch updates"""
        self.document_grid_view.load_batch(batch)
        self.page_assignment_view.set_current_batch(batch)

    def _on_schema_changed(self, schema):
        """Handle schema changes from index editor"""
        self.page_assignment_controller.set_current_schema(schema)
        self.page_assignment_view.set_current_schema(schema)

        # Update current profile if loaded
        if self.profile_controller.current_profile:
            self.profile_controller.update_profile_schema(
                self.profile_controller.current_profile,
                schema
            )

    def _on_profile_changed(self, profile):
        """Handle profile changes from index editor"""
        self.profile_controller.set_current_profile(profile)
        self._update_profile_display(profile)

    def _on_assignment_requested(self, page_ids, index_values):
        """Handle assignment request from page assignment view"""
        success = self.page_assignment_controller.assign_pages_to_index(page_ids, index_values)
        if success:
            self.show_status_message(f"Assigned {len(page_ids)} pages to new document")

    def _on_assignment_updated(self, assignment_id, index_values):
        """Handle assignment update request"""
        success = self.page_assignment_controller.update_assignment_values(assignment_id, index_values)
        if success:
            self.show_status_message("Assignment updated successfully")

    def _on_assignment_deleted(self, assignment_id):
        """Handle assignment deletion request"""
        success = self.page_assignment_controller.remove_assignment(assignment_id)
        if success:
            self.show_status_message("Assignment deleted")

    def _on_assignment_created(self, assignment):
        """Handle new assignment creation"""
        # Update assignment view
        assignments = self.page_assignment_controller.get_all_assignments()
        self.page_assignment_view.update_assignments(assignments)
        self._update_assignment_summary()

    def _on_assignments_changed(self):
        """Handle general assignment changes"""
        assignments = self.page_assignment_controller.get_all_assignments()
        self.page_assignment_view.update_assignments(assignments)
        self._update_assignment_summary()

    def _on_validation_errors(self, errors):
        """Handle validation errors"""
        self.page_assignment_view.show_validation_errors(errors)

    def _on_assignment_conflicts(self, conflicts):
        """Handle assignment conflicts"""
        self.page_assignment_view.show_assignment_conflicts(conflicts)

    def _on_profile_loaded(self, profile):
        """Handle profile loaded"""
        self._update_profile_display(profile)

        # Update index editor with profile schema
        self.index_editor.set_schema(profile.schema)

        # Update page assignment controller
        self.page_assignment_controller.set_current_schema(profile.schema)
        self.page_assignment_view.set_current_schema(profile.schema)

        # Apply profile defaults if available
        if profile.filled_values:
            self.page_assignment_controller.apply_profile_defaults(profile)

        self.save_profile_action.setEnabled(True)
        self.show_status_message(f"Profile '{profile.name}' loaded successfully")

    def _on_profile_saved(self, profile_name):
        """Handle profile saved"""
        self.show_status_message(f"Profile '{profile_name}' saved successfully")

    def _on_profile_validation_error(self, message, field_errors):
        """Handle profile validation errors"""
        error_text = f"{message}\n\n"
        for field, error in field_errors.items():
            error_text += f"• {field}: {error}\n"

        QMessageBox.warning(self, "Profile Validation Error", error_text)

    def _new_profile(self):
        """Create new profile"""
        dialog = ProfileInfoDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile_info = dialog.get_profile_info()
            profile = self.profile_controller.create_new_profile(
                profile_info['name'],
                profile_info['description']
            )
            if profile:
                # Set scanner and export settings
                profile.scanner_settings = profile_info['scanner_settings']
                profile.export_settings = profile_info['export_settings']

                # Switch to index editor for field setup
                self.tab_widget.setCurrentIndex(1)

    def _quick_profile_setup(self):
        """Quick profile setup with templates"""
        dialog = QuickProfileDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            template_info = dialog.get_profile_template()

            profile = self.profile_controller.create_new_profile(
                template_info['name'],
                f"Created from {template_info['template_key']} template"
            )

            if profile:
                # Set the template schema
                profile.schema = template_info['schema']
                self.profile_controller.update_profile_schema(profile, template_info['schema'])

                # Switch to index editor to show the template
                self.tab_widget.setCurrentIndex(1)

    def _load_profile(self):
        """Load existing profile"""
        dialog = ProfileManagerDialog(self)
        dialog.profile_selected.connect(self.profile_controller.set_current_profile)
        dialog.exec()

    def _save_profile(self):
        """Save current profile"""
        if self.profile_controller.current_profile:
            # Update profile with current schema from editor
            current_schema = self.index_editor.get_schema()
            field_values = self.index_editor.get_field_values()

            self.profile_controller.update_profile_schema(
                self.profile_controller.current_profile,
                current_schema
            )
            self.profile_controller.update_profile_values(
                self.profile_controller.current_profile,
                field_values
            )

            self.profile_controller.save_profile(self.profile_controller.current_profile)

    def _save_profile_as(self):
        """Save profile with new name"""
        current_profile = self.profile_controller.current_profile
        dialog = ProfileInfoDialog(self, current_profile)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile_info = dialog.get_profile_info()

            if current_profile:
                # Update existing profile
                current_profile.name = profile_info['name']
                current_profile.description = profile_info['description']
                current_profile.scanner_settings = profile_info['scanner_settings']
                current_profile.export_settings = profile_info['export_settings']

                # Update schema and values
                current_schema = self.index_editor.get_schema()
                field_values = self.index_editor.get_field_values()

                self.profile_controller.update_profile_schema(current_profile, current_schema)
                self.profile_controller.update_profile_values(current_profile, field_values)

                self.profile_controller.save_profile(current_profile, save_as=True)

    def _manage_profiles(self):
        """Open profile manager"""
        dialog = ProfileManagerDialog(self)
        dialog.profile_selected.connect(self.profile_controller.set_current_profile)
        dialog.profile_deleted.connect(self._on_profile_deleted)
        dialog.exec()

    def _switch_to_index_editor(self):
        """Switch to index editor tab"""
        self.tab_widget.setCurrentIndex(1)

    def _switch_to_assignment_view(self):
        """Switch to assignment view tab"""
        self.tab_widget.setCurrentIndex(2)

    def _clear_all_assignments(self):
        """Clear all page assignments"""
        reply = QMessageBox.question(
            self,
            "Clear All Assignments",
            "Are you sure you want to clear all page assignments?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.page_assignment_controller.clear_all_assignments()

    def _validate_all_assignments(self):
        """Validate all current assignments"""
        errors = self.page_assignment_controller.validate_all_assignments()
        if errors:
            self.page_assignment_view.show_validation_errors(errors)
        else:
            QMessageBox.information(self, "Validation Success", "All assignments are valid!")

    def _preview_export(self):
        """Preview export structure"""
        groups = self.page_assignment_controller.generate_export_preview()
        if groups:
            self.tab_widget.setCurrentIndex(2)  # Switch to assignment view to see preview
        else:
            QMessageBox.information(self, "Export Preview", "No assignments to preview")

    def _update_profile_display(self, profile):
        """Update profile display in status bar"""
        if profile:
            self.profile_label.setText(f"Profile: {profile.name}")
        else:
            self.profile_label.setText("No profile loaded")

    def _update_assignment_summary(self):
        """Update assignment summary in status bar"""
        summary = self.page_assignment_controller.get_assignment_summary()
        if summary['total_assignments'] > 0:
            self.assignment_summary_label.setText(
                f"{summary['total_assignments']} assignments, {summary['total_assigned_pages']} pages"
            )
        else:
            self.assignment_summary_label.setText("No assignments")

    def _on_profile_deleted(self, profile_name):
        """Handle profile deletion"""
        if (self.profile_controller.current_profile and
                self.profile_controller.current_profile.name == profile_name):
            self.profile_controller.current_profile = None
            self._update_profile_display(None)
            self.save_profile_action.setEnabled(False)

    def show_progress(self, message: str, maximum: int = 0):
        """Show progress bar with message"""
        self.status_label.setText(message)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

    def update_progress(self, value: int):
        """Update progress bar value"""
        self.progress_bar.setValue(value)

    def hide_progress(self):
        """Hide progress bar"""
        self.progress_bar.hide()
        self.status_label.setText("Ready")

    def show_status_message(self, message: str, timeout: int = 5000):
        """Show temporary status message"""
        self.status_bar.showMessage(message, timeout)

    def closeEvent(self, event):
        """Handle window close event"""
        # Check if there are unsaved changes
        if self.profile_controller.current_profile:
            # Could implement unsaved changes checking here
            pass

        # Cleanup any temporary files
        if self.document_controller.current_batch:
            self.document_controller.current_batch.cleanup_all_files()

        event.accept()
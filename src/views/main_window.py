from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QMenuBar, QStatusBar, QToolBar, QSplitter,
                               QLabel, QProgressBar, QDockWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from .scanner_control_view import ScannerControlView
from .document_grid_view import DocumentGridView
from ..controllers.scan_controller import ScanController
from ..controllers.document_controller import DocumentController


class MainWindow(QMainWindow):
    # Signals for communication between components
    profile_changed = Signal(object)  # ScanProfile
    scan_requested = Signal()
    export_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Scanner - Phase 2")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize controllers
        self.scan_controller = ScanController()
        self.document_controller = DocumentController()

        # Initialize UI components
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_dock_widgets()
        self._setup_status_bar()

        # Connect signals
        self._connect_signals()

    def _setup_dock_widgets(self):
        """Setup dockable widgets"""
        # Scanner Control Dock
        scanner_dock = QDockWidget("Scanner Control", self)
        scanner_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.scanner_control_view = ScannerControlView()
        scanner_dock.setWidget(self.scanner_control_view)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, scanner_dock)

    def _setup_central_widget(self):
        """Create main application layout"""
        # Document grid as central widget
        self.document_grid_view = DocumentGridView()
        self.setCentralWidget(self.document_grid_view)

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
            self.document_grid_view.load_batch
        )
        self.document_controller.page_updated.connect(
            self.document_grid_view.refresh_page_display
        )
        self.document_controller.operation_error.connect(
            self.show_status_message
        )

    def _on_scan_requested(self, settings, page_count, batch_name):
        """Handle scan request"""
        self.scanner_control_view.start_scan_feedback()
        self.show_progress(f"Starting scan of {page_count} pages...", page_count)
        self.scan_controller.start_batch_scan(settings, page_count, batch_name)

    def _on_scan_completed(self, batch):
        """Handle scan completion"""
        self.scanner_control_view.finish_scan_feedback(True)
        self.hide_progress()
        self.document_controller.set_current_batch(batch)
        self.show_status_message(f"Scan completed: {batch.total_pages} pages")

    # ... (rest of the methods remain the same as Phase 1)
    def _setup_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        self.new_profile_action = QAction("&New Profile...", self)
        self.new_profile_action.setShortcut(QKeySequence.StandardKey.New)
        file_menu.addAction(self.new_profile_action)

        self.open_profile_action = QAction("&Open Profile...", self)
        self.open_profile_action.setShortcut(QKeySequence.StandardKey.Open)
        file_menu.addAction(self.open_profile_action)

        self.save_profile_action = QAction("&Save Profile", self)
        self.save_profile_action.setShortcut(QKeySequence.StandardKey.Save)
        file_menu.addAction(self.save_profile_action)

        self.save_profile_as_action = QAction("Save Profile &As...", self)
        self.save_profile_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        file_menu.addAction(self.save_profile_as_action)

        file_menu.addSeparator()

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")

        self.add_field_action = QAction("&Add Index Field", self)
        self.add_field_action.setShortcut(QKeySequence("Ctrl+A"))
        edit_menu.addAction(self.add_field_action)

        # Scan Menu
        scan_menu = menubar.addMenu("&Scan")

        self.scan_action = QAction("&Start Scan", self)
        self.scan_action.setShortcut(QKeySequence("Ctrl+S"))
        self.scan_action.triggered.connect(self.scan_requested.emit)
        scan_menu.addAction(self.scan_action)

        # Export Menu
        export_menu = menubar.addMenu("&Export")

        self.export_action = QAction("&Export Documents", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.triggered.connect(self.export_requested.emit)
        export_menu.addAction(self.export_action)

    def _setup_toolbar(self):
        """Create application toolbar"""
        toolbar = self.addToolBar("Main")

        toolbar.addAction(self.new_profile_action)
        toolbar.addAction(self.open_profile_action)
        toolbar.addAction(self.save_profile_action)
        toolbar.addSeparator()
        toolbar.addAction(self.add_field_action)
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

    def update_profile_status(self, profile_name: str):
        """Update current profile indicator"""
        self.profile_label.setText(f"Profile: {profile_name}")

    def show_status_message(self, message: str, timeout: int = 5000):
        """Show temporary status message"""
        self.status_bar.showMessage(message, timeout)
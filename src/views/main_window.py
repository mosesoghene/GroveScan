from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QMenuBar, QStatusBar, QToolBar, QSplitter,
                               QLabel, QProgressBar)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence


class MainWindow(QMainWindow):
    # Signals for communication between components
    profile_changed = Signal(object)  # ScanProfile
    scan_requested = Signal()
    export_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Scanner - Phase 1")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize UI components
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()

        # Connect signals
        self._connect_signals()

    def _setup_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        self.new_profile_action = QAction("&New Profile...", self)
        self.new_profile_action.setShortcut(QKeySequence.New)
        file_menu.addAction(self.new_profile_action)

        self.open_profile_action = QAction("&Open Profile...", self)
        self.open_profile_action.setShortcut(QKeySequence.Open)
        file_menu.addAction(self.open_profile_action)

        self.save_profile_action = QAction("&Save Profile", self)
        self.save_profile_action.setShortcut(QKeySequence.Save)
        file_menu.addAction(self.save_profile_action)

        self.save_profile_as_action = QAction("Save Profile &As...", self)
        self.save_profile_as_action.setShortcut(QKeySequence.SaveAs)
        file_menu.addAction(self.save_profile_as_action)

        file_menu.addSeparator()

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
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

    def _setup_central_widget(self):
        """Create main application layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)

        # Create main splitter for resizable panels
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # Left panel - Index Configuration (will be implemented in Phase 3)
        self.index_panel = self._create_placeholder_panel("Index Configuration")
        self.main_splitter.addWidget(self.index_panel)

        # Right panel - Document Grid (will be implemented in Phase 2/4)
        self.document_panel = self._create_placeholder_panel("Document Management")
        self.main_splitter.addWidget(self.document_panel)

        # Set initial splitter sizes (30% left, 70% right)
        self.main_splitter.setSizes([300, 700])

    def _create_placeholder_panel(self, title: str) -> QWidget:
        """Create placeholder panel for future implementation"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        title_label = QLabel(f"{title}\n(Coming in future phases)")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #666;
                padding: 20px;
                border: 2px dashed #ccc;
                border-radius: 5px;
            }
        """)

        layout.addWidget(title_label)
        return panel

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

    def _connect_signals(self):
        """Connect internal signals"""
        # These will be connected to controllers in later phases
        pass

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
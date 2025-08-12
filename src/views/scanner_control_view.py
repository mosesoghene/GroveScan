from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QComboBox, QSpinBox, QLabel, QPushButton,
                               QProgressBar, QTextEdit, QGridLayout)
from PySide6.QtCore import pyqtSignal, Qt
from ..models.scan_profile import ScannerSettings
from ..models.scanner_interface import ScannerDevice
from typing import List


class ScannerControlView(QWidget):
    """Scanner control panel widget"""

    # Signals
    device_selection_changed = pyqtSignal(str)  # device_id
    scan_requested = pyqtSignal(object, int, str)  # ScannerSettings, page_count, batch_name
    stop_scan_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.available_devices = []
        self.is_scanning = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)

        # Device Selection Group
        device_group = QGroupBox("Scanner Device")
        device_layout = QVBoxLayout(device_group)

        self.device_combo = QComboBox()
        self.device_combo.addItem("No devices found", "")
        device_layout.addWidget(QLabel("Select Scanner:"))
        device_layout.addWidget(self.device_combo)

        self.refresh_devices_btn = QPushButton("Refresh Devices")
        device_layout.addWidget(self.refresh_devices_btn)

        layout.addWidget(device_group)

        # Scan Settings Group
        settings_group = QGroupBox("Scan Settings")
        settings_layout = QGridLayout(settings_group)

        # Resolution
        settings_layout.addWidget(QLabel("Resolution (DPI):"), 0, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["150", "200", "300", "400", "600", "1200"])
        self.resolution_combo.setCurrentText("300")
        settings_layout.addWidget(self.resolution_combo, 0, 1)

        # Color Mode
        settings_layout.addWidget(QLabel("Color Mode:"), 1, 0)
        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItems(["Color", "Grayscale", "Black&White"])
        settings_layout.addWidget(self.color_mode_combo, 1, 1)

        # Format
        settings_layout.addWidget(QLabel("Format:"), 2, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["TIFF", "PNG", "JPEG"])
        settings_layout.addWidget(self.format_combo, 2, 1)

        # Quality (for JPEG)
        settings_layout.addWidget(QLabel("Quality:"), 3, 0)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.setSuffix("%")
        settings_layout.addWidget(self.quality_spin, 3, 1)

        layout.addWidget(settings_group)

        # Batch Scan Group
        batch_group = QGroupBox("Batch Scanning")
        batch_layout = QGridLayout(batch_group)

        batch_layout.addWidget(QLabel("Number of Pages:"), 0, 0)
        self.page_count_spin = QSpinBox()
        self.page_count_spin.setRange(1, 100)
        self.page_count_spin.setValue(1)
        batch_layout.addWidget(self.page_count_spin, 0, 1)

        # Scan Control Buttons
        button_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setEnabled(False)
        self.stop_btn = QPushButton("Stop Scan")
        self.stop_btn.setEnabled(False)

        button_layout.addWidget(self.scan_btn)
        button_layout.addWidget(self.stop_btn)
        batch_layout.addLayout(button_layout, 1, 0, 1, 2)

        layout.addWidget(batch_group)

        # Progress Group
        progress_group = QGroupBox("Scan Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.append("Ready to scan...")
        progress_layout.addWidget(self.status_text)

        layout.addWidget(progress_group)

        # Enable quality control only for JPEG
        self.format_combo.currentTextChanged.connect(self._on_format_changed)

    def _connect_signals(self):
        """Connect internal signals"""
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.refresh_devices_btn.clicked.connect(self.device_selection_changed.emit)

    def _on_format_changed(self, format_name: str):
        """Handle format change"""
        self.quality_spin.setEnabled(format_name == "JPEG")

    def _on_device_changed(self):
        """Handle device selection change"""
        device_id = self.device_combo.currentData()
        if device_id:
            self.device_selection_changed.emit(device_id)

    def _on_scan_clicked(self):
        """Handle scan button click"""
        settings = self.get_scan_settings()
        page_count = self.page_count_spin.value()
        batch_name = f"Batch {page_count} pages"

        self.scan_requested.emit(settings, page_count, batch_name)

    def _on_stop_clicked(self):
        """Handle stop button click"""
        self.stop_scan_requested.emit()

    def get_scan_settings(self) -> ScannerSettings:
        """Get current scan settings"""
        return ScannerSettings(
            device_name=self.device_combo.currentText(),
            resolution=int(self.resolution_combo.currentText()),
            color_mode=self.color_mode_combo.currentText(),
            format=self.format_combo.currentText(),
            quality=self.quality_spin.value()
        )

    def update_devices(self, devices: List[ScannerDevice]):
        """Update available devices"""
        self.available_devices = devices
        self.device_combo.clear()

        if devices:
            for device in devices:
                self.device_combo.addItem(f"{device.name} ({device.manufacturer})", device.device_id)
            self.scan_btn.setEnabled(True)
        else:
            self.device_combo.addItem("No devices found", "")
            self.scan_btn.setEnabled(False)

    def set_device_connected(self, connected: bool, message: str):
        """Update device connection status"""
        self.append_status(message)
        self.scan_btn.setEnabled(connected and not self.is_scanning)

    def start_scan_feedback(self):
        """Update UI for scan start"""
        self.is_scanning = True
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.page_count_spin.value())
        self.progress_bar.setValue(0)

    def update_scan_progress(self, current: int, total: int, message: str):
        """Update scan progress"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.append_status(message)

    def finish_scan_feedback(self, success: bool = True):
        """Update UI for scan completion"""
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        if success:
            self.append_status("Scan completed successfully!")
        else:
            self.append_status("Scan stopped or failed.")

    def append_status(self, message: str):
        """Append message to status text"""
        self.status_text.append(message)
        # Auto-scroll to bottom
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )

    def show_error(self, error_message: str):
        """Show error message"""
        self.append_status(f"ERROR: {error_message}")
        self.finish_scan_feedback(False)
from PySide6.QtCore import QObject, pyqtSignal, QThread, QTimer
from typing import Optional, Callable, List
from ..models.scanner_interface import ScannerInterface, MockScannerInterface, ScannerDevice
from ..models.document_batch import DocumentBatch
from ..models.scan_profile import ScannerSettings
from ..models.scanned_page import ScannedPage
import uuid


class ScanWorker(QThread):
    """Worker thread for scanning operations"""
    page_scanned = pyqtSignal(object)  # ScannedPage
    scan_progress = pyqtSignal(int, int)  # current, total
    scan_error = pyqtSignal(str)
    scan_completed = pyqtSignal()

    def __init__(self, scanner: ScannerInterface, settings: ScannerSettings, page_count: int):
        super().__init__()
        self.scanner = scanner
        self.settings = settings
        self.page_count = page_count
        self.should_stop = False

    def run(self):
        """Run scanning in separate thread"""
        try:
            for i in range(self.page_count):
                if self.should_stop:
                    break

                # Scan page
                page = self.scanner.scan_page(self.settings)

                if page:
                    self.page_scanned.emit(page)
                    self.scan_progress.emit(i + 1, self.page_count)
                else:
                    self.scan_error.emit(f"Failed to scan page {i + 1}")
                    break

                # Small delay between pages
                self.msleep(500)

            self.scan_completed.emit()

        except Exception as e:
            self.scan_error.emit(f"Scanning error: {str(e)}")

    def stop(self):
        """Stop scanning"""
        self.should_stop = True


class ScanController(QObject):
    """Controller for scanning operations"""

    # Signals
    devices_discovered = pyqtSignal(list)  # List[ScannerDevice]
    device_connected = pyqtSignal(bool, str)  # success, message
    page_scanned = pyqtSignal(object)  # ScannedPage
    scan_progress = pyqtSignal(int, int, str)  # current, total, message
    scan_completed = pyqtSignal(object)  # DocumentBatch
    scan_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # For now, use mock scanner. In production, detect platform and use appropriate scanner
        self.scanner_interface = MockScannerInterface()
        self.current_device = None
        self.current_batch = None
        self.scan_worker = None

        # Auto-discover devices on startup
        QTimer.singleShot(1000, self.discover_devices)

    def discover_devices(self):
        """Discover available scanner devices"""
        try:
            devices = self.scanner_interface.discover_devices()
            self.devices_discovered.emit(devices)
        except Exception as e:
            self.scan_error.emit(f"Error discovering devices: {str(e)}")

    def connect_device(self, device_id: str):
        """Connect to a scanner device"""
        try:
            success = self.scanner_interface.connect_device(device_id)
            if success:
                devices = self.scanner_interface.discover_devices()
                self.current_device = next((d for d in devices if d.device_id == device_id), None)
                self.device_connected.emit(True, f"Connected to {self.current_device.name}")
            else:
                self.device_connected.emit(False, "Failed to connect to device")
        except Exception as e:
            self.device_connected.emit(False, f"Connection error: {str(e)}")

    def start_batch_scan(self, settings: ScannerSettings, page_count: int = 1, batch_name: str = ""):
        """Start scanning multiple pages"""
        if not self.scanner_interface.is_device_ready():
            self.scan_error.emit("No scanner device connected")
            return

        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_error.emit("Scan already in progress")
            return

        # Create new batch
        batch_id = str(uuid.uuid4())
        self.current_batch = DocumentBatch(
            batch_id=batch_id,
            batch_name=batch_name or f"Batch {batch_id[:8]}"
        )

        # Start scanning in worker thread
        self.scan_worker = ScanWorker(self.scanner_interface, settings, page_count)
        self.scan_worker.page_scanned.connect(self._on_page_scanned)
        self.scan_worker.scan_progress.connect(self._on_scan_progress)
        self.scan_worker.scan_error.connect(self._on_scan_error)
        self.scan_worker.scan_completed.connect(self._on_scan_completed)

        self.scan_worker.start()

    def stop_scanning(self):
        """Stop current scanning operation"""
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.stop()
            self.scan_worker.wait(3000)  # Wait up to 3 seconds

    def _on_page_scanned(self, page: ScannedPage):
        """Handle page scanned event"""
        if self.current_batch:
            self.current_batch.add_page(page)
            self.page_scanned.emit(page)

    def _on_scan_progress(self, current: int, total: int):
        """Handle scan progress"""
        message = f"Scanning page {current} of {total}"
        self.scan_progress.emit(current, total, message)

    def _on_scan_error(self, error_message: str):
        """Handle scan error"""
        self.scan_error.emit(error_message)

    def _on_scan_completed(self):
        """Handle scan completion"""
        if self.current_batch:
            self.scan_completed.emit(self.current_batch)

    def get_device_capabilities(self) -> dict:
        """Get current device capabilities"""
        if self.scanner_interface:
            return self.scanner_interface.get_device_capabilities()
        return {}

from PySide6.QtCore import QObject, Signal, QThread, QTimer
from typing import Optional, List
from ..models.scanner_interface import create_scanner_interface, get_scanner_backend_info
from ..models.document_batch import DocumentBatch
from ..models.scan_profile import ScannerSettings
from ..models.scanned_page import ScannedPage
import uuid

from ..utils.error_handling import ErrorHandler, ErrorSeverity


class ScanWorker(QThread):
    """Worker thread for scanning operations with PyInsane2 support"""
    page_scanned = Signal(object)  # ScannedPage
    scan_progress = Signal(int, int)  # current, total
    scan_error = Signal(str)
    scan_completed = Signal()

    def __init__(self, scanner_interface, settings: ScannerSettings, page_count: int):
        super().__init__()
        self.scanner_interface = scanner_interface
        self.settings = settings
        self.page_count = page_count
        self.should_stop = False

    def run(self):
        """Run scanning in separate thread"""
        try:
            print(f"Starting scan of {self.page_count} pages...")

            for i in range(self.page_count):
                if self.should_stop:
                    print("Scan stopped by user")
                    break

                print(f"Scanning page {i + 1} of {self.page_count}...")

                # Scan page
                page = self.scanner_interface.scan_page(self.settings)

                if page:
                    self.page_scanned.emit(page)
                    self.scan_progress.emit(i + 1, self.page_count)
                    print(f"Successfully scanned page {i + 1}")
                else:
                    error_msg = f"Failed to scan page {i + 1}"
                    print(error_msg)
                    self.scan_error.emit(error_msg)
                    break

                # Small delay between pages to allow UI updates and prevent device overload
                if not self.should_stop:
                    self.msleep(1000)  # 1 second delay

            if not self.should_stop:
                print("Scan batch completed successfully")
                self.scan_completed.emit()
            else:
                print("Scan batch was cancelled")

        except Exception as e:
            error_msg = f"Scanning error: {str(e)}"
            print(error_msg)
            self.scan_error.emit(error_msg)

    def stop(self):
        """Stop scanning"""
        print("Stopping scan...")
        self.should_stop = True


class ScanController(QObject):
    """Enhanced controller for scanning operations with PyInsane2 support"""

    # Signals
    devices_discovered = Signal(list)  # List[ScannerDevice]
    device_connected = Signal(bool, str)  # success, message
    page_scanned = Signal(object)  # ScannedPage
    scan_progress = Signal(int, int, str)  # current, total, message
    scan_completed = Signal(object)  # DocumentBatch
    scan_error = Signal(str)
    backend_info_updated = Signal(dict)  # backend information

    def __init__(self):
        super().__init__()

        # Get scanner backend info
        backend_info = get_scanner_backend_info()
        print(f"Scanner Controller initialized with backend: {backend_info['backend']}")

        # Create scanner interface
        self.scanner_interface = create_scanner_interface()

        self.current_device = None
        self.current_batch = None
        self.scan_worker = None
        self.error_handler = ErrorHandler()

        # Emit backend info
        self.backend_info_updated.emit(backend_info)

        # Auto-discover devices on startup with a delay
        QTimer.singleShot(2000, self.discover_devices)

    def get_backend_info(self) -> dict:
        """Get current scanner backend information"""
        return get_scanner_backend_info()

    def discover_devices(self):
        """Discover available scanner devices"""
        try:
            print("Discovering scanner devices...")
            devices = self.scanner_interface.discover_devices()

            print(f"Found {len(devices)} scanner devices:")
            for device in devices:
                print(f"  - {device.name} ({device.manufacturer}) [ID: {device.device_id}]")

            self.devices_discovered.emit(devices)

            if not devices:
                backend_info = get_scanner_backend_info()
                if backend_info['backend'] == 'mock':
                    print("No real scanners found - using mock scanner for testing")
                else:
                    print("No scanner devices found. Please check:")
                    print("  1. Scanner is connected and powered on")
                    print("  2. Scanner drivers are installed")
                    print("  3. PyInsane2 is properly installed")

        except Exception as e:
            error_msg = f"Failed to discover devices: {str(e)}"
            self.error_handler.handle_error(e, "Device discovery", ErrorSeverity.WARNING)
            self.scan_error.emit(error_msg)

            # Fall back to empty list
            self.devices_discovered.emit([])

    def connect_device(self, device_id: str):
        """Connect to a scanner device"""
        try:
            print(f"Connecting to device: {device_id}")
            success = self.scanner_interface.connect_device(device_id)

            if success:
                # Update current device info
                devices = self.scanner_interface.discover_devices()
                self.current_device = next((d for d in devices if d.device_id == device_id), None)

                if self.current_device:
                    success_msg = f"Connected to {self.current_device.name}"
                    print(success_msg)

                    # Get and display device capabilities
                    capabilities = self.scanner_interface.get_device_capabilities()
                    print(f"Device capabilities:")
                    print(f"  - Resolutions: {capabilities.get('resolutions', [])}")
                    print(f"  - Color modes: {capabilities.get('color_modes', [])}")
                    print(f"  - Formats: {capabilities.get('formats', [])}")

                    self.device_connected.emit(True, success_msg)
                else:
                    self.device_connected.emit(True, f"Connected to device {device_id}")
            else:
                error_msg = f"Failed to connect to device {device_id}"
                print(error_msg)
                self.device_connected.emit(False, error_msg)

        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            print(error_msg)
            self.error_handler.handle_error(e, "Device connection", ErrorSeverity.ERROR)
            self.device_connected.emit(False, error_msg)

    def start_batch_scan(self, settings: ScannerSettings, page_count: int = 1, batch_name: str = ""):
        """Start scanning multiple pages"""
        if not self.scanner_interface.is_device_ready():
            error_msg = "No scanner device connected. Please connect a device first."
            print(error_msg)
            self.scan_error.emit(error_msg)
            return

        if self.scan_worker and self.scan_worker.isRunning():
            error_msg = "Scan already in progress"
            print(error_msg)
            self.scan_error.emit(error_msg)
            return

        # Validate settings
        if not self._validate_scan_settings(settings):
            return

        try:
            # Create new batch
            batch_id = str(uuid.uuid4())
            self.current_batch = DocumentBatch(
                batch_id=batch_id,
                batch_name=batch_name or f"Batch {batch_id[:8]}"
            )

            print(f"Starting batch scan: {self.current_batch.batch_name}")
            print(f"Settings: {settings.resolution} DPI, {settings.color_mode}, {settings.format}")

            # Start scanning in worker thread
            self.scan_worker = ScanWorker(self.scanner_interface, settings, page_count)
            self.scan_worker.page_scanned.connect(self._on_page_scanned)
            self.scan_worker.scan_progress.connect(self._on_scan_progress)
            self.scan_worker.scan_error.connect(self._on_scan_error)
            self.scan_worker.scan_completed.connect(self._on_scan_completed)

            self.scan_worker.start()

        except Exception as e:
            error_msg = f"Failed to start scan: {str(e)}"
            print(error_msg)
            self.error_handler.handle_error(e, "Start scan", ErrorSeverity.ERROR)
            self.scan_error.emit(error_msg)

    def _validate_scan_settings(self, settings: ScannerSettings) -> bool:
        """Validate scan settings against device capabilities"""
        try:
            capabilities = self.scanner_interface.get_device_capabilities()

            # Check resolution
            supported_resolutions = capabilities.get('resolutions', [])
            if supported_resolutions and settings.resolution not in supported_resolutions:
                # Find closest supported resolution
                closest_res = min(supported_resolutions, key=lambda x: abs(x - settings.resolution))
                print(f"Warning: Resolution {settings.resolution} not supported. Using {closest_res} instead.")
                settings.resolution = closest_res

            # Check color mode
            supported_modes = capabilities.get('color_modes', [])
            if supported_modes and settings.color_mode not in supported_modes:
                print(f"Warning: Color mode '{settings.color_mode}' not supported. Available modes: {supported_modes}")
                if supported_modes:
                    settings.color_mode = supported_modes[0]
                    print(f"Using {settings.color_mode} instead.")

            return True

        except Exception as e:
            print(f"Warning: Could not validate scan settings: {e}")
            return True  # Continue with original settings

    def stop_scanning(self):
        """Stop current scanning operation"""
        if self.scan_worker and self.scan_worker.isRunning():
            print("Stopping scan operation...")
            self.scan_worker.stop()

            # Wait for worker to finish with timeout
            if not self.scan_worker.wait(5000):  # 5 second timeout
                print("Warning: Scan worker did not stop gracefully")
                self.scan_worker.terminate()
                self.scan_worker.wait()

    def _on_page_scanned(self, page: ScannedPage):
        """Handle page scanned event"""
        if self.current_batch:
            self.current_batch.add_page(page)
            print(f"Added page to batch: {page.page_id}")

        self.page_scanned.emit(page)

    def _on_scan_progress(self, current: int, total: int):
        """Handle scan progress"""
        message = f"Scanning page {current} of {total}"
        print(message)
        self.scan_progress.emit(current, total, message)

    def _on_scan_error(self, error_message: str):
        """Handle scan error"""
        print(f"Scan error: {error_message}")
        self.scan_error.emit(error_message)

    def _on_scan_completed(self):
        """Handle scan completion"""
        if self.current_batch:
            print(f"Scan completed: {self.current_batch.batch_name} with {self.current_batch.total_pages} pages")
            self.scan_completed.emit(self.current_batch)
        else:
            print("Scan completed but no batch was created")

    def get_device_capabilities(self) -> dict:
        """Get current device capabilities"""
        if self.scanner_interface:
            return self.scanner_interface.get_device_capabilities()
        return {}

    def is_device_connected(self) -> bool:
        """Check if a device is currently connected"""
        return self.scanner_interface.is_device_ready()

    def get_current_device(self):
        """Get information about the currently connected device"""
        return self.current_device

    def refresh_device_list(self):
        """Manually refresh the device list"""
        self.discover_devices()

    def test_device_connection(self, device_id: str) -> dict:
        """Test connection to a device without fully connecting"""
        try:
            # Try to get basic device info
            devices = self.scanner_interface.discover_devices()
            device = next((d for d in devices if d.device_id == device_id), None)

            if not device:
                return {
                    "success": False,
                    "message": f"Device {device_id} not found",
                    "details": {}
                }

            # Try a quick connection test
            test_success = self.scanner_interface.connect_device(device_id)

            if test_success:
                capabilities = self.scanner_interface.get_device_capabilities()
                return {
                    "success": True,
                    "message": f"Device {device.name} is ready",
                    "details": {
                        "name": device.name,
                        "manufacturer": device.manufacturer,
                        "model": device.model,
                        "capabilities": capabilities
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Could not connect to {device.name}",
                    "details": {"name": device.name}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Test failed: {str(e)}",
                "details": {}
            }

    def get_recommended_settings(self) -> ScannerSettings:
        """Get recommended scan settings based on device capabilities"""
        capabilities = self.get_device_capabilities()

        # Choose best resolution (prefer 300 DPI if available)
        resolutions = capabilities.get('resolutions', [300])
        recommended_resolution = 300 if 300 in resolutions else resolutions[len(resolutions) // 2]

        # Choose best color mode (prefer Color if available)
        color_modes = capabilities.get('color_modes', ['Color'])
        recommended_color = 'Color' if 'Color' in color_modes else color_modes[0]

        # Choose best format (prefer TIFF for quality)
        formats = capabilities.get('formats', ['TIFF'])
        recommended_format = 'TIFF' if 'TIFF' in formats else formats[0]

        return ScannerSettings(
            device_name=self.current_device.name if self.current_device else "",
            resolution=recommended_resolution,
            color_mode=recommended_color,
            format=recommended_format,
            quality=95
        )

    def preview_scan(self, settings: ScannerSettings) -> Optional[ScannedPage]:
        """Perform a quick preview scan (single page)"""
        if not self.scanner_interface.is_device_ready():
            self.scan_error.emit("No scanner device connected")
            return None

        try:
            print("Starting preview scan...")
            page = self.scanner_interface.scan_page(settings)

            if page:
                print(f"Preview scan successful: {page.image_path}")
                return page
            else:
                error_msg = "Preview scan failed - no image data received"
                print(error_msg)
                self.scan_error.emit(error_msg)
                return None

        except Exception as e:
            error_msg = f"Preview scan error: {str(e)}"
            print(error_msg)
            self.error_handler.handle_error(e, "Preview scan", ErrorSeverity.ERROR)
            self.scan_error.emit(error_msg)
            return None

    def get_scan_statistics(self) -> dict:
        """Get statistics about completed scans"""
        stats = {
            "total_batches": 0,
            "total_pages": 0,
            "current_batch_pages": 0,
            "last_scan_time": None,
            "backend_info": get_scanner_backend_info()
        }

        if self.current_batch:
            stats["current_batch_pages"] = self.current_batch.total_pages
            stats["total_batches"] = 1  # For now, we only track current batch
            stats["total_pages"] = self.current_batch.total_pages

        return stats

    def cleanup_resources(self):
        """Clean up scanner resources"""
        try:
            # Stop any running scans
            self.stop_scanning()

            # Clean up scanner interface
            if hasattr(self.scanner_interface, '__del__'):
                self.scanner_interface.__del__()

            print("Scanner resources cleaned up")

        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")

    def __del__(self):
        """Cleanup when controller is destroyed"""
        self.cleanup_resources()
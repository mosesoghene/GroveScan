import os
import platform
import tempfile
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import threading
import subprocess
from pathlib import Path

from src.models import ScannedPage
from src.utils.settings_manager import ScannerSettings

# PyInsane2 scanner backend detection
SCANNER_BACKEND = "mock"
BACKEND_INFO = "No scanner backend loaded"

try:
    import pyinsane2

    # Initialize pyinsane2
    pyinsane2.init()

    # Test if we can get devices
    devices = pyinsane2.get_devices()

    SCANNER_BACKEND = "pyinsane2"
    BACKEND_INFO = f"PyInsane2 backend loaded successfully ({len(devices)} devices found)"

    print(f"✓ Scanner backend: {BACKEND_INFO}")

except ImportError:
    SCANNER_BACKEND = "mock"
    BACKEND_INFO = "PyInsane2 not installed - using mock scanner"
    print(f"⚠ PyInsane2 not available: {BACKEND_INFO}")
    print("  Install with: pip install pyinsane2")

except Exception as e:
    SCANNER_BACKEND = "mock"
    BACKEND_INFO = f"PyInsane2 initialization failed: {str(e)}"
    print(f"⚠ PyInsane2 error: {BACKEND_INFO}")


@dataclass
class ScannerDevice:
    name: str
    device_id: str
    manufacturer: str = ""
    model: str = ""
    is_available: bool = True


class ScannerInterface(ABC):
    """Abstract base class for scanner implementations"""

    @abstractmethod
    def discover_devices(self) -> List[ScannerDevice]:
        """Discover available scanner devices"""
        pass

    @abstractmethod
    def connect_device(self, device_id: str) -> bool:
        """Connect to a specific scanner device"""
        pass

    @abstractmethod
    def scan_page(self, settings: ScannerSettings) -> Optional[ScannedPage]:
        """Scan a single page with given settings"""
        pass

    @abstractmethod
    def is_device_ready(self) -> bool:
        """Check if device is ready for scanning"""
        pass

    @abstractmethod
    def get_device_capabilities(self) -> Dict:
        """Get device capabilities (resolutions, formats, etc.)"""
        pass


class PyInsane2ScannerInterface(ScannerInterface):
    """PyInsane2 scanner implementation for cross-platform support"""

    def __init__(self):
        self.connected_device = None
        self.pyinsane_device = None
        self.available_devices = []
        self.scan_count = 0

        # Initialize pyinsane2 if not already done
        try:
            if not hasattr(pyinsane2, '_initialized'):
                pyinsane2.init()
                pyinsane2._initialized = True
        except Exception as e:
            print(f"PyInsane2 initialization error: {e}")

    def discover_devices(self) -> List[ScannerDevice]:
        """Discover available scanner devices using PyInsane2"""
        devices = []

        try:
            # Get devices from pyinsane2
            pyinsane_devices = pyinsane2.get_devices()

            for device_info in pyinsane_devices:
                try:
                    # Extract device information
                    device_id = device_info[0]  # Device ID
                    device_name = device_info[1] if len(device_info) > 1 else device_id

                    # Try to get more detailed info by opening the device
                    try:
                        temp_device = pyinsane2.Scanner(name=device_id)

                        # Get manufacturer and model if available
                        manufacturer = getattr(temp_device, 'manufacturer', 'Unknown')
                        model = getattr(temp_device, 'model', device_name)

                        temp_device.close()

                    except Exception:
                        # If we can't open the device, use basic info
                        manufacturer = "Unknown"
                        model = device_name

                    scanner_device = ScannerDevice(
                        name=device_name,
                        device_id=device_id,
                        manufacturer=manufacturer,
                        model=model,
                        is_available=True
                    )

                    devices.append(scanner_device)

                except Exception as e:
                    print(f"Error processing device {device_info}: {e}")
                    continue

            self.available_devices = devices

        except Exception as e:
            print(f"Error discovering devices: {e}")

        return devices

    def connect_device(self, device_id: str) -> bool:
        """Connect to a specific scanner device"""
        try:
            # Find the device in our available list
            target_device = None
            for device in self.available_devices:
                if device.device_id == device_id:
                    target_device = device
                    break

            if not target_device:
                print(f"Device {device_id} not found in available devices")
                return False

            # Try to connect to the PyInsane2 device
            self.pyinsane_device = pyinsane2.Scanner(name=device_id)
            self.connected_device = target_device

            print(f"Connected to scanner: {target_device.name}")
            return True

        except Exception as e:
            print(f"Error connecting to device {device_id}: {e}")
            self.pyinsane_device = None
            self.connected_device = None
            return False

    def scan_page(self, settings: ScannerSettings) -> Optional[ScannedPage]:
        """Scan a single page using PyInsane2"""
        if not self.pyinsane_device:
            print("No scanner device connected")
            return None

        try:
            # Configure scanner settings
            self._configure_scanner_settings(settings)

            # Perform the scan
            scan_session = self.pyinsane_device.scan(multiple=False)

            # Get the scanned image
            try:
                while True:
                    scan_session.scan.read()
            except EOFError:
                # End of scan data
                pass

            # Get the PIL image
            image = scan_session.images[0] if scan_session.images else None

            if not image:
                print("No image data received from scanner")
                return None

            # Save image to temporary file
            temp_dir = tempfile.gettempdir()
            self.scan_count += 1
            timestamp = int(time.time())
            temp_filename = f"pyinsane_scan_{timestamp}_{self.scan_count}.{settings.format.lower()}"
            temp_path = os.path.join(temp_dir, temp_filename)

            # Save based on format
            if settings.format.upper() == "JPEG":
                # Convert to RGB if necessary for JPEG
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                image.save(temp_path, "JPEG", quality=settings.quality)
            else:
                image.save(temp_path, settings.format.upper())

            # Create ScannedPage object
            width, height = image.size
            page = ScannedPage(
                image_path=temp_path,
                resolution=settings.resolution,
                color_mode=settings.color_mode,
                format=settings.format,
                width=width,
                height=height
            )

            # Generate thumbnail
            page.generate_thumbnail()

            print(f"Successfully scanned page: {temp_path}")
            return page

        except Exception as e:
            print(f"Error during scanning: {e}")
            return None

    def _configure_scanner_settings(self, settings: ScannerSettings):
        """Configure scanner settings in PyInsane2"""
        try:
            # Set resolution if supported
            if hasattr(self.pyinsane_device.options, 'resolution'):
                self.pyinsane_device.options['resolution'].value = settings.resolution
            elif hasattr(self.pyinsane_device.options, 'x_resolution'):
                self.pyinsane_device.options['x_resolution'].value = settings.resolution
                self.pyinsane_device.options['y_resolution'].value = settings.resolution

            # Set color mode
            mode_mapping = {
                'Color': ['Color', 'RGB', 'color'],
                'Grayscale': ['Grayscale', 'Gray', 'grayscale', 'gray'],
                'Black&White': ['Lineart', 'Black & White', 'Monochrome', 'lineart']
            }

            if hasattr(self.pyinsane_device.options, 'mode'):
                available_modes = self.pyinsane_device.options['mode'].constraint
                target_modes = mode_mapping.get(settings.color_mode, [])

                for target_mode in target_modes:
                    if target_mode in available_modes:
                        self.pyinsane_device.options['mode'].value = target_mode
                        break

            # Set scan area to maximum (optional - could be made configurable)
            try:
                if hasattr(self.pyinsane_device.options, 'tl_x'):
                    self.pyinsane_device.options['tl_x'].value = 0
                if hasattr(self.pyinsane_device.options, 'tl_y'):
                    self.pyinsane_device.options['tl_y'].value = 0
                if hasattr(self.pyinsane_device.options, 'br_x'):
                    max_x = self.pyinsane_device.options['br_x'].constraint[1]
                    self.pyinsane_device.options['br_x'].value = max_x
                if hasattr(self.pyinsane_device.options, 'br_y'):
                    max_y = self.pyinsane_device.options['br_y'].constraint[1]
                    self.pyinsane_device.options['br_y'].value = max_y
            except Exception as e:
                print(f"Warning: Could not set scan area: {e}")

        except Exception as e:
            print(f"Warning: Could not configure all scanner settings: {e}")

    def is_device_ready(self) -> bool:
        """Check if device is ready for scanning"""
        return self.pyinsane_device is not None

    def get_device_capabilities(self) -> Dict:
        """Get device capabilities"""
        if not self.pyinsane_device:
            return {
                "resolutions": [150, 200, 300, 400, 600],
                "color_modes": ["Color", "Grayscale", "Black&White"],
                "formats": ["TIFF", "PNG", "JPEG"]
            }

        capabilities = {
            "resolutions": [150, 200, 300, 400, 600, 1200],
            "color_modes": ["Color", "Grayscale", "Black&White"],
            "formats": ["TIFF", "PNG", "JPEG"]
        }

        try:
            # Get actual device capabilities
            if hasattr(self.pyinsane_device.options, 'resolution'):
                res_constraint = self.pyinsane_device.options['resolution'].constraint
                if isinstance(res_constraint, (list, tuple)):
                    capabilities["resolutions"] = list(res_constraint)
                elif isinstance(res_constraint, dict) and 'range' in res_constraint:
                    # Handle range constraints
                    min_res, max_res = res_constraint['range'][:2]
                    capabilities["resolutions"] = [res for res in [75, 150, 200, 300, 400, 600, 1200]
                                                   if min_res <= res <= max_res]

            # Get color modes
            if hasattr(self.pyinsane_device.options, 'mode'):
                available_modes = self.pyinsane_device.options['mode'].constraint
                color_modes = []

                mode_mapping = {
                    'Color': ['Color', 'RGB', 'color'],
                    'Grayscale': ['Grayscale', 'Gray', 'grayscale', 'gray'],
                    'Black&White': ['Lineart', 'Black & White', 'Monochrome', 'lineart']
                }

                for mode_name, mode_values in mode_mapping.items():
                    if any(mode in available_modes for mode in mode_values):
                        color_modes.append(mode_name)

                if color_modes:
                    capabilities["color_modes"] = color_modes

        except Exception as e:
            print(f"Warning: Could not get all device capabilities: {e}")

        return capabilities

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            if self.pyinsane_device:
                self.pyinsane_device.close()
        except:
            pass


class MockScannerInterface(ScannerInterface):
    """Mock scanner implementation for development/testing"""

    def __init__(self):
        self.connected_device = None
        self.scan_count = 0

    def discover_devices(self) -> List[ScannerDevice]:
        """Return mock scanner devices"""
        return [
            ScannerDevice("Mock Scanner 1", "mock_001", "MockCorp", "ScanMaster 3000"),
            ScannerDevice("Mock Scanner 2", "mock_002", "TestScan", "QuickScan Pro"),
            ScannerDevice("PyInsane2 Test Scanner", "mock_003", "PyInsane", "Test Device"),
        ]

    def connect_device(self, device_id: str) -> bool:
        """Mock device connection"""
        devices = self.discover_devices()
        for device in devices:
            if device.device_id == device_id:
                self.connected_device = device
                return True
        return False

    def scan_page(self, settings: ScannerSettings) -> Optional[ScannedPage]:
        """Generate mock scanned page"""
        if not self.connected_device:
            return None

        # Create mock image
        from PIL import Image, ImageDraw
        import tempfile

        # Create a simple test image
        width = int(8.5 * settings.resolution)  # 8.5" width
        height = int(11 * settings.resolution)  # 11" height

        if settings.color_mode == "Black&White":
            img = Image.new('1', (width, height), 1)
        elif settings.color_mode == "Grayscale":
            img = Image.new('L', (width, height), 255)
        else:
            img = Image.new('RGB', (width, height), (255, 255, 255))

        # Add some mock content
        draw = ImageDraw.Draw(img)
        self.scan_count += 1

        # Draw mock document content
        text_color = 0 if settings.color_mode == "Black&White" else (0, 0, 0)
        y_pos = height // 4

        draw.text((width // 10, y_pos), f"Mock Scanned Document #{self.scan_count}", fill=text_color)
        draw.text((width // 10, y_pos + 100), f"Resolution: {settings.resolution} DPI", fill=text_color)
        draw.text((width // 10, y_pos + 200), f"Color Mode: {settings.color_mode}", fill=text_color)
        draw.text((width // 10, y_pos + 300), f"Device: {self.connected_device.name}", fill=text_color)
        draw.text((width // 10, y_pos + 400), f"Backend: PyInsane2 Mock", fill=text_color)

        # Add a border
        border_color = 0 if settings.color_mode == "Black&White" else (100, 100, 100)
        draw.rectangle([50, 50, width - 50, height - 50], outline=border_color, width=5)

        # Save to temporary file
        temp_dir = tempfile.gettempdir()
        temp_filename = f"scan_{int(time.time())}_{self.scan_count}.{settings.format.lower()}"
        temp_path = os.path.join(temp_dir, temp_filename)

        if settings.format.upper() == "JPEG":
            img.save(temp_path, "JPEG", quality=settings.quality)
        else:
            img.save(temp_path, settings.format.upper())

        # Create ScannedPage object
        page = ScannedPage(
            image_path=temp_path,
            resolution=settings.resolution,
            color_mode=settings.color_mode,
            format=settings.format,
            width=width,
            height=height
        )

        # Generate thumbnail
        page.generate_thumbnail()

        return page

    def is_device_ready(self) -> bool:
        """Mock device ready check"""
        return self.connected_device is not None

    def get_device_capabilities(self) -> Dict:
        """Mock device capabilities"""
        return {
            "resolutions": [150, 200, 300, 400, 600, 1200],
            "color_modes": ["Color", "Grayscale", "Black&White"],
            "formats": ["TIFF", "PNG", "JPEG"],
            "max_width": 8.5,
            "max_height": 14
        }


# Factory function to create the appropriate scanner interface
def create_scanner_interface() -> ScannerInterface:
    """Create the appropriate scanner interface based on availability"""
    if SCANNER_BACKEND == "pyinsane2":
        try:
            return PyInsane2ScannerInterface()
        except Exception as e:
            print(f"Failed to create PyInsane2 interface: {e}")
            print("Falling back to mock scanner")
            return MockScannerInterface()
    else:
        return MockScannerInterface()


# Module-level information
def get_scanner_backend_info() -> Dict[str, str]:
    """Get information about the current scanner backend"""
    return {
        "backend": SCANNER_BACKEND,
        "info": BACKEND_INFO,
        "platform": platform.system(),
        "pyinsane2_available": SCANNER_BACKEND == "pyinsane2"
    }
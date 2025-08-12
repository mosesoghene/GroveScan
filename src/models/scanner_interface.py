import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from .scan_profile import ScannerSettings
from .scanned_page import ScannedPage
import threading
import time


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
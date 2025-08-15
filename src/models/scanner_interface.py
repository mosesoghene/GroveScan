import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from .scan_profile import ScannerSettings
from .scanned_page import ScannedPage
import threading
import time
import platform
import subprocess
from pathlib import Path
import tempfile
import sys

# No direct scanner imports - we'll use system detection
SCANNER_BACKEND = "mock"
BACKEND_INFO = "No scanner backend loaded"


def detect_system_scanner_support():
    """Detect scanner support using system tools only"""
    system = platform.system()

    if system == "Linux":
        # Check for SANE command line tools
        try:
            result = subprocess.run(['scanimage', '--version'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "sane-cli", "SANE command-line tools detected"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return "none", "No SANE tools found (install sane-utils)"

    elif system == "Windows":
        # Check for Windows built-in scanning
        try:
            # Try to access Windows WIA via COM without importing libraries
            result = subprocess.run([
                'powershell', '-Command',
                'Get-WmiObject -Class Win32_PnPEntity | Where-Object {$_.Name -like "*scan*" -or $_.Name -like "*imaging*"} | Select-Object -First 1'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout.strip():
                return "windows-native", "Windows imaging devices detected"
        except Exception:
            pass
        return "none", "No Windows scanner support detected"

    else:
        return "none", f"Platform {system} not supported"


# Detect what's available
detected_backend, backend_message = detect_system_scanner_support()
SCANNER_BACKEND = detected_backend
BACKEND_INFO = backend_message

print(f"Scanner detection: {BACKEND_INFO}")


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


class WindowsNativeScannerInterface(ScannerInterface):
    """Windows native scanner using PowerShell and system tools"""

    def __init__(self):
        self.connected_device = None
        self.available_devices = []
        self._discover_devices_cached()

    def _discover_devices_cached(self):
        """Cache device discovery to avoid repeated PowerShell calls"""
        try:
            # Use PowerShell to find imaging devices
            ps_command = '''
            Get-WmiObject -Class Win32_PnPEntity | 
            Where-Object {$_.Name -like "*scan*" -or $_.Name -like "*imaging*" -or $_.DeviceID -like "*SCANNER*"} |
            ForEach-Object { "$($_.Name)|$($_.DeviceID)|$($_.Manufacturer)" }
            '''

            result = subprocess.run([
                'powershell', '-Command', ps_command
            ], capture_output=True, text=True, timeout=15)

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            name = parts[0].strip()
                            device_id = parts[1].strip()
                            manufacturer = parts[2].strip() or "Unknown"

                            if name and device_id:
                                device = ScannerDevice(
                                    name=name,
                                    device_id=device_id,
                                    manufacturer=manufacturer,
                                    model=name,
                                    is_available=True
                                )
                                self.available_devices.append(device)

        except Exception as e:
            print(f"Windows scanner detection error: {e}")

    def discover_devices(self) -> List[ScannerDevice]:
        return self.available_devices.copy()

    def connect_device(self, device_id: str) -> bool:
        self.connected_device = next(
            (d for d in self.available_devices if d.device_id == device_id),
            None
        )
        return self.connected_device is not None

    def scan_page(self, settings: ScannerSettings) -> Optional[ScannedPage]:
        if not self.connected_device:
            return None

        try:
            # Use Windows built-in scan functionality via PowerShell
            temp_dir = tempfile.gettempdir()
            timestamp = int(time.time())
            output_file = os.path.join(temp_dir, f"windows_scan_{timestamp}.bmp")

            # PowerShell script to trigger Windows scan dialog
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.MessageBox]::Show("Please scan your document using the scanner software, then press OK when the scan is complete.", "Scan Ready")
            '''

            subprocess.run(['powershell', '-Command', ps_script], timeout=300)

            # For now, create a placeholder - in real implementation,
            # you'd integrate with scanner manufacturer's SDK or Windows WIA COM objects
            return self._create_placeholder_scan(settings)

        except Exception as e:
            print(f"Windows scanning error: {e}")
            return None

    def _create_placeholder_scan(self, settings: ScannerSettings) -> ScannedPage:
        """Create a placeholder scan file"""
        from PIL import Image, ImageDraw

        # Create test image
        width = int(8.5 * settings.resolution)
        height = int(11 * settings.resolution)

        if settings.color_mode == "Black&White":
            img = Image.new('1', (width, height), 1)
        elif settings.color_mode == "Grayscale":
            img = Image.new('L', (width, height), 255)
        else:
            img = Image.new('RGB', (width, height), (255, 255, 255))

        draw = ImageDraw.Draw(img)
        text_color = 0 if settings.color_mode == "Black&White" else (0, 0, 0)

        draw.text((width // 10, height // 4),
                  f"Windows Native Scanner\nDevice: {self.connected_device.name}\nResolution: {settings.resolution} DPI",
                  fill=text_color)

        # Save file
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        temp_filename = f"win_scan_{timestamp}.{settings.format.lower()}"
        temp_path = os.path.join(temp_dir, temp_filename)

        if settings.format.upper() == "JPEG":
            img.save(temp_path, "JPEG", quality=settings.quality)
        else:
            img.save(temp_path, settings.format.upper())

        page = ScannedPage(
            image_path=temp_path,
            resolution=settings.resolution,
            color_mode=settings.color_mode,
            format=settings.format,
            width=width,
            height=height
        )

        page.generate_thumbnail()
        return page

    def is_device_ready(self) -> bool:
        return self.connected_device is not None

    def get_device_capabilities(self) -> Dict:
        return {
            "resolutions": [150, 200, 300, 600],
            "color_modes": ["Color", "Grayscale", "Black&White"],
            "formats": ["BMP", "TIFF", "PNG", "JPEG"]
        }


class SANECommandLineScannerInterface(ScannerInterface):
    """SANE scanner using command-line tools only"""

    def __init__(self):
        self.connected_device = None
        self.available_scanners = []
        self._discover_sane_devices()

    def _discover_sane_devices(self):
        """Find SANE devices via command line"""
        try:
            result = subprocess.run(['scanimage', '-L'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip() and 'device' in line and "'" in line:
                        # Parse: device `epson2:libusb:001:003' is a Epson GT-2500 flatbed scanner
                        try:
                            device_id = line.split("'")[1]
                            description = line.split("' is a ")[-1] if "' is a " in line else device_id

                            device = ScannerDevice(
                                name=description,
                                device_id=device_id,
                                manufacturer=description.split()[0] if description else "Unknown",
                                model=description,
                                is_available=True
                            )
                            self.available_scanners.append(device)
                        except IndexError:
                            continue

        except Exception as e:
            print(f"SANE device discovery error: {e}")

    def discover_devices(self) -> List[ScannerDevice]:
        return self.available_scanners.copy()

    def connect_device(self, device_id: str) -> bool:
        self.connected_device = next(
            (d for d in self.available_scanners if d.device_id == device_id),
            None
        )
        return self.connected_device is not None

    def scan_page(self, settings: ScannerSettings) -> Optional[ScannedPage]:
        if not self.connected_device:
            return None

        try:
            temp_dir = tempfile.gettempdir()
            timestamp = int(time.time())
            temp_filename = f"sane_scan_{timestamp}.{settings.format.lower()}"
            temp_path = os.path.join(temp_dir, temp_filename)

            # Build scanimage command
            cmd = [
                'scanimage',
                '--device-name', self.connected_device.device_id,
                '--resolution', str(settings.resolution),
                '--format', settings.format.lower(),
                '--output-file', temp_path
            ]

            # Set mode
            if settings.color_mode == "Grayscale":
                cmd.extend(['--mode', 'Gray'])
            elif settings.color_mode == "Black&White":
                cmd.extend(['--mode', 'Lineart'])
            else:
                cmd.extend(['--mode', 'Color'])

            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0 and os.path.exists(temp_path):
                # Get image info
                from PIL import Image
                with Image.open(temp_path) as img:
                    width, height = img.size

                page = ScannedPage(
                    image_path=temp_path,
                    resolution=settings.resolution,
                    color_mode=settings.color_mode,
                    format=settings.format,
                    width=width,
                    height=height
                )

                page.generate_thumbnail()
                return page
            else:
                print(f"Scan command failed: {result.stderr}")
                return None

        except Exception as e:
            print(f"SANE scanning error: {e}")
            return None

    def is_device_ready(self) -> bool:
        return self.connected_device is not None

    def get_device_capabilities(self) -> Dict:
        return {
            "resolutions": [75, 150, 300, 600, 1200],
            "color_modes": ["Color", "Grayscale", "Black&White"],
            "formats": ["TIFF", "PNG", "JPEG"]
        }


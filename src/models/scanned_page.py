from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from PIL import Image
import os
import tempfile
import uuid


@dataclass
class ScannedPage:
    page_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    image_path: str = ""
    thumbnail_path: str = ""
    page_number: int = 0
    scan_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    resolution: int = 300
    color_mode: str = "Color"
    format: str = "TIFF"
    width: int = 0
    height: int = 0
    rotation: int = 0  # 0, 90, 180, 270 degrees
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.image_path and os.path.exists(self.image_path):
            self._update_image_info()

    def _update_image_info(self):
        """Update width, height from actual image"""
        try:
            with Image.open(self.image_path) as img:
                self.width, self.height = img.size
        except Exception:
            pass

    def generate_thumbnail(self, size: tuple = (150, 200)) -> str:
        """Generate thumbnail and return path"""
        if not os.path.exists(self.image_path):
            return ""

        try:
            with Image.open(self.image_path) as img:
                # Apply current rotation
                if self.rotation != 0:
                    img = img.rotate(-self.rotation, expand=True)

                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Save thumbnail
                temp_dir = tempfile.gettempdir()
                thumbnail_filename = f"thumb_{self.page_id}.png"
                thumbnail_path = os.path.join(temp_dir, thumbnail_filename)

                img.save(thumbnail_path, "PNG")
                self.thumbnail_path = thumbnail_path
                return thumbnail_path

        except PermissionError:
            print(f"Permission denied creating thumbnail for {self.page_id}")
            return ""
        except OSError as e:
            print(f"Disk error creating thumbnail for {self.page_id}: {e}")
            return ""
        except Exception as e:
            print(f"Error generating thumbnail for {self.page_id}: {e}")
            return ""

    def rotate_page(self, degrees: int):
        """Rotate page by specified degrees (90, 180, 270)"""
        if degrees not in [90, 180, 270]:
            return

        self.rotation = (self.rotation + degrees) % 360

        # Regenerate thumbnail with new rotation
        if self.thumbnail_path:
            self.generate_thumbnail()

    def get_display_size(self) -> tuple:
        """Get display size accounting for rotation"""
        if self.rotation in [90, 270]:
            return (self.height, self.width)
        return (self.width, self.height)
    
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

    def generate_thumbnail(self, size: tuple = (150, 200), use_cache: bool = True) -> str:
        """Generate thumbnail and return path with caching optimization"""
        if not os.path.exists(self.image_path):
            return ""

        # Check if thumbnail already exists and is newer than source
        if self.thumbnail_path and os.path.exists(self.thumbnail_path) and use_cache:
            source_mtime = os.path.getmtime(self.image_path)
            thumb_mtime = os.path.getmtime(self.thumbnail_path)
            if thumb_mtime > source_mtime:
                return self.thumbnail_path

        try:
            from PIL import Image, ImageOps

            # Use optimized thumbnail generation
            with Image.open(self.image_path) as img:
                # Apply current rotation
                if self.rotation != 0:
                    img = img.rotate(-self.rotation, expand=True)

                # Use draft mode for faster processing of large images
                img.draft('RGB', size)

                # Create thumbnail using optimized method
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Optimize for size while maintaining quality
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Save thumbnail with optimization
                temp_dir = tempfile.gettempdir()
                thumbnail_filename = f"thumb_{self.page_id}.jpg"  # Use JPEG for smaller size
                thumbnail_path = os.path.join(temp_dir, thumbnail_filename)

                img.save(thumbnail_path, "JPEG", quality=85, optimize=True)
                self.thumbnail_path = thumbnail_path
                return thumbnail_path

        except PermissionError:
            print(f"Permission denied creating thumbnail for {self.page_id}")
            return ""
        except OSError as e:
            print(f"Disk error creating thumbnail for {self.page_id}: {e}")
            return ""
        except MemoryError:
            print(f"Out of memory creating thumbnail for {self.page_id}")
            # Try with smaller size
            try:
                smaller_size = (size[0] // 2, size[1] // 2)
                return self.generate_thumbnail(smaller_size, use_cache=False)
            except:
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
    
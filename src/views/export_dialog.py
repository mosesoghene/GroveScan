from PySide6.QtCore import QObject, Signal, QThread
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from PIL import Image
import os
import json
import tempfile
import gc
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import QMessageBox, QDialog, QLabel, QGridLayout, QHBoxLayout, QPushButton, QGroupBox, \
    QVBoxLayout, QTextEdit

# Try to import reportlab for advanced PDF features
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.units import inch

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from src.models.document_batch import DocumentBatch
from src.models.page_assignment import PageAssignment
from src.models.dynamic_index_schema import DynamicIndexSchema


class ExportFormat(Enum):
    PDF = "pdf"
    TIFF = "tiff"
    PNG = "png"
    JPEG = "jpeg"


class PDFEngine(Enum):
    PIL = "pil"
    REPORTLAB = "reportlab"


@dataclass
class ExportTemplate:
    """Export configuration template"""
    name: str
    description: str
    format: ExportFormat
    pdf_engine: PDFEngine = PDFEngine.PIL
    quality: int = 95
    compression: str = "medium"
    create_folders: bool = True
    overwrite_existing: bool = False
    add_timestamp: bool = False
    page_size: str = "auto"  # auto, letter, a4
    margins: Tuple[float, float, float, float] = (0.5, 0.5, 0.5, 0.5)  # top, right, bottom, left (inches)
    fit_to_page: bool = True
    maintain_aspect_ratio: bool = True

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'format': self.format.value,
            'pdf_engine': self.pdf_engine.value,
            'quality': self.quality,
            'compression': self.compression,
            'create_folders': self.create_folders,
            'overwrite_existing': self.overwrite_existing,
            'add_timestamp': self.add_timestamp,
            'page_size': self.page_size,
            'margins': self.margins,
            'fit_to_page': self.fit_to_page,
            'maintain_aspect_ratio': self.maintain_aspect_ratio
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ExportTemplate':
        return cls(
            name=data['name'],
            description=data['description'],
            format=ExportFormat(data['format']),
            pdf_engine=PDFEngine(data.get('pdf_engine', 'pil')),
            quality=data.get('quality', 95),
            compression=data.get('compression', 'medium'),
            create_folders=data.get('create_folders', True),
            overwrite_existing=data.get('overwrite_existing', False),
            add_timestamp=data.get('add_timestamp', False),
            page_size=data.get('page_size', 'auto'),
            margins=tuple(data.get('margins', [0.5, 0.5, 0.5, 0.5])),
            fit_to_page=data.get('fit_to_page', True),
            maintain_aspect_ratio=data.get('maintain_aspect_ratio', True)
        )


@dataclass
class ExportState:
    """State information for resumable exports"""
    export_id: str
    output_directory: str
    template: ExportTemplate
    total_groups: int
    completed_groups: List[str]  # assignment_ids
    failed_groups: List[Tuple[str, str]]  # (assignment_id, error_message)
    started_timestamp: str
    last_update_timestamp: str

    def to_dict(self) -> Dict:
        return {
            'export_id': self.export_id,
            'output_directory': self.output_directory,
            'template': self.template.to_dict(),
            'total_groups': self.total_groups,
            'completed_groups': self.completed_groups,
            'failed_groups': self.failed_groups,
            'started_timestamp': self.started_timestamp,
            'last_update_timestamp': self.last_update_timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ExportState':
        return cls(
            export_id=data['export_id'],
            output_directory=data['output_directory'],
            template=ExportTemplate.from_dict(data['template']),
            total_groups=data['total_groups'],
            completed_groups=data['completed_groups'],
            failed_groups=data['failed_groups'],
            started_timestamp=data['started_timestamp'],
            last_update_timestamp=data['last_update_timestamp']
        )


class MemoryManager:
    """Manages memory usage during large batch exports"""

    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self.current_images = []
        self.memory_usage_mb = 0

    def can_load_image(self, estimated_size_mb: float) -> bool:
        """Check if we can load another image without exceeding memory limit"""
        return (self.memory_usage_mb + estimated_size_mb) <= self.max_memory_mb

    def add_image(self, image: Image.Image, estimated_size_mb: float):
        """Add image to memory tracking"""
        self.current_images.append(image)
        self.memory_usage_mb += estimated_size_mb

    def clear_images(self):
        """Clear all cached images and run garbage collection"""
        for img in self.current_images:
            if hasattr(img, 'close'):
                img.close()
        self.current_images.clear()
        self.memory_usage_mb = 0
        gc.collect()

    def estimate_image_size(self, width: int, height: int, mode: str) -> float:
        """Estimate image memory size in MB"""
        bytes_per_pixel = 1 if mode == 'L' else 3 if mode == 'RGB' else 4
        total_bytes = width * height * bytes_per_pixel
        return total_bytes / (1024 * 1024)


class EnhancedExportWorker(QThread):
    """Enhanced worker thread for document export operations"""

    export_progress = Signal(int, int, str)  # current, total, message
    document_exported = Signal(str, str)  # document_name, output_path
    export_error = Signal(str, str)  # document_name, error_message
    export_completed = Signal(int, int)  # successful_count, total_count
    memory_warning = Signal(str)  # warning_message

    def __init__(self, export_groups: List[Dict], template: ExportTemplate,
                 output_dir: str, batch: DocumentBatch, resume_state: Optional[ExportState] = None):
        super().__init__()
        self.export_groups = export_groups
        self.template = template
        self.output_dir = output_dir
        self.batch = batch
        self.resume_state = resume_state
        self.should_stop = False
        self.successful_exports = 0
        self.memory_manager = MemoryManager()

        # Create export state for resumability
        self.export_state = resume_state or ExportState(
            export_id=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            output_directory=output_dir,
            template=template,
            total_groups=len(export_groups),
            completed_groups=[],
            failed_groups=[],
            started_timestamp=datetime.now().isoformat(),
            last_update_timestamp=datetime.now().isoformat()
        )

    def run(self):
        """Run export in separate thread"""
        try:
            self._save_export_state()

            total_docs = len(self.export_groups)
            completed_count = len(self.export_state.completed_groups) if self.resume_state else 0

            for i, group in enumerate(self.export_groups):
                if self.should_stop:
                    break

                # Skip already completed groups if resuming
                if group['assignment_id'] in self.export_state.completed_groups:
                    continue

                document_name = group['filename']
                self.export_progress.emit(completed_count, total_docs, f"Exporting: {document_name}")

                try:
                    output_path = self._export_document_group(group)
                    if output_path:
                        self.document_exported.emit(document_name, output_path)
                        self.successful_exports += 1
                        self.export_state.completed_groups.append(group['assignment_id'])
                    else:
                        error_msg = "Failed to create document"
                        self.export_error.emit(document_name, error_msg)
                        self.export_state.failed_groups.append((group['assignment_id'], error_msg))

                except Exception as e:
                    error_msg = str(e)
                    self.export_error.emit(document_name, error_msg)
                    self.export_state.failed_groups.append((group['assignment_id'], error_msg))

                completed_count += 1
                self.export_state.last_update_timestamp = datetime.now().isoformat()
                self._save_export_state()

                # Memory management - clear cache periodically
                if completed_count % 5 == 0:
                    self.memory_manager.clear_images()

                # Small delay for UI responsiveness
                self.msleep(50)

            self.export_completed.emit(self.successful_exports, total_docs)
            self._cleanup_export_state()

        except Exception as e:
            self.export_error.emit("Export Process", f"Critical error: {str(e)}")

    def _export_document_group(self, group: Dict) -> Optional[str]:
        """Export a single document group with multiple format support"""
        try:
            # Create folder structure
            folder_path = Path(self.output_dir)
            if group['folder_path'] and self.template.create_folders:
                folder_path = folder_path / group['folder_path']

            folder_path.mkdir(parents=True, exist_ok=True)

            # Collect pages for this group
            pages_to_export = self._collect_pages_for_group(group)
            if not pages_to_export:
                return None

            # Generate output filename
            output_filename = self._generate_filename(group)
            output_path = folder_path / output_filename

            # Handle existing files
            output_path = self._handle_existing_file(output_path)

            # Export based on format
            success = self._create_document_by_format(pages_to_export, str(output_path))

            return str(output_path) if success else None

        except Exception as e:
            raise Exception(f"Error exporting document group: {str(e)}")

    def _collect_pages_for_group(self, group: Dict) -> List:
        """Collect and validate pages for export group"""
        pages_to_export = []

        for page_id in group['page_ids']:
            page = self.batch.get_page_by_id(page_id)
            if page and os.path.exists(page.image_path):
                pages_to_export.append(page)
            else:
                print(f"Warning: Page {page_id} not found or file missing")

        return pages_to_export

    def _generate_filename(self, group: Dict) -> str:
        """Generate filename with format extension and optional timestamp"""
        filename = group['filename']

        # Remove existing extension
        if '.' in filename:
            filename = filename.rsplit('.', 1)[0]

        # Add timestamp if requested
        if self.template.add_timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{timestamp}"

        # Add format extension
        extension = f".{self.template.format.value}"
        return filename + extension

    def _handle_existing_file(self, output_path: Path) -> Path:
        """Handle existing files based on template settings"""
        if not output_path.exists() or self.template.overwrite_existing:
            return output_path

        # Generate unique filename
        counter = 1
        base_name = output_path.stem
        extension = output_path.suffix
        parent = output_path.parent

        while output_path.exists():
            new_name = f"{base_name}_{counter:03d}{extension}"
            output_path = parent / new_name
            counter += 1

        return output_path

    def _create_document_by_format(self, pages: List, output_path: str) -> bool:
        """Create document in specified format"""
        format_handlers = {
            ExportFormat.PDF: self._create_pdf_document,
            ExportFormat.TIFF: self._create_tiff_document,
            ExportFormat.PNG: self._create_png_document,
            ExportFormat.JPEG: self._create_jpeg_document
        }

        handler = format_handlers.get(self.template.format)
        if not handler:
            raise Exception(f"Unsupported export format: {self.template.format}")

        return handler(pages, output_path)

    def _create_pdf_document(self, pages: List, output_path: str) -> bool:
        """Create PDF using selected engine"""
        if self.template.pdf_engine == PDFEngine.REPORTLAB and HAS_REPORTLAB:
            return self._create_pdf_with_reportlab(pages, output_path)
        else:
            return self._create_pdf_with_pil(pages, output_path)

    def _create_pdf_with_reportlab(self, pages: List, output_path: str) -> bool:
        """Create PDF using ReportLab for advanced features"""
        try:
            # Page size mapping
            page_sizes = {
                'letter': letter,
                'a4': A4,
                'auto': None  # Will be determined from first page
            }

            page_size = page_sizes.get(self.template.page_size)
            c = None

            for i, page in enumerate(pages):
                try:
                    img = Image.open(page.image_path)

                    # Apply rotation
                    if page.rotation != 0:
                        img = img.rotate(-page.rotation, expand=True)

                    # Determine page size for auto mode
                    if page_size is None:
                        # Use image dimensions for auto sizing
                        img_width, img_height = img.size
                        dpi = 72  # ReportLab default
                        page_size = (img_width * 72 / page.resolution, img_height * 72 / page.resolution)

                    # Create canvas on first page
                    if c is None:
                        c = canvas.Canvas(output_path, pagesize=page_size)

                    # Calculate positioning
                    page_width, page_height = page_size
                    margins = self.template.margins
                    content_width = page_width - (margins[1] + margins[3]) * inch
                    content_height = page_height - (margins[0] + margins[2]) * inch

                    # Position image
                    x = margins[3] * inch
                    y = margins[2] * inch

                    if self.template.fit_to_page:
                        width = content_width
                        height = content_height

                        if self.template.maintain_aspect_ratio:
                            img_ratio = img.size[0] / img.size[1]
                            content_ratio = content_width / content_height

                            if img_ratio > content_ratio:
                                height = width / img_ratio
                                y += (content_height - height) / 2
                            else:
                                width = height * img_ratio
                                x += (content_width - width) / 2
                    else:
                        width, height = img.size

                    # Draw image
                    c.drawImage(ImageReader(img), x, y, width, height)

                    if i < len(pages) - 1:
                        c.showPage()

                    img.close()

                    # Memory management
                    estimated_size = self.memory_manager.estimate_image_size(
                        img.size[0], img.size[1], img.mode
                    )

                    if not self.memory_manager.can_load_image(estimated_size):
                        self.memory_manager.clear_images()
                        if i % 10 == 0:  # Warning every 10 pages
                            self.memory_warning.emit(f"Memory usage high during PDF creation")

                except Exception as e:
                    print(f"Error processing page {page.page_id} with ReportLab: {e}")
                    continue

            if c:
                c.save()
                return True

            return False

        except Exception as e:
            print(f"ReportLab PDF creation failed: {e}")
            # Fallback to PIL
            return self._create_pdf_with_pil(pages, output_path)

    def _create_pdf_with_pil(self, pages: List, output_path: str) -> bool:
        """Create PDF using PIL (fallback method)"""
        try:
            images = []

            for page in pages:
                try:
                    img = Image.open(page.image_path)

                    # Apply rotation
                    if page.rotation != 0:
                        img = img.rotate(-page.rotation, expand=True)

                    # Convert to RGB if needed
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    images.append(img)

                    # Memory management check
                    estimated_size = self.memory_manager.estimate_image_size(
                        img.size[0], img.size[1], img.mode
                    )

                    if not self.memory_manager.can_load_image(estimated_size):
                        # Process what we have so far
                        if len(images) > 1:
                            break

                except Exception as e:
                    print(f"Warning: Could not process page {page.page_id}: {e}")
                    continue

            if not images:
                return False

            # Save as PDF
            images[0].save(
                output_path,
                "PDF",
                save_all=True,
                append_images=images[1:] if len(images) > 1 else [],
                quality=self.template.quality,
                optimize=True
            )

            # Cleanup
            for img in images:
                img.close()

            return True

        except Exception as e:
            print(f"PIL PDF creation error: {e}")
            return False

    def _create_tiff_document(self, pages: List, output_path: str) -> bool:
        """Create multi-page TIFF document"""
        try:
            images = []

            for page in pages:
                try:
                    img = Image.open(page.image_path)

                    if page.rotation != 0:
                        img = img.rotate(-page.rotation, expand=True)

                    images.append(img)

                except Exception as e:
                    print(f"Warning: Could not process page {page.page_id}: {e}")
                    continue

            if not images:
                return False

            # Compression mapping
            compression_map = {
                'none': None,
                'low': 'lzw',
                'medium': 'tiff_lzw',
                'high': 'tiff_adobe_deflate'
            }

            compression = compression_map.get(self.template.compression)

            images[0].save(
                output_path,
                "TIFF",
                save_all=True,
                append_images=images[1:] if len(images) > 1 else [],
                compression=compression,
                quality=self.template.quality
            )

            # Cleanup
            for img in images:
                img.close()

            return True

        except Exception as e:
            print(f"TIFF creation error: {e}")
            return False

    def _create_png_document(self, pages: List, output_path: str) -> bool:
        """Create PNG files (separate files for each page)"""
        try:
            if len(pages) == 1:
                # Single page
                return self._save_single_image(pages[0], output_path, "PNG")
            else:
                # Multiple files
                base_path = Path(output_path)
                base_name = base_path.stem
                parent = base_path.parent

                for i, page in enumerate(pages):
                    page_filename = f"{base_name}_page_{i + 1:03d}.png"
                    page_path = parent / page_filename

                    if not self._save_single_image(page, str(page_path), "PNG"):
                        return False

                return True

        except Exception as e:
            print(f"PNG creation error: {e}")
            return False

    def _create_jpeg_document(self, pages: List, output_path: str) -> bool:
        """Create JPEG files (separate files for each page)"""
        try:
            if len(pages) == 1:
                # Single page
                return self._save_single_image(pages[0], output_path, "JPEG")
            else:
                # Multiple files
                base_path = Path(output_path)
                base_name = base_path.stem
                parent = base_path.parent

                for i, page in enumerate(pages):
                    page_filename = f"{base_name}_page_{i + 1:03d}.jpg"
                    page_path = parent / page_filename

                    if not self._save_single_image(page, str(page_path), "JPEG"):
                        return False

                return True

        except Exception as e:
            print(f"JPEG creation error: {e}")
            return False

    def _save_single_image(self, page, output_path: str, format_name: str) -> bool:
        """Save a single page as an image"""
        try:
            img = Image.open(page.image_path)

            if page.rotation != 0:
                img = img.rotate(-page.rotation, expand=True)

            # Convert to RGB for JPEG
            if format_name == "JPEG" and img.mode != 'RGB':
                img = img.convert('RGB')

            save_kwargs = {'quality': self.template.quality, 'optimize': True}

            img.save(output_path, format_name, **save_kwargs)
            img.close()

            return True

        except Exception as e:
            print(f"Single image save error: {e}")
            return False

    def _save_export_state(self):
        """Save export state for resumability"""
        try:
            state_dir = Path(tempfile.gettempdir()) / "dynamic_scanner_exports"
            state_dir.mkdir(exist_ok=True)

            state_file = state_dir / f"{self.export_state.export_id}.json"

            with open(state_file, 'w') as f:
                json.dump(self.export_state.to_dict(), f, indent=2)

        except Exception as e:
            print(f"Warning: Could not save export state: {e}")

    def _cleanup_export_state(self):
        """Clean up export state file after successful completion"""
        try:
            state_dir = Path(tempfile.gettempdir()) / "dynamic_scanner_exports"
            state_file = state_dir / f"{self.export_state.export_id}.json"

            if state_file.exists():
                state_file.unlink()

        except Exception as e:
            print(f"Warning: Could not cleanup export state: {e}")

    def stop(self):
        """Stop export process"""
        self.should_stop = True

class ExportProgressDialog(QDialog):
    """Dialog showing export progress"""

    export_cancelled = Signal()

    def __init__(self, total_documents: int, parent=None):
        super().__init__(parent)
        self.total_documents = total_documents
        self.exported_count = 0
        self.failed_count = 0
        self.export_cancelled_flag = False

        self.setWindowTitle("Exporting Documents")
        self.setModal(True)
        self.resize(500, 300)
        self._setup_ui()

    def _setup_ui(self):
        """Setup progress dialog UI"""
        layout = QVBoxLayout(self)

        # Progress information
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("Exporting documents..."), 0, 0, 1, 2)

        info_layout.addWidget(QLabel("Progress:"), 1, 0)
        self.progress_label = QLabel(f"0 of {self.total_documents}")
        info_layout.addWidget(self.progress_label, 1, 1)

        info_layout.addWidget(QLabel("Current:"), 2, 0)
        self.current_label = QLabel("Preparing...")
        info_layout.addWidget(self.current_label, 2, 1)

        layout.addLayout(info_layout)

        # Progress bar
        from PySide6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.total_documents)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status log
        status_group = QGroupBox("Export Status")
        status_layout = QVBoxLayout(status_group)

        self.status_log = QTextEdit()
        self.status_log.setMaximumHeight(150)
        self.status_log.setReadOnly(True)
        status_layout.addWidget(self.status_log)

        layout.addWidget(status_group)

        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel Export")
        self.cancel_btn.clicked.connect(self._cancel_export)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def update_progress(self, current: int, total: int, message: str):
        """Update export progress"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

        self.progress_label.setText(f"{current} of {total}")
        self.current_label.setText(message)

        # Add to status log
        self.status_log.append(f"[{current}/{total}] {message}")

        # Auto-scroll to bottom
        self.status_log.verticalScrollBar().setValue(
            self.status_log.verticalScrollBar().maximum()
        )

    def document_exported(self, document_name: str, output_path: str):
        """Handle successful document export"""
        self.exported_count += 1
        message = f"✅ Exported: {document_name}"
        self.status_log.append(message)
        self.status_log.verticalScrollBar().setValue(
            self.status_log.verticalScrollBar().maximum()
        )

    def export_error(self, document_name: str, error_message: str):
        """Handle export error"""
        self.failed_count += 1
        message = f"❌ Failed: {document_name} - {error_message}"
        self.status_log.append(message)
        self.status_log.verticalScrollBar().setValue(
            self.status_log.verticalScrollBar().maximum()
        )

    def export_completed(self, summary: Dict):
        """Handle export completion"""
        self.current_label.setText("Export completed!")

        success_rate = summary.get('success_rate', 0)
        total_msg = f"""
Export Summary:
• Successful: {summary['successful_exports']}
• Failed: {summary['failed_exports']}
• Success Rate: {success_rate:.1f}%
        """

        self.status_log.append("=" * 40)
        self.status_log.append(total_msg)

        # Change cancel button to close
        self.cancel_btn.setText("Close")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)

    def _cancel_export(self):
        """Cancel the export process"""
        if not self.export_cancelled_flag:
            reply = QMessageBox.question(
                self,
                "Cancel Export",
                "Are you sure you want to cancel the export?\n\nDocuments exported so far will be kept.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.export_cancelled_flag = True
                self.export_cancelled.emit()
                self.current_label.setText("Cancelling export...")
                self.cancel_btn.setEnabled(False)
        else:
            # Export already cancelled, just close
            self.reject()

    def closeEvent(self, event):
        """Handle dialog close"""
        if not self.export_cancelled_flag and self.exported_count < self.total_documents:
            reply = QMessageBox.question(
                self,
                "Cancel Export",
                "Export is still in progress. Cancel export and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.export_cancelled.emit()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
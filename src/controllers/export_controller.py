import gc
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QObject, Signal, QThread
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from PIL import Image
import os
import tempfile
from src.models.document_batch import DocumentBatch
from src.models.page_assignment import PageAssignment
from src.models.dynamic_index_schema import DynamicIndexSchema
from src.models.scan_profile import ExportSettings

# Try to import reportlab for advanced PDF features
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.units import inch

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class ExportWorker(QThread):
    """Worker thread for document export operations"""

    export_progress = Signal(int, int, str)  # current, total, message
    document_exported = Signal(str, str)  # document_name, output_path
    export_error = Signal(str, str)  # document_name, error_message
    export_completed = Signal(int, int)  # successful_count, total_count

    def __init__(self, export_groups: List[Dict], output_dir: str, batch: DocumentBatch,
                 export_settings: ExportSettings):
        super().__init__()
        self.export_groups = export_groups
        self.output_dir = output_dir
        self.batch = batch
        self.export_settings = export_settings
        self.should_stop = False
        self.successful_exports = 0

    def run(self):
        """Run export in separate thread"""
        try:
            total_docs = len(self.export_groups)

            for i, group in enumerate(self.export_groups):
                if self.should_stop:
                    break

                document_name = group['filename']
                self.export_progress.emit(i, total_docs, f"Exporting: {document_name}")

                try:
                    output_path = self._export_document_group(group)
                    if output_path:
                        self.document_exported.emit(document_name, output_path)
                        self.successful_exports += 1
                    else:
                        self.export_error.emit(document_name, "Failed to create document")

                except Exception as e:
                    self.export_error.emit(document_name, str(e))

                # Small delay for UI responsiveness
                self.msleep(100)

            self.export_completed.emit(self.successful_exports, total_docs)

        except Exception as e:
            self.export_error.emit("Export Process", f"Critical error: {str(e)}")

    def _export_document_group(self, group: Dict) -> Optional[str]:
        """Export a single document group"""
        try:
            # Create folder structure
            folder_path = Path(self.output_dir)
            if group['folder_path']:
                folder_path = folder_path / group['folder_path']

            folder_path.mkdir(parents=True, exist_ok=True)

            # Collect pages for this group
            pages_to_export = []
            for page_id in group['page_ids']:
                page = self.batch.get_page_by_id(page_id)
                if page and os.path.exists(page.image_path):
                    pages_to_export.append(page)

            if not pages_to_export:
                return None

            # Generate output filename
            output_filename = group['filename']
            if not output_filename.lower().endswith('.pdf'):
                output_filename += '.pdf'

            output_path = folder_path / output_filename

            # Handle existing files
            if output_path.exists() and not self.export_settings.overwrite_existing:
                # Add number suffix
                counter = 1
                base_name = output_path.stem
                while output_path.exists():
                    new_name = f"{base_name}_{counter:03d}.pdf"
                    output_path = folder_path / new_name
                    counter += 1

            # Create PDF from pages
            success = self._create_pdf_from_pages(pages_to_export, str(output_path))

            return str(output_path) if success else None

        except Exception as e:
            raise Exception(f"Error exporting document group: {str(e)}")

    def _create_pdf_from_pages(self, pages: List, output_path: str) -> bool:
        """Create PDF from list of pages"""
        try:
            images = []

            for page in pages:
                try:
                    img = Image.open(page.image_path)

                    # Apply rotation if needed
                    if page.rotation != 0:
                        img = img.rotate(-page.rotation, expand=True)

                    # Convert to RGB if needed (for PDF)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    images.append(img)

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
                quality=self.export_settings.pdf_quality,
                optimize=True
            )

            return True

        except Exception as e:
            print(f"Error creating PDF: {e}")
            return False

    def stop(self):
        """Stop export process"""
        self.should_stop = True


class DocumentExportController(QObject):
    """Controller for document export operations"""

    # Signals
    export_started = Signal()
    export_progress = Signal(int, int, str)  # current, total, message
    document_exported = Signal(str, str)  # document_name, output_path
    export_error = Signal(str, str)  # document_name, error_message
    export_completed = Signal(dict)  # export_summary
    validation_failed = Signal(list)  # validation_errors

    def __init__(self):
        super().__init__()
        self.export_worker = None
        self.current_batch = None
        self.current_schema = None
        self.export_settings = None

    def set_current_batch(self, batch: DocumentBatch):
        """Set current document batch"""
        self.current_batch = batch

    def set_current_schema(self, schema: DynamicIndexSchema):
        """Set current index schema"""
        self.current_schema = schema

    def set_export_settings(self, settings: ExportSettings):
        """Set export settings"""
        self.export_settings = settings

    def validate_export_readiness(self, assignments: List[PageAssignment]) -> tuple[bool, List[str]]:
        """Validate that export is ready to proceed"""
        errors = []

        if not self.current_batch:
            errors.append("No document batch loaded")

        if not self.current_schema:
            errors.append("No index schema available")

        if not assignments:
            errors.append("No page assignments found")

        if not self.export_settings:
            # Set default export settings
            from src.models.scan_profile import ExportSettings
            self.export_settings = ExportSettings()

        # Check that all assignments have valid pages
        if self.current_batch and assignments:
            for assignment in assignments:
                valid_pages = 0
                for page_id in assignment.page_ids:
                    page = self.current_batch.get_page_by_id(page_id)
                    if page and os.path.exists(page.image_path):
                        valid_pages += 1

                if valid_pages == 0:
                    errors.append(f"Assignment {assignment.assignment_id[:8]} has no valid pages")

        # Check schema validation
        if self.current_schema and assignments:
            for assignment in assignments:
                field_errors = self.current_schema.validate_all_values(assignment.index_values)
                if field_errors:
                    errors.append(f"Assignment {assignment.assignment_id[:8]} has validation errors")

        return len(errors) == 0, errors

    def generate_export_groups(self, assignments: List[PageAssignment]) -> List[Dict]:
        """Generate export groups from assignments"""
        if not self.current_schema:
            return []

        groups = []

        for assignment in assignments:
            if not assignment.page_ids:  # Skip empty assignments
                continue

            # Update previews to ensure they're current
            assignment.update_previews(self.current_schema)

            group = {
                'assignment_id': assignment.assignment_id,
                'page_ids': assignment.page_ids.copy(),
                'index_values': assignment.index_values.copy(),
                'folder_path': assignment.folder_path_preview,
                'filename': assignment.document_name_preview,
                'page_count': len(assignment.page_ids)
            }
            groups.append(group)

        return groups

    def preview_export_structure(self, assignments: List[PageAssignment]) -> Dict:
        """Generate preview of export structure"""
        groups = self.generate_export_groups(assignments)

        # Analyze folder structure
        folders = set()
        files_per_folder = {}
        total_pages = 0

        for group in groups:
            folder_path = group['folder_path'] or "Root"
            folders.add(folder_path)
            files_per_folder[folder_path] = files_per_folder.get(folder_path, 0) + 1
            total_pages += group['page_count']

        return {
            'document_groups': groups,
            'total_documents': len(groups),
            'total_pages': total_pages,
            'folder_structure': {
                'total_folders': len(folders),
                'folder_paths': sorted(list(folders)),
                'files_per_folder': files_per_folder,
                'max_files_in_folder': max(files_per_folder.values()) if files_per_folder else 0
            }
        }

    def start_export(self, assignments: List[PageAssignment], output_directory: str) -> bool:
        """Start the export process"""
        try:
            # Validate readiness
            is_ready, errors = self.validate_export_readiness(assignments)
            if not is_ready:
                self.validation_failed.emit(errors)
                return False

            # Check if already exporting
            if self.export_worker and self.export_worker.isRunning():
                return False

            # Generate export groups
            export_groups = self.generate_export_groups(assignments)
            if not export_groups:
                self.validation_failed.emit(["No valid document groups to export"])
                return False

            # Validate output directory
            output_path = Path(output_directory)
            if not output_path.exists():
                try:
                    output_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.validation_failed.emit([f"Cannot create output directory: {str(e)}"])
                    return False

            # Start export worker
            self.export_worker = ExportWorker(
                export_groups,
                output_directory,
                self.current_batch,
                self.export_settings or ExportSettings()
            )

            # Connect signals
            self.export_worker.export_progress.connect(self.export_progress.emit)
            self.export_worker.document_exported.connect(self.document_exported.emit)
            self.export_worker.export_error.connect(self.export_error.emit)
            self.export_worker.export_completed.connect(self._on_export_completed)

            self.export_worker.start()
            self.export_started.emit()

            return True

        except Exception as e:
            self.validation_failed.emit([f"Failed to start export: {str(e)}"])
            return False

    def stop_export(self):
        """Stop current export process"""
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.stop()
            self.export_worker.wait(5000)  # Wait up to 5 seconds

    def _on_export_completed(self, successful_count: int, total_count: int):
        """Handle export completion"""
        summary = {
            'successful_exports': successful_count,
            'total_documents': total_count,
            'failed_exports': total_count - successful_count,
            'success_rate': (successful_count / max(total_count, 1)) * 100
        }

        self.export_completed.emit(summary)

    def is_exporting(self) -> bool:
        """Check if export is currently in progress"""
        return self.export_worker is not None and self.export_worker.isRunning()

    def get_export_summary_for_assignments(self, assignments: List[PageAssignment]) -> Dict:
        """Get detailed export summary for given assignments"""
        # Ensure we have export settings for validation
        if not self.export_settings:
            from src.models.scan_profile import ExportSettings
            self.export_settings = ExportSettings()

        groups = self.generate_export_groups(assignments)
        preview = self.preview_export_structure(assignments)

        # Calculate file sizes (estimated)
        total_estimated_size = 0
        for assignment in assignments:
            # Estimate ~500KB per page for PDF
            total_estimated_size += len(assignment.page_ids) * 500 * 1024

        return {
            'preview': preview,
            'estimated_file_size': total_estimated_size,
            'estimated_file_size_mb': total_estimated_size / (1024 * 1024),
            'validation_ready': self.validate_export_readiness(assignments)[0],
            'validation_errors': self.validate_export_readiness(assignments)[1]
        }


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
    
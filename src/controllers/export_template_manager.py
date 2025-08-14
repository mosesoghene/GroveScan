from PySide6.QtCore import QObject, Signal
from typing import List, Dict, Optional
import json
import os
from pathlib import Path

from src.controllers.export_controller import ExportFormat, PDFEngine, ExportTemplate


class ExportTemplateManager(QObject):
    """Manager for export configuration templates"""

    # Signals
    templates_updated = Signal(list)  # List[ExportTemplate]
    template_saved = Signal(str)  # template_name
    template_deleted = Signal(str)  # template_name
    operation_error = Signal(str)  # error_message

    def __init__(self):
        super().__init__()
        self.templates_directory = "export_templates"
        self._ensure_templates_directory()
        self._create_default_templates()

    def _ensure_templates_directory(self):
        """Ensure templates directory exists"""
        if not os.path.exists(self.templates_directory):
            os.makedirs(self.templates_directory)

    def _create_default_templates(self):
        """Create default export templates if they don't exist"""
        default_templates = [
            ExportTemplate(
                name="High Quality PDF",
                description="High quality PDF with ReportLab engine for professional documents",
                format=ExportFormat.PDF,
                pdf_engine=PDFEngine.REPORTLAB,
                quality=95,
                compression="low",
                create_folders=True,
                overwrite_existing=False,
                add_timestamp=False,
                page_size="auto",
                margins=(0.5, 0.5, 0.5, 0.5),
                fit_to_page=True,
                maintain_aspect_ratio=True
            ),
            ExportTemplate(
                name="Fast PDF",
                description="Quick PDF export using PIL for fast processing",
                format=ExportFormat.PDF,
                pdf_engine=PDFEngine.PIL,
                quality=85,
                compression="medium",
                create_folders=True,
                overwrite_existing=False,
                add_timestamp=False
            ),
            ExportTemplate(
                name="Archive TIFF",
                description="Multi-page TIFF for long-term archival storage",
                format=ExportFormat.TIFF,
                quality=100,
                compression="lzw",
                create_folders=True,
                overwrite_existing=False,
                add_timestamp=True
            ),
            ExportTemplate(
                name="Web Images",
                description="Individual PNG files optimized for web use",
                format=ExportFormat.PNG,
                quality=85,
                compression="medium",
                create_folders=True,
                overwrite_existing=False,
                add_timestamp=False
            ),
            ExportTemplate(
                name="Letter Size PDF",
                description="PDF formatted for US Letter size pages",
                format=ExportFormat.PDF,
                pdf_engine=PDFEngine.REPORTLAB,
                quality=90,
                compression="medium",
                create_folders=True,
                overwrite_existing=False,
                add_timestamp=False,
                page_size="letter",
                margins=(1.0, 1.0, 1.0, 1.0),
                fit_to_page=True,
                maintain_aspect_ratio=True
            ),
            ExportTemplate(
                name="A4 PDF",
                description="PDF formatted for A4 size pages",
                format=ExportFormat.PDF,
                pdf_engine=PDFEngine.REPORTLAB,
                quality=90,
                compression="medium",
                create_folders=True,
                overwrite_existing=False,
                add_timestamp=False,
                page_size="a4",
                margins=(1.0, 1.0, 1.0, 1.0),
                fit_to_page=True,
                maintain_aspect_ratio=True
            ),
            ExportTemplate(
                name="Email Friendly",
                description="Compressed files suitable for email attachment",
                format=ExportFormat.PDF,
                pdf_engine=PDFEngine.PIL,
                quality=70,
                compression="high",
                create_folders=False,
                overwrite_existing=True,
                add_timestamp=True
            )
        ]

        # Save default templates if they don't exist
        existing_templates = self.get_available_templates()
        existing_names = {t.name for t in existing_templates}

        for template in default_templates:
            if template.name not in existing_names:
                try:
                    self.save_template(template)
                except Exception as e:
                    print(f"Warning: Could not save default template '{template.name}': {e}")

    def get_available_templates(self) -> List[ExportTemplate]:
        """Get list of available export templates"""
        templates = []

        try:
            if not os.path.exists(self.templates_directory):
                return templates

            for filename in os.listdir(self.templates_directory):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.templates_directory, filename)
                    template = self._load_template_from_file(filepath)
                    if template:
                        templates.append(template)

            # Sort by name
            templates.sort(key=lambda t: t.name.lower())
            self.templates_updated.emit(templates)

        except Exception as e:
            self.operation_error.emit(f"Error loading templates: {str(e)}")

        return templates

    def save_template(self, template: ExportTemplate) -> bool:
        """Save an export template"""
        try:
            filename = f"{template.name.replace(' ', '_').replace('/', '_').lower()}.json"
            filepath = os.path.join(self.templates_directory, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)

            self.template_saved.emit(template.name)
            self.templates_updated.emit(self.get_available_templates())
            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to save template: {str(e)}")
            return False

    def load_template(self, template_name: str) -> Optional[ExportTemplate]:
        """Load a template by name"""
        try:
            filepath = self._get_template_filepath(template_name)
            if not filepath:
                raise ValueError(f"Template '{template_name}' not found")

            return self._load_template_from_file(filepath)

        except Exception as e:
            self.operation_error.emit(f"Failed to load template: {str(e)}")
            return None

    def delete_template(self, template_name: str) -> bool:
        """Delete a template"""
        try:
            filepath = self._get_template_filepath(template_name)
            if not filepath:
                raise ValueError(f"Template '{template_name}' not found")

            os.remove(filepath)
            self.template_deleted.emit(template_name)
            self.templates_updated.emit(self.get_available_templates())
            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to delete template: {str(e)}")
            return False

    def duplicate_template(self, template_name: str, new_name: str) -> Optional[ExportTemplate]:
        """Duplicate an existing template with new name"""
        try:
            original_template = self.load_template(template_name)
            if not original_template:
                raise ValueError(f"Original template '{template_name}' not found")

            # Create duplicate
            duplicate = ExportTemplate(
                name=new_name,
                description=f"Copy of {original_template.description}",
                format=original_template.format,
                pdf_engine=original_template.pdf_engine,
                quality=original_template.quality,
                compression=original_template.compression,
                create_folders=original_template.create_folders,
                overwrite_existing=original_template.overwrite_existing,
                add_timestamp=original_template.add_timestamp,
                page_size=original_template.page_size,
                margins=original_template.margins,
                fit_to_page=original_template.fit_to_page,
                maintain_aspect_ratio=original_template.maintain_aspect_ratio
            )

            # Save duplicate
            if self.save_template(duplicate):
                return duplicate
            else:
                raise ValueError("Failed to save duplicated template")

        except Exception as e:
            self.operation_error.emit(f"Failed to duplicate template: {str(e)}")
            return None

    def import_template(self, filepath: str) -> Optional[ExportTemplate]:
        """Import a template from external file"""
        try:
            template = self._load_template_from_file(filepath)
            if not template:
                raise ValueError("Invalid template file")

            # Check if template already exists
            existing_templates = self.get_available_templates()
            existing_names = {t.name for t in existing_templates}

            if template.name in existing_names:
                # Could prompt user for new name or overwrite
                template.name = f"{template.name}_imported"

            # Save to templates directory
            if self.save_template(template):
                return template
            else:
                raise ValueError("Failed to save imported template")

        except Exception as e:
            self.operation_error.emit(f"Failed to import template: {str(e)}")
            return None

    def export_template(self, template_name: str, export_path: str) -> bool:
        """Export a template to specified path"""
        try:
            template = self.load_template(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' not found")

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to export template: {str(e)}")
            return False

    def get_template_by_format(self, format: ExportFormat) -> List[ExportTemplate]:
        """Get templates filtered by format"""
        all_templates = self.get_available_templates()
        return [t for t in all_templates if t.format == format]

    def get_recommended_template(self, page_count: int, estimated_size_mb: float) -> ExportTemplate:
        """Get recommended template based on document characteristics"""
        templates = self.get_available_templates()

        # Find templates by name (fallback to first available)
        template_map = {t.name: t for t in templates}

        # Recommendation logic
        if page_count > 50 or estimated_size_mb > 100:
            # Large batch - use fast processing
            return template_map.get("Fast PDF", templates[0] if templates else self._get_default_template())
        elif estimated_size_mb < 10:
            # Small document - use high quality
            return template_map.get("High Quality PDF", templates[0] if templates else self._get_default_template())
        else:
            # Medium size - balanced approach
            return template_map.get("High Quality PDF", templates[0] if templates else self._get_default_template())

    def validate_template(self, template: ExportTemplate) -> List[str]:
        """Validate template configuration"""
        errors = []

        # Check name
        if not template.name or not template.name.strip():
            errors.append("Template name is required")

        # Check quality range
        if not (10 <= template.quality <= 100):
            errors.append("Quality must be between 10 and 100")

        # Check margins
        if any(m < 0 for m in template.margins):
            errors.append("Margins cannot be negative")

        # Check ReportLab availability for advanced features
        if template.pdf_engine == PDFEngine.REPORTLAB and template.format == ExportFormat.PDF:
            try:
                import reportlab
            except ImportError:
                errors.append("ReportLab is not installed but required for advanced PDF features")

        return errors

    def _load_template_from_file(self, filepath: str) -> Optional[ExportTemplate]:
        """Load template from specific file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return ExportTemplate.from_dict(data)

        except Exception as e:
            print(f"Error loading template from {filepath}: {e}")
            return None

    def _get_template_filepath(self, template_name: str) -> Optional[str]:
        """Get filepath for a template by name"""
        try:
            for filename in os.listdir(self.templates_directory):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.templates_directory, filename)
                    template = self._load_template_from_file(filepath)
                    if template and template.name == template_name:
                        return filepath
        except Exception:
            pass

        return None

    def _get_default_template(self) -> ExportTemplate:
        """Get a basic default template"""
        return ExportTemplate(
            name="Default",
            description="Basic PDF export",
            format=ExportFormat.PDF,
            pdf_engine=PDFEngine.PIL,
            quality=85,
            compression="medium",
            create_folders=True,
            overwrite_existing=False,
            add_timestamp=False
        )

    def get_format_capabilities(self) -> Dict[str, Dict]:
        """Get capabilities information for each format"""
        return {
            "PDF": {
                "multi_page": True,
                "compression": True,
                "engines": ["PIL", "ReportLab"],
                "page_sizing": True,
                "professional": True,
                "file_size": "Medium"
            },
            "TIFF": {
                "multi_page": True,
                "compression": True,
                "engines": ["PIL"],
                "page_sizing": False,
                "professional": True,
                "file_size": "Large"
            },
            "PNG": {
                "multi_page": False,
                "compression": True,
                "engines": ["PIL"],
                "page_sizing": False,
                "professional": False,
                "file_size": "Medium"
            },
            "JPEG": {
                "multi_page": False,
                "compression": True,
                "engines": ["PIL"],
                "page_sizing": False,
                "professional": False,
                "file_size": "Small"
            }
        }

    def get_compression_levels(self) -> Dict[str, str]:
        """Get available compression levels with descriptions"""
        return {
            "none": "No compression - largest file size, fastest processing",
            "low": "Light compression - good quality, moderate file size",
            "medium": "Balanced compression - good quality/size balance",
            "high": "Heavy compression - smaller files, may reduce quality"
        }

    def create_template_from_settings(self, name: str, settings_dict: Dict) -> ExportTemplate:
        """Create template from settings dictionary"""
        return ExportTemplate(
            name=name,
            description=settings_dict.get('description', ''),
            format=ExportFormat(settings_dict.get('format', 'pdf')),
            pdf_engine=PDFEngine(settings_dict.get('pdf_engine', 'pil')),
            quality=settings_dict.get('quality', 85),
            compression=settings_dict.get('compression', 'medium'),
            create_folders=settings_dict.get('create_folders', True),
            overwrite_existing=settings_dict.get('overwrite_existing', False),
            add_timestamp=settings_dict.get('add_timestamp', False),
            page_size=settings_dict.get('page_size', 'auto'),
            margins=tuple(settings_dict.get('margins', [0.5, 0.5, 0.5, 0.5])),
            fit_to_page=settings_dict.get('fit_to_page', True),
            maintain_aspect_ratio=settings_dict.get('maintain_aspect_ratio', True)
        )

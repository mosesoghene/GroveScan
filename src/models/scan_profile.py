from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from .dynamic_index_schema import DynamicIndexSchema
import json
import os
from datetime import datetime


@dataclass
class ScannerSettings:
    device_name: str = ""
    resolution: int = 300
    color_mode: str = "Color"  # Color, Grayscale, Black&White
    format: str = "TIFF"  # TIFF, PNG, JPEG
    quality: int = 95  # For JPEG compression


@dataclass
class ExportSettings:
    output_format: str = "PDF"  # PDF, TIFF, PNG, JPEG
    pdf_quality: int = 95
    create_folders: bool = True
    overwrite_existing: bool = False


@dataclass
class ScanProfile:
    name: str
    schema: DynamicIndexSchema
    filled_values: Dict[str, str] = field(default_factory=dict)
    scanner_settings: ScannerSettings = field(default_factory=ScannerSettings)
    export_settings: ExportSettings = field(default_factory=ExportSettings)
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_date: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""

    def update_modified_date(self):
        """Update the modified date to current time"""
        self.modified_date = datetime.now().isoformat()

    def clone(self, new_name: str) -> 'ScanProfile':
        """Create a copy of this profile with a new name"""
        # Deep copy the schema
        import copy
        new_schema = copy.deepcopy(self.schema)

        return ScanProfile(
            name=new_name,
            schema=new_schema,
            filled_values=self.filled_values.copy(),
            scanner_settings=self.scanner_settings,
            export_settings=self.export_settings,
            description=f"Copy of {self.name}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for serialization"""
        data = asdict(self)

        # Convert schema fields to dict format
        data['schema']['fields'] = [
            {
                'name': f.name,
                'field_type': f.field_type.value,
                'order': f.order,
                'default_value': f.default_value,
                'is_required': f.is_required,
                'validation_rules': asdict(f.validation_rules)
            }
            for f in self.schema.fields
        ]

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanProfile':
        """Create profile from dictionary"""
        from .index_field import IndexField, IndexFieldType, ValidationRule

        # Reconstruct schema
        schema = DynamicIndexSchema(separator=data['schema']['separator'])

        for field_data in data['schema']['fields']:
            validation_rule = ValidationRule(**field_data['validation_rules'])
            field = IndexField(
                name=field_data['name'],
                field_type=IndexFieldType(field_data['field_type']),
                order=field_data['order'],
                default_value=field_data['default_value'],
                is_required=field_data['is_required'],
                validation_rules=validation_rule
            )
            schema.fields.append(field)

        return cls(
            name=data['name'],
            schema=schema,
            filled_values=data['filled_values'],
            scanner_settings=ScannerSettings(**data['scanner_settings']),
            export_settings=ExportSettings(**data['export_settings']),
            created_date=data.get('created_date', datetime.now().isoformat()),
            modified_date=data.get('modified_date', datetime.now().isoformat()),
            description=data.get('description', '')
        )
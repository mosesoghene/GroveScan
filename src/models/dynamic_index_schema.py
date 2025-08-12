from typing import List, Dict, Optional
from dataclasses import dataclass, field
from .index_field import IndexField, IndexFieldType
import json
import os


@dataclass
class DynamicIndexSchema:
    fields: List[IndexField] = field(default_factory=list)
    separator: str = "_"

    def add_field(self, field: IndexField) -> None:
        """Add a new field to the schema"""
        # Ensure unique names
        if self.get_field_by_name(field.name):
            raise ValueError(f"Field with name '{field.name}' already exists")

        self.fields.append(field)
        self._reorder_fields()

    def remove_field(self, field_name: str) -> bool:
        """Remove a field by name"""
        for i, field in enumerate(self.fields):
            if field.name == field_name:
                del self.fields[i]
                self._reorder_fields()
                return True
        return False

    def reorder_field(self, field_name: str, new_position: int) -> bool:
        """Move a field to a new position"""
        field = self.get_field_by_name(field_name)
        if not field:
            return False

        # Remove from current position
        self.fields.remove(field)

        # Insert at new position
        field.order = new_position
        self.fields.insert(min(new_position, len(self.fields)), field)
        self._reorder_fields()
        return True

    def get_field_by_name(self, name: str) -> Optional[IndexField]:
        """Get field by name"""
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def get_folder_hierarchy(self) -> List[IndexField]:
        """Get fields that create folder structure in order"""
        folder_fields = [f for f in self.fields if f.field_type == IndexFieldType.FOLDER]
        return sorted(folder_fields, key=lambda x: x.order)

    def get_filename_components(self) -> List[IndexField]:
        """Get fields that are part of filename in order"""
        filename_fields = [f for f in self.fields if f.field_type == IndexFieldType.FILENAME]
        return sorted(filename_fields, key=lambda x: x.order)

    def get_metadata_fields(self) -> List[IndexField]:
        """Get metadata fields"""
        return [f for f in self.fields if f.field_type == IndexFieldType.METADATA]

    def _reorder_fields(self) -> None:
        """Reorder fields based on their order attribute"""
        self.fields.sort(key=lambda x: x.order)

    def generate_folder_path(self, values: Dict[str, str]) -> str:
        """Generate folder path from field values"""
        folder_fields = self.get_folder_hierarchy()
        path_parts = []

        for field in folder_fields:
            value = values.get(field.name, field.default_value)
            if value:
                # Sanitize folder name
                sanitized = self._sanitize_filename(value)
                path_parts.append(sanitized)

        return os.path.join(*path_parts) if path_parts else ""

    def generate_filename(self, values: Dict[str, str], extension: str = ".pdf") -> str:
        """Generate filename from field values"""
        filename_fields = self.get_filename_components()
        filename_parts = []

        for field in filename_fields:
            value = values.get(field.name, field.default_value)
            if value:
                # Sanitize filename part
                sanitized = self._sanitize_filename(value)
                filename_parts.append(sanitized)

        if not filename_parts:
            filename_parts.append("document")

        filename = self.separator.join(filename_parts)
        return f"{filename}{extension}"

    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid characters from filename/folder name"""
        # Remove invalid characters for Windows/Linux/Mac
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')

        # Remove leading/trailing spaces and dots
        return name.strip(' .')

    def validate_all_values(self, values: Dict[str, str]) -> Dict[str, str]:
        """Validate all field values, return dict of field_name -> error_message"""
        errors = {}

        for field in self.fields:
            value = values.get(field.name, "")
            is_valid, error_msg = field.validate_value(value)
            if not is_valid:
                errors[field.name] = error_msg

        return errors
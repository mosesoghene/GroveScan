from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import re


class IndexFieldType(Enum):
    FOLDER = "folder"
    FILENAME = "filename"
    METADATA = "metadata"


@dataclass
class ValidationRule:
    pattern: Optional[str] = None
    allowed_values: Optional[list] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    required: bool = True


@dataclass
class IndexField:
    name: str
    field_type: IndexFieldType
    order: int
    default_value: str = ""
    is_required: bool = True
    validation_rules: ValidationRule = field(default_factory=ValidationRule)

    def validate_value(self, value: str) -> tuple[bool, str]:
        """Validate a value against this field's rules"""
        if not value and self.is_required:
            return False, f"Field '{self.name}' is required"

        if not value:
            return True, ""

        # Check pattern
        if self.validation_rules.pattern:
            if not re.match(self.validation_rules.pattern, value):
                return False, f"Value '{value}' doesn't match required pattern"

        # Check allowed values
        if self.validation_rules.allowed_values:
            if value not in self.validation_rules.allowed_values:
                return False, f"Value '{value}' not in allowed values"

        # Check length
        if self.validation_rules.min_length and len(value) < self.validation_rules.min_length:
            return False, f"Value too short (minimum {self.validation_rules.min_length} characters)"

        if self.validation_rules.max_length and len(value) > self.validation_rules.max_length:
            return False, f"Value too long (maximum {self.validation_rules.max_length} characters)"

        return True, ""
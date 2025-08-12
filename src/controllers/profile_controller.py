from PySide6.QtCore import QObject, Signal
from typing import List, Dict, Optional
from src.models.scan_profile import ScanProfile
from src.models.dynamic_index_schema import DynamicIndexSchema
from src.models.index_field import IndexField, IndexFieldType
import json
import os
from datetime import datetime


class ProfileController(QObject):
    """Controller for profile management operations"""

    # Signals
    profile_loaded = Signal(object)  # ScanProfile
    profile_saved = Signal(str)  # profile_name
    profile_deleted = Signal(str)  # profile_name
    profiles_updated = Signal(list)  # List[ScanProfile]
    operation_error = Signal(str)  # error_message
    validation_error = Signal(str, dict)  # error_message, field_errors

    def __init__(self):
        super().__init__()
        self.current_profile = None
        self.profiles_directory = "profiles"
        self._ensure_profiles_directory()

    def _ensure_profiles_directory(self):
        """Ensure profiles directory exists"""
        if not os.path.exists(self.profiles_directory):
            os.makedirs(self.profiles_directory)

    def create_new_profile(self, name: str, description: str = "") -> ScanProfile:
        """Create a new profile"""
        try:
            # Validate name
            if not name or not name.strip():
                raise ValueError("Profile name cannot be empty")

            # Check if profile already exists
            if self._profile_exists(name):
                raise ValueError(f"Profile '{name}' already exists")

            # Create new profile
            profile = ScanProfile(
                name=name.strip(),
                description=description.strip(),
                schema=DynamicIndexSchema()
            )

            self.current_profile = profile
            self.profile_loaded.emit(profile)
            return profile

        except Exception as e:
            self.operation_error.emit(str(e))
            return None

    def save_profile(self, profile: ScanProfile, save_as: bool = False) -> bool:
        """Save a profile to disk"""
        try:
            # Update modification timestamp
            profile.update_modified_date()

            # Generate filename
            filename = f"{profile.name.replace(' ', '_').replace('/', '_').lower()}.json"
            filepath = os.path.join(self.profiles_directory, filename)

            # Check for conflicts if not save_as
            if not save_as and os.path.exists(filepath):
                existing_profile = self.load_profile_from_file(filepath)
                if existing_profile and existing_profile.name != profile.name:
                    raise ValueError(f"Filename conflict with existing profile")

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

            self.profile_saved.emit(profile.name)
            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to save profile: {str(e)}")
            return False

    def load_profile(self, profile_name: str) -> Optional[ScanProfile]:
        """Load a profile by name"""
        try:
            filepath = self._get_profile_filepath(profile_name)
            if not filepath:
                raise ValueError(f"Profile '{profile_name}' not found")

            profile = self.load_profile_from_file(filepath)
            if profile:
                self.current_profile = profile
                self.profile_loaded.emit(profile)
                return profile
            else:
                raise ValueError(f"Failed to load profile '{profile_name}'")

        except Exception as e:
            self.operation_error.emit(str(e))
            return None

    def load_profile_from_file(self, filepath: str) -> Optional[ScanProfile]:
        """Load profile from specific file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return ScanProfile.from_dict(data)

        except Exception as e:
            self.operation_error.emit(f"Failed to load profile from {filepath}: {str(e)}")
            return None

    def delete_profile(self, profile_name: str) -> bool:
        """Delete a profile"""
        try:
            filepath = self._get_profile_filepath(profile_name)
            if not filepath:
                raise ValueError(f"Profile '{profile_name}' not found")

            os.remove(filepath)
            self.profile_deleted.emit(profile_name)

            # Clear current profile if it was deleted
            if self.current_profile and self.current_profile.name == profile_name:
                self.current_profile = None

            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to delete profile: {str(e)}")
            return False

    def duplicate_profile(self, profile_name: str, new_name: str) -> Optional[ScanProfile]:
        """Duplicate an existing profile with new name"""
        try:
            # Load original profile
            original_profile = self.load_profile(profile_name)
            if not original_profile:
                raise ValueError(f"Original profile '{profile_name}' not found")

            # Create duplicate
            duplicate = original_profile.clone(new_name)

            # Save duplicate
            if self.save_profile(duplicate):
                return duplicate
            else:
                raise ValueError("Failed to save duplicated profile")

        except Exception as e:
            self.operation_error.emit(f"Failed to duplicate profile: {str(e)}")
            return None

    def get_available_profiles(self) -> List[ScanProfile]:
        """Get list of available profiles"""
        profiles = []

        try:
            if not os.path.exists(self.profiles_directory):
                return profiles

            for filename in os.listdir(self.profiles_directory):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.profiles_directory, filename)
                    profile = self.load_profile_from_file(filepath)
                    if profile:
                        profiles.append(profile)

            # Sort by name
            profiles.sort(key=lambda p: p.name.lower())
            self.profiles_updated.emit(profiles)

        except Exception as e:
            self.operation_error.emit(f"Error loading profiles: {str(e)}")

        return profiles

    def validate_profile_schema(self, profile: ScanProfile) -> Dict[str, str]:
        """Validate a profile's schema"""
        errors = {}

        try:
            # Check for at least one field
            if not profile.schema.fields:
                errors['schema'] = "Profile must have at least one index field"

            # Check for duplicate field names
            field_names = [f.name for f in profile.schema.fields]
            if len(field_names) != len(set(field_names)):
                errors['schema'] = "Duplicate field names found"

            # Check field name validity
            import re
            for field in profile.schema.fields:
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9_\s]*$', field.name):
                    errors[field.name] = "Invalid field name format"

            # Validate that we have proper ordering
            orders = [f.order for f in profile.schema.fields]
            if sorted(orders) != list(range(len(orders))):
                # Fix ordering
                for i, field in enumerate(sorted(profile.schema.fields, key=lambda x: x.order)):
                    field.order = i

            # Check for at least one folder or filename field
            has_folder_or_filename = any(
                f.field_type in [IndexFieldType.FOLDER, IndexFieldType.FILENAME]
                for f in profile.schema.fields
            )

            if not has_folder_or_filename:
                errors['schema'] = "Profile must have at least one Folder or Filename field"

        except Exception as e:
            errors['validation'] = f"Validation error: {str(e)}"

        if errors:
            self.validation_error.emit("Profile validation failed", errors)

        return errors

    def import_profile(self, filepath: str) -> Optional[ScanProfile]:
        """Import a profile from external file"""
        try:
            profile = self.load_profile_from_file(filepath)
            if not profile:
                raise ValueError("Invalid profile file")

            # Validate profile
            errors = self.validate_profile_schema(profile)
            if errors:
                raise ValueError(f"Profile validation failed: {list(errors.values())[0]}")

            # Check if profile already exists
            if self._profile_exists(profile.name):
                # Could prompt user for new name or overwrite
                profile.name = f"{profile.name}_imported"

            # Save to profiles directory
            if self.save_profile(profile):
                self.profiles_updated.emit(self.get_available_profiles())
                return profile
            else:
                raise ValueError("Failed to save imported profile")

        except Exception as e:
            self.operation_error.emit(f"Failed to import profile: {str(e)}")
            return None

    def export_profile(self, profile_name: str, export_path: str) -> bool:
        """Export a profile to specified path"""
        try:
            filepath = self._get_profile_filepath(profile_name)
            if not filepath:
                raise ValueError(f"Profile '{profile_name}' not found")

            profile = self.load_profile_from_file(filepath)
            if not profile:
                raise ValueError(f"Failed to load profile '{profile_name}'")

            # Save to export path
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to export profile: {str(e)}")
            return False

    def update_profile_schema(self, profile: ScanProfile, schema: DynamicIndexSchema) -> bool:
        """Update a profile's schema"""
        try:
            # Validate schema
            temp_profile = ScanProfile(
                name=profile.name,
                schema=schema,
                filled_values=profile.filled_values,
                scanner_settings=profile.scanner_settings,
                export_settings=profile.export_settings,
                description=profile.description
            )

            errors = self.validate_profile_schema(temp_profile)
            if errors:
                return False

            # Update profile
            profile.schema = schema
            profile.update_modified_date()

            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to update schema: {str(e)}")
            return False

    def update_profile_values(self, profile: ScanProfile, values: Dict[str, str]) -> bool:
        """Update profile's filled values"""
        try:
            # Validate values against schema
            errors = profile.schema.validate_all_values(values)
            if errors:
                self.validation_error.emit("Field validation failed", errors)
                return False

            profile.filled_values = values.copy()
            profile.update_modified_date()
            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to update values: {str(e)}")
            return False

    def _profile_exists(self, profile_name: str) -> bool:
        """Check if a profile with given name exists"""
        return self._get_profile_filepath(profile_name) is not None

    def _get_profile_filepath(self, profile_name: str) -> Optional[str]:
        """Get filepath for a profile by name"""
        try:
            for filename in os.listdir(self.profiles_directory):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.profiles_directory, filename)
                    profile = self.load_profile_from_file(filepath)
                    if profile and profile.name == profile_name:
                        return filepath
        except Exception:
            pass

        return None

    def get_current_profile(self) -> Optional[ScanProfile]:
        """Get current active profile"""
        return self.current_profile

    def set_current_profile(self, profile: ScanProfile):
        """Set current active profile"""
        self.current_profile = profile
        self.profile_loaded.emit(profile)
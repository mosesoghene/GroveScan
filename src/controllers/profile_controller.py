# Update to src/controllers/profile_controller.py

from PySide6.QtCore import QObject, Signal
from typing import List, Dict, Optional, Any
from src.models.scan_profile import ScanProfile
from src.models.dynamic_index_schema import DynamicIndexSchema
from src.models.index_field import IndexField, IndexFieldType
import json
import os
from datetime import datetime
from pathlib import Path

from src.utils.error_handling import ErrorHandler, ErrorSeverity
from src.utils.settings_manager import UserDataManager


class ProfileController(QObject):
    """Enhanced controller for profile management with proper user data directories"""

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

        # Use user data manager for proper directory handling
        self.user_data = UserDataManager()
        self.profiles_directory = self.user_data.get_profiles_dir()

        self.error_handler = ErrorHandler()
        self._ensure_profiles_directory()

    def _ensure_profiles_directory(self):
        """Ensure profiles directory exists and create welcome file"""
        self.profiles_directory.mkdir(parents=True, exist_ok=True)

        # Create a README file in the profiles directory if it doesn't exist
        readme_file = self.profiles_directory / "README.txt"
        if not readme_file.exists():
            readme_content = """Dynamic Scanner Profiles
========================

This folder contains your scanning profiles.
Profiles define the structure and organization of your scanned documents.

You can:
- Create new profiles in the application
- Import/export profiles as JSON files
- Back up this folder to preserve your configurations

Each profile (.json file) contains:
- Index field definitions (folder structure, filename components)
- Default scanner settings (resolution, color mode, format)
- Export preferences (PDF quality, folder creation options)

Profile files are stored as JSON and can be shared between installations.
"""
            try:
                with open(readme_file, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
            except Exception:
                pass  # Don't fail if we can't create the README

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
        """Save a profile to the user profiles directory"""
        try:
            # Update modification timestamp
            profile.update_modified_date()

            # Generate filename - use safe filename
            safe_name = self._make_safe_filename(profile.name)
            filename = f"{safe_name}.json"
            filepath = self.profiles_directory / filename

            # Check for conflicts if not save_as
            if not save_as and filepath.exists():
                existing_profile = self.load_profile_from_file(str(filepath))
                if existing_profile and existing_profile.name != profile.name:
                    raise ValueError(f"Filename conflict with existing profile")

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

            self.profile_saved.emit(profile.name)
            return True

        except PermissionError as e:
            self.error_handler.handle_error(e, "Profile save - permission denied", ErrorSeverity.ERROR)
            self.operation_error.emit("Permission denied. Please check write permissions for the profiles folder.")
            return False
        except OSError as e:
            self.error_handler.handle_error(e, "Profile save - disk error", ErrorSeverity.ERROR)
            self.operation_error.emit("Disk error occurred while saving profile. Check available disk space.")
            return False
        except Exception as e:
            self.error_handler.handle_error(e, "Profile save", ErrorSeverity.ERROR)
            self.operation_error.emit(f"Failed to save profile: {str(e)}")
            return False

    def _make_safe_filename(self, name: str) -> str:
        """Make a safe filename from profile name"""
        # Remove invalid characters for Windows/Linux/Mac
        invalid_chars = '<>:"/\\|?*'
        safe_name = name
        for char in invalid_chars:
            safe_name = safe_name.replace(char, '_')

        # Remove leading/trailing spaces and dots, limit length
        safe_name = safe_name.strip(' .').replace(' ', '_')
        return safe_name[:50]  # Limit length for filesystem compatibility

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

            # Remove file
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
            # Load original profile - search by name first
            original_profile = None
            for available_profile in self.get_available_profiles():
                if available_profile.name == profile_name:
                    original_profile = available_profile
                    break

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
        """Get list of available profiles from user directory"""
        profiles = []

        try:
            if not self.profiles_directory.exists():
                return profiles

            for filepath in self.profiles_directory.glob("*.json"):
                if filepath.name == "README.txt":
                    continue  # Skip README file

                profile = self.load_profile_from_file(str(filepath))
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
                # Suggest new name
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
            # Find profile by name
            profile = None
            for available_profile in self.get_available_profiles():
                if available_profile.name == profile_name:
                    profile = available_profile
                    break

            if not profile:
                raise ValueError(f"Profile '{profile_name}' not found")

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
        for profile in self.get_available_profiles():
            if profile.name == profile_name:
                return True
        return False

    def _get_profile_filepath(self, profile_name: str) -> Optional[str]:
        """Get filepath for a profile by name"""
        try:
            for filepath in self.profiles_directory.glob("*.json"):
                if filepath.name == "README.txt":
                    continue

                profile = self.load_profile_from_file(str(filepath))
                if profile and profile.name == profile_name:
                    return str(filepath)
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

    def get_profiles_directory(self) -> Path:
        """Get the profiles directory path"""
        return self.profiles_directory

    def get_profile_backup_info(self) -> Dict[str, Any]:
        """Get information for profile backup purposes"""
        profiles_info = []

        for profile in self.get_available_profiles():
            filepath = self._get_profile_filepath(profile.name)
            if filepath:
                file_path = Path(filepath)
                profiles_info.append({
                    'name': profile.name,
                    'description': profile.description,
                    'filepath': str(file_path),
                    'size_kb': round(file_path.stat().st_size / 1024, 2) if file_path.exists() else 0,
                    'modified': profile.modified_date,
                    'field_count': len(profile.schema.fields)
                })

        return {
            'profiles_directory': str(self.profiles_directory),
            'profile_count': len(profiles_info),
            'profiles': profiles_info,
            'total_size_kb': sum(p['size_kb'] for p in profiles_info)
        }

    def create_profile_backup(self, backup_directory: str) -> bool:
        """Create a backup of all profiles"""
        try:
            backup_path = Path(backup_directory)
            backup_path.mkdir(parents=True, exist_ok=True)

            # Create backup with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"dynamic_scanner_profiles_backup_{timestamp}"
            backup_folder = backup_path / backup_name
            backup_folder.mkdir()

            # Copy all profile files
            import shutil
            copied_count = 0

            for filepath in self.profiles_directory.glob("*.json"):
                if filepath.name != "README.txt":
                    dest_path = backup_folder / filepath.name
                    shutil.copy2(filepath, dest_path)
                    copied_count += 1

            # Create backup info file
            backup_info = {
                'created': datetime.now().isoformat(),
                'source_directory': str(self.profiles_directory),
                'profile_count': copied_count,
                'application': 'Dynamic Scanner',
                'version': '1.0.0'
            }

            with open(backup_folder / "backup_info.json", 'w') as f:
                json.dump(backup_info, f, indent=2)

            print(f"Created profile backup: {backup_folder}")
            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to create backup: {str(e)}")
            return False

    def restore_profile_backup(self, backup_directory: str) -> bool:
        """Restore profiles from a backup directory"""
        try:
            backup_path = Path(backup_directory)
            if not backup_path.exists():
                raise ValueError("Backup directory does not exist")

            # Look for backup info file to validate
            backup_info_file = backup_path / "backup_info.json"
            if backup_info_file.exists():
                with open(backup_info_file, 'r') as f:
                    backup_info = json.load(f)
                print(f"Restoring backup created: {backup_info.get('created', 'Unknown')}")

            # Copy profile files
            restored_count = 0
            for json_file in backup_path.glob("*.json"):
                if json_file.name == "backup_info.json":
                    continue

                # Validate it's a profile file by trying to load it
                try:
                    profile = self.load_profile_from_file(str(json_file))
                    if profile:
                        # Copy to profiles directory
                        import shutil
                        dest_path = self.profiles_directory / json_file.name
                        shutil.copy2(json_file, dest_path)
                        restored_count += 1
                except Exception:
                    print(f"Skipping invalid profile file: {json_file.name}")
                    continue

            # Refresh profiles list
            self.profiles_updated.emit(self.get_available_profiles())

            print(f"Restored {restored_count} profiles from backup")
            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to restore backup: {str(e)}")
            return False
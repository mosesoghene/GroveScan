from PySide6.QtCore import QObject, Signal
from typing import Dict, List, Optional
from ..controllers.scan_controller import ScanController
from ..controllers.document_controller import DocumentController
from ..controllers.profile_controller import ProfileController
from ..controllers.page_assignment_controller import PageAssignmentController
from ..models.scan_profile import ScanProfile
from ..models.document_batch import DocumentBatch
from ..models.dynamic_index_schema import DynamicIndexSchema


class ApplicationController(QObject):
    """Main application controller that coordinates all other controllers"""

    # Master signals
    application_state_changed = Signal(dict)  # Application state info
    workflow_step_completed = Signal(str)  # Step name
    critical_error = Signal(str)  # Critical error message

    def __init__(self):
        super().__init__()

        # Initialize sub-controllers
        self.scan_controller = ScanController()
        self.document_controller = DocumentController()
        self.profile_controller = ProfileController()
        self.page_assignment_controller = PageAssignmentController()

        # Application state
        self.current_workflow_step = "initial"  # initial, profile_ready, scanned, assigned, ready_to_export
        self.application_state = {
            'has_profile': False,
            'has_batch': False,
            'has_assignments': False,
            'ready_to_export': False
        }

        self._connect_controllers()

    def _connect_controllers(self):
        """Connect signals between controllers"""

        # Profile events
        self.profile_controller.profile_loaded.connect(self._on_profile_loaded)
        self.profile_controller.operation_error.connect(self._on_controller_error)

        # Scan events
        self.scan_controller.scan_completed.connect(self._on_scan_completed)
        self.scan_controller.scan_error.connect(self._on_controller_error)

        # Document events
        self.document_controller.batch_updated.connect(self._on_batch_updated)
        self.document_controller.operation_error.connect(self._on_controller_error)

        # Assignment events
        self.page_assignment_controller.assignments_changed.connect(self._on_assignments_changed)
        self.page_assignment_controller.operation_error.connect(self._on_controller_error)

    def _on_profile_loaded(self, profile: ScanProfile):
        """Handle profile loading"""
        # Update assignment controller with schema
        self.page_assignment_controller.set_current_schema(profile.schema)

        # Update application state
        self.application_state['has_profile'] = True
        self.current_workflow_step = "profile_ready"

        self._emit_state_change()
        self.workflow_step_completed.emit("profile_loaded")

    def _on_scan_completed(self, batch: DocumentBatch):
        """Handle scan completion"""
        # Update document controller
        self.document_controller.set_current_batch(batch)

        # Update assignment controller
        self.page_assignment_controller.set_current_batch(batch)

        # Update application state
        self.application_state['has_batch'] = True
        self.current_workflow_step = "scanned"

        self._emit_state_change()
        self.workflow_step_completed.emit("scan_completed")

    def _on_batch_updated(self, batch: DocumentBatch):
        """Handle batch updates"""
        # Re-validate assignments if batch structure changed
        if self.application_state['has_assignments']:
            errors = self.page_assignment_controller.validate_all_assignments()
            if errors:
                # Handle validation errors
                pass

    def _on_assignments_changed(self):
        """Handle assignment changes"""
        assignments = self.page_assignment_controller.get_all_assignments()
        has_assignments = len(assignments) > 0

        self.application_state['has_assignments'] = has_assignments

        # Check if ready to export
        if has_assignments and self.application_state['has_batch']:
            # Validate all assignments
            errors = self.page_assignment_controller.validate_all_assignments()
            self.application_state['ready_to_export'] = len(errors) == 0

            if self.application_state['ready_to_export']:
                self.current_workflow_step = "ready_to_export"
            else:
                self.current_workflow_step = "assigned"
        else:
            self.application_state['ready_to_export'] = False
            if has_assignments:
                self.current_workflow_step = "assigned"

        self._emit_state_change()

    def _on_controller_error(self, error_message: str):
        """Handle errors from any controller"""
        self.critical_error.emit(error_message)

    def _emit_state_change(self):
        """Emit application state change"""
        state_info = self.application_state.copy()
        state_info['workflow_step'] = self.current_workflow_step
        state_info['controllers_ready'] = self._check_controllers_ready()

        self.application_state_changed.emit(state_info)

    def _check_controllers_ready(self) -> Dict[str, bool]:
        """Check readiness of all controllers"""
        return {
            'scan_controller': True,  # Always ready
            'document_controller': self.document_controller.current_batch is not None,
            'profile_controller': self.profile_controller.current_profile is not None,
            'assignment_controller': len(self.page_assignment_controller.get_all_assignments()) > 0
        }

    def get_application_summary(self) -> Dict:
        """Get comprehensive application summary"""
        summary = {
            'workflow_step': self.current_workflow_step,
            'application_state': self.application_state.copy()
        }

        # Add profile info
        if self.profile_controller.current_profile:
            summary['current_profile'] = {
                'name': self.profile_controller.current_profile.name,
                'field_count': len(self.profile_controller.current_profile.schema.fields),
                'has_defaults': bool(self.profile_controller.current_profile.filled_values)
            }

        # Add batch info
        if self.document_controller.current_batch:
            summary['current_batch'] = {
                'name': self.document_controller.current_batch.batch_name,
                'page_count': len(self.document_controller.current_batch.scanned_pages),
                'created': self.document_controller.current_batch.created_timestamp
            }

        # Add assignment info
        assignment_summary = self.page_assignment_controller.get_assignment_summary()
        summary['assignments'] = assignment_summary

        return summary

    def can_proceed_to_export(self) -> tuple[bool, str]:
        """Check if application is ready for export"""
        if not self.application_state['has_profile']:
            return False, "No profile loaded. Please create or load a profile first."

        if not self.application_state['has_batch']:
            return False, "No documents scanned. Please scan some pages first."

        if not self.application_state['has_assignments']:
            return False, "No page assignments. Please assign pages to index values."

        # Check for validation errors
        errors = self.page_assignment_controller.validate_all_assignments()
        if errors:
            return False, f"Assignment validation errors: {len(errors)} fields have issues."

        # Check for unassigned pages
        unassigned = self.page_assignment_controller.get_unassigned_pages()
        if unassigned:
            return False, f"{len(unassigned)} pages are not assigned to any document."

        return True, "Ready to export"

    def get_export_preview(self) -> Dict:
        """Get export preview information"""
        if not self.application_state['ready_to_export']:
            return {}

        groups = self.page_assignment_controller.generate_export_preview()

        preview = {
            'document_groups': groups,
            'total_documents': len(groups),
            'total_pages': sum(group['page_count'] for group in groups),
            'folder_structure': self._analyze_folder_structure(groups)
        }

        return preview

    def _analyze_folder_structure(self, groups: List[Dict]) -> Dict:
        """Analyze the folder structure that will be created"""
        folders = set()
        files_per_folder = {}

        for group in groups:
            folder_path = group['folder_path']
            if folder_path:
                folders.add(folder_path)
                files_per_folder[folder_path] = files_per_folder.get(folder_path, 0) + 1

        return {
            'total_folders': len(folders),
            'folder_paths': sorted(list(folders)),
            'files_per_folder': files_per_folder,
            'max_files_in_folder': max(files_per_folder.values()) if files_per_folder else 0
        }

    def reset_application_state(self):
        """Reset application to initial state"""
        # Clear all controllers
        self.document_controller.current_batch = None
        self.page_assignment_controller.clear_all_assignments()

        # Reset state
        self.application_state = {
            'has_profile': self.profile_controller.current_profile is not None,
            'has_batch': False,
            'has_assignments': False,
            'ready_to_export': False
        }

        self.current_workflow_step = "profile_ready" if self.application_state['has_profile'] else "initial"

        self._emit_state_change()

    def force_sync_all_components(self):
        """Force synchronization of all components"""
        """Use this method when components might be out of sync"""

        # Sync profile and schema
        if self.profile_controller.current_profile:
            schema = self.profile_controller.current_profile.schema
            self.page_assignment_controller.set_current_schema(schema)

        # Sync batch
        if self.document_controller.current_batch:
            batch = self.document_controller.current_batch
            self.page_assignment_controller.set_current_batch(batch)

        # Re-evaluate state
        self._on_assignments_changed()

    def get_workflow_guidance(self) -> Dict[str, str]:
        """Get guidance for next steps in workflow"""
        guidance = {
            'current_step': self.current_workflow_step,
            'next_action': '',
            'description': ''
        }

        if self.current_workflow_step == "initial":
            guidance.update({
                'next_action': 'Create or load a profile',
                'description': 'Start by creating a new profile or loading an existing one to define your document structure.'
            })
        elif self.current_workflow_step == "profile_ready":
            guidance.update({
                'next_action': 'Scan documents',
                'description': 'Use the scanner controls to scan the pages you want to organize.'
            })
        elif self.current_workflow_step == "scanned":
            guidance.update({
                'next_action': 'Assign pages to documents',
                'description': 'Select pages and assign them index values to create organized documents.'
            })
        elif self.current_workflow_step == "assigned":
            guidance.update({
                'next_action': 'Validate and fix assignments',
                'description': 'Check that all assignments are valid and all pages are assigned.'
            })
        elif self.current_workflow_step == "ready_to_export":
            guidance.update({
                'next_action': 'Export documents',
                'description': 'Your documents are ready to be exported with the organized structure.'
            })

        return guidance

    
from PySide6.QtCore import QObject, Signal
from typing import List, Dict, Optional
from src.models.page_assignment import PageAssignmentManager, PageAssignment, ValidationError, AssignmentConflict
from src.models.document_batch import DocumentBatch
from src.models.dynamic_index_schema import DynamicIndexSchema
from src.models.scan_profile import ScanProfile


class PageAssignmentController(QObject):
    """Controller for page assignment operations"""

    # Signals
    assignment_created = Signal(object)  # PageAssignment
    assignment_updated = Signal(str)  # assignment_id
    assignment_deleted = Signal(str)  # assignment_id
    assignments_changed = Signal()  # General change notification
    validation_errors = Signal(list)  # List[ValidationError]
    assignment_conflicts = Signal(list)  # List[AssignmentConflict]
    preview_updated = Signal(list)  # List[document_groups]
    operation_error = Signal(str)  # error_message

    def __init__(self):
        super().__init__()
        self.assignment_manager = PageAssignmentManager()
        self.current_batch = None
        self.current_schema = None

    def set_current_batch(self, batch: DocumentBatch):
        """Set the current document batch"""
        self.current_batch = batch
        # Clear existing assignments when batch changes
        self.assignment_manager.clear_all_assignments()
        self.assignments_changed.emit()

    def set_current_schema(self, schema: DynamicIndexSchema):
        """Set the current index schema"""
        self.current_schema = schema
        # Update all assignment previews
        self._update_all_previews()

    def assign_pages_to_index(self, page_ids: List[str], index_values: Dict[str, str]) -> bool:
        """Assign pages to index values"""
        try:
            # Validate that pages exist in current batch
            if not self.current_batch:
                self.operation_error.emit("No document batch loaded")
                return False

            valid_page_ids = []
            for page_id in page_ids:
                if self.current_batch.get_page_by_id(page_id):
                    valid_page_ids.append(page_id)
                else:
                    self.operation_error.emit(f"Page {page_id} not found in current batch")
                    return False

            # Validate index values against schema
            if self.current_schema:
                errors = self.current_schema.validate_all_values(index_values)
                if errors:
                    error_list = []
                    for field_name, error_msg in errors.items():
                        error_list.append(ValidationError(
                            assignment_id="",
                            field_name=field_name,
                            error_message=error_msg,
                            page_ids=valid_page_ids
                        ))

                    self.validation_errors.emit(error_list)
                    return False

            # Create assignment
            assignment = self.assignment_manager.create_assignment(valid_page_ids, index_values)

            # Update previews
            if self.current_schema:
                assignment.update_previews(self.current_schema)

            self.assignment_created.emit(assignment)
            self.assignments_changed.emit()
            self._update_preview()

            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to assign pages: {str(e)}")
            return False

    def update_assignment_values(self, assignment_id: str, index_values: Dict[str, str]) -> bool:
        """Update index values for an existing assignment"""
        try:
            # Validate values
            if self.current_schema:
                errors = self.current_schema.validate_all_values(index_values)
                if errors:
                    error_list = []
                    assignment = self.assignment_manager.get_assignment_by_id(assignment_id)
                    page_ids = assignment.page_ids if assignment else []

                    for field_name, error_msg in errors.items():
                        error_list.append(ValidationError(
                            assignment_id=assignment_id,
                            field_name=field_name,
                            error_message=error_msg,
                            page_ids=page_ids
                        ))

                    self.validation_errors.emit(error_list)
                    return False

            # Update assignment
            success = self.assignment_manager.update_assignment(assignment_id, index_values)
            if success:
                # Update previews
                assignment = self.assignment_manager.get_assignment_by_id(assignment_id)
                if assignment and self.current_schema:
                    assignment.update_previews(self.current_schema)

                self.assignment_updated.emit(assignment_id)
                self.assignments_changed.emit()
                self._update_preview()
                return True
            else:
                self.operation_error.emit(f"Assignment {assignment_id} not found")
                return False

        except Exception as e:
            self.operation_error.emit(f"Failed to update assignment: {str(e)}")
            return False

    def remove_assignment(self, assignment_id: str) -> bool:
        """Remove an assignment"""
        try:
            success = self.assignment_manager.remove_assignment(assignment_id)
            if success:
                self.assignment_deleted.emit(assignment_id)
                self.assignments_changed.emit()
                self._update_preview()
                return True
            else:
                self.operation_error.emit(f"Assignment {assignment_id} not found")
                return False

        except Exception as e:
            self.operation_error.emit(f"Failed to remove assignment: {str(e)}")
            return False

    def move_pages_between_assignments(self, page_ids: List[str],
                                       source_assignment_id: str,
                                       target_assignment_id: str) -> bool:
        """Move pages from one assignment to another"""
        try:
            # Remove from source
            if source_assignment_id:
                self.assignment_manager.remove_pages_from_assignment(source_assignment_id, page_ids)

            # Add to target
            success = self.assignment_manager.add_pages_to_assignment(target_assignment_id, page_ids)

            if success:
                self.assignments_changed.emit()
                self._update_preview()
                return True
            else:
                self.operation_error.emit("Failed to move pages between assignments")
                return False

        except Exception as e:
            self.operation_error.emit(f"Failed to move pages: {str(e)}")
            return False

    def get_assignment_for_page(self, page_id: str) -> Optional[PageAssignment]:
        """Get assignment containing a specific page"""
        return self.assignment_manager.get_assignment_for_page(page_id)

    def get_unassigned_pages(self) -> List[str]:
        """Get pages that have no assignments"""
        if not self.current_batch:
            return []

        all_page_ids = [page.page_id for page in self.current_batch.scanned_pages]
        return self.assignment_manager.get_unassigned_pages(all_page_ids)

    def get_all_assignments(self) -> List[PageAssignment]:
        """Get all current assignments"""
        return self.assignment_manager.get_all_assignments()

    def validate_all_assignments(self) -> List[ValidationError]:
        """Validate all assignments against current schema"""
        if not self.current_schema:
            return []

        return self.assignment_manager.validate_assignments(self.current_schema)

    def get_assignment_summary(self) -> Dict:
        """Get summary of current assignments"""
        summary = self.assignment_manager.get_assignment_summary()

        # Add batch-specific info
        if self.current_batch:
            total_pages = len(self.current_batch.scanned_pages)
            unassigned_count = len(self.get_unassigned_pages())

            summary.update({
                'total_pages_in_batch': total_pages,
                'unassigned_pages': unassigned_count,
                'assignment_coverage': (summary['total_assigned_pages'] / max(total_pages, 1)) * 100
            })

        return summary

    def generate_export_preview(self) -> List[Dict]:
        """Generate preview of documents that will be created"""
        if not self.current_schema:
            return []

        try:
            groups = self.assignment_manager.generate_document_groups(self.current_schema)
            self.preview_updated.emit(groups)
            return groups

        except Exception as e:
            self.operation_error.emit(f"Failed to generate preview: {str(e)}")
            return []

    def apply_profile_defaults(self, profile: ScanProfile) -> bool:
        """Apply profile's default values to all assignments"""
        try:
            if not profile.filled_values:
                return True

            for assignment in self.assignment_manager.get_all_assignments():
                # Merge profile defaults with existing values (existing values take precedence)
                merged_values = profile.filled_values.copy()
                merged_values.update(assignment.index_values)

                self.assignment_manager.update_assignment(assignment.assignment_id, merged_values)

                # Update previews
                assignment.update_previews(self.current_schema)

            self.assignments_changed.emit()
            self._update_preview()
            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to apply profile defaults: {str(e)}")
            return False

    def clear_all_assignments(self):
        """Clear all page assignments"""
        self.assignment_manager.clear_all_assignments()
        self.assignments_changed.emit()
        self._update_preview()

    def auto_assign_sequential(self, pages_per_doc: int, base_values: Dict[str, str]) -> bool:
        """Auto-assign pages sequentially into documents"""
        try:
            if not self.current_batch:
                return False

            pages = self.current_batch.scanned_pages
            if not pages:
                return False

            # Clear existing assignments
            self.clear_all_assignments()

            # Create sequential assignments
            for i in range(0, len(pages), pages_per_doc):
                page_group = pages[i:i + pages_per_doc]
                page_ids = [page.page_id for page in page_group]

                # Create values with document number
                values = base_values.copy()
                doc_number = (i // pages_per_doc) + 1

                # Add document number to first filename field if it exists
                filename_fields = self.current_schema.get_filename_components() if self.current_schema else []
                if filename_fields:
                    first_filename_field = filename_fields[0]
                    current_value = values.get(first_filename_field.name, "")
                    values[
                        first_filename_field.name] = f"{current_value}_Doc{doc_number:03d}" if current_value else f"Doc{doc_number:03d}"

                self.assign_pages_to_index(page_ids, values)

            return True

        except Exception as e:
            self.operation_error.emit(f"Failed to auto-assign pages: {str(e)}")
            return False

    def _update_all_previews(self):
        """Update previews for all assignments"""
        if not self.current_schema:
            return

        for assignment in self.assignment_manager.get_all_assignments():
            assignment.update_previews(self.current_schema)

        self._update_preview()

    def _update_preview(self):
        """Update export preview"""
        if self.current_schema:
            self.generate_export_preview()


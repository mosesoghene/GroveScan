from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid


@dataclass
class PageAssignment:
    """Represents assignment of index values to specific pages"""

    page_ids: List[str] = field(default_factory=list)  # References to scanned pages
    index_values: Dict[str, str] = field(default_factory=dict)  # Field name → assigned value
    assignment_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Unique identifier
    document_name_preview: str = ""  # Generated filename preview
    folder_path_preview: str = ""  # Generated folder path preview

    def add_page(self, page_id: str):
        """Add a page to this assignment"""
        if page_id not in self.page_ids:
            self.page_ids.append(page_id)

    def remove_page(self, page_id: str) -> bool:
        """Remove a page from this assignment"""
        if page_id in self.page_ids:
            self.page_ids.remove(page_id)
            return True
        return False

    def has_page(self, page_id: str) -> bool:
        """Check if assignment contains a specific page"""
        return page_id in self.page_ids

    def is_empty(self) -> bool:
        """Check if assignment has no pages"""
        return len(self.page_ids) == 0

    def get_page_count(self) -> int:
        """Get number of pages in this assignment"""
        return len(self.page_ids)

    def set_index_value(self, field_name: str, value: str):
        """Set value for a specific index field"""
        self.index_values[field_name] = value

    def get_index_value(self, field_name: str) -> str:
        """Get value for a specific index field"""
        return self.index_values.get(field_name, "")

    def update_previews(self, schema):
        """Update filename and folder path previews based on current values"""
        from ..models.dynamic_index_schema import DynamicIndexSchema

        if isinstance(schema, DynamicIndexSchema):
            self.folder_path_preview = schema.generate_folder_path(self.index_values)
            self.document_name_preview = schema.generate_filename(self.index_values)


@dataclass
class ValidationError:
    """Represents a validation error for assignments"""

    assignment_id: str
    field_name: str
    error_message: str
    page_ids: List[str] = field(default_factory=list)


@dataclass
class AssignmentConflict:
    """Represents conflicts between page assignments"""

    page_id: str
    conflicting_assignments: List[str] = field(default_factory=list)  # assignment_ids
    conflict_type: str = "multiple_assignments"  # Type of conflict


class PageAssignmentManager:
    """Manages page assignments and resolves conflicts"""

    def __init__(self):
        self.assignments: List[PageAssignment] = []
        self.page_to_assignment: Dict[str, str] = {}  # page_id -> assignment_id

    def create_assignment(self, page_ids: List[str], index_values: Dict[str, str]) -> PageAssignment:
        """Create a new page assignment"""
        # Check for conflicts
        conflicts = self._check_for_conflicts(page_ids)
        if conflicts:
            # Remove pages from conflicting assignments
            self._resolve_conflicts(conflicts)

        # Create new assignment
        assignment = PageAssignment(
            page_ids=page_ids.copy(),
            index_values=index_values.copy()
        )

        self.assignments.append(assignment)

        # Update page mapping
        for page_id in page_ids:
            self.page_to_assignment[page_id] = assignment.assignment_id

        return assignment

    def update_assignment(self, assignment_id: str, index_values: Dict[str, str]) -> bool:
        """Update index values for an assignment"""
        assignment = self.get_assignment_by_id(assignment_id)
        if assignment:
            assignment.index_values = index_values.copy()
            return True
        return False

    def add_pages_to_assignment(self, assignment_id: str, page_ids: List[str]) -> bool:
        """Add pages to existing assignment"""
        assignment = self.get_assignment_by_id(assignment_id)
        if not assignment:
            return False

        # Check for conflicts
        conflicts = self._check_for_conflicts(page_ids)
        if conflicts:
            self._resolve_conflicts(conflicts)

        # Add pages to assignment
        for page_id in page_ids:
            assignment.add_page(page_id)
            self.page_to_assignment[page_id] = assignment_id

        return True

    def remove_pages_from_assignment(self, assignment_id: str, page_ids: List[str]) -> bool:
        """Remove pages from assignment"""
        assignment = self.get_assignment_by_id(assignment_id)
        if not assignment:
            return False

        for page_id in page_ids:
            if assignment.remove_page(page_id):
                if page_id in self.page_to_assignment:
                    del self.page_to_assignment[page_id]

        # Remove assignment if it's empty
        if assignment.is_empty():
            self.remove_assignment(assignment_id)

        return True

    def remove_assignment(self, assignment_id: str) -> bool:
        """Remove an entire assignment"""
        assignment = self.get_assignment_by_id(assignment_id)
        if not assignment:
            return False

        # Clear page mappings
        for page_id in assignment.page_ids:
            if page_id in self.page_to_assignment:
                del self.page_to_assignment[page_id]

        # Remove assignment
        self.assignments = [a for a in self.assignments if a.assignment_id != assignment_id]
        return True

    def get_assignment_by_id(self, assignment_id: str) -> Optional[PageAssignment]:
        """Get assignment by ID"""
        for assignment in self.assignments:
            if assignment.assignment_id == assignment_id:
                return assignment
        return None

    def get_assignment_for_page(self, page_id: str) -> Optional[PageAssignment]:
        """Get assignment containing a specific page"""
        assignment_id = self.page_to_assignment.get(page_id)
        if assignment_id:
            return self.get_assignment_by_id(assignment_id)
        return None

    def get_unassigned_pages(self, all_page_ids: List[str]) -> List[str]:
        """Get list of pages that have no assignments"""
        return [page_id for page_id in all_page_ids if page_id not in self.page_to_assignment]

    def get_all_assignments(self) -> List[PageAssignment]:
        """Get all assignments"""
        return self.assignments.copy()

    def validate_assignments(self, schema) -> List[ValidationError]:
        """Validate all assignments against schema"""
        errors = []

        for assignment in self.assignments:
            # Validate field values
            field_errors = schema.validate_all_values(assignment.index_values)

            for field_name, error_message in field_errors.items():
                errors.append(ValidationError(
                    assignment_id=assignment.assignment_id,
                    field_name=field_name,
                    error_message=error_message,
                    page_ids=assignment.page_ids.copy()
                ))

        return errors

    def _check_for_conflicts(self, page_ids: List[str]) -> List[AssignmentConflict]:
        """Check for assignment conflicts"""
        conflicts = []

        for page_id in page_ids:
            if page_id in self.page_to_assignment:
                existing_assignment_id = self.page_to_assignment[page_id]
                conflicts.append(AssignmentConflict(
                    page_id=page_id,
                    conflicting_assignments=[existing_assignment_id],
                    conflict_type="multiple_assignments"
                ))

        return conflicts

    def _resolve_conflicts(self, conflicts: List[AssignmentConflict]):
        """Resolve assignment conflicts by removing pages from previous assignments"""
        for conflict in conflicts:
            page_id = conflict.page_id

            # Remove from existing assignment
            if page_id in self.page_to_assignment:
                existing_assignment_id = self.page_to_assignment[page_id]
                existing_assignment = self.get_assignment_by_id(existing_assignment_id)

                if existing_assignment:
                    existing_assignment.remove_page(page_id)

                    # Remove assignment if empty
                    if existing_assignment.is_empty():
                        self.remove_assignment(existing_assignment_id)

                # Clear page mapping
                del self.page_to_assignment[page_id]

    def clear_all_assignments(self):
        """Clear all assignments"""
        self.assignments.clear()
        self.page_to_assignment.clear()

    def get_assignment_summary(self) -> Dict[str, int]:
        """Get summary statistics for assignments"""
        total_assignments = len(self.assignments)
        total_assigned_pages = len(self.page_to_assignment)

        # Count pages per assignment
        pages_per_assignment = {}
        for assignment in self.assignments:
            pages_per_assignment[assignment.assignment_id] = len(assignment.page_ids)

        return {
            'total_assignments': total_assignments,
            'total_assigned_pages': total_assigned_pages,
            'average_pages_per_assignment': total_assigned_pages / max(total_assignments, 1),
            'pages_per_assignment': pages_per_assignment
        }

    def generate_document_groups(self, schema) -> List[Dict]:
        """Generate document groups for export"""
        groups = []

        for assignment in self.assignments:
            if assignment.page_ids:  # Only include non-empty assignments
                # Update previews
                assignment.update_previews(schema)

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

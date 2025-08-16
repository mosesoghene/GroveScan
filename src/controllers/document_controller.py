from PySide6.QtCore import QObject, Signal
from typing import List, Optional
from src.models.document_batch import DocumentBatch
from src.models.scanned_page import ScannedPage


class DocumentController(QObject):
    """Controller for document operations"""

    # Signals
    batch_updated = Signal(object)  # DocumentBatch
    page_updated = Signal(str)  # page_id
    operation_error = Signal(str)  # error_message

    def __init__(self):
        super().__init__()
        self.current_batch = None

    def set_current_batch(self, batch: DocumentBatch):
        """Set the current document batch"""
        self.current_batch = batch
        self.batch_updated.emit(batch)

    def rotate_page(self, page_id: str, degrees: int) -> bool:
        """Rotate a page by specified degrees"""
        if not self.current_batch:
            self.operation_error.emit("No batch loaded")
            return False

        page = self.current_batch.get_page_by_id(page_id)
        if not page:
            self.operation_error.emit(f"Page {page_id} not found")
            return False

        try:
            page.rotate_page(degrees)
            self.page_updated.emit(page_id)
            return True
        except Exception as e:
            self.operation_error.emit(f"Error rotating page: {str(e)}")
            return False

    def delete_page(self, page_id: str) -> bool:
        """Delete a page from the current batch"""
        if not self.current_batch:
            self.operation_error.emit("No batch loaded")
            return False

        try:
            success = self.current_batch.remove_page(page_id)
            if success:
                self.batch_updated.emit(self.current_batch)
                return True
            else:
                self.operation_error.emit(f"Page {page_id} not found")
                return False
        except Exception as e:
            self.operation_error.emit(f"Error deleting page: {str(e)}")
            return False

    def reorder_pages(self, page_ids: List[str]) -> bool:
        """Reorder pages in the current batch"""
        if not self.current_batch:
            self.operation_error.emit("No batch loaded")
            return False

        try:
            success = self.current_batch.reorder_pages(page_ids)
            if success:
                self.batch_updated.emit(self.current_batch)
                return True
            else:
                self.operation_error.emit("Invalid page order provided")
                return False
        except Exception as e:
            self.operation_error.emit(f"Error reordering pages: {str(e)}")
            return False

    def get_current_batch(self) -> Optional[DocumentBatch]:
        """Get the current document batch"""
        return self.current_batch

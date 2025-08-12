import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from .scanned_page import ScannedPage
from .dynamic_index_schema import DynamicIndexSchema


@dataclass
class DocumentBatch:
    batch_id: str
    scanned_pages: List[ScannedPage] = field(default_factory=list)
    batch_name: str = "Untitled Batch"
    created_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_pages: int = 0

    def add_page(self, page: ScannedPage):
        """Add a page to the batch"""
        page.page_number = len(self.scanned_pages) + 1
        self.scanned_pages.append(page)
        self.total_pages = len(self.scanned_pages)

    def remove_page(self, page_id: str) -> bool:
        """Remove a page by ID"""
        for i, page in enumerate(self.scanned_pages):
            if page.page_id == page_id:
                # Clean up files
                self._cleanup_page_files(page)
                del self.scanned_pages[i]
                self._renumber_pages()
                return True
        return False

    def reorder_pages(self, page_ids: List[str]):
        """Reorder pages based on list of page IDs"""
        if len(page_ids) != len(self.scanned_pages):
            return False

        # Create mapping of page_id to page object
        page_map = {page.page_id: page for page in self.scanned_pages}

        # Reorder based on provided IDs
        try:
            self.scanned_pages = [page_map[pid] for pid in page_ids]
            self._renumber_pages()
            return True
        except KeyError:
            return False

    def get_page_by_id(self, page_id: str) -> Optional[ScannedPage]:
        """Get page by ID"""
        for page in self.scanned_pages:
            if page.page_id == page_id:
                return page
        return None

    def _renumber_pages(self):
        """Renumber all pages sequentially"""
        for i, page in enumerate(self.scanned_pages):
            page.page_number = i + 1
        self.total_pages = len(self.scanned_pages)

    def _cleanup_page_files(self, page: ScannedPage):
        """Clean up temporary files for a page"""
        try:
            if page.image_path and os.path.exists(page.image_path):
                os.remove(page.image_path)
            if page.thumbnail_path and os.path.exists(page.thumbnail_path):
                os.remove(page.thumbnail_path)
        except Exception:
            pass

    def cleanup_all_files(self):
        """Clean up all temporary files"""
        for page in self.scanned_pages:
            self._cleanup_page_files(page)

from PySide6.QtWidgets import (QWidget, QGridLayout, QScrollArea, QLabel,
                               QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
                               QMenu, QSizePolicy)
from PySide6.QtCore import pyqtSignal, Qt, QSize
from PySide6.QtGui import QPixmap, QAction, QContextMenuEvent
from ..models.scanned_page import ScannedPage
from ..models.document_batch import DocumentBatch
from typing import List, Set
import os


class PageThumbnail(QFrame):
    """Individual page thumbnail widget"""

    clicked = pyqtSignal(str)  # page_id
    double_clicked = pyqtSignal(str)  # page_id
    context_menu_requested = pyqtSignal(str, object)  # page_id, position

    def __init__(self, page: ScannedPage):
        super().__init__()
        self.page = page
        self.is_selected = False
        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """Setup thumbnail UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setFixedSize(180, 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        self.image_label.setFixedSize(160, 200)
        self.image_label.setStyleSheet("border: 1px solid #ccc;")
        layout.addWidget(self.image_label)

        # Page info
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self._update_selection_style()

    def _update_display(self):
        """Update thumbnail display"""
        # Load thumbnail image
        if os.path.exists(self.page.thumbnail_path):
            pixmap = QPixmap(self.page.thumbnail_path)
            self.image_label.setPixmap(pixmap)
        else:
            # Generate thumbnail if it doesn't exist
            if self.page.generate_thumbnail():
                pixmap = QPixmap(self.page.thumbnail_path)
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("No Preview")

        # Update info text
        info_text = f"Page {self.page.page_number}\n{self.page.resolution} DPI"
        if self.page.rotation != 0:
            info_text += f"\nRotated {self.page.rotation}°"

        self.info_label.setText(info_text)

    def set_selected(self, selected: bool):
        """Set selection state"""
        if self.is_selected != selected:
            self.is_selected = selected
            self._update_selection_style()

    def _update_selection_style(self):
        """Update visual style based on selection"""
        if self.is_selected:
            self.setStyleSheet("""
                PageThumbnail {
                    border: 3px solid #0078d4;
                    background-color: #e6f3ff;
                }
            """)
        else:
            self.setStyleSheet("""
                PageT
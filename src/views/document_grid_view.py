from PySide6.QtWidgets import (QWidget, QGridLayout, QScrollArea, QLabel,
                               QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
                               QMenu, QSizePolicy)
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QThread
from PySide6.QtGui import QPixmap, QAction, QContextMenuEvent
from src.models.scanned_page import ScannedPage
from src.models.document_batch import DocumentBatch
from typing import List, Set
import os

from src.utils.performance_monitor import PerformanceMonitor, MemoryOptimizer


class PageThumbnail(QFrame):
    """Individual page thumbnail widget"""

    clicked = Signal(str)  # page_id
    double_clicked = Signal(str)  # page_id
    context_menu_requested = Signal(str, object)  # page_id, position

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
                PageThumbnail {
                    border: 2px solid #ccc;
                    background-color: white;
                }
            """)

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.page.page_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.page.page_id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Handle right-click context menu"""
        self.context_menu_requested.emit(self.page.page_id, event.globalPos())

    def update_page_data(self, page: ScannedPage):
        """Update with new page data"""
        self.page = page
        self._update_display()


class DocumentGridView(QWidget):
    """Grid view for displaying scanned document pages"""

    # Signals
    page_selected = Signal(list)  # List[page_id]
    page_double_clicked = Signal(str)  # page_id
    pages_reordered = Signal(list)  # List[page_id] in new order
    page_rotated = Signal(str, int)  # page_id, degrees
    page_deleted = Signal(str)  # page_id

    def __init__(self):
        super().__init__()
        self.current_batch = None
        self.thumbnails = {}  # page_id -> PageThumbnail
        self.selected_pages = set()  # Set of selected page_ids
        self._setup_ui()

        # optimization settings
        self.performance_monitor = PerformanceMonitor()
        self.memory_optimizer = MemoryOptimizer(self.performance_monitor)
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._delayed_load_batch)
        self.pending_batch = None

        self.batch_load_size = 20  # Load thumbnails in batches
        self.visible_range_buffer = 5  # Extra thumbnails to keep around visible area

        # Connect performance monitoring
        self.performance_monitor.memory_warning.connect(self._handle_memory_warning)

    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)

        # Header with controls
        header_layout = QHBoxLayout()

        self.batch_label = QLabel("No batch loaded")
        self.batch_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.batch_label)

        header_layout.addStretch()

        # Selection controls
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        header_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none)
        header_layout.addWidget(select_none_btn)

        layout.addLayout(header_layout)

        # Scrollable grid area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Grid widget
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)

        self.scroll_area.setWidget(self.grid_widget)
        layout.addWidget(self.scroll_area)

        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def load_batch(self, batch: DocumentBatch):
        """Load a document batch for display with performance optimization"""
        if batch is None:
            self._clear_grid()
            return

        with self.performance_monitor.measure_operation("load_batch"):
            self.current_batch = batch
            self.selected_pages.clear()

            # For large batches, use delayed loading
            if batch and len(batch.scanned_pages) > 50:
                self.pending_batch = batch
                self.load_timer.start(100)  # Delay loading to avoid UI freeze
            else:
                self._immediate_load_batch(batch)

            self._update_batch_info()

    def _delayed_load_batch(self):
        """Load batch with delay to prevent UI freezing"""
        if self.pending_batch:
            self._immediate_load_batch(self.pending_batch)
            self.pending_batch = None

    def _immediate_load_batch(self, batch: DocumentBatch):
        """Immediate batch loading with memory optimization"""
        self._clear_grid()

        # Load thumbnails in batches for large document sets
        total_pages = len(batch.scanned_pages)

        if total_pages > self.batch_load_size:
            self._load_batch_progressive(batch)
        else:
            self._populate_grid()

    def _load_batch_progressive(self, batch: DocumentBatch):
        """Load large batches progressively"""
        self.setUpdatesEnabled(False)  # Prevent repaints during loading

        try:
            # Load first batch immediately
            for i, page in enumerate(batch.scanned_pages[:self.batch_load_size]):
                self._create_and_add_thumbnail(page, i)

            # Schedule remaining pages for background loading
            if len(batch.scanned_pages) > self.batch_load_size:
                self._schedule_background_loading(batch.scanned_pages[self.batch_load_size:])

        finally:
            self.setUpdatesEnabled(True)

    def _schedule_background_loading(self, remaining_pages: List):
        """Schedule background loading of remaining thumbnails"""
        self.background_loader = BackgroundThumbnailLoader(remaining_pages, self)
        self.background_loader.thumbnail_ready.connect(self._add_background_thumbnail)
        self.background_loader.start()

    def _create_and_add_thumbnail(self, page, position_hint: int = -1):
        """Create and add thumbnail with optimization"""
        # Check cache first
        cached_thumbnail = self.memory_optimizer.get_cached_image(page.page_id, 'thumbnails')

        if cached_thumbnail:
            thumbnail = cached_thumbnail
        else:
            thumbnail = PageThumbnail(page)
            # Cache the thumbnail
            self.memory_optimizer.cache_image(page.page_id, thumbnail, 'thumbnails')

        thumbnail.clicked.connect(self._on_page_clicked)
        thumbnail.double_clicked.connect(self._on_page_double_clicked)
        thumbnail.context_menu_requested.connect(self._on_context_menu_requested)

        self.thumbnails[page.page_id] = thumbnail

        if position_hint >= 0:
            row = position_hint // 4
            col = position_hint % 4
        else:
            page_count = len(self.thumbnails)
            row = (page_count - 1) // 4
            col = (page_count - 1) % 4

        self.grid_layout.addWidget(thumbnail, row, col)

    def _handle_memory_warning(self, memory_mb: float):
        """Handle memory usage warnings"""
        print(f"Memory warning: {memory_mb:.1f} MB")

        # Clear thumbnail cache if memory usage is high
        if memory_mb > 1024:  # 1GB threshold
            self.memory_optimizer.clear_cache('thumbnails')

            # Also clear non-visible thumbnails
            self._cleanup_non_visible_thumbnails()

    def _cleanup_non_visible_thumbnails(self):
        """Remove thumbnails that are not currently visible"""
        if not self.current_batch:
            return

        visible_rect = self.scroll_area.viewport().rect()

        # Find thumbnails outside visible area
        to_remove = []
        for page_id, thumbnail in self.thumbnails.items():
            if not thumbnail.geometry().intersects(visible_rect):
                to_remove.append(page_id)

        # Remove excess thumbnails (keep some buffer)
        buffer_count = min(20, len(to_remove) // 2)
        for page_id in to_remove[buffer_count:]:
            thumbnail = self.thumbnails.pop(page_id)
            thumbnail.setParent(None)

    def add_page(self, page: ScannedPage):
        """Add a single page to the current batch"""
        if not self.current_batch:
            return

        # Create thumbnail widget
        thumbnail = PageThumbnail(page)
        thumbnail.clicked.connect(self._on_page_clicked)
        thumbnail.double_clicked.connect(self._on_page_double_clicked)
        thumbnail.context_menu_requested.connect(self._on_context_menu_requested)

        self.thumbnails[page.page_id] = thumbnail

        # Add to grid
        self._add_thumbnail_to_grid(thumbnail)
        self._update_batch_info()

    def _clear_grid(self):
        """Clear all thumbnails from grid"""
        # Remove all widgets from layout
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.thumbnails.clear()

    def _populate_grid(self):
        """Populate grid with current batch pages"""
        if not self.current_batch:
            return

        for page in self.current_batch.scanned_pages:
            thumbnail = PageThumbnail(page)
            thumbnail.clicked.connect(self._on_page_clicked)
            thumbnail.double_clicked.connect(self._on_page_double_clicked)
            thumbnail.context_menu_requested.connect(self._on_context_menu_requested)

            self.thumbnails[page.page_id] = thumbnail
            self._add_thumbnail_to_grid(thumbnail)

    def _add_thumbnail_to_grid(self, thumbnail: PageThumbnail):
        """Add thumbnail to grid layout"""
        # Calculate grid position (4 columns)
        page_count = len(self.thumbnails)
        row = (page_count - 1) // 4
        col = (page_count - 1) % 4

        self.grid_layout.addWidget(thumbnail, row, col)

    def _update_batch_info(self):
        """Update batch information display"""
        if self.current_batch:
            batch_text = f"Batch: {self.current_batch.batch_name} ({len(self.current_batch.scanned_pages)} pages)"
            self.batch_label.setText(batch_text)

            selected_count = len(self.selected_pages)
            if selected_count > 0:
                self.status_label.setText(f"{selected_count} pages selected")
            else:
                self.status_label.setText("Ready")
        else:
            self.batch_label.setText("No batch loaded")
            self.status_label.setText("Ready")

    def _on_page_clicked(self, page_id: str):
        """Handle page thumbnail click"""
        # Check for Ctrl+Click for multi-selection
        from PySide6.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()

        if modifiers & Qt.ControlModifier:
            # Toggle selection
            if page_id in self.selected_pages:
                self.selected_pages.remove(page_id)
                self.thumbnails[page_id].set_selected(False)
            else:
                self.selected_pages.add(page_id)
                self.thumbnails[page_id].set_selected(True)
        else:
            # Single selection
            self._clear_selection()
            self.selected_pages.add(page_id)
            self.thumbnails[page_id].set_selected(True)

        self._update_batch_info()
        self.page_selected.emit(list(self.selected_pages))

    def _on_page_double_clicked(self, page_id: str):
        """Handle page thumbnail double click"""
        self.page_double_clicked.emit(page_id)

    def _on_context_menu_requested(self, page_id: str, position):
        """Handle context menu request"""
        # Ensure page is selected
        if page_id not in self.selected_pages:
            self._clear_selection()
            self.selected_pages.add(page_id)
            self.thumbnails[page_id].set_selected(True)
            self._update_batch_info()

        # Create context menu
        menu = QMenu(self)

        rotate_90_action = QAction("Rotate 90° CW", self)
        rotate_90_action.triggered.connect(lambda: self._rotate_selected_pages(90))
        menu.addAction(rotate_90_action)

        rotate_180_action = QAction("Rotate 180°", self)
        rotate_180_action.triggered.connect(lambda: self._rotate_selected_pages(180))
        menu.addAction(rotate_180_action)

        rotate_270_action = QAction("Rotate 90° CCW", self)
        rotate_270_action.triggered.connect(lambda: self._rotate_selected_pages(270))
        menu.addAction(rotate_270_action)

        menu.addSeparator()

        delete_action = QAction("Delete Page(s)", self)
        delete_action.triggered.connect(self._delete_selected_pages)
        menu.addAction(delete_action)

        menu.exec(position)

    def _rotate_selected_pages(self, degrees: int):
        """Rotate selected pages"""
        for page_id in self.selected_pages:
            self.page_rotated.emit(page_id, degrees)

            # Update thumbnail display
            if page_id in self.thumbnails:
                # Find page in current batch and update
                page = self.current_batch.get_page_by_id(page_id)
                if page:
                    page.rotate_page(degrees)
                    self.thumbnails[page_id].update_page_data(page)

    def _delete_selected_pages(self):
        """Delete selected pages"""
        if not self.selected_pages:
            return

        # Confirm deletion
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Delete Pages",
            f"Delete {len(self.selected_pages)} selected page(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            pages_to_delete = list(self.selected_pages)
            for page_id in pages_to_delete:
                self.page_deleted.emit(page_id)

            # Refresh display
            if self.current_batch:
                self.load_batch(self.current_batch)

    def _clear_selection(self):
        """Clear all selections"""
        for page_id in self.selected_pages:
            if page_id in self.thumbnails:
                self.thumbnails[page_id].set_selected(False)

        self.selected_pages.clear()

    def _select_all(self):
        """Select all pages"""
        if not self.current_batch:
            return

        self.selected_pages.clear()
        for page in self.current_batch.scanned_pages:
            self.selected_pages.add(page.page_id)
            if page.page_id in self.thumbnails:
                self.thumbnails[page.page_id].set_selected(True)

        self._update_batch_info()
        self.page_selected.emit(list(self.selected_pages))

    def _select_none(self):
        """Clear all selections"""
        self._clear_selection()
        self._update_batch_info()
        self.page_selected.emit([])

    def get_selected_page_ids(self) -> List[str]:
        """Get list of selected page IDs"""
        return list(self.selected_pages)

    def refresh_page_display(self, page_id: str):
        """Refresh display for a specific page"""
        if page_id in self.thumbnails and self.current_batch:
            page = self.current_batch.get_page_by_id(page_id)
            if page:
                self.thumbnails[page_id].update_page_data(page)


class BackgroundThumbnailLoader(QThread):
    """Background thread for loading thumbnails"""

    thumbnail_ready = Signal(object, int)  # page, position
    batch_completed = Signal()

    def __init__(self, pages: List, parent_view):
        super().__init__()
        self.pages = pages
        self.parent_view = parent_view
        self.should_stop = False

    def run(self):
        """Load thumbnails in background"""
        for i, page in enumerate(self.pages):
            if self.should_stop:
                break

            try:
                # Generate thumbnail if needed
                if not page.thumbnail_path or not os.path.exists(page.thumbnail_path):
                    page.generate_thumbnail()

                # Emit signal for main thread to add thumbnail
                self.thumbnail_ready.emit(page, i + self.parent_view.batch_load_size)

                # Small delay to prevent overwhelming the main thread
                self.msleep(50)

            except Exception as e:
                print(f"Error loading thumbnail for {page.page_id}: {e}")
                continue

        self.batch_completed.emit()

    def stop(self):
        """Stop background loading"""
        self.should_stop = True


# Add this method to DocumentGridView:
def _add_background_thumbnail(self, page, position: int):
    """Add thumbnail loaded in background"""
    QTimer.singleShot(0, lambda: self._create_and_add_thumbnail(page, position))
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QListWidget, QListWidgetItem,
                               QMenu, QApplication, QStyleOption, QStyle)
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint, QRect
from PySide6.QtGui import (QDrag, QPainter, QPixmap, QPen, QBrush, QColor,
                           QFontMetrics, QFont, QAction, QCursor)
from src.models.index_field import IndexField, IndexFieldType
from typing import List, Optional


class IndexFieldWidget(QFrame):
    """Individual index field widget with drag-and-drop support"""

    # Signals
    edit_requested = Signal(str)  # field_name
    delete_requested = Signal(str)  # field_name
    drag_started = Signal(str)  # field_name

    def __init__(self, field: IndexField):
        super().__init__()
        self.field = field
        self.is_dragging = False
        self.drag_start_position = QPoint()
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self):
        """Setup the widget UI"""
        self.setFixedHeight(50)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)

        # Drag handle
        self.drag_label = QLabel("⋮⋮")
        self.drag_label.setFixedWidth(20)
        self.drag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_label.setStyleSheet("color: #888; font-weight: bold;")
        self.drag_label.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        layout.addWidget(self.drag_label)

        # Field type icon
        type_icons = {
            IndexFieldType.FOLDER: "📁",
            IndexFieldType.FILENAME: "📄",
            IndexFieldType.METADATA: "🏷️"
        }

        self.type_label = QLabel(type_icons.get(self.field.field_type, "❓"))
        self.type_label.setFixedWidth(25)
        self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.type_label)

        # Field info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Field name
        name_text = self.field.name
        if self.field.is_required:
            name_text += " *"

        self.name_label = QLabel(name_text)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        info_layout.addWidget(self.name_label)

        # Field details
        details = []
        details.append(f"Type: {self.field.field_type.value.title()}")
        if self.field.default_value:
            details.append(f"Default: {self.field.default_value}")

        self.details_label = QLabel(" | ".join(details))
        self.details_label.setStyleSheet("color: #666; font-size: 9pt;")
        info_layout.addWidget(self.details_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Order indicator
        self.order_label = QLabel(f"#{self.field.order + 1}")
        self.order_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 9pt;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.order_label)

        # Action buttons
        self.edit_btn = QPushButton("✎")
        self.edit_btn.setFixedSize(25, 25)
        self.edit_btn.setToolTip("Edit Field")
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedSize(25, 25)
        self.delete_btn.setToolTip("Delete Field")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_btn)

    def _setup_style(self):
        """Setup widget styling"""
        type_colors = {
            IndexFieldType.FOLDER: "#e3f2fd",  # Light blue
            IndexFieldType.FILENAME: "#f3e5f5",  # Light purple
            IndexFieldType.METADATA: "#e8f5e8"  # Light green
        }

        bg_color = type_colors.get(self.field.field_type, "#f5f5f5")

        self.setStyleSheet(f"""
            IndexFieldWidget {{
                background-color: {bg_color};
                border: 1px solid #ccc;
                border-radius: 4px;
            }}
            IndexFieldWidget:hover {{
                border: 2px solid #0078d4;
                background-color: white;
            }}
            QPushButton {{
                border: none;
                border-radius: 3px;
                font-size: 10pt;
                background-color: transparent;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 120, 212, 0.1);
            }}
        """)

    def _on_edit_clicked(self):
        """Handle edit button click"""
        self.edit_requested.emit(self.field.name)

    def _on_delete_clicked(self):
        """Handle delete button click"""
        self.delete_requested.emit(self.field.name)

    def mousePressEvent(self, event):
        """Handle mouse press for drag initiation"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() <
                QApplication.startDragDistance()):
            return

        self._start_drag()

    def _start_drag(self):
        """Start drag operation"""
        drag = QDrag(self)
        mime_data = QMimeData()

        # Set the field name as drag data
        mime_data.setText(self.field.name)
        mime_data.setData("application/x-indexfield", self.field.name.encode())
        drag.setMimeData(mime_data)

        # Create drag pixmap
        pixmap = self._create_drag_pixmap()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Emit signal
        self.drag_started.emit(self.field.name)

        # Execute drag
        drop_action = drag.exec(Qt.DropAction.MoveAction)

    def _create_drag_pixmap(self) -> QPixmap:
        """Create pixmap for drag operation"""
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setOpacity(0.8)

        # Render widget to pixmap
        self.render(painter)

        painter.end()
        return pixmap

    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        menu = QMenu(self)

        edit_action = QAction("Edit Field", self)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.field.name))
        menu.addAction(edit_action)

        duplicate_action = QAction("Duplicate Field", self)
        # Note: Implement duplication in parent widget
        menu.addAction(duplicate_action)

        menu.addSeparator()

        delete_action = QAction("Delete Field", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.field.name))
        menu.addAction(delete_action)

        menu.exec(event.globalPos())

    def update_field(self, field: IndexField):
        """Update widget with new field data"""
        self.field = field
        self._setup_ui()
        self._setup_style()


class FieldListWidget(QListWidget):
    """List widget for index fields with drag-and-drop reordering"""

    # Signals
    field_reordered = Signal(str, int)  # field_name, new_position
    field_edited = Signal(str)  # field_name
    field_deleted = Signal(str)  # field_name

    def __init__(self):
        super().__init__()
        self.fields = []
        self._setup_widget()

    def _setup_widget(self):
        """Setup the list widget"""
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setSpacing(2)

        # Custom styling
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                background-color: #fafafa;
                border-radius: 4px;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: transparent;
                border: none;
            }
        """)

    def set_fields(self, fields: List[IndexField]):
        """Set the list of fields"""
        self.clear()
        self.fields = fields.copy()

        for field in sorted(fields, key=lambda x: x.order):
            self._add_field_item(field)

    def _add_field_item(self, field: IndexField):
        """Add a field item to the list"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, field.name)
        item.setSizeHint(self._get_item_size_hint())

        # Create field widget
        field_widget = IndexFieldWidget(field)
        field_widget.edit_requested.connect(self.field_edited.emit)
        field_widget.delete_requested.connect(self.field_deleted.emit)

        self.addItem(item)
        self.setItemWidget(item, field_widget)

    def _get_item_size_hint(self):
        """Get the size hint for list items"""
        from PySide6.QtCore import QSize
        return QSize(-1, 54)  # Height to accommodate IndexFieldWidget

    def dropEvent(self, event):
        """Handle drop events for reordering"""
        if event.source() == self and event.dropAction() == Qt.DropAction.MoveAction:
            # Get the dropped item info
            drop_index = self.indexAt(event.position().toPoint()).row()

            # Get the dragged item
            dragged_items = self.selectedItems()
            if not dragged_items:
                return

            dragged_item = dragged_items[0]
            field_name = dragged_item.data(Qt.ItemDataRole.UserRole)

            # Perform the move
            super().dropEvent(event)

            # Update field orders and emit signal
            self._update_field_orders()

            # Find new position
            new_position = 0
            for i in range(self.count()):
                item = self.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == field_name:
                    new_position = i
                    break

            self.field_reordered.emit(field_name, new_position)

    def _update_field_orders(self):
        """Update field orders based on current list order"""
        for i in range(self.count()):
            item = self.item(i)
            if item:
                widget = self.itemWidget(item)
                if isinstance(widget, IndexFieldWidget):
                    widget.field.order = i
                    widget.order_label.setText(f"#{i + 1}")


class DragDropIndicator(QWidget):
    """Visual indicator for drag and drop operations"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self.hide()

    def paintEvent(self, event):
        """Paint the drop indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw indicator line
        pen = QPen(QColor("#0078d4"))
        pen.setWidth(3)
        painter.setPen(pen)

        rect = self.rect()
        painter.drawLine(0, rect.height() // 2, rect.width(), rect.height() // 2)

        # Draw arrow indicators at ends
        arrow_size = 6
        painter.setBrush(QBrush(QColor("#0078d4")))

        # Left arrow
        left_arrow = [
            QPoint(0, rect.height() // 2),
            QPoint(arrow_size, rect.height() // 2 - arrow_size // 2),
            QPoint(arrow_size, rect.height() // 2 + arrow_size // 2)
        ]
        painter.drawPolygon(left_arrow)

        # Right arrow
        right_arrow = [
            QPoint(rect.width(), rect.height() // 2),
            QPoint(rect.width() - arrow_size, rect.height() // 2 - arrow_size // 2),
            QPoint(rect.width() - arrow_size, rect.height() // 2 + arrow_size // 2)
        ]
        painter.drawPolygon(right_arrow)

    def show_at_position(self, position: QPoint, width: int):
        """Show indicator at specific position"""
        self.setGeometry(position.x(), position.y(), width, 3)
        self.show()
        self.raise_()


class FieldValidationWidget(QFrame):
    """Widget for displaying field validation status"""

    def __init__(self, field: IndexField):
        super().__init__()
        self.field = field
        self.validation_errors = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup validation display UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        header_layout = QHBoxLayout()

        self.status_label = QLabel("✅")
        self.status_label.setFixedSize(20, 20)
        header_layout.addWidget(self.status_label)

        self.field_label = QLabel(self.field.name)
        self.field_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.field_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Validation messages
        self.message_label = QLabel("Field is valid")
        self.message_label.setStyleSheet("color: #666; font-size: 9pt;")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

    def set_validation_result(self, is_valid: bool, errors: List[str]):
        """Update validation display"""
        self.validation_errors = errors.copy()

        if is_valid:
            self.status_label.setText("✅")
            self.message_label.setText("Field is valid")
            self.setStyleSheet("QFrame { border: 1px solid #4caf50; background-color: #e8f5e8; }")
        else:
            self.status_label.setText("❌")
            self.message_label.setText("\n".join(errors))
            self.setStyleSheet("QFrame { border: 1px solid #f44336; background-color: #ffebee; }")

    def get_field_name(self) -> str:
        """Get the field name"""
        return self.field.name

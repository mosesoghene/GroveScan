from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QProgressBar, QGroupBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPalette
from typing import Dict


class WorkflowStepWidget(QFrame):
    """Individual workflow step indicator"""

    step_clicked = Signal(str)  # step_name

    def __init__(self, step_name: str, display_name: str, description: str):
        super().__init__()
        self.step_name = step_name
        self.display_name = display_name
        self.description = description
        self.is_active = False
        self.is_completed = False
        self.is_available = True
        self._setup_ui()

    def _setup_ui(self):
        """Setup step widget UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setFixedHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        # Header with status indicator
        header_layout = QHBoxLayout()

        self.status_label = QLabel("○")
        self.status_label.setFixedSize(20, 20)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(self.status_label)

        self.title_label = QLabel(self.display_name)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        self.desc_label = QLabel(self.description)
        self.desc_label.setStyleSheet("color: #666; font-size: 9pt;")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        self._update_appearance()

    def set_status(self, is_active: bool, is_completed: bool, is_available: bool = True):
        """Set the status of this step"""
        self.is_active = is_active
        self.is_completed = is_completed
        self.is_available = is_available
        self._update_appearance()

    def _update_appearance(self):
        """Update visual appearance based on status"""
        if self.is_completed:
            self.status_label.setText("✅")
            self.setStyleSheet("""
                WorkflowStepWidget {
                    background-color: #e8f5e8;
                    border: 2px solid #4caf50;
                    border-radius: 6px;
                }
            """)
        elif self.is_active:
            self.status_label.setText("🔄")
            self.setStyleSheet("""
                WorkflowStepWidget {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 6px;
                }
            """)
        elif self.is_available:
            self.status_label.setText("○")
            self.setStyleSheet("""
                WorkflowStepWidget {
                    background-color: #f5f5f5;
                    border: 1px solid #ccc;
                    border-radius: 6px;
                }
                WorkflowStepWidget:hover {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                }
            """)
        else:
            self.status_label.setText("⏸")
            self.setStyleSheet("""
                WorkflowStepWidget {
                    background-color: #fafafa;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    color: #999;
                }
            """)

    def mousePressEvent(self, event):
        """Handle mouse press for step selection"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_available:
            self.step_clicked.emit(self.step_name)
        super().mousePressEvent(event)


class WorkflowStatusWidget(QWidget):
    """Widget showing current workflow status and next steps"""

    step_selected = Signal(str)  # step_name
    action_requested = Signal(str)  # action_name

    def __init__(self):
        super().__init__()
        self.current_step = "initial"
        self.step_widgets
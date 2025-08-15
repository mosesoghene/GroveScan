from typing import Dict, List
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


class HelpHint(QFrame):
    """Animated help hint widget"""

    dismissed = Signal(str)  # hint_id

    def __init__(self, hint_id: str, title: str, message: str, parent=None):
        super().__init__(parent)
        self.hint_id = hint_id
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            HelpHint {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self._setup_ui(title, message)

    def _setup_ui(self, title: str, message: str):
        layout = QVBoxLayout(self)

        # Header with title and close button
        header_layout = QHBoxLayout()

        title_label = QLabel(f"💡 {title}")
        font = QFont()
        font.setBold(True)
        title_label.setFont(font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("border: none; background: transparent;")
        close_btn.clicked.connect(self._dismiss)
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #856404;")
        layout.addWidget(message_label)

    def _dismiss(self):
        """Dismiss this hint"""
        self.dismissed.emit(self.hint_id)
        self.hide()

    def show_animated(self):
        """Show with animation"""
        self.show()
        # Could add fade-in animation here


class HelpHintsManager:
    """Manages contextual help hints"""

    def __init__(self):
        self.shown_hints = set()
        self.hints_config = {
            "first_profile": {
                "title": "Welcome to Dynamic Scanner!",
                "message": "Start by creating your first profile to define how documents will be organized.",
                "trigger": "no_profile_loaded"
            },
            "after_profile": {
                "title": "Great! Profile Created",
                "message": "Now you can start scanning documents. Use the scanner controls to begin.",
                "trigger": "profile_loaded_first_time"
            },
            "first_scan": {
                "title": "Ready to Scan",
                "message": "Configure your scanner settings and click 'Start Scan' to capture your documents.",
                "trigger": "scanner_ready_first_time"
            },
            "pages_scanned": {
                "title": "Documents Scanned",
                "message": "Now select pages and assign them index values to organize your documents.",
                "trigger": "batch_completed_first_time"
            },
            "assignments_ready": {
                "title": "Almost Done!",
                "message": "Your pages are assigned. Validate assignments and then export your organized documents.",
                "trigger": "assignments_created_first_time"
            }
        }

    def should_show_hint(self, hint_id: str, context: dict) -> bool:
        """Check if a hint should be shown"""
        if hint_id in self.shown_hints:
            return False

        hint_config = self.hints_config.get(hint_id)
        if not hint_config:
            return False

        # Check trigger conditions
        trigger = hint_config["trigger"]

        if trigger == "no_profile_loaded":
            return not context.get("has_profile", False)
        elif trigger == "profile_loaded_first_time":
            return (context.get("has_profile", False) and
                    context.get("workflow_step") == "profile_ready" and
                    not context.get("has_batch", False))
        elif trigger == "scanner_ready_first_time":
            return (context.get("has_profile", False) and
                    context.get("scanner_connected", False) and
                    not context.get("has_batch", False))
        elif trigger == "batch_completed_first_time":
            return (context.get("has_batch", False) and
                    not context.get("has_assignments", False))
        elif trigger == "assignments_created_first_time":
            return (context.get("has_assignments", False) and
                    not context.get("ready_to_export", False))

        return False

    def create_hint_widget(self, hint_id: str, parent: QWidget = None) -> HelpHint:
        """Create hint widget"""
        hint_config = self.hints_config.get(hint_id)
        if not hint_config:
            return None

        hint_widget = HelpHint(
            hint_id,
            hint_config["title"],
            hint_config["message"],
            parent
        )

        hint_widget.dismissed.connect(self._mark_hint_shown)
        return hint_widget

    def _mark_hint_shown(self, hint_id: str):
        """Mark hint as shown"""
        self.shown_hints.add(hint_id)
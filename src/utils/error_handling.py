import logging
import traceback
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
from PySide6.QtCore import QObject, Signal


class ErrorSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AppError:
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    timestamp: str = None
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.context is None:
            self.context = {}


class ErrorHandler(QObject):
    error_occurred = Signal(object)  # AppError

    def __init__(self):
        super().__init__()
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scanner_app.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('DynamicScanner')

    def handle_error(self, error: Exception, context: str = "", severity: ErrorSeverity = ErrorSeverity.ERROR):
        """Handle an exception with context"""
        error_obj = AppError(
            severity=severity,
            message=str(error),
            details=traceback.format_exc(),
            context={'operation': context}
        )

        self.logger.error(f"{context}: {str(error)}")
        self.error_occurred.emit(error_obj)

        if severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            self.show_error_dialog(error_obj)

    def show_error_dialog(self, error: AppError):
        """Show user-friendly error dialog"""
        dialog = ErrorDialog(error)
        dialog.exec()


class ErrorDialog(QDialog):
    def __init__(self, error: AppError, parent=None):
        super().__init__(parent)
        self.error = error
        self.setWindowTitle("Error")
        self.setModal(True)
        self.resize(500, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # User-friendly message
        message = QTextEdit()
        message.setPlainText(self._get_user_message())
        message.setMaximumHeight(100)
        layout.addWidget(message)

        # Technical details (collapsible)
        if self.error.details:
            details = QTextEdit()
            details.setPlainText(self.error.details)
            details.setMaximumHeight(150)
            layout.addWidget(details)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _get_user_message(self) -> str:
        """Convert technical error to user-friendly message"""
        error_msg = self.error.message.lower()

        if "permission" in error_msg or "access" in error_msg:
            return "Permission denied. Please check file permissions or run as administrator."
        elif "file not found" in error_msg:
            return "Required file not found. Please check that all files are in place."
        elif "memory" in error_msg:
            return "Not enough memory. Try closing other applications or processing fewer pages."
        elif "disk" in error_msg or "space" in error_msg:
            return "Not enough disk space. Please free up space and try again."
        else:
            return f"An error occurred: {self.error.message}"

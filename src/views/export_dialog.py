from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
                               QLineEdit, QFileDialog, QProgressDialog, QCheckBox,
                               QSpinBox, QComboBox, QTextEdit, QDialogButtonBox,
                               QMessageBox, QGridLayout, QFrame, QSplitter)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from typing import Dict, List
import os


class ExportPreviewDialog(QDialog):
    """Dialog for previewing export structure before exporting"""

    export_confirmed = Signal(str, dict)  # output_dir, export_settings

    def __init__(self, export_summary: Dict, parent=None):
        super().__init__(parent)
        self.export_summary = export_summary
        self.setWindowTitle("Export Preview")
        self.setModal(True)
        self.resize(800, 600)
        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)

        # Create splitter for preview and settings
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Structure preview
        preview_panel = self._create_preview_panel()
        splitter.addWidget(preview_panel)

        # Right panel - Export settings
        settings_panel = self._create_settings_panel()
        splitter.addWidget(settings_panel)

        splitter.setSizes([500, 300])
        layout.addWidget(splitter)

        # Summary information
        summary_group = QGroupBox("Export Summary")
        summary_layout = QGridLayout(summary_group)

        preview = self.export_summary['preview']

        summary_layout.addWidget(QLabel("Documents to create:"), 0, 0)
        summary_layout.addWidget(QLabel(str(preview['total_documents'])), 0, 1)

        summary_layout.addWidget(QLabel("Total pages:"), 1, 0)
        summary_layout.addWidget(QLabel(str(preview['total_pages'])), 1, 1)

        summary_layout.addWidget(QLabel("Folders to create:"), 2, 0)
        summary_layout.addWidget(QLabel(str(preview['folder_structure']['total_folders'])), 2, 1)

        summary_layout.addWidget(QLabel("Estimated size:"), 3, 0)
        size_mb = self.export_summary.get('estimated_file_size_mb', 0)
        summary_layout.addWidget(QLabel(f"{size_mb:.1f} MB"), 3, 1)

        layout.addWidget(summary_group)

        # Validation status
        if not self.export_summary.get('validation_ready', True):
            validation_frame = QFrame()
            validation_frame.setStyleSheet(
                "QFrame { background-color: #ffebee; border: 1px solid #f44336; border-radius: 4px; }")
            validation_layout = QVBoxLayout(validation_frame)

            warning_label = QLabel("⚠️ Validation Issues Found:")
            warning_label.setStyleSheet("font-weight: bold; color: #d32f2f;")
            validation_layout.addWidget(warning_label)

            errors = self.export_summary.get('validation_errors', [])
            for error in errors[:5]:  # Show first 5 errors
                error_label = QLabel(f"• {error}")
                error_label.setStyleSheet("color: #d32f2f; margin-left: 10px;")
                validation_layout.addWidget(error_label)

            if len(errors) > 5:
                more_label = QLabel(f"... and {len(errors) - 5} more issues")
                more_label.setStyleSheet("color: #d32f2f; margin-left: 10px; font-style: italic;")
                validation_layout.addWidget(more_label)

            layout.addWidget(validation_frame)

        # Dialog buttons
        button_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        button_layout.addStretch()

        self.export_btn = QPushButton("Start Export")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.export_btn.clicked.connect(self._start_export)
        self.export_btn.setEnabled(self.export_summary.get('validation_ready', True))
        button_layout.addWidget(self.export_btn)

        layout.addLayout(button_layout)

    def _create_preview_panel(self) -> QGroupBox:
        """Create structure preview panel"""
        group = QGroupBox("Export Structure Preview")
        layout = QVBoxLayout(group)

        # Tree widget showing folder structure
        self.preview_tree = QTreeWidget()
        self.preview_tree.setHeaderLabels(["Structure", "Pages", "Size"])

        # Populate tree
        self._populate_preview_tree()

        self.preview_tree.expandAll()
        layout.addWidget(self.preview_tree)

        return group

    def _create_settings_panel(self) -> QGroupBox:
        """Create export settings panel"""
        group = QGroupBox("Export Settings")
        layout = QVBoxLayout(group)

        # Output directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Output Directory:"))

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        dir_layout.addWidget(self.output_dir_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(self.browse_btn)

        layout.addLayout(dir_layout)

        # PDF Settings
        pdf_group = QGroupBox("PDF Settings")
        pdf_layout = QGridLayout(pdf_group)

        pdf_layout.addWidget(QLabel("Quality:"), 0, 0)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.setSuffix("%")
        pdf_layout.addWidget(self.quality_spin, 0, 1)

        pdf_layout.addWidget(QLabel("Compression:"), 1, 0)
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["None", "Low", "Medium", "High"])
        self.compression_combo.setCurrentText("Medium")
        pdf_layout.addWidget(self.compression_combo, 1, 1)

        layout.addWidget(pdf_group)

        # File Handling
        file_group = QGroupBox("File Handling")
        file_layout = QVBoxLayout(file_group)

        self.create_folders_check = QCheckBox("Create folder structure")
        self.create_folders_check.setChecked(True)
        file_layout.addWidget(self.create_folders_check)

        self.overwrite_check = QCheckBox("Overwrite existing files")
        self.overwrite_check.setChecked(False)
        file_layout.addWidget(self.overwrite_check)

        self.add_timestamp_check = QCheckBox("Add timestamp to filenames")
        self.add_timestamp_check.setChecked(False)
        file_layout.addWidget(self.add_timestamp_check)

        layout.addWidget(file_group)

        layout.addStretch()

        return group

    def _populate_preview_tree(self):
        """Populate the preview tree with export structure"""
        preview = self.export_summary['preview']

        # Group documents by folder
        folder_groups = {}
        for group in preview['document_groups']:
            folder_path = group['folder_path'] or "Root"
            if folder_path not in folder_groups:
                folder_groups[folder_path] = []
            folder_groups[folder_path].append(group)

        # Create tree items
        for folder_path, groups in folder_groups.items():
            folder_item = QTreeWidgetItem(self.preview_tree)
            folder_item.setText(0, f"📁 {folder_path}")
            folder_item.setText(1, f"{len(groups)} documents")

            total_folder_pages = sum(g['page_count'] for g in groups)
            folder_item.setText(2, f"{total_folder_pages} pages")

            # Add document items
            for group in groups:
                doc_item = QTreeWidgetItem(folder_item)
                doc_item.setText(0, f"📄 {group['filename']}")
                doc_item.setText(1, f"{group['page_count']} pages")

                # Estimate file size (500KB per page average)
                estimated_size_kb = group['page_count'] * 500
                if estimated_size_kb > 1024:
                    size_text = f"{estimated_size_kb / 1024:.1f} MB"
                else:
                    size_text = f"{estimated_size_kb} KB"
                doc_item.setText(2, size_text)

    def _browse_output_dir(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            self.output_dir_edit.text() or os.path.expanduser("~/Documents")
        )

        if directory:
            self.output_dir_edit.setText(directory)

    def _start_export(self):
        """Start the export process"""
        output_dir = self.output_dir_edit.text().strip()

        if not output_dir:
            QMessageBox.warning(self, "Export Error", "Please select an output directory.")
            return

        if not os.path.exists(output_dir):
            reply = QMessageBox.question(
                self,
                "Create Directory",
                f"Directory '{output_dir}' does not exist. Create it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        # Collect export settings
        export_settings = {
            'pdf_quality': self.quality_spin.value(),
            'compression': self.compression_combo.currentText(),
            'create_folders': self.create_folders_check.isChecked(),
            'overwrite_existing': self.overwrite_check.isChecked(),
            'add_timestamp': self.add_timestamp_check.isChecked()
        }

        self.export_confirmed.emit(output_dir, export_settings)
        self.accept()


class ExportProgressDialog(QDialog):
    """Dialog showing export progress"""

    export_cancelled = Signal()

    def __init__(self, total_documents: int, parent=None):
        super().__init__(parent)
        self.total_documents = total_documents
        self.exported_count = 0
        self.failed_count = 0
        self.export_cancelled_flag = False

        self.setWindowTitle("Exporting Documents")
        self.setModal(True)
        self.resize(500, 300)
        self._setup_ui()

    def _setup_ui(self):
        """Setup progress dialog UI"""
        layout = QVBoxLayout(self)

        # Progress information
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("Exporting documents..."), 0, 0, 1, 2)

        info_layout.addWidget(QLabel("Progress:"), 1, 0)
        self.progress_label = QLabel(f"0 of {self.total_documents}")
        info_layout.addWidget(self.progress_label, 1, 1)

        info_layout.addWidget(QLabel("Current:"), 2, 0)
        self.current_label = QLabel("Preparing...")
        info_layout.addWidget(self.current_label, 2, 1)

        layout.addLayout(info_layout)

        # Progress bar
        from PySide6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.total_documents)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status log
        status_group = QGroupBox("Export Status")
        status_layout = QVBoxLayout(status_group)

        self.status_log = QTextEdit()
        self.status_log.setMaximumHeight(150)
        self.status_log.setReadOnly(True)
        status_layout.addWidget(self.status_log)

        layout.addWidget(status_group)

        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel Export")
        self.cancel_btn.clicked.connect(self._cancel_export)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def update_progress(self, current: int, total: int, message: str):
        """Update export progress"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

        self.progress_label.setText(f"{current} of {total}")
        self.current_label.setText(message)

        # Add to status log
        self.status_log.append(f"[{current}/{total}] {message}")

        # Auto-scroll to bottom
        self.status_log.verticalScrollBar().setValue(
            self.status_log.verticalScrollBar().maximum()
        )

    def document_exported(self, document_name: str, output_path: str):
        """Handle successful document export"""
        self.exported_count += 1
        message = f"✅ Exported: {document_name}"
        self.status_log.append(message)
        self.status_log.verticalScrollBar().setValue(
            self.status_log.verticalScrollBar().maximum()
        )

    def export_error(self, document_name: str, error_message: str):
        """Handle export error"""
        self.failed_count += 1
        message = f"❌ Failed: {document_name} - {error_message}"
        self.status_log.append(message)
        self.status_log.verticalScrollBar().setValue(
            self.status_log.verticalScrollBar().maximum()
        )

    def export_completed(self, summary: Dict):
        """Handle export completion"""
        self.current_label.setText("Export completed!")

        success_rate = summary.get('success_rate', 0)
        total_msg = f"""
Export Summary:
• Successful: {summary['successful_exports']}
• Failed: {summary['failed_exports']}
• Success Rate: {success_rate:.1f}%
        """

        self.status_log.append("=" * 40)
        self.status_log.append(total_msg)

        # Change cancel button to close
        self.cancel_btn.setText("Close")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)

    def _cancel_export(self):
        """Cancel the export process"""
        if not self.export_cancelled_flag:
            reply = QMessageBox.question(
                self,
                "Cancel Export",
                "Are you sure you want to cancel the export?\n\nDocuments exported so far will be kept.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.export_cancelled_flag = True
                self.export_cancelled.emit()
                self.current_label.setText("Cancelling export...")
                self.cancel_btn.setEnabled(False)
        else:
            # Export already cancelled, just close
            self.reject()

    def closeEvent(self, event):
        """Handle dialog close"""
        if not self.export_cancelled_flag and self.exported_count < self.total_documents:
            reply = QMessageBox.question(
                self,
                "Cancel Export",
                "Export is still in progress. Cancel export and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.export_cancelled.emit()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

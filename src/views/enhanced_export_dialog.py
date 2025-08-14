from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
                               QLineEdit, QFileDialog, QCheckBox, QSpinBox, QComboBox,
                               QTextEdit, QTabWidget, QWidget, QGridLayout, QFrame,
                               QMessageBox, QSplitter, QScrollArea, QDoubleSpinBox,
                               QListWidget, QListWidgetItem, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from typing import Dict, List, Optional
import os


from src.controllers.export_controller import ExportFormat
from src.controllers.export_template_manager import ExportTemplateManager
from src.views.export_dialog import ExportTemplate, PDFEngine


class TemplateEditorDialog(QDialog):
    """Dialog for creating/editing export templates"""

    template_saved = Signal(object)  # ExportTemplate

    def __init__(self, template: Optional[ExportTemplate] = None, parent=None):
        super().__init__(parent)
        self.template = template
        self.is_editing = template is not None

        self.setWindowTitle("Edit Export Template" if self.is_editing else "Create Export Template")
        self.setModal(True)
        self.resize(600, 700)
        self._setup_ui()

        if template:
            self._load_template_data(template)

    def _setup_ui(self):
        """Setup template editor UI"""
        layout = QVBoxLayout(self)

        # Basic Information
        basic_group = QGroupBox("Template Information")
        basic_layout = QGridLayout(basic_group)

        basic_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter template name...")
        basic_layout.addWidget(self.name_edit, 0, 1)

        basic_layout.addWidget(QLabel("Description:"), 1, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Optional description...")
        basic_layout.addWidget(self.description_edit, 1, 1)

        layout.addWidget(basic_group)

        # Format Settings
        format_group = QGroupBox("Export Format")
        format_layout = QGridLayout(format_group)

        format_layout.addWidget(QLabel("Format:"), 0, 0)
        self.format_combo = QComboBox()
        for fmt in ExportFormat:
            self.format_combo.addItem(fmt.value.upper(), fmt)
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_combo, 0, 1)

        format_layout.addWidget(QLabel("Quality:"), 1, 0)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(85)
        self.quality_spin.setSuffix("%")
        format_layout.addWidget(self.quality_spin, 1, 1)

        format_layout.addWidget(QLabel("Compression:"), 2, 0)
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["none", "low", "medium", "high"])
        self.compression_combo.setCurrentText("medium")
        format_layout.addWidget(self.compression_combo, 2, 1)

        layout.addWidget(format_group)

        # PDF-specific settings
        self.pdf_group = QGroupBox("PDF Settings")
        pdf_layout = QGridLayout(self.pdf_group)

        pdf_layout.addWidget(QLabel("Engine:"), 0, 0)
        self.pdf_engine_combo = QComboBox()
        self.pdf_engine_combo.addItem("PIL (Fast)", PDFEngine.PIL)

        # Check if ReportLab is available
        try:
            import reportlab
            self.pdf_engine_combo.addItem("ReportLab (Advanced)", PDFEngine.REPORTLAB)
        except ImportError:
            pass

        pdf_layout.addWidget(self.pdf_engine_combo, 0, 1)

        pdf_layout.addWidget(QLabel("Page Size:"), 1, 0)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["auto", "letter", "a4"])
        pdf_layout.addWidget(self.page_size_combo, 1, 1)

        # Margins
        pdf_layout.addWidget(QLabel("Margins (inches):"), 2, 0)
        margins_layout = QHBoxLayout()

        self.margin_top = QDoubleSpinBox()
        self.margin_top.setRange(0, 5)
        self.margin_top.setValue(0.5)
        self.margin_top.setDecimals(2)
        self.margin_top.setSuffix(" top")
        margins_layout.addWidget(self.margin_top)

        self.margin_right = QDoubleSpinBox()
        self.margin_right.setRange(0, 5)
        self.margin_right.setValue(0.5)
        self.margin_right.setDecimals(2)
        self.margin_right.setSuffix(" right")
        margins_layout.addWidget(self.margin_right)

        self.margin_bottom = QDoubleSpinBox()
        self.margin_bottom.setRange(0, 5)
        self.margin_bottom.setValue(0.5)
        self.margin_bottom.setDecimals(2)
        self.margin_bottom.setSuffix(" bottom")
        margins_layout.addWidget(self.margin_bottom)

        self.margin_left = QDoubleSpinBox()
        self.margin_left.setRange(0, 5)
        self.margin_left.setValue(0.5)
        self.margin_left.setDecimals(2)
        self.margin_left.setSuffix(" left")
        margins_layout.addWidget(self.margin_left)

        pdf_layout.addLayout(margins_layout, 2, 1)

        self.fit_to_page_check = QCheckBox("Fit to page")
        self.fit_to_page_check.setChecked(True)
        pdf_layout.addWidget(self.fit_to_page_check, 3, 0, 1, 2)

        self.maintain_aspect_check = QCheckBox("Maintain aspect ratio")
        self.maintain_aspect_check.setChecked(True)
        pdf_layout.addWidget(self.maintain_aspect_check, 4, 0, 1, 2)

        layout.addWidget(self.pdf_group)

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

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Initialize format-specific visibility
        self._on_format_changed()

    def _on_format_changed(self):
        """Handle format selection change"""
        selected_format = self.format_combo.currentData()

        # Show/hide PDF-specific settings
        self.pdf_group.setVisible(selected_format == ExportFormat.PDF)

    def _load_template_data(self, template: ExportTemplate):
        """Load existing template data"""
        self.name_edit.setText(template.name)
        self.description_edit.setText(template.description)

        # Set format
        for i in range(self.format_combo.count()):
            if self.format_combo.itemData(i) == template.format:
                self.format_combo.setCurrentIndex(i)
                break

        self.quality_spin.setValue(template.quality)
        self.compression_combo.setCurrentText(template.compression)

        # PDF settings
        for i in range(self.pdf_engine_combo.count()):
            if self.pdf_engine_combo.itemData(i) == template.pdf_engine:
                self.pdf_engine_combo.setCurrentIndex(i)
                break

        self.page_size_combo.setCurrentText(template.page_size)

        # Margins
        self.margin_top.setValue(template.margins[0])
        self.margin_right.setValue(template.margins[1])
        self.margin_bottom.setValue(template.margins[2])
        self.margin_left.setValue(template.margins[3])

        self.fit_to_page_check.setChecked(template.fit_to_page)
        self.maintain_aspect_check.setChecked(template.maintain_aspect_ratio)

        # File handling
        self.create_folders_check.setChecked(template.create_folders)
        self.overwrite_check.setChecked(template.overwrite_existing)
        self.add_timestamp_check.setChecked(template.add_timestamp)

    def _validate_and_accept(self):
        """Validate template data and accept"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Template name is required.")
            return

        # Create template
        template = ExportTemplate(
            name=name,
            description=self.description_edit.toPlainText().strip(),
            format=self.format_combo.currentData(),
            pdf_engine=self.pdf_engine_combo.currentData() or PDFEngine.PIL,
            quality=self.quality_spin.value(),
            compression=self.compression_combo.currentText(),
            create_folders=self.create_folders_check.isChecked(),
            overwrite_existing=self.overwrite_check.isChecked(),
            add_timestamp=self.add_timestamp_check.isChecked(),
            page_size=self.page_size_combo.currentText(),
            margins=(
                self.margin_top.value(),
                self.margin_right.value(),
                self.margin_bottom.value(),
                self.margin_left.value()
            ),
            fit_to_page=self.fit_to_page_check.isChecked(),
            maintain_aspect_ratio=self.maintain_aspect_check.isChecked()
        )

        self.template_saved.emit(template)
        self.accept()


class EnhancedExportPreviewDialog(QDialog):
    """Enhanced export preview dialog with template support"""

    export_confirmed = Signal(str, object)  # output_dir, ExportTemplate

    def __init__(self, export_summary: Dict, parent=None):
        super().__init__(parent)
        self.export_summary = export_summary
        self.template_manager = ExportTemplateManager()
        self.current_template = None

        self.setWindowTitle("Export Documents")
        self.setModal(True)
        self.resize(1000, 700)
        self._setup_ui()

    def _setup_ui(self):
        """Setup enhanced export dialog UI"""
        layout = QVBoxLayout(self)

        # Create tab widget for different sections
        tab_widget = QTabWidget()

        # Template Selection Tab
        template_tab = self._create_template_tab()
        tab_widget.addTab(template_tab, "📋 Export Template")

        # Preview Tab
        preview_tab = self._create_preview_tab()
        tab_widget.addTab(preview_tab, "👁️ Structure Preview")

        # Settings Tab
        settings_tab = self._create_settings_tab()
        tab_widget.addTab(settings_tab, "⚙️ Advanced Settings")

        layout.addWidget(tab_widget)

        # Summary information
        summary_group = QGroupBox("Export Summary")
        summary_layout = QGridLayout(summary_group)

        preview = self.export_summary['preview']

        summary_layout.addWidget(QLabel("Documents:"), 0, 0)
        summary_layout.addWidget(QLabel(str(preview['total_documents'])), 0, 1)

        summary_layout.addWidget(QLabel("Pages:"), 0, 2)
        summary_layout.addWidget(QLabel(str(preview['total_pages'])), 0, 3)

        summary_layout.addWidget(QLabel("Folders:"), 1, 0)
        summary_layout.addWidget(QLabel(str(preview['folder_structure']['total_folders'])), 1, 1)

        summary_layout.addWidget(QLabel("Est. Size:"), 1, 2)
        size_mb = self.export_summary.get('estimated_file_size_mb', 0)
        summary_layout.addWidget(QLabel(f"{size_mb:.1f} MB"), 1, 3)

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
            for error in errors[:3]:  # Show first 3 errors
                error_label = QLabel(f"• {error}")
                error_label.setStyleSheet("color: #d32f2f; margin-left: 10px;")
                validation_layout.addWidget(error_label)

            if len(errors) > 3:
                more_label = QLabel(f"... and {len(errors) - 3} more issues")
                more_label.setStyleSheet("color: #d32f2f; margin-left: 10px; font-style: italic;")
                validation_layout.addWidget(more_label)

            layout.addWidget(validation_frame)

        # Dialog buttons
        button_layout = QHBoxLayout()

        # Resume button (if applicable)
        self.resume_btn = QPushButton("Resume Previous Export")
        self.resume_btn.setVisible(False)  # Will be shown if resume state found
        self.resume_btn.clicked.connect(self._resume_export)
        button_layout.addWidget(self.resume_btn)

        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

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

        # Load templates and set recommended one
        self._load_templates()

    def _create_template_tab(self) -> QWidget:
        """Create template selection tab"""
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # Template list
        list_group = QGroupBox("Available Templates")
        list_layout = QVBoxLayout(list_group)

        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        list_layout.addWidget(self.template_list)

        # Template management buttons
        template_btn_layout = QHBoxLayout()

        self.new_template_btn = QPushButton("New Template")
        self.new_template_btn.clicked.connect(self._create_new_template)
        template_btn_layout.addWidget(self.new_template_btn)

        self.edit_template_btn = QPushButton("Edit")
        self.edit_template_btn.clicked.connect(self._edit_current_template)
        self.edit_template_btn.setEnabled(False)
        template_btn_layout.addWidget(self.edit_template_btn)

        self.delete_template_btn = QPushButton("Delete")
        self.delete_template_btn.clicked.connect(self._delete_current_template)
        self.delete_template_btn.setEnabled(False)
        template_btn_layout.addWidget(self.delete_template_btn)

        list_layout.addLayout(template_btn_layout)
        layout.addWidget(list_group)

        # Template details
        details_group = QGroupBox("Template Details")
        details_layout = QVBoxLayout(details_group)

        self.template_details = QTextEdit()
        self.template_details.setReadOnly(True)
        details_layout.addWidget(self.template_details)

        layout.addWidget(details_group)

        return tab

    def _create_preview_tab(self) -> QWidget:
        """Create structure preview tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Output directory selection
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Output Directory:"))

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        dir_layout.addWidget(self.output_dir_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(self.browse_btn)

        layout.addLayout(dir_layout)

        # Tree widget showing folder structure
        self.preview_tree = QTreeWidget()
        self.preview_tree.setHeaderLabels(["Structure", "Pages", "Est. Size"])

        # Populate tree
        self._populate_preview_tree()

        self.preview_tree.expandAll()
        layout.addWidget(self.preview_tree)

        return tab

    def _create_settings_tab(self) -> QWidget:
        """Create advanced settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Memory management
        memory_group = QGroupBox("Memory Management")
        memory_layout = QGridLayout(memory_group)

        memory_layout.addWidget(QLabel("Max Memory Usage:"), 0, 0)
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(128, 2048)
        self.memory_limit_spin.setValue(512)
        self.memory_limit_spin.setSuffix(" MB")
        memory_layout.addWidget(self.memory_limit_spin, 0, 1)

        self.clear_cache_check = QCheckBox("Clear image cache between documents")
        self.clear_cache_check.setChecked(True)
        memory_layout.addWidget(self.clear_cache_check, 1, 0, 1, 2)

        layout.addWidget(memory_group)

        # Error handling
        error_group = QGroupBox("Error Handling")
        error_layout = QVBoxLayout(error_group)

        self.continue_on_error_check = QCheckBox("Continue export on individual document errors")
        self.continue_on_error_check.setChecked(True)
        error_layout.addWidget(self.continue_on_error_check)

        self.save_resume_state_check = QCheckBox("Save export state for resuming (recommended for large batches)")
        self.save_resume_state_check.setChecked(True)
        error_layout.addWidget(self.save_resume_state_check)

        layout.addWidget(error_group)

        layout.addStretch()

        return tab

    def _load_templates(self):
        """Load available templates into list"""
        templates = self.template_manager.get_available_templates()

        self.template_list.clear()

        for template in templates:
            item = QListWidgetItem(template.name)
            item.setData(Qt.ItemDataRole.UserRole, template)
            self.template_list.addItem(item)

        # Select recommended template
        if templates:
            preview = self.export_summary['preview']
            page_count = preview['total_pages']
            estimated_size = self.export_summary.get('estimated_file_size_mb', 0)

            recommended = self.template_manager.get_recommended_template(page_count, estimated_size)

            # Find and select recommended template
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                template = item.data(Qt.ItemDataRole.UserRole)
                if template.name == recommended.name:
                    self.template_list.setCurrentItem(item)
                    break

    def _on_template_selected(self, current_item, previous_item):
        """Handle template selection"""
        if current_item:
            template = current_item.data(Qt.ItemDataRole.UserRole)
            self.current_template = template
            self._update_template_details(template)
            self.edit_template_btn.setEnabled(True)
            self.delete_template_btn.setEnabled(True)
            self.export_btn.setEnabled(self.export_summary.get('validation_ready', True))
        else:
            self.current_template = None
            self.template_details.clear()
            self.edit_template_btn.setEnabled(False)
            self.delete_template_btn.setEnabled(False)
            self.export_btn.setEnabled(False)

    def _update_template_details(self, template: ExportTemplate):
        """Update template details display"""
        capabilities = self.template_manager.get_format_capabilities()
        format_info = capabilities.get(template.format.value.upper(), {})

        details = f"""
<h3>{template.name}</h3>
<p><b>Description:</b> {template.description or 'No description'}</p>

<h4>Format Settings</h4>
<p><b>Format:</b> {template.format.value.upper()}</p>
<p><b>Quality:</b> {template.quality}%</p>
<p><b>Compression:</b> {template.compression.title()}</p>

<h4>Format Capabilities</h4>
<p><b>Multi-page:</b> {'Yes' if format_info.get('multi_page') else 'No'}</p>
<p><b>Professional:</b> {'Yes' if format_info.get('professional') else 'No'}</p>
<p><b>Typical file size:</b> {format_info.get('file_size', 'Unknown')}</p>
"""

        if template.format == ExportFormat.PDF:
            details += f"""
<h4>PDF Settings</h4>
<p><b>Engine:</b> {template.pdf_engine.value.title()}</p>
<p><b>Page Size:</b> {template.page_size.title()}</p>
<p><b>Margins:</b> {template.margins[0]}" top, {template.margins[1]}" right, {template.margins[2]}" bottom, {template.margins[3]}" left</p>
<p><b>Fit to page:</b> {'Yes' if template.fit_to_page else 'No'}</p>
<p><b>Maintain aspect ratio:</b> {'Yes' if template.maintain_aspect_ratio else 'No'}</p>
"""

        details += f"""
<h4>File Handling</h4>
<p><b>Create folders:</b> {'Yes' if template.create_folders else 'No'}</p>
<p><b>Overwrite existing:</b> {'Yes' if template.overwrite_existing else 'No'}</p>
<p><b>Add timestamp:</b> {'Yes' if template.add_timestamp else 'No'}</p>

<h4>Estimated Results</h4>
<p><b>Total documents:</b> {self.export_summary['preview']['total_documents']}</p>
<p><b>Estimated export time:</b> {self._estimate_export_time(template)} minutes</p>
"""

        self.template_details.setHtml(details)

    def _estimate_export_time(self, template: ExportTemplate) -> int:
        """Estimate export time based on template and document count"""
        total_pages = self.export_summary['preview']['total_pages']

        # Base time per page (seconds)
        if template.format == ExportFormat.PDF:
            if template.pdf_engine == PDFEngine.REPORTLAB:
                base_time = 2  # ReportLab is slower but better quality
            else:
                base_time = 1  # PIL is faster
        elif template.format == ExportFormat.TIFF:
            base_time = 1.5
        else:
            base_time = 0.5  # PNG/JPEG are fastest

        # Adjust for quality settings
        if template.quality > 90:
            base_time *= 1.2
        elif template.quality < 70:
            base_time *= 0.8

        total_seconds = total_pages * base_time
        return max(1, int(total_seconds / 60))  # Convert to minutes, minimum 1

    def _create_new_template(self):
        """Create new export template"""
        dialog = TemplateEditorDialog(parent=self)
        dialog.template_saved.connect(self._on_template_saved)
        dialog.exec()

    def _edit_current_template(self):
        """Edit current template"""
        if not self.current_template:
            return

        dialog = TemplateEditorDialog(self.current_template, self)
        dialog.template_saved.connect(self._on_template_saved)
        dialog.exec()

    def _delete_current_template(self):
        """Delete current template"""
        if not self.current_template:
            return

        reply = QMessageBox.question(
            self,
            "Delete Template",
            f"Are you sure you want to delete template '{self.current_template.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.template_manager.delete_template(self.current_template.name)
            if success:
                self._load_templates()

    def _on_template_saved(self, template: ExportTemplate):
        """Handle template save"""
        success = self.template_manager.save_template(template)
        if success:
            self._load_templates()
            # Select the saved template
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole).name == template.name:
                    self.template_list.setCurrentItem(item)
                    break

    def _populate_preview_tree(self):
        """Populate the preview tree with export structure"""
        preview = self.export_summary['preview']

        self.preview_tree.clear()

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

                # Update filename based on current template
                filename = group['filename']
                if self.current_template:
                    if self.current_template.add_timestamp:
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                        filename = f"{base_name}_{timestamp}.{self.current_template.format.value}"
                    elif not filename.endswith(f".{self.current_template.format.value}"):
                        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                        filename = f"{base_name}.{self.current_template.format.value}"

                doc_item.setText(0, f"📄 {filename}")
                doc_item.setText(1, f"{group['page_count']} pages")

                # Estimate file size based on format
                if self.current_template:
                    if self.current_template.format == ExportFormat.PDF:
                        estimated_kb = group['page_count'] * 400  # ~400KB per page for PDF
                    elif self.current_template.format == ExportFormat.TIFF:
                        estimated_kb = group['page_count'] * 800  # ~800KB per page for TIFF
                    else:
                        estimated_kb = group['page_count'] * 300  # ~300KB per page for PNG/JPEG
                else:
                    estimated_kb = group['page_count'] * 500  # Default estimate

                if estimated_kb > 1024:
                    size_text = f"{estimated_kb / 1024:.1f} MB"
                else:
                    size_text = f"{estimated_kb} KB"
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

    def _resume_export(self):
        """Resume a previous export"""
        # This would be implemented to resume from saved state
        QMessageBox.information(
            self,
            "Resume Export",
            "Resume functionality will be implemented to continue interrupted exports."
        )

    def _start_export(self):
        """Start the export process"""
        output_dir = self.output_dir_edit.text().strip()

        if not output_dir:
            QMessageBox.warning(self, "Export Error", "Please select an output directory.")
            return

        if not self.current_template:
            QMessageBox.warning(self, "Export Error", "Please select an export template.")
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

        # Validate template
        errors = self.template_manager.validate_template(self.current_template)
        if errors:
            error_text = "Template validation failed:\n\n" + "\n".join(f"• {error}" for error in errors)
            QMessageBox.warning(self, "Template Error", error_text)
            return

        self.export_confirmed.emit(output_dir, self.current_template)
        self.accept()
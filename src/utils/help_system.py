from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QTreeWidget, QTreeWidgetItem, QSplitter, QPushButton,
                               QLineEdit, QLabel, QDialogButtonBox, QTreeWidgetItemIterator)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class HelpCategory(Enum):
    GETTING_STARTED = "getting_started"
    PROFILES = "profiles"
    SCANNING = "scanning"
    PAGE_ASSIGNMENT = "page_assignment"
    EXPORT = "export"
    TROUBLESHOOTING = "troubleshooting"


@dataclass
class HelpTopic:
    id: str
    title: str
    category: HelpCategory
    content: str
    keywords: List[str]
    related_topics: List[str] = None

    def __post_init__(self):
        if self.related_topics is None:
            self.related_topics = []


class HelpManager:
    def __init__(self):
        self.topics = {}
        self.tooltips = {}
        self._initialize_help_content()
        self._initialize_tooltips()

    def _initialize_help_content(self):
        """Initialize help topics"""
        # Getting Started topics
        self.add_topic(HelpTopic(
            "quick_start",
            "Quick Start Guide",
            HelpCategory.GETTING_STARTED,
            """
            <h2>Quick Start Guide</h2>
            <p>Welcome to Dynamic Scanner! Follow these steps to get started:</p>

            <h3>1. Create a Profile</h3>
            <p>Click <b>File → New Profile</b> or use the workflow panel to create your first scanning profile.</p>
            <ul>
                <li>Choose a template (Legal, Medical, Invoice, etc.) or create custom fields</li>
                <li>Define folder structure and filename components</li>
                <li>Save your profile for reuse</li>
            </ul>

            <h3>2. Scan Documents</h3>
            <p>Once your profile is loaded:</p>
            <ul>
                <li>Connect your scanner device</li>
                <li>Configure scan settings (resolution, color mode)</li>
                <li>Start scanning your document pages</li>
            </ul>

            <h3>3. Assign Pages</h3>
            <p>Organize your scanned pages:</p>
            <ul>
                <li>Select pages in the document grid</li>
                <li>Fill in index values (client, date, document type, etc.)</li>
                <li>Assign pages to create organized documents</li>
            </ul>

            <h3>4. Export Documents</h3>
            <p>Generate your organized documents:</p>
            <ul>
                <li>Validate assignments</li>
                <li>Preview the folder structure</li>
                <li>Export to PDF, TIFF, or other formats</li>
            </ul>
            """,
            ["quick", "start", "getting started", "tutorial", "first time"]
        ))

        self.add_topic(HelpTopic(
            "profiles_overview",
            "Understanding Profiles",
            HelpCategory.PROFILES,
            """
            <h2>Understanding Profiles</h2>
            <p>Profiles define how your documents will be organized and named.</p>

            <h3>What is a Profile?</h3>
            <p>A profile contains:</p>
            <ul>
                <li><b>Index Fields</b> - The information you want to track (Client, Date, Document Type, etc.)</li>
                <li><b>Field Types</b> - How each field is used (Folder, Filename, or Metadata)</li>
                <li><b>Default Values</b> - Pre-filled values to save time</li>
                <li><b>Scanner Settings</b> - Default resolution, color mode, etc.</li>
            </ul>

            <h3>Field Types Explained</h3>
            <ul>
                <li><b>📁 Folder Fields</b> - Create directory structure (e.g., Client → Case Type)</li>
                <li><b>📄 Filename Fields</b> - Become part of document names (e.g., Document_Type_Date.pdf)</li>
                <li><b>🏷️ Metadata Fields</b> - Store additional information without affecting file structure</li>
            </ul>

            <h3>Example Structure</h3>
            <p>With fields: Client (Folder), Case Type (Folder), Document (Filename), Date (Filename)</p>
            <p>Result: <code>/Smith/Divorce/Petition_2024-08-11.pdf</code></p>
            """,
            ["profile", "fields", "folder", "filename", "metadata", "structure"]
        ))

        self.add_topic(HelpTopic(
            "scanning_tips",
            "Scanning Best Practices",
            HelpCategory.SCANNING,
            """
            <h2>Scanning Best Practices</h2>

            <h3>Scanner Settings</h3>
            <ul>
                <li><b>Resolution:</b> 300 DPI for most documents, 600 DPI for small text</li>
                <li><b>Color Mode:</b> Color for forms/charts, Grayscale for text, Black&White for simple documents</li>
                <li><b>Format:</b> TIFF for archival quality, PNG for web use, JPEG for smaller files</li>
            </ul>

            <h3>Batch Scanning Tips</h3>
            <ul>
                <li>Scan all pages for a batch before starting assignments</li>
                <li>Use consistent orientation - rotate pages after scanning if needed</li>
                <li>Preview each page to ensure quality before proceeding</li>
                <li>Group similar document types together when possible</li>
            </ul>

            <h3>Quality Control</h3>
            <ul>
                <li>Check for skewed pages and rescan if necessary</li>
                <li>Ensure text is readable at 100% zoom</li>
                <li>Delete and rescan any blurry or incomplete pages</li>
            </ul>
            """,
            ["scanning", "resolution", "quality", "batch", "tips", "best practices"]
        ))

        self.add_topic(HelpTopic(
            "page_assignment_guide",
            "Page Assignment Guide",
            HelpCategory.PAGE_ASSIGNMENT,
            """
            <h2>Page Assignment Guide</h2>

            <h3>Basic Assignment</h3>
            <ol>
                <li>Select pages in the document grid (Ctrl+Click for multiple pages)</li>
                <li>Fill in the index values in the assignment panel</li>
                <li>Click "Assign Pages" to create the assignment</li>
            </ol>

            <h3>Advanced Techniques</h3>
            <ul>
                <li><b>Auto Assignment:</b> Use "Auto Assign All" to quickly assign pages with incremental numbering</li>
                <li><b>Editing Assignments:</b> Click "Edit" on any assignment to modify its values</li>
                <li><b>Moving Pages:</b> Delete from one assignment and create a new one with different values</li>
            </ul>

            <h3>Validation</h3>
            <p>The system will validate your assignments:</p>
            <ul>
                <li>Required fields must be filled</li>
                <li>Field validation rules (if any) must be met</li>
                <li>All pages must be assigned to exactly one document</li>
            </ul>

            <h3>Preview Structure</h3>
            <p>Use the preview panel to see how your folder structure will look before exporting.</p>
            """,
            ["assignment", "pages", "index", "values", "validation", "preview"]
        ))

        self.add_topic(HelpTopic(
            "troubleshooting_common",
            "Common Issues & Solutions",
            HelpCategory.TROUBLESHOOTING,
            """
            <h2>Common Issues & Solutions</h2>

            <h3>Scanner Not Detected</h3>
            <ul>
                <li>Check USB/network connections</li>
                <li>Restart the scanner and click "Refresh Devices"</li>
                <li>Install latest scanner drivers</li>
                <li>Try the mock scanner for testing</li>
            </ul>

            <h3>Export Fails</h3>
            <ul>
                <li><b>Permission Denied:</b> Check write permissions for output folder</li>
                <li><b>Out of Space:</b> Free up disk space or choose different location</li>
                <li><b>Files Already Exist:</b> Enable overwrite or choose different names</li>
            </ul>

            <h3>Poor Image Quality</h3>
            <ul>
                <li>Increase resolution (try 400-600 DPI)</li>
                <li>Clean scanner glass</li>
                <li>Ensure documents are flat against glass</li>
                <li>Use Color mode instead of Black&White for complex documents</li>
            </ul>

            <h3>Application Crashes</h3>
            <ul>
                <li>Check log files for error details</li>
                <li>Reduce memory usage in Advanced settings</li>
                <li>Process smaller batches</li>
                <li>Update graphics drivers</li>
            </ul>
            """,
            ["troubleshooting", "scanner", "export", "crash", "error", "quality"]
        ))

    def _initialize_tooltips(self):
        """Initialize tooltips for UI elements"""
        self.tooltips = {
            # Profile Editor tooltips
            "field_name": "Enter a descriptive name for this index field (e.g., 'Client Name', 'Document Date')",
            "field_type": "Choose how this field is used:\n• Folder: Creates directory structure\n• Filename: Part of document name\n• Metadata: Additional information only",
            "field_required": "Check if this field must be filled for every document",
            "field_default": "Optional default value to pre-fill this field",
            "field_validation": "Set rules for valid values (patterns, allowed values, length limits)",

            # Scanner Control tooltips
            "scan_resolution": "Higher resolution = better quality but larger files\n• 300 DPI: Standard documents\n• 600 DPI: Small text or detailed images",
            "scan_color_mode": "Color Mode:\n• Color: Full color documents\n• Grayscale: Black/white with shades\n• Black&White: Pure black and white only",
            "scan_format": "Output format:\n• TIFF: Best quality (large files)\n• PNG: Good quality, compressed\n• JPEG: Smaller files, some quality loss",
            "page_count": "Number of pages to scan in this batch",

            # Page Assignment tooltips
            "assign_pages": "Select pages in the grid, fill index values, then click to create organized document",
            "auto_assign": "Automatically assign all pages with incremental document numbers",
            "pages_per_doc": "How many scanned pages should be combined into each document",

            # Export tooltips
            "export_template": "Choose export format and quality settings",
            "output_directory": "Where to save the organized documents and folders",
            "create_folders": "Create folder structure based on folder fields in your profile"
        }

    def add_topic(self, topic: HelpTopic):
        """Add a help topic"""
        self.topics[topic.id] = topic

    def get_topic(self, topic_id: str) -> Optional[HelpTopic]:
        """Get a specific help topic"""
        return self.topics.get(topic_id)

    def search_topics(self, query: str) -> List[HelpTopic]:
        """Search help topics by keywords"""
        query = query.lower()
        results = []

        for topic in self.topics.values():
            # Search in title, content, and keywords
            if (query in topic.title.lower() or
                    query in topic.content.lower() or
                    any(query in keyword.lower() for keyword in topic.keywords)):
                results.append(topic)

        return results

    def get_topics_by_category(self, category: HelpCategory) -> List[HelpTopic]:
        """Get all topics in a category"""
        return [topic for topic in self.topics.values() if topic.category == category]

    def get_tooltip(self, element_id: str) -> str:
        """Get tooltip text for UI element"""
        return self.tooltips.get(element_id, "")


class HelpDialog(QDialog):
    def __init__(self, help_manager: HelpManager, initial_topic: str = None, parent=None):
        super().__init__(parent)
        self.help_manager = help_manager
        self.setWindowTitle("Dynamic Scanner Help")
        self.setModal(False)  # Allow interaction with main window
        self.resize(800, 600)
        self._setup_ui()

        if initial_topic:
            self._show_topic(initial_topic)
        else:
            self._show_topic("quick_start")

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter keywords to search help topics...")
        self.search_edit.textChanged.connect(self._search_help)
        search_layout.addWidget(self.search_edit)

        layout.addLayout(search_layout)

        # Main content area
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Topics tree
        self.topics_tree = QTreeWidget()
        self.topics_tree.setHeaderLabel("Help Topics")
        self.topics_tree.setFixedWidth(250)
        self.topics_tree.itemClicked.connect(self._on_topic_selected)
        self._populate_topics_tree()
        splitter.addWidget(self.topics_tree)

        # Content area
        self.content_area = QTextEdit()
        self.content_area.setReadOnly(True)
        splitter.addWidget(self.content_area)

        layout.addWidget(splitter)

        # Buttons
        button_layout = QHBoxLayout()

        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setEnabled(False)
        button_layout.addWidget(self.back_btn)

        self.home_btn = QPushButton("🏠 Home")
        self.home_btn.clicked.connect(lambda: self._show_topic("quick_start"))
        button_layout.addWidget(self.home_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # History for back button
        self.history = []

    def _populate_topics_tree(self):
        """Populate the topics tree"""
        categories = {
            HelpCategory.GETTING_STARTED: "Getting Started",
            HelpCategory.PROFILES: "Profiles & Fields",
            HelpCategory.SCANNING: "Scanning Documents",
            HelpCategory.PAGE_ASSIGNMENT: "Page Assignment",
            HelpCategory.EXPORT: "Export & Output",
            HelpCategory.TROUBLESHOOTING: "Troubleshooting"
        }

        for category, display_name in categories.items():
            category_item = QTreeWidgetItem(self.topics_tree)
            category_item.setText(0, display_name)
            category_item.setData(0, Qt.ItemDataRole.UserRole, f"category_{category.value}")

            # Add topics in this category
            topics = self.help_manager.get_topics_by_category(category)
            for topic in topics:
                topic_item = QTreeWidgetItem(category_item)
                topic_item.setText(0, topic.title)
                topic_item.setData(0, Qt.ItemDataRole.UserRole, topic.id)

        self.topics_tree.expandAll()

    def _on_topic_selected(self, item, column):
        """Handle topic selection"""
        topic_id = item.data(0, Qt.ItemDataRole.UserRole)
        if topic_id and not topic_id.startswith("category_"):
            self._show_topic(topic_id)

    def _show_topic(self, topic_id: str):
        """Show a specific help topic"""
        topic = self.help_manager.get_topic(topic_id)
        if topic:
            # Add to history
            if self.history and self.history[-1] != topic_id:
                self.history.append(topic_id)
            elif not self.history:
                self.history.append(topic_id)

            self.back_btn.setEnabled(len(self.history) > 1)

            # Show content
            self.content_area.setHtml(topic.content)

    def _go_back(self):
        """Go back to previous topic"""
        if len(self.history) > 1:
            self.history.pop()  # Remove current
            previous_topic = self.history[-1]
            self._show_topic(previous_topic)

    def _search_help(self, query: str):
        """Search help topics"""
        if len(query) < 2:
            return

        results = self.help_manager.search_topics(query)
        if results:
            # Show first result
            self._show_topic(results[0].id)

            # Update tree selection
            self._highlight_search_results(results)

    def _highlight_search_results(self, results: List[HelpTopic]):
        """Highlight search results in tree"""
        # Reset all items
        iterator = QTreeWidgetItemIterator(self.topics_tree)
        while iterator.value():
            item = iterator.value()
            item.setSelected(False)
            iterator += 1

        # Highlight results
        for result in results:
            iterator = QTreeWidgetItemIterator(self.topics_tree)
            while iterator.value():
                item = iterator.value()
                if item.data(0, Qt.ItemDataRole.UserRole) == result.id:
                    item.setSelected(True)
                    break
                iterator += 1
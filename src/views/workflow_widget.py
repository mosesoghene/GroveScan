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
        self.setFixedHeight(60)  # Make more compact
        self.setFixedWidth(100)  # Set consistent width
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)  # Reduce margins
        layout.setSpacing(2)  # Reduce spacing

        # Header with status indicator
        header_layout = QHBoxLayout()

        self.status_label = QLabel("○")
        self.status_label.setFixedSize(16, 16)  # Smaller icon
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        header_layout.addWidget(self.status_label)

        self.title_label = QLabel(self.display_name)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 9pt;")  # Smaller font
        self.title_label.setWordWrap(True)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description - make shorter
        short_desc = self.description[:30] + "..." if len(self.description) > 30 else self.description
        self.desc_label = QLabel(short_desc)
        self.desc_label.setStyleSheet("color: #666; font-size: 8pt;")  # Smaller font
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
        self.step_widgets = {}
        self.workflow_steps = self._define_workflow_steps()
        self._setup_ui()

    def _define_workflow_steps(self) -> Dict:
        """Define the workflow steps"""
        return {
            "initial": {
                "display_name": "Start",
                "description": "Create or load a scanning profile",
                "next_steps": ["profile_ready"],
                "actions": ["create_profile", "load_profile"]
            },
            "profile_ready": {
                "display_name": "Profile Ready",
                "description": "Profile loaded, ready to scan documents",
                "next_steps": ["scanned"],
                "actions": ["start_scan", "edit_profile"]
            },
            "scanned": {
                "display_name": "Documents Scanned",
                "description": "Pages scanned, ready for assignment",
                "next_steps": ["assigned"],
                "actions": ["assign_pages", "scan_more", "edit_pages"]
            },
            "assigned": {
                "display_name": "Pages Assigned",
                "description": "Index values assigned to pages",
                "next_steps": ["ready_to_export"],
                "actions": ["validate_assignments", "edit_assignments", "assign_more"]
            },
            "ready_to_export": {
                "display_name": "Ready to Export",
                "description": "All assignments valid, ready to export",
                "next_steps": [],
                "actions": ["export_documents", "preview_structure"]
            }
        }

    def _setup_ui(self):
        """Setup the workflow UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)  # Reduce spacing
        layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Workflow Progress")
        title.setStyleSheet("font-size: 13pt; font-weight: bold; margin-bottom: 5px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.workflow_steps) - 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximumHeight(20)  # Make it more compact
        layout.addWidget(self.progress_bar)

        # Step widgets container - make it more compact
        steps_frame = QFrame()
        steps_frame.setFrameStyle(QFrame.Shape.Box)
        steps_frame.setLineWidth(1)
        steps_frame.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 4px; }")

        steps_layout = QHBoxLayout(steps_frame)
        steps_layout.setSpacing(3)  # Reduce spacing between steps
        steps_layout.setContentsMargins(5, 5, 5, 5)

        # Create step widgets
        for i, (step_key, step_info) in enumerate(self.workflow_steps.items()):
            step_widget = WorkflowStepWidget(
                step_key,
                step_info["display_name"],
                step_info["description"]
            )
            step_widget.step_clicked.connect(self.step_selected.emit)

            self.step_widgets[step_key] = step_widget
            steps_layout.addWidget(step_widget)

        layout.addWidget(steps_frame)

        # Current step info and actions - make more compact
        current_info_group = QGroupBox("Next Steps")
        current_info_group.setMaximumHeight(150)  # Limit height
        current_info_layout = QVBoxLayout(current_info_group)
        current_info_layout.setSpacing(5)  # Reduce spacing

        self.current_step_label = QLabel("Getting started...")
        self.current_step_label.setStyleSheet("font-weight: bold; font-size: 10pt; margin-bottom: 3px;")
        current_info_layout.addWidget(self.current_step_label)

        self.guidance_label = QLabel("Create or load a profile to begin scanning.")
        self.guidance_label.setStyleSheet("color: #666; font-size: 9pt; margin-bottom: 5px;")
        self.guidance_label.setWordWrap(True)
        current_info_layout.addWidget(self.guidance_label)

        # Action buttons
        self.action_buttons_layout = QHBoxLayout()
        self.action_buttons_layout.setSpacing(5)  # Reduce button spacing
        current_info_layout.addLayout(self.action_buttons_layout)

        layout.addWidget(current_info_group)

        # Initialize display
        self._update_display()

    def update_workflow_state(self, state_info: Dict):
        """Update workflow based on application state"""
        # Determine current step based on state
        if not state_info.get('has_profile', False):
            self.current_step = "initial"
        elif not state_info.get('has_batch', False):
            self.current_step = "profile_ready"
        elif not state_info.get('has_assignments', False):
            self.current_step = "scanned"
        elif not state_info.get('ready_to_export', False):
            self.current_step = "assigned"
        else:
            self.current_step = "ready_to_export"

        self._update_display()

    def _update_display(self):
        """Update the workflow display"""
        # Update progress bar
        step_index = list(self.workflow_steps.keys()).index(self.current_step)
        self.progress_bar.setValue(step_index)
        self.progress_bar.setFormat(
            f"Step {step_index + 1} of {len(self.workflow_steps)}: {self.workflow_steps[self.current_step]['display_name']}")

        # Update step widgets status
        for i, (step_key, step_widget) in enumerate(self.step_widgets.items()):
            current_index = list(self.workflow_steps.keys()).index(self.current_step)

            is_completed = i < current_index
            is_active = i == current_index
            is_available = i <= current_index + 1  # Current step and next step are available

            step_widget.set_status(is_active, is_completed, is_available)

        # Update current step info
        current_step_info = self.workflow_steps[self.current_step]
        self.current_step_label.setText(f"Current: {current_step_info['display_name']}")
        self.guidance_label.setText(current_step_info['description'])

        # Update action buttons
        self._update_action_buttons()

    def _update_action_buttons(self):
        """Update action buttons for current step"""
        # Clear existing buttons
        for i in reversed(range(self.action_buttons_layout.count())):
            child = self.action_buttons_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Add buttons for current step actions
        current_step_info = self.workflow_steps[self.current_step]
        actions = current_step_info.get('actions', [])

        action_labels = {
            'create_profile': 'Create Profile',
            'load_profile': 'Load Profile',
            'start_scan': 'Start Scanning',
            'edit_profile': 'Edit Profile',
            'assign_pages': 'Assign Pages',
            'scan_more': 'Scan More',
            'edit_pages': 'Edit Pages',
            'validate_assignments': 'Validate',
            'edit_assignments': 'Edit Assignments',
            'assign_more': 'Assign More',
            'export_documents': 'Export Documents',
            'preview_structure': 'Preview Structure'
        }

        for action in actions:
            btn = QPushButton(action_labels.get(action, action.replace('_', ' ').title()))
            btn.clicked.connect(lambda checked, a=action: self.action_requested.emit(a))

            # Style primary action differently
            if action in ['create_profile', 'start_scan', 'assign_pages', 'export_documents']:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0078d4;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #106ebe;
                    }
                """)

            self.action_buttons_layout.addWidget(btn)

        self.action_buttons_layout.addStretch()

    def get_current_step(self) -> str:
        """Get current workflow step"""
        return self.current_step

    def can_proceed_to_step(self, step_name: str) -> bool:
        """Check if we can proceed to a specific step"""
        current_index = list(self.workflow_steps.keys()).index(self.current_step)
        target_index = list(self.workflow_steps.keys()).index(step_name)
        return target_index <= current_index + 1

    def get_workflow_summary(self) -> Dict:
        """Get summary of workflow state"""
        current_index = list(self.workflow_steps.keys()).index(self.current_step)
        total_steps = len(self.workflow_steps)

        return {
            'current_step': self.current_step,
            'current_step_name': self.workflow_steps[self.current_step]['display_name'],
            'progress_percentage': (current_index / (total_steps - 1)) * 100,
            'completed_steps': current_index,
            'total_steps': total_steps,
            'next_actions': self.workflow_steps[self.current_step].get('actions', [])
        }

    def set_step_enabled(self, step_name: str, enabled: bool):
        """Enable or disable a specific step"""
        if step_name in self.step_widgets:
            widget = self.step_widgets[step_name]
            widget.is_available = enabled
            widget._update_appearance()

    def highlight_step(self, step_name: str, highlight: bool = True):
        """Highlight a specific step temporarily"""
        if step_name in self.step_widgets:
            widget = self.step_widgets[step_name]
            if highlight:
                widget.setStyleSheet(widget.styleSheet() + """
                    WorkflowStepWidget {
                        animation: pulse 1s infinite;
                        box-shadow: 0 0 10px #2196f3;
                    }
                """)
            else:
                widget._update_appearance()  # Reset to normal appearance
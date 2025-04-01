#!/usr/bin/env python3
"""
Cursor Prompt Preview Tab

This module provides a PyQt5 UI tab for previewing prompt templates and queued tasks,
allowing users to see how tasks will be executed and modify them before execution.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QSplitter, QTextEdit,
    QHeaderView, QTabWidget, QComboBox, QFileDialog, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QGroupBox, QFormLayout
)
from PyQt5.QtGui import QIcon, QFont, QColor, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtCore import Qt, pyqtSignal, QSize

# Add parent directory to path to allow importing from modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

logger = logging.getLogger(__name__)

class PromptSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for prompt templates and variables."""
    
    def __init__(self, document):
        """
        Initialize the highlighter.
        
        Args:
            document: Document to highlight
        """
        super().__init__(document)
        
        # Create formatting for different elements
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor("#0077cc"))  # Blue for variables
        self.variable_format.setFontWeight(QFont.Bold)
        
        self.directive_format = QTextCharFormat()
        self.directive_format.setForeground(QColor("#cc7000"))  # Orange for directives
        self.directive_format.setFontWeight(QFont.Bold)
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#008800"))  # Green for comments
        self.comment_format.setFontItalic(True)
    
    def highlightBlock(self, text):
        """
        Highlight a block of text.
        
        Args:
            text: Text to highlight
        """
        # Highlight variables like {{variable}}
        index = text.find("{{")
        while index >= 0:
            end_index = text.find("}}", index)
            if end_index >= 0:
                length = end_index - index + 2
                self.setFormat(index, length, self.variable_format)
                index = text.find("{{", end_index)
            else:
                break
        
        # Highlight directives like [[directive]]
        index = text.find("[[")
        while index >= 0:
            end_index = text.find("]]", index)
            if end_index >= 0:
                length = end_index - index + 2
                self.setFormat(index, length, self.directive_format)
                index = text.find("[[", end_index)
            else:
                break
        
        # Highlight comments like <!-- comment -->
        index = text.find("<!--")
        while index >= 0:
            end_index = text.find("-->", index)
            if end_index >= 0:
                length = end_index - index + 3
                self.setFormat(index, length, self.comment_format)
                index = text.find("<!--", end_index)
            else:
                break


class CursorPromptPreviewTab(QWidget):
    """Tab for previewing and modifying prompt templates and queued tasks."""
    
    execute_task_signal = pyqtSignal(str)  # Signal emitted when a task is to be executed
    
    def __init__(self, parent=None, orchestrator_bridge=None, template_dir="templates"):
        """
        Initialize the CursorPromptPreviewTab.
        
        Args:
            parent: Parent widget
            orchestrator_bridge: Optional orchestrator bridge for task execution
            template_dir: Directory containing prompt templates
        """
        super().__init__(parent)
        self.orchestrator_bridge = orchestrator_bridge
        self.template_dir = template_dir
        self.templates = {}
        self.queued_tasks = []
        self.setup_ui()
        self.load_templates()
        self.load_queued_tasks()
    
    def setup_ui(self):
        """Set up the tab UI."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create header
        header_layout = QHBoxLayout()
        
        header_label = QLabel("Cursor Prompt Preview")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        header_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(header_layout)
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Templates and tasks
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        
        # Tabs for templates and queued tasks
        self.left_tabs = QTabWidget()
        
        # Templates tab
        self.templates_widget = QWidget()
        templates_layout = QVBoxLayout(self.templates_widget)
        
        # Template tree widget
        self.template_tree = QTreeWidget()
        self.template_tree.setHeaderLabels(["Templates"])
        self.template_tree.itemClicked.connect(self.on_template_selected)
        templates_layout.addWidget(self.template_tree)
        
        # Template controls
        template_controls = QHBoxLayout()
        
        self.reload_templates_button = QPushButton("Reload Templates")
        self.reload_templates_button.clicked.connect(self.load_templates)
        template_controls.addWidget(self.reload_templates_button)
        
        template_controls.addStretch()
        
        templates_layout.addLayout(template_controls)
        
        self.left_tabs.addTab(self.templates_widget, "Templates")
        
        # Queued tasks tab
        self.tasks_widget = QWidget()
        tasks_layout = QVBoxLayout(self.tasks_widget)
        
        # Tasks table
        self.tasks_table = QTableWidget(0, 4)  # ID, Template, Status, Created
        self.tasks_table.setHorizontalHeaderLabels(["ID", "Template", "Status", "Created"])
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tasks_table.itemClicked.connect(self.on_task_selected)
        tasks_layout.addWidget(self.tasks_table)
        
        # Task controls
        task_controls = QHBoxLayout()
        
        self.reload_tasks_button = QPushButton("Reload Tasks")
        self.reload_tasks_button.clicked.connect(self.load_queued_tasks)
        task_controls.addWidget(self.reload_tasks_button)
        
        self.execute_task_button = QPushButton("Execute Selected")
        self.execute_task_button.clicked.connect(self.execute_selected_task)
        self.execute_task_button.setEnabled(False)
        task_controls.addWidget(self.execute_task_button)
        
        task_controls.addStretch()
        
        tasks_layout.addLayout(task_controls)
        
        self.left_tabs.addTab(self.tasks_widget, "Queued Tasks")
        
        left_layout.addWidget(self.left_tabs)
        
        # Right panel: Preview and editor
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        
        # Preview tabs
        self.preview_tabs = QTabWidget()
        
        # Source tab
        self.source_widget = QWidget()
        source_layout = QVBoxLayout(self.source_widget)
        
        self.source_editor = QTextEdit()
        self.source_editor.setReadOnly(True)
        self.source_highlighter = PromptSyntaxHighlighter(self.source_editor.document())
        source_layout.addWidget(self.source_editor)
        
        self.preview_tabs.addTab(self.source_widget, "Source")
        
        # Preview tab
        self.preview_widget = QWidget()
        preview_layout = QVBoxLayout(self.preview_widget)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        self.preview_tabs.addTab(self.preview_widget, "Preview")
        
        # Variables tab
        self.variables_widget = QWidget()
        variables_layout = QVBoxLayout(self.variables_widget)
        
        self.variables_form = QFormLayout()
        variables_layout.addLayout(self.variables_form)
        
        variables_layout.addStretch()
        
        self.preview_tabs.addTab(self.variables_widget, "Variables")
        
        right_layout.addWidget(self.preview_tabs)
        
        # Right panel controls
        right_controls = QHBoxLayout()
        
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_changes)
        self.save_button.setEnabled(False)
        right_controls.addWidget(self.save_button)
        
        self.render_button = QPushButton("Render Preview")
        self.render_button.clicked.connect(self.render_preview)
        self.render_button.setEnabled(False)
        right_controls.addWidget(self.render_button)
        
        right_controls.addStretch()
        
        right_layout.addLayout(right_controls)
        
        # Add panels to splitter
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([300, 700])  # Initial sizes
        
        main_layout.addWidget(self.main_splitter)
        
        # Status bar
        self.status_bar = QLabel("Ready")
        self.status_bar.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_bar)
    
    def load_templates(self):
        """Load templates from the template directory."""
        try:
            self.template_tree.clear()
            self.templates = {}
            
            template_path = Path(self.template_dir)
            if not template_path.exists():
                self.status_bar.setText(f"Template directory not found: {self.template_dir}")
                return
            
            # Add root category for all templates
            root_item = QTreeWidgetItem(self.template_tree, ["All Templates"])
            
            # Track categories
            categories = {}
            
            # Find all templates
            for file_path in template_path.glob("**/*.txt"):
                try:
                    # Get relative path for category structure
                    rel_path = file_path.relative_to(template_path)
                    category_path = rel_path.parent
                    
                    # Create category item if needed
                    if str(category_path) not in categories and str(category_path) != ".":
                        category_item = QTreeWidgetItem(root_item, [str(category_path)])
                        categories[str(category_path)] = category_item
                    
                    # Get template name and create item
                    template_name = file_path.stem
                    
                    # Determine parent item
                    if str(category_path) == ".":
                        parent_item = root_item
                    else:
                        parent_item = categories[str(category_path)]
                    
                    template_item = QTreeWidgetItem(parent_item, [template_name])
                    template_item.setData(0, Qt.UserRole, str(file_path))
                    
                    # Load template content
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    # Store template
                    self.templates[str(file_path)] = {
                        'name': template_name,
                        'path': str(file_path),
                        'content': content,
                        'variables': self._extract_variables(content)
                    }
                    
                except Exception as e:
                    logger.warning(f"Error loading template {file_path}: {e}")
            
            # Expand root item
            root_item.setExpanded(True)
            
            self.status_bar.setText(f"Loaded {len(self.templates)} templates")
            
        except Exception as e:
            self.status_bar.setText(f"Error loading templates: {e}")
            logger.error(f"Error loading templates: {e}")
    
    def load_queued_tasks(self):
        """Load queued tasks."""
        try:
            self.tasks_table.setRowCount(0)
            self.queued_tasks = []
            
            # If connected to orchestrator bridge, use it
            if self.orchestrator_bridge:
                task_data = self.orchestrator_bridge.refresh_tasks()
                self.queued_tasks = task_data.get("queued", [])
            else:
                # Fallback to loading from queued directory
                queued_dir = Path("queued")
                if not queued_dir.exists():
                    self.status_bar.setText("Queued directory not found")
                    return
                
                # Load all task files
                for file_path in queued_dir.glob("*.json"):
                    try:
                        with open(file_path, 'r') as f:
                            task = json.load(f)
                        self.queued_tasks.append(task)
                    except Exception as e:
                        logger.warning(f"Error loading task {file_path}: {e}")
            
            # Populate table
            self.tasks_table.setRowCount(len(self.queued_tasks))
            
            for i, task in enumerate(self.queued_tasks):
                # ID
                id_item = QTableWidgetItem(task.get("id", ""))
                self.tasks_table.setItem(i, 0, id_item)
                
                # Template
                template_item = QTableWidgetItem(task.get("template_name", ""))
                self.tasks_table.setItem(i, 1, template_item)
                
                # Status
                status_item = QTableWidgetItem(task.get("status", "queued"))
                self.tasks_table.setItem(i, 2, status_item)
                
                # Created
                created_item = QTableWidgetItem(task.get("created_at", ""))
                self.tasks_table.setItem(i, 3, created_item)
            
            self.status_bar.setText(f"Loaded {len(self.queued_tasks)} queued tasks")
            
        except Exception as e:
            self.status_bar.setText(f"Error loading queued tasks: {e}")
            logger.error(f"Error loading queued tasks: {e}")
    
    def on_template_selected(self, item, column):
        """
        Handle template selection.
        
        Args:
            item: Selected item
            column: Selected column
        """
        template_path = item.data(0, Qt.UserRole)
        if not template_path or template_path not in self.templates:
            return
        
        template = self.templates[template_path]
        
        # Show template in source editor
        self.source_editor.setText(template['content'])
        
        # Clear variables form
        self._clear_variables_form()
        
        # Add variables to form
        for var in template['variables']:
            self._add_variable_to_form(var, "")
        
        # Enable render button
        self.render_button.setEnabled(True)
        
        # Update status
        self.status_bar.setText(f"Template: {template['name']}")
    
    def on_task_selected(self, item):
        """
        Handle task selection.
        
        Args:
            item: Selected item
        """
        row = item.row()
        if row < 0 or row >= len(self.queued_tasks):
            return
        
        task = self.queued_tasks[row]
        
        # Find template
        template_name = task.get("template_name", "")
        template_path = None
        
        # Look for matching template
        for path, template in self.templates.items():
            if template['name'] == template_name:
                template_path = path
                break
        
        if template_path:
            # Show template in source editor
            self.source_editor.setText(self.templates[template_path]['content'])
            
            # Clear and populate variables form
            self._clear_variables_form()
            
            variables = task.get("variables", {})
            for var, value in variables.items():
                self._add_variable_to_form(var, value)
            
            # Render preview
            self._render_with_variables(
                self.templates[template_path]['content'], 
                variables
            )
        else:
            # Template not found, show task JSON
            self.source_editor.setText(json.dumps(task, indent=2))
            self._clear_variables_form()
            self.preview_text.setText("Template not found")
        
        # Enable execute button
        self.execute_task_button.setEnabled(True)
        
        # Update status
        self.status_bar.setText(f"Task: {task.get('id', '')}")
    
    def refresh_all(self):
        """Refresh templates and queued tasks."""
        self.load_templates()
        self.load_queued_tasks()
    
    def render_preview(self):
        """Render preview with current variables."""
        # Get current template content
        content = self.source_editor.toPlainText()
        
        # Collect variables from form
        variables = self._collect_variables_from_form()
        
        # Render with variables
        self._render_with_variables(content, variables)
    
    def save_changes(self):
        """Save changes to template or task."""
        # Not implemented yet
        self.status_bar.setText("Save functionality not implemented yet")
    
    def execute_selected_task(self):
        """Execute the selected task."""
        # Get selected task
        selected_items = self.tasks_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        if row < 0 or row >= len(self.queued_tasks):
            return
        
        task = self.queued_tasks[row]
        task_id = task.get("id", "")
        
        if not task_id:
            self.status_bar.setText("Cannot execute task: Invalid task ID")
            return
        
        # Emit signal for execution
        self.execute_task_signal.emit(task_id)
        
        # If we have orchestrator bridge, execute directly
        if self.orchestrator_bridge:
            success = self.orchestrator_bridge.execute_task(task_id)
            if success:
                self.status_bar.setText(f"Task {task_id} sent for execution")
            else:
                self.status_bar.setText(f"Failed to execute task {task_id}")
        else:
            self.status_bar.setText(f"Task {task_id} execution requested (no orchestrator bridge)")
    
    def _extract_variables(self, content: str) -> List[str]:
        """
        Extract variables from template content.
        
        Args:
            content: Template content
            
        Returns:
            List of variable names
        """
        variables = set()
        
        index = content.find("{{")
        while index >= 0:
            end_index = content.find("}}", index)
            if end_index >= 0:
                var_name = content[index+2:end_index].strip()
                if var_name:
                    variables.add(var_name)
                index = content.find("{{", end_index)
            else:
                break
        
        return sorted(list(variables))
    
    def _clear_variables_form(self):
        """Clear the variables form."""
        # Remove all widgets from form
        while self.variables_form.rowCount() > 0:
            self.variables_form.removeRow(0)
    
    def _add_variable_to_form(self, var_name: str, value: str):
        """
        Add a variable to the form.
        
        Args:
            var_name: Variable name
            value: Variable value
        """
        label = QLabel(var_name)
        editor = QTextEdit()
        editor.setPlainText(str(value))
        editor.setMaximumHeight(80)
        
        self.variables_form.addRow(label, editor)
    
    def _collect_variables_from_form(self) -> Dict[str, str]:
        """
        Collect variables from the form.
        
        Returns:
            Dictionary of variable names and values
        """
        variables = {}
        
        for i in range(self.variables_form.rowCount()):
            label_item = self.variables_form.itemAt(i, QFormLayout.LabelRole)
            field_item = self.variables_form.itemAt(i, QFormLayout.FieldRole)
            
            if label_item and field_item:
                var_name = label_item.widget().text()
                value = field_item.widget().toPlainText()
                variables[var_name] = value
        
        return variables
    
    def _render_with_variables(self, content: str, variables: Dict[str, str]):
        """
        Render template with variables.
        
        Args:
            content: Template content
            variables: Dictionary of variable names and values
        """
        rendered = content
        
        # Simple variable replacement
        for var_name, value in variables.items():
            rendered = rendered.replace(f"{{{{{var_name}}}}}", str(value))
        
        # Show in preview tab
        self.preview_text.setText(rendered)
        
        # Switch to preview tab
        self.preview_tabs.setCurrentIndex(1)


class CursorPromptPreviewTabFactory:
    """Factory for creating CursorPromptPreviewTab instances."""
    
    @staticmethod
    def create(orchestrator_bridge=None, template_dir="templates", parent=None) -> CursorPromptPreviewTab:
        """
        Create a CursorPromptPreviewTab instance.
        
        Args:
            orchestrator_bridge: Optional orchestrator bridge to connect to
            template_dir: Directory containing templates
            parent: Parent widget
            
        Returns:
            CursorPromptPreviewTab instance
        """
        tab = CursorPromptPreviewTab(
            parent=parent, 
            orchestrator_bridge=orchestrator_bridge,
            template_dir=template_dir
        )
        return tab


if __name__ == "__main__":
    # For testing as standalone
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = CursorPromptPreviewTabFactory.create()
    window.show()
    sys.exit(app.exec_()) 
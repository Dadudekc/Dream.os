import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer, QSize, QPoint
from PyQt5.QtGui import QDrag, QColor, QPalette, QIcon, QPixmap, QPainter, QBrush
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QTextEdit, QMessageBox, QMenu, QAction, QDialog, QComboBox,
    QSlider, QGroupBox, QLineEdit, QFileDialog, QCheckBox, QSpinBox
)

import logging
logger = logging.getLogger(__name__)

class PromptBlock(QFrame):
    """Draggable block representing a prompt component or action."""
    
    def __init__(self, block_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.block_data = block_data
        self.init_ui()
        
        # Setup for drag and drop
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        # Set fixed block height but expandable width
        self.setMinimumHeight(120)
        self.setMaximumHeight(150)
        self.setMinimumWidth(250)
        
        # Styling
        self.category_colors = {
            "analysis": "#4a6da7",  # Blue
            "generation": "#6ba26b", # Green
            "refactoring": "#a26b6b", # Red
            "testing": "#a29a6b",    # Yellow
            "other": "#8a6ba2"       # Purple
        }
        self.setup_styling()
    
    def init_ui(self):
        """Initialize the block UI components."""
        layout = QVBoxLayout(self)
        
        # Title with priority
        title_layout = QHBoxLayout()
        
        # Priority indicator (1-5 stars)
        priority = self.block_data.get("priority", 3)
        priority_label = QLabel("⭐" * priority)
        title_layout.addWidget(priority_label)
        
        # Block title
        title = self.block_data.get("title", "Unnamed Block")
        title_label = QLabel(f"<b>{title}</b>")
        title_layout.addWidget(title_label)
        
        # Category label
        category = self.block_data.get("category", "other")
        category_label = QLabel(f"[{category}]")
        category_label.setStyleSheet(f"color: {self.category_colors.get(category, '#8a6ba2')}")
        title_layout.addWidget(category_label)
        
        title_layout.addStretch()
        
        # Action buttons
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(24, 24)
        edit_btn.clicked.connect(self.edit_block)
        title_layout.addWidget(edit_btn)
        
        layout.addLayout(title_layout)
        
        # Content preview
        content = self.block_data.get("content", "")
        if len(content) > 150:
            content = content[:147] + "..."
            
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("color: #666; background-color: #f8f8f8; padding: 4px; border-radius: 2px;")
        layout.addWidget(content_label)
        
        # Metadata footer
        footer_layout = QHBoxLayout()
        
        # Block ID
        block_id = self.block_data.get("id", "")
        id_label = QLabel(f"ID: {block_id[:8]}..." if block_id else "New Block")
        id_label.setStyleSheet("color: #999; font-size: 9px;")
        footer_layout.addWidget(id_label)
        
        footer_layout.addStretch()
        
        # Dependencies indication
        dependencies = self.block_data.get("dependencies", [])
        if dependencies:
            dep_label = QLabel(f"Dependencies: {len(dependencies)}")
            dep_label.setStyleSheet("color: #999; font-size: 9px;")
            footer_layout.addWidget(dep_label)
        
        layout.addLayout(footer_layout)
    
    def setup_styling(self):
        """Apply styling based on the block's category."""
        category = self.block_data.get("category", "other")
        color = self.category_colors.get(category, self.category_colors["other"])
        
        # Lighter version of the color for background
        bg_color = self.lighten_color(color)
        
        self.setStyleSheet(f"""
            PromptBlock {{
                background-color: {bg_color};
                border: 2px solid {color};
                border-radius: 5px;
                padding: 8px;
            }}
            PromptBlock:hover {{
                border: 2px solid #000;
                background-color: #f0f0f0;
            }}
        """)
    
    def lighten_color(self, hex_color: str, factor: float = 0.7) -> str:
        """Lighten a hex color by the given factor."""
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Lighten
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def mousePressEvent(self, event):
        """Handle mouse press events for dragging."""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging."""
        if not (event.buttons() & Qt.LeftButton):
            return
            
        # Check if we've moved far enough to start a drag
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        # Start the drag
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Store block data as JSON in mime data
        mime_data.setText(json.dumps(self.block_data))
        mime_data.setData("application/x-promptblock", json.dumps(self.block_data).encode())
        
        drag.setMimeData(mime_data)
        
        # Create a pixmap of the block for drag visual
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Execute the drag
        drag.exec_(Qt.MoveAction)
    
    def edit_block(self):
        """Open dialog to edit the block data."""
        dialog = BlockEditDialog(self.block_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self.block_data = dialog.get_block_data()
            # Refresh the UI with new data
            self.layout().setParent(None)  # Remove old layout
            self.init_ui()  # Recreate UI with new data
            self.setup_styling()  # Update styling


class BlockEditDialog(QDialog):
    """Dialog for editing a prompt block's properties."""
    
    def __init__(self, block_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.block_data = block_data.copy()  # Work with a copy
        self.init_ui()
        self.setWindowTitle("Edit Prompt Block")
        self.resize(500, 400)
    
    def init_ui(self):
        """Initialize the dialog UI components."""
        layout = QVBoxLayout(self)
        
        # Title field
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit(self.block_data.get("title", ""))
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)
        
        # Category dropdown
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "analysis", "generation", "refactoring", "testing", "other"
        ])
        self.category_combo.setCurrentText(self.block_data.get("category", "other"))
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)
        
        # Priority slider
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("Priority:"))
        self.priority_slider = QSlider(Qt.Horizontal)
        self.priority_slider.setMinimum(1)
        self.priority_slider.setMaximum(5)
        self.priority_slider.setValue(self.block_data.get("priority", 3))
        self.priority_slider.setTickPosition(QSlider.TicksBelow)
        self.priority_slider.setTickInterval(1)
        priority_layout.addWidget(self.priority_slider)
        self.priority_label = QLabel(str(self.priority_slider.value()))
        self.priority_slider.valueChanged.connect(
            lambda val: self.priority_label.setText(str(val))
        )
        priority_layout.addWidget(self.priority_label)
        layout.addLayout(priority_layout)
        
        # Content text area
        layout.addWidget(QLabel("Content:"))
        self.content_edit = QTextEdit(self.block_data.get("content", ""))
        layout.addWidget(self.content_edit)
        
        # Dependency selection
        layout.addWidget(QLabel("Dependencies (placeholders):"))
        self.dependencies_edit = QLineEdit(
            ", ".join(self.block_data.get("dependencies", []))
        )
        layout.addWidget(self.dependencies_edit)
        
        # Auto-execute checkbox
        self.auto_execute_check = QCheckBox("Auto-execute when chain runs")
        self.auto_execute_check.setChecked(self.block_data.get("auto_execute", False))
        layout.addWidget(self.auto_execute_check)
        
        # Validation checkbox
        self.requires_validation_check = QCheckBox("Requires validation before next block")
        self.requires_validation_check.setChecked(self.block_data.get("requires_validation", True))
        layout.addWidget(self.requires_validation_check)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def get_block_data(self) -> Dict[str, Any]:
        """Get the edited block data."""
        # Ensure block has an ID
        if "id" not in self.block_data:
            self.block_data["id"] = str(uuid.uuid4())
            
        # Update with form values
        self.block_data["title"] = self.title_edit.text()
        self.block_data["category"] = self.category_combo.currentText()
        self.block_data["priority"] = self.priority_slider.value()
        self.block_data["content"] = self.content_edit.toPlainText()
        self.block_data["auto_execute"] = self.auto_execute_check.isChecked()
        self.block_data["requires_validation"] = self.requires_validation_check.isChecked()
        
        # Parse dependencies
        deps_text = self.dependencies_edit.text()
        if deps_text:
            self.block_data["dependencies"] = [
                dep.strip() for dep in deps_text.split(",") if dep.strip()
            ]
        else:
            self.block_data["dependencies"] = []
            
        return self.block_data


class PromptSequenceBoard(QScrollArea):
    """A board for arranging prompt blocks in sequence."""
    
    sequence_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocks = []
        
        # Central widget and layout for blocks
        self.central_widget = QWidget()
        self.blocks_layout = QVBoxLayout(self.central_widget)
        self.blocks_layout.setAlignment(Qt.AlignTop)
        self.blocks_layout.setSpacing(10)
        self.blocks_layout.setContentsMargins(10, 10, 10, 10)
        
        # Set the central widget in the scroll area
        self.setWidget(self.central_widget)
        self.setWidgetResizable(True)
        
        # Setup for drag and drop
        self.setAcceptDrops(True)
        
        # Styling
        self.setStyleSheet("""
            PromptSequenceBoard {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        """)
    
    def add_block(self, block_data: Dict[str, Any]) -> PromptBlock:
        """Add a new prompt block to the board."""
        # Create new block widget
        block = PromptBlock(block_data)
        
        # Add to layout
        self.blocks_layout.addWidget(block)
        self.blocks.append(block)
        
        # Emit signal that sequence has been updated
        self.sequence_updated.emit()
        
        return block
    
    def clear_blocks(self):
        """Remove all blocks from the board."""
        for block in self.blocks:
            self.blocks_layout.removeWidget(block)
            block.deleteLater()
        
        self.blocks = []
        self.sequence_updated.emit()
    
    def get_sequence_data(self) -> List[Dict[str, Any]]:
        """Get the ordered sequence of block data."""
        sequence = []
        
        # Iterate through widgets in the layout
        for i in range(self.blocks_layout.count()):
            widget = self.blocks_layout.itemAt(i).widget()
            if isinstance(widget, PromptBlock):
                sequence.append(widget.block_data)
                
        return sequence
    
    def load_sequence_data(self, sequence_data: List[Dict[str, Any]]):
        """Load a sequence of blocks from data."""
        self.clear_blocks()
        
        for block_data in sequence_data:
            self.add_block(block_data)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events."""
        if event.mimeData().hasFormat("application/x-promptblock"):
            event.accept()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move events for positioning."""
        if event.mimeData().hasFormat("application/x-promptblock"):
            event.accept()
            
            # Determine the insert position based on cursor position
            position = self.get_drop_position(event.pos())
            
            # TODO: Implement visual indicator for insert position
            
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Handle drop events for rearranging blocks."""
        if event.mimeData().hasFormat("application/x-promptblock"):
            event.accept()
            
            # Get block data from mime data
            data = event.mimeData().data("application/x-promptblock").data()
            block_data = json.loads(data.decode())
            
            # Determine insert position
            position = self.get_drop_position(event.pos())
            
            # If the block is already in the sequence, remove it first
            for i, block in enumerate(self.blocks):
                if block.block_data.get("id") == block_data.get("id"):
                    self.blocks_layout.removeWidget(block)
                    self.blocks.pop(i)
                    block.deleteLater()
                    break
            
            # Insert the new block at the determined position
            new_block = PromptBlock(block_data)
            self.blocks_layout.insertWidget(position, new_block)
            self.blocks.insert(position, new_block)
            
            # Emit signal that sequence has been updated
            self.sequence_updated.emit()
        else:
            event.ignore()
    
    def get_drop_position(self, pos) -> int:
        """Determine the drop position based on cursor position."""
        # Convert to position in the content widget
        content_pos = self.widget().mapFrom(self, pos)
        
        # Find the widget at that position
        for i in range(self.blocks_layout.count()):
            widget = self.blocks_layout.itemAt(i).widget()
            widget_rect = widget.frameGeometry()
            
            if content_pos.y() < (widget_rect.top() + widget_rect.height() / 2):
                return i
        
        # If we're past all widgets, append to the end
        return self.blocks_layout.count()


class DraggablePromptBoardTab(QWidget):
    """Tab for managing a draggable prompt board interface."""
    
    def __init__(self, prompt_service=None, context_analyzer=None, parent=None):
        super().__init__(parent)
        self.prompt_service = prompt_service
        self.context_analyzer = context_analyzer
        self.current_sequence_file = ""
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Top controls
        top_controls = QHBoxLayout()
        
        # Sequence file controls
        file_group = QGroupBox("Sequence File")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file selected")
        file_layout.addWidget(self.file_path_edit)
        
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self.load_sequence)
        file_layout.addWidget(load_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_sequence)
        file_layout.addWidget(save_btn)
        
        save_as_btn = QPushButton("Save As")
        save_as_btn.clicked.connect(self.save_sequence_as)
        file_layout.addWidget(save_as_btn)
        
        top_controls.addWidget(file_group, 3)
        
        # Sequence metadata
        metadata_group = QGroupBox("Sequence Metadata")
        metadata_layout = QHBoxLayout(metadata_group)
        
        self.sequence_name_edit = QLineEdit()
        self.sequence_name_edit.setPlaceholderText("Sequence Name")
        metadata_layout.addWidget(self.sequence_name_edit)
        
        metadata_layout.addWidget(QLabel("Blocks:"))
        self.block_count_label = QLabel("0")
        metadata_layout.addWidget(self.block_count_label)
        
        top_controls.addWidget(metadata_group, 2)
        
        # Add the top controls to the main layout
        main_layout.addLayout(top_controls)
        
        # Splitter for board and sidebar
        content_layout = QHBoxLayout()
        
        # Main board area
        board_group = QGroupBox("Prompt Sequence")
        board_layout = QVBoxLayout(board_group)
        
        self.prompt_board = PromptSequenceBoard()
        self.prompt_board.sequence_updated.connect(self.update_block_count)
        board_layout.addWidget(self.prompt_board)
        
        # Board controls
        board_controls = QHBoxLayout()
        
        add_block_btn = QPushButton("Add Block")
        add_block_btn.clicked.connect(self.add_new_block)
        board_controls.addWidget(add_block_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_board)
        board_controls.addWidget(clear_btn)
        
        generate_btn = QPushButton("Generate from Context")
        generate_btn.clicked.connect(self.generate_from_context)
        board_controls.addWidget(generate_btn)
        
        board_layout.addLayout(board_controls)
        
        content_layout.addWidget(board_group, 3)
        
        # Sidebar with block templates and execution controls
        sidebar_layout = QVBoxLayout()
        
        # Block templates section
        templates_group = QGroupBox("Block Templates")
        templates_layout = QVBoxLayout(templates_group)
        
        # Template categories
        for category in ["Analysis", "Generation", "Refactoring", "Testing"]:
            template_btn = QPushButton(f"{category} Template")
            template_btn.clicked.connect(
                lambda checked, cat=category.lower(): self.add_template_block(cat)
            )
            templates_layout.addWidget(template_btn)
        
        templates_layout.addStretch()
        sidebar_layout.addWidget(templates_group)
        
        # Execution controls
        execution_group = QGroupBox("Execution")
        execution_layout = QVBoxLayout(execution_group)
        
        execute_btn = QPushButton("▶ Execute Sequence")
        execute_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        execute_btn.clicked.connect(self.execute_sequence)
        execution_layout.addWidget(execute_btn)
        
        # Execution options
        self.validate_check = QCheckBox("Validate each step")
        self.validate_check.setChecked(True)
        execution_layout.addWidget(self.validate_check)
        
        self.auto_execute_check = QCheckBox("Auto-execute all blocks")
        execution_layout.addWidget(self.auto_execute_check)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["GPT-4", "GPT-3.5-Turbo", "Claude 3", "Local LLM"])
        model_layout.addWidget(self.model_combo)
        execution_layout.addLayout(model_layout)
        
        # Delay between blocks
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay between blocks (s):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setMinimum(0)
        self.delay_spin.setMaximum(60)
        self.delay_spin.setValue(5)
        delay_layout.addWidget(self.delay_spin)
        execution_layout.addLayout(delay_layout)
        
        # Status display
        execution_layout.addWidget(QLabel("Status:"))
        self.status_edit = QTextEdit()
        self.status_edit.setReadOnly(True)
        self.status_edit.setMaximumHeight(100)
        execution_layout.addWidget(self.status_edit)
        
        sidebar_layout.addWidget(execution_group)
        
        content_layout.addLayout(sidebar_layout, 1)
        
        # Add the content layout to the main layout
        main_layout.addLayout(content_layout)
    
    def add_new_block(self):
        """Add a new empty block to the board."""
        # Create empty block data
        block_data = {
            "id": str(uuid.uuid4()),
            "title": "New Block",
            "category": "other",
            "content": "Enter prompt content here...",
            "priority": 3,
            "dependencies": [],
            "created_at": datetime.now().isoformat(),
            "auto_execute": False,
            "requires_validation": True
        }
        
        # Open edit dialog
        dialog = BlockEditDialog(block_data, self)
        if dialog.exec_() == QDialog.Accepted:
            # Add the new block to the board
            self.prompt_board.add_block(dialog.get_block_data())
    
    def add_template_block(self, category: str):
        """Add a template block of the specified category."""
        # Create template block data based on category
        templates = {
            "analysis": {
                "title": "Project Analysis",
                "content": "Analyze the project structure and provide insights on key components and dependencies.",
                "priority": 4
            },
            "generation": {
                "title": "Code Generation",
                "content": "Generate code for [component] following the project's architecture patterns and style guides.",
                "priority": 3
            },
            "refactoring": {
                "title": "Code Refactoring",
                "content": "Refactor [component] to improve [aspect] while maintaining test coverage and existing functionality.",
                "priority": 3
            },
            "testing": {
                "title": "Test Generation",
                "content": "Generate comprehensive tests for [component] including edge cases and error handling scenarios.",
                "priority": 3
            }
        }
        
        template = templates.get(category, {
            "title": "Custom Block",
            "content": "Enter custom prompt content here...",
            "priority": 3
        })
        
        block_data = {
            "id": str(uuid.uuid4()),
            "title": template["title"],
            "category": category,
            "content": template["content"],
            "priority": template["priority"],
            "dependencies": [],
            "created_at": datetime.now().isoformat(),
            "auto_execute": False,
            "requires_validation": True
        }
        
        # Open edit dialog with template data
        dialog = BlockEditDialog(block_data, self)
        if dialog.exec_() == QDialog.Accepted:
            # Add the new block to the board
            self.prompt_board.add_block(dialog.get_block_data())
    
    def clear_board(self):
        """Clear all blocks from the board."""
        reply = QMessageBox.question(
            self, "Clear Board",
            "Are you sure you want to clear all blocks from the board?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.prompt_board.clear_blocks()
    
    def update_block_count(self):
        """Update the block count display."""
        count = len(self.prompt_board.get_sequence_data())
        self.block_count_label.setText(str(count))
    
    def load_sequence(self):
        """Load a sequence from a JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Sequence", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                # Extract sequence data and metadata
                sequence_data = data.get("blocks", [])
                sequence_name = data.get("name", "Unnamed Sequence")
                
                # Update UI
                self.prompt_board.load_sequence_data(sequence_data)
                self.sequence_name_edit.setText(sequence_name)
                self.file_path_edit.setText(file_path)
                self.current_sequence_file = file_path
                
                # Update block count
                self.update_block_count()
                
                self.status_edit.append(f"Loaded sequence from {file_path}")
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Load Error", f"Error loading sequence: {str(e)}"
                )
    
    def save_sequence(self):
        """Save the current sequence to the current file or prompt for a new file."""
        if not self.current_sequence_file:
            self.save_sequence_as()
            return
            
        self._save_to_file(self.current_sequence_file)
    
    def save_sequence_as(self):
        """Save the current sequence to a new file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Sequence", "", "JSON Files (*.json)"
        )
        
        if file_path:
            self._save_to_file(file_path)
            self.current_sequence_file = file_path
            self.file_path_edit.setText(file_path)
    
    def _save_to_file(self, file_path: str):
        """Save the sequence data to the specified file."""
        try:
            # Get sequence data
            sequence_data = self.prompt_board.get_sequence_data()
            
            # Create full data structure
            data = {
                "name": self.sequence_name_edit.text() or "Unnamed Sequence",
                "created_at": datetime.now().isoformat(),
                "blocks": sequence_data
            }
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.status_edit.append(f"Saved sequence to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Error saving sequence: {str(e)}"
            )
    
    def generate_from_context(self):
        """Generate blocks from project context analysis."""
        if not self.context_analyzer:
            self.status_edit.append("Context analyzer service not available")
            return
            
        self.status_edit.append("Analyzing project context...")
        
        # This would be replaced with actual call to context analyzer
        # For now, we'll simulate it with some sample blocks
        
        try:
            # Sample blocks based on project analysis
            sample_blocks = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Analyze Project Structure",
                    "category": "analysis",
                    "content": "Analyze the current project structure and identify key components and relationships.",
                    "priority": 5,
                    "dependencies": [],
                    "created_at": datetime.now().isoformat(),
                    "auto_execute": True,
                    "requires_validation": True
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Implement Task Manager",
                    "category": "generation",
                    "content": "Create a TaskManager class that provides a consistent interface for managing task objects across the system.",
                    "priority": 4,
                    "dependencies": [],
                    "created_at": datetime.now().isoformat(),
                    "auto_execute": False,
                    "requires_validation": True
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Refactor PromptExecutionService",
                    "category": "refactoring",
                    "content": "Refactor the PromptExecutionService to use the new TaskManager for better consistency and reduced duplication.",
                    "priority": 3,
                    "dependencies": [],
                    "created_at": datetime.now().isoformat(),
                    "auto_execute": False,
                    "requires_validation": True
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Generate Unit Tests",
                    "category": "testing",
                    "content": "Create comprehensive unit tests for the TaskManager class to ensure it meets all requirements.",
                    "priority": 3,
                    "dependencies": [],
                    "created_at": datetime.now().isoformat(),
                    "auto_execute": False,
                    "requires_validation": True
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Implement UI Integration",
                    "category": "generation",
                    "content": "Integrate the TaskManager with the CursorExecutionTab UI to provide a consistent user experience.",
                    "priority": 3,
                    "dependencies": [],
                    "created_at": datetime.now().isoformat(),
                    "auto_execute": False,
                    "requires_validation": True
                }
            ]
            
            # Ask if user wants to add these blocks
            reply = QMessageBox.question(
                self, "Generated Blocks",
                f"Generated {len(sample_blocks)} blocks from project context. Add them to the board?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Add blocks to the board
                for block_data in sample_blocks:
                    self.prompt_board.add_block(block_data)
                    
                self.status_edit.append(f"Added {len(sample_blocks)} blocks from context analysis")
            
        except Exception as e:
            self.status_edit.append(f"Error generating blocks: {str(e)}")
    
    def execute_sequence(self):
        """Execute the current sequence of blocks."""
        sequence_data = self.prompt_board.get_sequence_data()
        
        if not sequence_data:
            self.status_edit.append("No blocks to execute")
            return
            
        # Confirm execution
        reply = QMessageBox.question(
            self, "Execute Sequence",
            f"Execute sequence of {len(sequence_data)} blocks?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # Check if prompt service is available
        if not self.prompt_service:
            self.status_edit.append("Prompt execution service not available")
            return
            
        # Start execution
        self.status_edit.clear()
        self.status_edit.append(f"Starting execution of {len(sequence_data)} blocks...")
        
        # Get execution parameters
        validate_steps = self.validate_check.isChecked()
        auto_execute_all = self.auto_execute_check.isChecked()
        model = self.model_combo.currentText()
        delay = self.delay_spin.value()
        
        self.status_edit.append(f"Model: {model}")
        self.status_edit.append(f"Validation: {'Enabled' if validate_steps else 'Disabled'}")
        self.status_edit.append(f"Auto-execute: {'All blocks' if auto_execute_all else 'Per block setting'}")
        self.status_edit.append(f"Delay between blocks: {delay}s")
        
        # TODO: Implement actual execution logic with the prompt_service
        # For now, we'll just simulate execution
        
        self.status_edit.append("\nSimulating execution (in actual implementation, this would call PromptExecutionService):")
        
        for i, block in enumerate(sequence_data):
            title = block.get("title", "Unnamed Block")
            self.status_edit.append(f"\nExecuting Block {i+1}: {title}")
            
            # Simulate execution delay
            QTimer.singleShot(i * 1000, lambda i=i, block=block: self._simulate_block_execution(i, block))
    
    def _simulate_block_execution(self, index: int, block: Dict[str, Any]):
        """Simulate execution of a block for demonstration purposes."""
        title = block.get("title", "Unnamed Block")
        category = block.get("category", "other")
        auto_execute = block.get("auto_execute", False) or self.auto_execute_check.isChecked()
        
        self.status_edit.append(f"  Category: {category}")
        self.status_edit.append(f"  Auto-execute: {'Yes' if auto_execute else 'No'}")
        self.status_edit.append(f"  Status: {'Executing automatically' if auto_execute else 'Waiting for manual approval'}")
        
        # Simulate completion
        QTimer.singleShot(2000, lambda: self.status_edit.append(f"  Completed: Block {index+1} - {title}"))


class DraggablePromptBoardTabFactory:
    """Factory for creating DraggablePromptBoardTab with dependencies."""
    
    @staticmethod
    def create(services: Dict[str, Any]) -> Optional[DraggablePromptBoardTab]:
        """Create a tab with required services injected."""
        # Get prompt execution service
        prompt_service = services.get('prompt_service')
        if not prompt_service:
            logger.warning("PromptExecutionService not available, some features will be limited")
        
        # Context analyzer is optional, can be None
        context_analyzer = services.get('context_analyzer')
        
        # Create the tab
        tab = DraggablePromptBoardTab(
            prompt_service=prompt_service,
            context_analyzer=context_analyzer
        )
        
        logger.info("DraggablePromptBoardTab created")
        return tab 
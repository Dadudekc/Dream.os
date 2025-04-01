"""
Context Tree Component

This module provides a tree view for displaying and filtering context data.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QLineEdit, QLabel
)
from PyQt5.QtCore import Qt
import logging
from typing import Dict, Optional, Any

class ContextTree(QWidget):
    """Widget for displaying episode context in a tree structure."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the context tree widget."""
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        # Filter input
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(QLabel("Filter Context:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Type to filter...")
        filter_layout.addWidget(self.filter_input)
        layout.addLayout(filter_layout)
        
        # Context tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Key", "Value"])
        self.tree.setColumnCount(2)
        layout.addWidget(self.tree)
        
        self.setLayout(layout)
        
        # Connect signals
        self.filter_input.textChanged.connect(self._filter_tree)
        
    def update_context(self, context_data: Dict[str, Any]):
        """Update the context tree with new data."""
        self.tree.clear()
        self._add_dict_to_tree(context_data)
        self.tree.expandAll()
        
    def _add_dict_to_tree(self, data: Dict[str, Any], parent: Optional[QTreeWidgetItem] = None):
        """Recursively add dictionary data to the tree."""
        for key, value in data.items():
            if parent is None:
                item = QTreeWidgetItem(self.tree)
            else:
                item = QTreeWidgetItem(parent)
                
            item.setText(0, str(key))
            
            if isinstance(value, dict):
                item.setText(1, "")
                self._add_dict_to_tree(value, item)
            elif isinstance(value, list):
                item.setText(1, "")
                for i, v in enumerate(value):
                    child = QTreeWidgetItem(item)
                    child.setText(0, str(i))
                    if isinstance(v, dict):
                        self._add_dict_to_tree(v, child)
                    else:
                        child.setText(1, str(v))
            else:
                item.setText(1, str(value))
                
    def _filter_tree(self, text: str):
        """Filter tree items based on input text."""
        if not text:
            for i in range(self.tree.topLevelItemCount()):
                self._set_item_visible(self.tree.topLevelItem(i), True)
            return
            
        text = text.lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            self._filter_item(item, text)
            
    def _filter_item(self, item: QTreeWidgetItem, text: str) -> bool:
        """Filter a single item and its children. Returns True if item or any children match."""
        if item is None:
            return False
            
        # Check if current item matches
        item_matches = (text in item.text(0).lower() or
                       text in item.text(1).lower())
                       
        # Check children
        child_matches = False
        for i in range(item.childCount()):
            if self._filter_item(item.child(i), text):
                child_matches = True
                
        # Show/hide based on matches
        visible = item_matches or child_matches
        self._set_item_visible(item, visible)
        
        return visible
        
    def _set_item_visible(self, item: QTreeWidgetItem, visible: bool):
        """Set the visibility of a tree item."""
        item.setHidden(not visible)
        
    def clear(self):
        """Clear the context tree."""
        self.tree.clear()
        self.filter_input.clear() 
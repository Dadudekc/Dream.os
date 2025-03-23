from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTextEdit, QLabel,
    QMessageBox, QListWidget, QListWidgetItem,
    QGroupBox, QSplitter, QComboBox, QInputDialog,
    QTabWidget
)
from PyQt5.QtCore import pyqtSignal, Qt, QSize

class PromptPanel(QWidget):
    """Panel for managing and executing prompts"""
    
    # Signals
    prompt_executed = pyqtSignal(str)      # Emitted when a prompt is executed
    prompt_saved = pyqtSignal()            # Emitted when prompts are saved
    prompts_reset = pyqtSignal()           # Emitted when prompts are reset
    prompt_selected = pyqtSignal(dict)     # Emitted when a prompt is selected for execution
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.prompts = {}  # Dictionary to store prompts
        self.setup_ui()
        self.load_sample_prompts()  # Load sample prompts for demonstration
        
    def setup_ui(self):
        main_layout = QVBoxLayout()
        
        # Create splitter for resizable sections
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Prompt categories and list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Create tabs for different prompt categories
        self.category_tabs = QTabWidget()
        
        # Default prompts tab
        default_tab = QWidget()
        default_layout = QVBoxLayout(default_tab)
        self.default_prompts_list = QListWidget()
        self.default_prompts_list.itemClicked.connect(self.on_prompt_selected)
        default_layout.addWidget(self.default_prompts_list)
        
        # Custom prompts tab
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)
        self.custom_prompts_list = QListWidget()
        self.custom_prompts_list.itemClicked.connect(self.on_prompt_selected)
        custom_buttons_layout = QHBoxLayout()
        self.add_custom_btn = QPushButton("Add New")
        self.remove_custom_btn = QPushButton("Remove")
        self.add_custom_btn.clicked.connect(self.add_custom_prompt)
        self.remove_custom_btn.clicked.connect(self.remove_custom_prompt)
        custom_buttons_layout.addWidget(self.add_custom_btn)
        custom_buttons_layout.addWidget(self.remove_custom_btn)
        custom_layout.addWidget(self.custom_prompts_list)
        custom_layout.addLayout(custom_buttons_layout)
        
        # Community prompts tab
        community_tab = QWidget()
        community_layout = QVBoxLayout(community_tab)
        self.community_prompts_list = QListWidget()
        self.community_prompts_list.itemClicked.connect(self.on_prompt_selected)
        community_layout.addWidget(self.community_prompts_list)
        
        # Add tabs to tab widget
        self.category_tabs.addTab(default_tab, "Default")
        self.category_tabs.addTab(custom_tab, "Custom")
        self.category_tabs.addTab(community_tab, "Community")
        
        left_layout.addWidget(self.category_tabs)
        
        # Right panel - Prompt editor and details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Prompt details
        details_group = QGroupBox("Prompt Details")
        details_layout = QVBoxLayout(details_group)
        
        # Prompt type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.prompt_type_selector = QComboBox()
        self.prompt_type_selector.addItems(["Default", "Custom", "Community"])
        type_layout.addWidget(self.prompt_type_selector)
        details_layout.addLayout(type_layout)
        
        # Prompt editor
        self.prompt_editor = QTextEdit()
        details_layout.addWidget(QLabel("Prompt Text:"))
        details_layout.addWidget(self.prompt_editor)
        
        # Description
        self.prompt_description = QTextEdit()
        self.prompt_description.setMaximumHeight(100)
        details_layout.addWidget(QLabel("Description:"))
        details_layout.addWidget(self.prompt_description)
        
        # Add details group to right panel
        right_layout.addWidget(details_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Changes")
        self.use_prompt_btn = QPushButton("Use This Prompt")
        self.save_btn.clicked.connect(self.save_prompt)
        self.use_prompt_btn.clicked.connect(self.use_prompt)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.use_prompt_btn)
        right_layout.addLayout(button_layout)
        
        # Add panels to splitter
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([200, 400])  # Set initial sizes
        
        # Add splitter to main layout
        main_layout.addWidget(self.splitter)
        
        self.setLayout(main_layout)
        
    def load_sample_prompts(self):
        """Load sample prompts for demonstration purposes"""
        # Default prompts
        default_prompts = [
            {
                "name": "General Chat Assistant",
                "text": "You are a helpful, friendly AI assistant. Answer any questions to the best of your ability.",
                "description": "Basic prompt for general AI assistance.",
                "type": "Default"
            },
            {
                "name": "Community Building Strategy",
                "text": "Analyze my social media presence and suggest strategies for building a stronger community. Focus on engagement and retention tactics that foster meaningful interactions.",
                "description": "Prompt for generating community building strategies.",
                "type": "Default"
            },
            {
                "name": "Content Idea Generator",
                "text": "Generate 5 content ideas for {platform} that would engage my target audience of {audience}. Include post structure, key points, and potential hashtags.",
                "description": "Prompt for generating content ideas for social media.",
                "type": "Default"
            }
        ]
        
        # Community prompts
        community_prompts = [
            {
                "name": "Twitter Growth Strategy",
                "text": "I want to grow my Twitter following from {current_followers} to {target_followers}. Suggest a 30-day strategy with daily actions, content themes, and engagement tactics.",
                "description": "Community-contributed prompt for Twitter growth.",
                "type": "Community"
            },
            {
                "name": "Reddit Community Management",
                "text": "I run a subreddit about {topic} with {members} members. Suggest moderation strategies, content guidelines, and engagement activities to foster a positive community.",
                "description": "Community-contributed prompt for Reddit community management.",
                "type": "Community"
            }
        ]
        
        # Add prompts to lists
        for prompt in default_prompts:
            self._add_prompt_to_list(prompt, self.default_prompts_list)
            self.prompts[prompt["name"]] = prompt
            
        for prompt in community_prompts:
            self._add_prompt_to_list(prompt, self.community_prompts_list)
            self.prompts[prompt["name"]] = prompt
    
    def _add_prompt_to_list(self, prompt, list_widget):
        """Add a prompt to the specified list widget"""
        item = QListWidgetItem(prompt["name"])
        item.setData(Qt.UserRole, prompt)
        list_widget.addItem(item)
    
    def on_prompt_selected(self, item):
        """Handle prompt selection from any list"""
        prompt_data = item.data(Qt.UserRole)
        if prompt_data:
            # Update the editor and details
            self.prompt_editor.setPlainText(prompt_data["text"])
            self.prompt_description.setPlainText(prompt_data.get("description", ""))
            
            # Set the type selector
            prompt_type = prompt_data.get("type", "Default")
            index = self.prompt_type_selector.findText(prompt_type)
            if index >= 0:
                self.prompt_type_selector.setCurrentIndex(index)
    
    def save_prompt(self):
        """Save the current prompt"""
        # Get the active list
        current_tab = self.category_tabs.currentWidget()
        if current_tab:
            active_list = None
            if current_tab == self.category_tabs.widget(0):
                active_list = self.default_prompts_list
            elif current_tab == self.category_tabs.widget(1):
                active_list = self.custom_prompts_list
            elif current_tab == self.category_tabs.widget(2):
                active_list = self.community_prompts_list
            
            if active_list and active_list.currentItem():
                prompt_data = active_list.currentItem().data(Qt.UserRole)
                if prompt_data:
                    # Update prompt data
                    prompt_data["text"] = self.prompt_editor.toPlainText()
                    prompt_data["description"] = self.prompt_description.toPlainText()
                    prompt_data["type"] = self.prompt_type_selector.currentText()
                    
                    # Update item in list
                    active_list.currentItem().setData(Qt.UserRole, prompt_data)
                    
                    # Update prompts dictionary
                    self.prompts[prompt_data["name"]] = prompt_data
                    
                    QMessageBox.information(self, "Prompt Saved", f"Prompt '{prompt_data['name']}' has been saved.")
                    self.prompt_saved.emit()
    
    def use_prompt(self):
        """Send the current prompt to the execution tab"""
        # Get the active list
        current_tab = self.category_tabs.currentWidget()
        if current_tab:
            active_list = None
            if current_tab == self.category_tabs.widget(0):
                active_list = self.default_prompts_list
            elif current_tab == self.category_tabs.widget(1):
                active_list = self.custom_prompts_list
            elif current_tab == self.category_tabs.widget(2):
                active_list = self.community_prompts_list
            
            if active_list and active_list.currentItem():
                prompt_data = active_list.currentItem().data(Qt.UserRole)
                if prompt_data:
                    # Emit prompt selected signal
                    self.prompt_selected.emit(prompt_data)
                    
                    # Optionally switch to the execution tab
                    if self.parent and hasattr(self.parent, 'tabs'):
                        # Find the index of the prompt execution tab
                        for i in range(self.parent.tabs.count()):
                            if "Prompt Execution" in self.parent.tabs.tabText(i):
                                self.parent.tabs.setCurrentIndex(i)
                                break
    
    def add_custom_prompt(self):
        """Add a new custom prompt"""
        name, ok = QInputDialog.getText(self, "New Custom Prompt", "Enter prompt name:")
        if ok and name:
            # Check if prompt already exists
            if name in self.prompts:
                QMessageBox.warning(self, "Duplicate Name", "A prompt with this name already exists.")
                return
            
            # Create new prompt
            new_prompt = {
                "name": name,
                "text": "",
                "description": "",
                "type": "Custom"
            }
            
            # Add to list and dictionary
            self._add_prompt_to_list(new_prompt, self.custom_prompts_list)
            self.prompts[name] = new_prompt
            
            # Select the new prompt
            for i in range(self.custom_prompts_list.count()):
                if self.custom_prompts_list.item(i).text() == name:
                    self.custom_prompts_list.setCurrentRow(i)
                    break
            
            # Switch to custom tab
            self.category_tabs.setCurrentIndex(1)
    
    def remove_custom_prompt(self):
        """Remove the selected custom prompt"""
        if self.custom_prompts_list.currentItem():
            prompt_name = self.custom_prompts_list.currentItem().text()
            
            reply = QMessageBox.question(
                self, "Confirm Deletion", 
                f"Are you sure you want to delete '{prompt_name}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Remove from dictionary
                if prompt_name in self.prompts:
                    del self.prompts[prompt_name]
                
                # Remove from list
                self.custom_prompts_list.takeItem(self.custom_prompts_list.currentRow())
                
                # Clear editor
                self.prompt_editor.clear()
                self.prompt_description.clear()
        
    def get_prompt_text(self) -> str:
        """Get the current prompt text"""
        return self.prompt_editor.toPlainText().strip()
        
    def set_prompt_text(self, text: str):
        """Set the prompt text"""
        self.prompt_editor.setPlainText(text) 
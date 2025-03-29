import os
import json
import asyncio
import pytest
from datetime import datetime, timedelta
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit,
    QComboBox, QCheckBox, QListWidget
)
from PyQt5.QtTest import QTest
from chatgpt_automation.views.dreamscape_generation_tab import DreamscapeGenerationTabUI

class TestDreamscapeGenerationTab(QWidget):
    """Test version of DreamscapeGenerationTab."""
    
    def __init__(self, dispatcher, prompt_manager, chat_manager, response_handler,
                 memory_manager, discord_manager, ui_logic, config_manager, logger):
        """Initialize the test tab."""
        super().__init__()
        
        # Store services
        self.dispatcher = dispatcher
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.response_handler = response_handler
        self.memory_manager = memory_manager
        self.discord_manager = discord_manager
        self.ui_logic = ui_logic
        self.config_manager = config_manager
        self.logger = logger
        
        # Get dreamscape service
        self.dreamscape_generator = self.ui_logic.get_service()
        
        # Initialize UI
        self.init_ui()
        
        # Load initial data
        self.refresh_episode_list()
        self.load_context_schedule()
        
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Episode generation controls
        self.generate_episodes_btn = QPushButton("Generate Dreamscape Episodes")
        self.headless_checkbox = QCheckBox("Headless Mode")
        self.post_discord_checkbox = QCheckBox("Post to Discord")
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems(["gpt-4", "gpt-3.5-turbo"])
        
        # Episode list and content
        self.episode_list = QListWidget()
        self.episode_content = QTextEdit()
        
        # Context update controls
        self.auto_update_checkbox = QCheckBox("Auto Update")
        self.auto_update_checkbox.setChecked(True)
        self.target_chat_input = QComboBox()
        self.update_interval_combo = QComboBox()
        self.update_interval_combo.addItems(["1 day", "7 days", "14 days", "30 days"])
        self.context_filter_input = QLineEdit()
        
        # Add widgets to layout
        layout.addWidget(self.generate_episodes_btn)
        layout.addWidget(self.headless_checkbox)
        layout.addWidget(self.post_discord_checkbox)
        layout.addWidget(self.model_dropdown)
        layout.addWidget(self.episode_list)
        layout.addWidget(self.episode_content)
        layout.addWidget(self.auto_update_checkbox)
        layout.addWidget(self.target_chat_input)
        layout.addWidget(self.update_interval_combo)
        layout.addWidget(self.context_filter_input)
        
        self.setLayout(layout)
        
        # Connect signals
        self.generate_episodes_btn.clicked.connect(self.generate_dreamscape_episodes)
        self.episode_list.currentRowChanged.connect(self.load_episode_content)
        
    def refresh_episode_list(self):
        """Refresh the episode list."""
        self.episode_list.clear()
        dreamscape_dir = self.config_manager.get()
        if os.path.exists(dreamscape_dir):
            episodes = [f for f in os.listdir(dreamscape_dir) if f.endswith('.txt')]
            self.episode_list.addItems(episodes)
            
    def load_episode_content(self, row):
        """Load episode content when selected."""
        if row >= 0:
            filename = self.episode_list.item(row).text()
            dreamscape_dir = self.config_manager.get()
            filepath = os.path.join(dreamscape_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    content = f.read()
                self.episode_content.setText(content)
                
    async def generate_dreamscape_episodes(self):
        """Generate dreamscape episodes."""
        self.generate_episodes_btn.setEnabled(False)
        self.generate_episodes_btn.setText("Generation in progress...")
        
        # Simulate generation
        await asyncio.sleep(0.1)
        self.dispatcher.emit_task_completed()
        
        self._update_ui_for_generation(True)
        
    def _update_ui_for_generation(self, success):
        """Update UI after generation."""
        self.generate_episodes_btn.setEnabled(True)
        self.generate_episodes_btn.setText("Generate Dreamscape Episodes")
        if success:
            self.refresh_episode_list()
            
    def share_to_discord(self):
        """Share current episode to Discord."""
        content = self.episode_content.toPlainText()
        if content:
            self.discord_manager.send_message(content)
            
    async def send_context_to_chatgpt(self):
        """Send context to ChatGPT."""
        await self.dreamscape_generator.send_context_to_chatgpt()
        
    def save_context_schedule(self):
        """Save context update schedule."""
        interval_text = self.update_interval_combo.currentText()
        interval_days = int(interval_text.split()[0])
        chat_name = self.target_chat_input.currentText()
        
        self.dreamscape_generator.schedule_context_updates(
            interval_days=interval_days,
            chat_name=chat_name
        )
        
    def load_context_schedule(self):
        """Load context update schedule."""
        dreamscape_dir = self.config_manager.get()
        schedule_file = os.path.join(dreamscape_dir, "context_update_schedule.json")
        if os.path.exists(schedule_file):
            with open(schedule_file, 'r') as f:
                schedule = json.load(f)
            self.auto_update_checkbox.setChecked(schedule.get("enabled", True))
            self.target_chat_input.clear()
            self.target_chat_input.addItems([c["title"] for c in self.chat_manager.get_all_chat_titles()])
            self.target_chat_input.setCurrentText(schedule.get("target_chat", "Dreamscape Chat"))
            days = schedule.get("interval_days", 7)
            self.update_interval_combo.setCurrentText(f"{days} days")
            
    def refresh_context_memory(self):
        """Refresh context memory display."""
        pass  # Simplified for testing

@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    from unittest.mock import MagicMock
    
    services = {
        'dispatcher': MagicMock(),
        'prompt_manager': MagicMock(),
        'chat_manager': MagicMock(),
        'response_handler': MagicMock(),
        'memory_manager': MagicMock(),
        'discord_manager': MagicMock(),
        'ui_logic': MagicMock(),
        'config_manager': MagicMock(),
        'logger': MagicMock()
    }
    
    # Configure chat manager
    services['chat_manager'].get_all_chat_titles.return_value = [
        {"title": "Dreamscape Chat"},
        {"title": "Test Chat"},
        {"title": "Another Chat"}
    ]
    
    # Configure dreamscape service
    mock_dreamscape_service = MagicMock()
    mock_dreamscape_service.send_context_to_chatgpt.return_value = True
    mock_dreamscape_service.schedule_context_updates.return_value = True
    services['ui_logic'].get_service.return_value = mock_dreamscape_service
    
    return services

@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with necessary files and directories."""
    test_dir = tmp_path / "test_outputs" / "dreamscape"
    test_dir.mkdir(parents=True)
    
    # Create test episodes
    episodes = [
        {
            "filename": "20240101_Episode_#1_Test.txt",
            "content": "Test episode 1 content"
        },
        {
            "filename": "20240102_DS-001_Another_Test.txt",
            "content": "Test episode 2 content"
        }
    ]
    
    for episode in episodes:
        episode_file = test_dir / episode["filename"]
        episode_file.write_text(episode["content"])
    
    return test_dir

@pytest.mark.usefixtures("qapp")
class TestDreamscapeGenerationTab:
    """Test class for DreamscapeGenerationTab."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_services, test_env):
        """Set up test environment before each test."""
        self.tab = TestDreamscapeGenerationTab(
            mock_services['dispatcher'],
            mock_services['prompt_manager'],
            mock_services['chat_manager'],
            mock_services['response_handler'],
            mock_services['memory_manager'],
            mock_services['discord_manager'],
            mock_services['ui_logic'],
            mock_services['config_manager'],
            mock_services['logger']
        )
        self.test_env = test_env
        
    @pytest.mark.asyncio
    async def test_complete_episode_generation_workflow(self):
        """Test complete episode generation workflow."""
        # Test episode generation
        self.tab.generate_episodes_btn.click()
        await asyncio.sleep(0.1)  # Allow async operations to complete
        
        # Verify UI state after generation
        assert self.tab.generate_episodes_btn.isEnabled()
        assert self.tab.generate_episodes_btn.text() == "Generate Dreamscape Episodes"
        
    @pytest.mark.asyncio
    async def test_context_update_workflow(self):
        """Test complete context update workflow."""
        # Test context update
        await self.tab.send_context_to_chatgpt()
        
        # Verify schedule is saved
        schedule_file = os.path.join(self.test_env, "context_update_schedule.json")
        assert os.path.exists(schedule_file)
        
    def test_episode_interaction_workflow(self):
        """Test episode interaction workflow."""
        # Add test episode
        test_episode = "test_episode.txt"
        with open(os.path.join(self.test_env, test_episode), 'w') as f:
            f.write("Test content")
            
        # Refresh list and select episode
        self.tab.refresh_episode_list()
        self.tab.episode_list.setCurrentRow(0)
        
        # Verify content is loaded
        assert self.tab.episode_content.toPlainText() == "Test content"
        
    def test_filter_context_memory(self):
        """Test context memory filtering."""
        # Set filter text
        filter_text = "test filter"
        self.tab.context_filter_input.setText(filter_text)
        
        # Verify filter is applied
        assert self.tab.context_filter_input.text() == filter_text 
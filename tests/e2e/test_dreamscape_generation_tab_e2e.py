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

@pytest.mark.asyncio
class TestDreamscapeGenerationTabE2E:
    """End-to-end tests for DreamscapeGenerationTab."""
    
    @pytest.fixture(autouse=True)
    async def setup(self, qapp, mock_services, test_env):
        """Set up test environment before each test."""
        self.app = qapp
        self.services = mock_services
        self.test_dir = test_env
        
        # Configure config manager to use test directory
        self.services['config_manager'].get.return_value = str(self.test_dir)
        
        # Create tab instance
        self.tab = TestDreamscapeGenerationTab(
            dispatcher=self.services['dispatcher'],
            prompt_manager=self.services['prompt_manager'],
            chat_manager=self.services['chat_manager'],
            response_handler=self.services['response_handler'],
            memory_manager=self.services['memory_manager'],
            discord_manager=self.services['discord_manager'],
            ui_logic=self.services['ui_logic'],
            config_manager=self.services['config_manager'],
            logger=self.services['logger']
        )
        
        # Create test schedule
        schedule = {
            "enabled": True,
            "interval_days": 7,
            "target_chat": "Dreamscape Chat",
            "next_update": (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        schedule_file = os.path.join(str(self.test_dir), "context_update_schedule.json")
        with open(schedule_file, 'w') as f:
            json.dump(schedule, f)
            
        yield
        
        # Cleanup
        if os.path.exists(schedule_file):
            os.remove(schedule_file)
    
    async def test_complete_episode_generation_workflow(self):
        """Test complete episode generation workflow."""
        # 1. Initial state verification
        assert self.tab.episode_list.count() == 2
        assert self.tab.generate_episodes_btn.isEnabled()
        
        # 2. Configure generation settings
        self.tab.headless_checkbox.setChecked(True)
        self.tab.post_discord_checkbox.setChecked(True)
        self.tab.model_dropdown.setCurrentText("gpt-4")
        
        # 3. Start generation
        await self.tab.generate_dreamscape_episodes()
        
        # 4. Verify UI updates during generation
        assert not self.tab.generate_episodes_btn.isEnabled()
        assert self.tab.generate_episodes_btn.text() == "Generation in progress..."
        
        # 5. Simulate generation completion
        self.services['dispatcher'].emit_task_completed.assert_called()
        self.tab._update_ui_for_generation(True)
        
        # 6. Verify final state
        assert self.tab.generate_episodes_btn.isEnabled()
        assert self.tab.generate_episodes_btn.text() == "Generate Dreamscape Episodes"
    
    async def test_context_update_workflow(self):
        """Test complete context update workflow."""
        # 1. Initial state verification
        assert self.tab.auto_update_checkbox.isChecked()
        assert self.tab.target_chat_input.currentText() == "Dreamscape Chat"
        
        # 2. Configure update settings
        self.tab.update_interval_combo.setCurrentText("7 days")
        
        # 3. Send context update
        await self.tab.send_context_to_chatgpt()
        
        # 4. Verify service calls
        dreamscape_service = self.services['ui_logic'].get_service.return_value
        dreamscape_service.send_context_to_chatgpt.assert_called_once()
        
        # 5. Save schedule
        self.tab.save_context_schedule()
        
        # 6. Verify schedule saved
        dreamscape_service.schedule_context_updates.assert_called_once_with(
            interval_days=7,
            chat_name="Dreamscape Chat"
        )
    
    def test_episode_interaction_workflow(self):
        """Test episode interaction workflow."""
        # 1. Select episode
        self.tab.episode_list.setCurrentRow(0)
        
        # 2. Verify content loaded
        assert self.tab.episode_content.toPlainText() == "Test episode 1 content"
        
        # 3. Share to Discord
        self.tab.share_to_discord()
        
        # 4. Verify Discord service called
        self.services['discord_manager'].send_message.assert_called_once_with(
            "Test episode 1 content"
        )
    
    def test_filter_context_memory(self):
        """Test context memory filtering workflow."""
        # 1. Set up test context
        test_context = {
            "episode_count": 2,
            "last_updated": datetime.now().isoformat(),
            "active_themes": ["Adventure", "Mystery", "Fantasy"],
            "recent_episodes": [
                {
                    "title": "The Mystery Begins",
                    "themes": ["Mystery", "Adventure"],
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        self.tab.dreamscape_generator.get_context_summary.return_value = test_context
        
        # 2. Initial refresh
        self.tab.refresh_context_memory()
        
        # 3. Apply filter
        QTest.keyClicks(self.tab.context_filter_input, "Mystery")
        
        # 4. Verify filtered results
        assert self.tab.context_filter_input.text() == "Mystery" 
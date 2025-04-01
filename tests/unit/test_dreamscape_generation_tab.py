import os
import json
from unittest import TestCase, mock
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab

class TestDreamscapeGenerationTab(TestCase):
    """Unit tests for DreamscapeGenerationTab."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication instance for all tests."""
        cls.app = QApplication([])
        
    def setUp(self):
        """Set up test environment before each test."""
        self.mock_dispatcher = mock.MagicMock()
        self.mock_prompt_manager = mock.MagicMock()
        self.mock_chat_manager = mock.MagicMock()
        self.mock_response_handler = mock.MagicMock()
        self.mock_memory_manager = mock.MagicMock()
        self.mock_discord_manager = mock.MagicMock()
        self.mock_ui_logic = mock.MagicMock()
        self.mock_config_manager = mock.MagicMock()
        self.mock_logger = mock.MagicMock()
        
        # Create test output directory
        self.test_output_dir = "test_outputs/dreamscape"
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Configure mock config manager
        self.mock_config_manager.get.return_value = self.test_output_dir
        
        self.tab = DreamscapeGenerationTab(
            dispatcher=self.mock_dispatcher,
            prompt_manager=self.mock_prompt_manager,
            chat_manager=self.mock_chat_manager,
            response_handler=self.mock_response_handler,
            memory_manager=self.mock_memory_manager,
            discord_manager=self.mock_discord_manager,
            ui_logic=self.mock_ui_logic,
            config_manager=self.mock_config_manager,
            logger=self.mock_logger
        )
        
    def tearDown(self):
        """Clean up after each test."""
        # Clean up test files
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)
    
    def test_init_services(self):
        """Test service initialization."""
        self.assertIsNotNone(self.tab.cycle_service)
        self.assertIsNotNone(self.tab.prompt_handler)
        self.assertIsNotNone(self.tab.discord_processor)
        self.assertIsNotNone(self.tab.task_orchestrator)
        self.assertIsNotNone(self.tab.dreamscape_generator)
        self.assertEqual(self.tab.output_dir, self.test_output_dir)
        
    def test_ui_initialization(self):
        """Test UI component initialization."""
        # Test main UI components
        self.assertIsNotNone(self.tab.episode_list)
        self.assertIsNotNone(self.tab.episode_content)
        self.assertIsNotNone(self.tab.context_tree)
        self.assertIsNotNone(self.tab.output_display)
        
        # Test control components
        self.assertIsNotNone(self.tab.headless_checkbox)
        self.assertIsNotNone(self.tab.post_discord_checkbox)
        self.assertIsNotNone(self.tab.model_dropdown)
        self.assertIsNotNone(self.tab.generate_episodes_btn)
        
        # Test context controls
        self.assertIsNotNone(self.tab.auto_update_checkbox)
        self.assertIsNotNone(self.tab.update_interval_combo)
        self.assertIsNotNone(self.tab.target_chat_input)
        
    def test_log_output(self):
        """Test logging functionality."""
        test_message = "Test log message"
        self.tab.log_output(test_message)
        
        # Check logger called
        self.mock_logger.info.assert_called_once()
        # Check dispatcher called
        self.mock_dispatcher.emit_log_output.assert_called_once()
        
    @mock.patch('os.path.exists')
    @mock.patch('os.listdir')
    def test_refresh_episode_list(self, mock_listdir, mock_exists):
        """Test episode list refresh functionality."""
        # Mock file system
        mock_exists.return_value = True
        mock_listdir.return_value = [
            "20240101_Episode_#1_Test.txt",
            "20240102_DS-001_Another_Test.txt"
        ]
        
        # Create mock file content
        with mock.patch('builtins.open', mock.mock_open()):
            self.tab.refresh_episode_list()
        
        # Verify episode list populated
        self.assertEqual(self.tab.episode_list.count(), 2)
        
    def test_share_to_discord(self):
        """Test Discord sharing functionality."""
        # Set up test content
        test_content = "Test episode content"
        self.tab.episode_content.setPlainText(test_content)
        
        # Test sharing
        self.tab.share_to_discord()
        
        # Verify Discord manager called
        self.mock_discord_manager.send_message.assert_called_once_with(test_content)
        
    @mock.patch('asyncio.create_task')
    def test_generate_dreamscape_episodes(self, mock_create_task):
        """Test episode generation initiation."""
        # Set up async mock
        mock_task = mock.MagicMock()
        mock_create_task.return_value = mock_task
        
        # Call generate method
        self.tab.generate_dreamscape_episodes()
        
        # Verify task created
        mock_create_task.assert_called_once()
        
    def test_validate_required_services(self):
        """Test service validation."""
        # Test with valid services
        self.assertTrue(self.tab._validate_required_services())
        
        # Test with missing services
        self.tab.chat_manager = None
        self.assertFalse(self.tab._validate_required_services())
        
    def test_confirm_generation(self):
        """Test generation confirmation dialog."""
        with mock.patch('PyQt5.QtWidgets.QMessageBox.question') as mock_question:
            # Test user confirms
            mock_question.return_value = mock_question.Yes
            self.assertTrue(self.tab._confirm_generation())
            
            # Test user cancels
            mock_question.return_value = mock_question.No
            self.assertFalse(self.tab._confirm_generation())
            
    def test_update_ui_for_generation(self):
        """Test UI updates during generation."""
        # Test disable UI
        self.tab._update_ui_for_generation(False)
        self.assertFalse(self.tab.generate_episodes_btn.isEnabled())
        self.assertEqual(
            self.tab.generate_episodes_btn.text(),
            "Generation in progress..."
        )
        
        # Test enable UI
        self.tab._update_ui_for_generation(True)
        self.assertTrue(self.tab.generate_episodes_btn.isEnabled())
        self.assertEqual(
            self.tab.generate_episodes_btn.text(),
            "Generate Dreamscape Episodes"
        )
        
    def test_get_schedule_interval(self):
        """Test schedule interval retrieval."""
        # Test different intervals
        intervals = ["1 day", "3 days", "7 days", "14 days", "30 days"]
        expected = [1, 3, 7, 14, 30]
        
        for interval, expected_days in zip(intervals, expected):
            self.tab.update_interval_combo.setCurrentText(interval)
            self.assertEqual(self.tab._get_schedule_interval(), expected_days)
            
    def test_auto_select_dreamscape_chat(self):
        """Test automatic Dreamscape chat selection."""
        # Add test items
        self.tab.target_chat_input.clear()
        test_items = ["Test Chat", "Dreamscape Chat", "Another Chat"]
        for item in test_items:
            self.tab.target_chat_input.addItem(item)
            
        # Test auto-selection
        self.tab._auto_select_dreamscape_chat()
        self.assertEqual(
            self.tab.target_chat_input.currentText(),
            "Dreamscape Chat"
        )
        
    def test_load_schedule_settings(self):
        """Test loading schedule settings."""
        # Create test schedule file
        test_schedule = {
            "enabled": True,
            "interval_days": 7,
            "target_chat": "Test Chat",
            "next_update": datetime.now().isoformat()
        }
        
        schedule_file = os.path.join(self.test_output_dir, "context_update_schedule.json")
        with open(schedule_file, 'w') as f:
            json.dump(test_schedule, f)
            
        # Load settings
        self.tab.load_schedule_settings()
        
        # Verify settings applied
        self.assertTrue(self.tab.auto_update_checkbox.isChecked())
        self.assertEqual(self.tab.update_interval_combo.currentText(), "7 days")
        
    @classmethod
    def tearDownClass(cls):
        """Clean up the QApplication."""
        cls.app.quit() 

import os
import sys
import unittest
from datetime import datetime, timedelta
import json
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.PromptCycleOrchestrator import PromptCycleOrchestrator
from core.AletheiaPromptManager import AletheiaPromptManager
from config.MemoryManager import MemoryManager
from core.ReinforcementEngine import ReinforcementEngine
from core.FileManager import FileManager
from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator

class TestPromptCycleOrchestrator(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create mock objects
        self.mock_prompt_manager = Mock(spec=AletheiaPromptManager)
        self.mock_memory_manager = Mock(spec=MemoryManager)
        self.mock_reinforcement_engine = Mock(spec=ReinforcementEngine)
        self.mock_file_manager = Mock(spec=FileManager)
        
        # Initialize test data
        self.test_prompts = ["prompt1", "prompt2", "prompt3"]
        self.test_chats = [
            {"title": "Chat 1", "link": "https://chat1.com"},
            {"title": "Chat 2", "link": "https://chat2.com"}
        ]
        self.test_system_state = {
            "architect_tier": 1,
            "active_domains": ["AI", "Data Science"],
            "unlocked_protocols": ["GPT-4"],
            "skill_levels": {"Python": 5, "ML": 3},
            "quest_progress": {"Quest1": 50},
            "last_update": datetime.now().isoformat()
        }
        
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize PromptCycleOrchestrator
        self.manager = PromptCycleOrchestrator(
            prompt_manager=self.mock_prompt_manager,
            memory_manager=self.mock_memory_manager,
            base_output_dir=self.test_output_dir,
            dry_run=True
        )
    
    def test_initialization(self):
        """Test if PromptCycleOrchestrator initializes correctly."""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.system_state["architect_tier"], 1)
        self.assertEqual(len(self.manager.system_state["active_domains"]), 0)
        self.assertEqual(len(self.manager.system_state["unlocked_protocols"]), 0)
        self.assertEqual(len(self.manager.system_state["skill_levels"]), 0)
        self.assertEqual(len(self.manager.system_state["quest_progress"]), 0)
    
    def test_get_contextual_prompt(self):
        """Test contextual prompt generation."""
        # Setup mock prompt
        self.mock_prompt_manager.get_prompt.return_value = "Test prompt with {{ architect_tier }}"
        
        # Set system state
        self.manager.system_state = self.test_system_state.copy()
        
        # Get contextual prompt
        prompt = self.manager._get_contextual_prompt("test_prompt")
        
        # Verify
        self.assertEqual(prompt, "Test prompt with 1")
        self.mock_prompt_manager.get_prompt.assert_called_once_with("test_prompt")
    
    def test_extract_narrative_elements(self):
        """Test narrative element extraction from response."""
        # Test response with narrative update
        test_response = """
        Some response text
        NARRATIVE_UPDATE: {
            "architect_tier": 2,
            "domains": ["AI", "ML"],
            "protocols": ["GPT-4", "BERT"],
            "skills": {"Python": 6},
            "quests": {"Quest1": 75}
        }
        More response text
        """
        
        # Extract narrative elements
        narrative_data = self.manager._extract_narrative_elements(test_response)
        
        # Verify
        self.assertEqual(narrative_data["architect_tier"], 2)
        self.assertEqual(narrative_data["domains"], ["AI", "ML"])
        self.assertEqual(narrative_data["protocols"], ["GPT-4", "BERT"])
        self.assertEqual(narrative_data["skills"]["Python"], 6)
        self.assertEqual(narrative_data["quests"]["Quest1"], 75)
    
    def test_update_system_state(self):
        """Test system state updates."""
        # Initial state
        self.manager.system_state = self.test_system_state.copy()
        
        # Test narrative data
        narrative_data = {
            "architect_tier": 2,
            "domains": ["AI", "ML"],
            "protocols": ["GPT-4", "BERT"],
            "skills": {"Python": 6},
            "quests": {"Quest1": 75}
        }
        
        # Update system state
        self.manager._update_system_state(narrative_data)
        
        # Verify updates
        self.assertEqual(self.manager.system_state["architect_tier"], 2)
        self.assertEqual(set(self.manager.system_state["active_domains"]), {"AI", "ML"})
        self.assertEqual(set(self.manager.system_state["unlocked_protocols"]), {"GPT-4", "BERT"})
        self.assertEqual(self.manager.system_state["skill_levels"]["Python"], 6)
        self.assertEqual(self.manager.system_state["quest_progress"]["Quest1"], 75)
    
    def test_update_memory(self):
        """Test memory updates."""
        # Setup test data
        feedback = {"base_score": 0.8, "metrics": {"quality": 0.9}}
        narrative_data = {"architect_tier": 2, "domains": ["AI"]}
        
        # Update memory
        self.manager._update_memory(feedback, narrative_data)
        
        # Verify memory manager was called
        self.mock_memory_manager.update.assert_called_once()
        call_args = self.mock_memory_manager.update.call_args[0]
        self.assertEqual(call_args[0], "narrative_cycle")
        self.assertIn("feedback", call_args[1])
        self.assertIn("narrative", call_args[1])
        self.assertIn("system_state", call_args[1])
        self.assertIn("timestamp", call_args[1])
    
    def test_generate_narrative_report(self):
        """Test narrative report generation."""
        # Setup test data
        self.manager.system_state = self.test_system_state.copy()
        self.manager.feedback_history = [
            {"base_score": 0.8, "timestamp": datetime.now().isoformat()}
        ]
        self.manager.scraped_content = [
            {
                "chat_title": "Test Chat",
                "prompt_type": "test_prompt",
                "response": "Test response",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        # Generate report
        self.manager._generate_narrative_report()
        
        # Verify report file was created
        report_files = [f for f in os.listdir(self.test_output_dir) if f.startswith("narrative_report_")]
        self.assertTrue(len(report_files) > 0)
        
        # Verify report content
        with open(os.path.join(self.test_output_dir, report_files[0]), 'r') as f:
            report = json.load(f)
            self.assertIn("timestamp", report)
            self.assertIn("system_state", report)
            self.assertIn("narrative_events", report)
            self.assertIn("total_conversations", report)
            self.assertIn("total_prompts", report)
            self.assertIn("total_responses", report)
            self.assertIn("average_feedback_score", report)
            self.assertIn("feedback_history", report)
            self.assertIn("scraped_content", report)
            self.assertIn("narrative_evolution", report)
    
    def test_perform_ai_audit(self):
        """Test AI audit functionality."""
        # Setup mock response
        mock_response = """
        AUDIT_RESULTS: {
            "score": 85,
            "issues": ["Issue 1", "Issue 2"],
            "recommendations": ["Rec 1", "Rec 2"]
        }
        """
        
        # Mock response handler
        self.manager.response_handler = Mock()
        self.manager.response_handler.send_prompt.return_value = True
        self.manager.response_handler.wait_for_stable_response.return_value = mock_response
        
        # Perform audit
        audit_data = self.manager.perform_ai_audit()
        
        # Verify
        self.assertIsNotNone(audit_data)
        self.assertEqual(audit_data["score"], 85)
        self.assertEqual(len(audit_data["issues"]), 2)
        self.assertEqual(len(audit_data["recommendations"]), 2)
        self.assertEqual(self.manager.audit_metrics["total_audits"], 1)
        self.assertEqual(self.manager.audit_metrics["successful_audits"], 1)
    
    def test_broadcast_narrative_update(self):
        """Test narrative update broadcasting."""
        # Setup mock Discord service
        self.manager.discord_service = Mock()
        self.manager.discord_service.get_or_create_channel.return_value = "test_channel"
        
        # Test event data
        event_type = "milestones"
        event_data = {
            "description": "Test milestone",
            "tier": 2
        }
        
        # Broadcast update
        self.manager._broadcast_narrative_update(event_type, event_data)
        
        # Verify
        self.manager.discord_service.send_message.assert_called_once()
        self.assertEqual(len(self.manager.narrative_events[event_type]), 1)
        self.assertEqual(self.manager.narrative_events[event_type][0]["data"], event_data)
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

class TestCycleServices(unittest.TestCase):
    def setUp(self):
        # Initialize mock managers
        self.prompt_manager = Mock()
        self.chat_manager = Mock()
        self.response_handler = Mock()
        self.memory_manager = Mock()
        self.discord_manager = Mock()

        # Initialize services
        self.cycle_service = CycleExecutionService(
            prompt_manager=self.prompt_manager,
            chat_manager=self.chat_manager,
            response_handler=self.response_handler,
            memory_manager=self.memory_manager,
            discord_manager=self.discord_manager
        )
        self.prompt_handler = PromptResponseHandler()
        self.discord_processor = DiscordQueueProcessor()
        self.task_orchestrator = TaskOrchestrator()

    def test_cycle_service_initialization(self):
        """Test if CycleExecutionService initializes correctly."""
        self.assertIsNotNone(self.cycle_service)
        self.assertIsNotNone(self.prompt_handler)
        self.assertIsNotNone(self.discord_processor)
        self.assertIsNotNone(self.task_orchestrator)

    def test_prompt_handler_initialization(self):
        """Test if PromptResponseHandler initializes correctly."""
        self.assertIsNotNone(self.prompt_handler)

    def test_discord_processor_initialization(self):
        """Test if DiscordQueueProcessor initializes correctly."""
        self.assertIsNotNone(self.discord_processor)

    def test_task_orchestrator_initialization(self):
        """Test if TaskOrchestrator initializes correctly."""
        self.assertIsNotNone(self.task_orchestrator)

if __name__ == '__main__':
    unittest.main() 

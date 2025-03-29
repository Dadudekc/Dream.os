#!/usr/bin/env python3
"""
Integration test for the DreamscapeGenerationService with PromptContextSynthesizer.
This test verifies the end-to-end flow of generating a dreamscape episode with synthesized context.
"""

import os
import json
import logging
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the classes we need to test
from core.services.dreamscape_generator_service import DreamscapeGenerationService
from core.services.prompt_context_synthesizer import PromptContextSynthesizer
from core.PathManager import PathManager
from core.TemplateManager import TemplateManager


class TestDreamscapeIntegration(unittest.TestCase):
    """Test the integration between DreamscapeGenerationService and PromptContextSynthesizer."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create test directories
        self.test_dir = Path("test_data")
        self.test_dir.mkdir(exist_ok=True)
        
        self.memory_dir = self.test_dir / "memory"
        self.memory_dir.mkdir(exist_ok=True)
        
        self.output_dir = self.test_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        self.template_dir = self.test_dir / "templates"
        self.template_dir.mkdir(exist_ok=True)
        
        # Create mock memory files
        self.memory_file = self.memory_dir / "dreamscape_memory.json"
        self.chain_file = self.memory_dir / "episode_chain.json"
        self.conversation_memory_file = self.memory_dir / "conversation_memory.json"
        
        # Sample memory data
        memory_data = {
            "active_quests": [
                {"name": "The Lost Artifact", "status": "active", "progress": 0.5},
                {"name": "Mystery of the Forest", "status": "active", "progress": 0.2}
            ],
            "completed_quests": [
                {"name": "Village Rescue", "status": "completed", "progress": 1.0}
            ],
            "character_traits": {
                "protagonist": {
                    "name": "Alex",
                    "traits": ["brave", "curious"],
                    "emotional_state": "determined"
                }
            },
            "locations": [
                {"name": "Forest of Whispers", "visited": True},
                {"name": "Mountain Pass", "visited": True},
                {"name": "Crystal Cave", "visited": False}
            ]
        }
        
        # Sample chain data
        chain_data = {
            "episodes": [
                {
                    "id": "ep001",
                    "title": "The Beginning",
                    "summary": "Alex starts their journey through the Forest of Whispers.",
                    "quests": ["The Lost Artifact"],
                    "timestamp": "2023-05-15T10:30:00"
                }
            ],
            "current_episode_id": "ep001"
        }
        
        # Sample conversation memory
        conversation_data = {
            "conversations": [
                {
                    "title": "Adventure Planning",
                    "messages": [
                        {"role": "user", "content": "Let's plan an adventure to find the lost artifact."},
                        {"role": "assistant", "content": "That sounds exciting! Where should we start our search?"},
                        {"role": "user", "content": "Let's start in the Forest of Whispers."}
                    ]
                }
            ]
        }
        
        # Write sample data to files
        with open(self.memory_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
            
        with open(self.chain_file, 'w') as f:
            json.dump(chain_data, f, indent=2)
            
        with open(self.conversation_memory_file, 'w') as f:
            json.dump(conversation_data, f, indent=2)
            
        # Create a simple template
        template_content = """
# Dreamscape Episode: {{episode_title}}

## Previously in the Dreamscape
{{previous_summary}}

## Active Quests
{% for quest in active_quests %}
- {{quest.name}} (Progress: {{quest.progress * 100}}%)
{% endfor %}

## Episode Content
{{episode_content}}

## Character Status
Protagonist: {{character_traits.protagonist.name}}
Emotional State: {{character_traits.protagonist.emotional_state}}

## Location
Current Location: {{current_location}}
"""
        
        template_path = self.template_dir / "episode_template.md"
        with open(template_path, 'w') as f:
            f.write(template_content)
            
        # Mock PathManager
        self.path_manager = MagicMock(spec=PathManager)
        self.path_manager.get_path.side_effect = lambda path_type: {
            "memory": self.memory_dir,
            "output": self.output_dir,
            "templates": self.template_dir
        }.get(path_type, self.test_dir)
        
        # Initialize TemplateManager with test template directory
        self.template_manager = TemplateManager(template_dir=str(self.template_dir))
        
        # Initialize our classes
        self.context_synthesizer = PromptContextSynthesizer(
            memory_path=self.memory_file,
            chain_path=self.chain_file,
            conversation_memory_path=self.conversation_memory_file,
            logger=logger
        )
        
        self.dreamscape_service = DreamscapeGenerationService(
            path_manager=self.path_manager,
            template_manager=self.template_manager,
            logger=logger
        )
        
        # Connect the context synthesizer to the dreamscape service
        self.dreamscape_service.context_synthesizer = self.context_synthesizer
        
    def tearDown(self):
        """Clean up after tests."""
        # Remove test directory and all contents
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @patch('core.services.dreamscape_generator_service.DreamscapeGenerationService._generate_llm_response')
    def test_generate_episode_with_synthesized_context(self, mock_generate_llm_response):
        """Test generating a dreamscape episode using synthesized context."""
        # Mock the LLM response
        mock_generate_llm_response.return_value = {
            "title": "The Quest Continues",
            "summary": "Alex ventures deeper into the Forest of Whispers, searching for clues about the Lost Artifact.",
            "content": "As morning light filtered through the dense canopy of the Forest of Whispers, Alex awoke with renewed determination...",
            "quests": [
                {"name": "The Lost Artifact", "status": "active", "progress": 0.7},
                {"name": "Mystery of the Forest", "status": "active", "progress": 0.3}
            ],
            "emotional_state": "hopeful",
            "current_location": "Forest of Whispers - Eastern Path"
        }
        
        # Sample chat history
        chat_history = [
            {"role": "user", "content": "Let's continue our adventure in the forest."},
            {"role": "assistant", "content": "Where would you like to explore next?"},
            {"role": "user", "content": "Let's check out the eastern path."}
        ]
        
        # Generate episode
        result = self.dreamscape_service.generate_dreamscape_episode(
            chat_title="Adventure Planning",
            chat_history=chat_history,
            source="memory"
        )
        
        # Verify the result
        self.assertIsNotNone(result)
        
        # Verify that the synthesize_context method was called
        mock_generate_llm_response.assert_called_once()
        
        # Check if the episode was written to a file
        episode_files = list(self.output_dir.glob("*.md"))
        self.assertGreaterEqual(len(episode_files), 1)
        
        # Read the episode content
        with open(episode_files[0], 'r') as f:
            content = f.read()
        
        # Verify the episode content contains expected elements
        self.assertIn("Dreamscape Episode: The Quest Continues", content)
        self.assertIn("Previously in the Dreamscape", content)
        self.assertIn("Active Quests", content)
        self.assertIn("The Lost Artifact", content)
        self.assertIn("Mystery of the Forest", content)
        self.assertIn("Character Status", content)
        self.assertIn("Alex", content)
        self.assertIn("hopeful", content)
        self.assertIn("Forest of Whispers - Eastern Path", content)
    
    @patch('core.services.prompt_context_synthesizer.PromptContextSynthesizer.synthesize_context')
    @patch('core.services.dreamscape_generator_service.DreamscapeGenerationService._generate_llm_response')
    def test_context_synthesis_integration(self, mock_generate_llm_response, mock_synthesize_context):
        """Test that the context synthesis is properly integrated with episode generation."""
        # Mock the context synthesis result
        mock_synthesize_context.return_value = {
            "context": "Alex is on a quest to find the Lost Artifact in the Forest of Whispers. " +
                      "They have also started investigating the Mystery of the Forest. " +
                      "The last episode ended with Alex discovering a hidden path.",
            "confidence": 0.85,
            "sources": {
                "memory": 0.4,
                "episode_chain": 0.3,
                "conversation_memory": 0.15
            }
        }
        
        # Mock the LLM response
        mock_generate_llm_response.return_value = {
            "title": "The Hidden Path",
            "summary": "Alex discovers where the hidden path leads.",
            "content": "Following the hidden path, Alex found...",
            "quests": [
                {"name": "The Lost Artifact", "status": "active", "progress": 0.8}
            ],
            "emotional_state": "excited",
            "current_location": "Forest of Whispers - Hidden Clearing"
        }
        
        # Sample chat history
        chat_history = [
            {"role": "user", "content": "I want to follow the hidden path."},
            {"role": "assistant", "content": "You follow the winding path deeper into the forest..."},
            {"role": "user", "content": "What do I find at the end?"}
        ]
        
        # Generate episode
        result = self.dreamscape_service.generate_dreamscape_episode(
            chat_title="Adventure Planning",
            chat_history=chat_history,
            source="memory"
        )
        
        # Verify the result
        self.assertIsNotNone(result)
        
        # Verify that both methods were called
        mock_synthesize_context.assert_called_once()
        mock_generate_llm_response.assert_called_once()
        
        # Extract the context passed to _generate_llm_response
        args, kwargs = mock_generate_llm_response.call_args
        self.assertIn("context", kwargs)
        
        # Verify the context from the synthesizer was passed to the LLM
        self.assertEqual(
            kwargs["context"],
            "Alex is on a quest to find the Lost Artifact in the Forest of Whispers. " +
            "They have also started investigating the Mystery of the Forest. " +
            "The last episode ended with Alex discovering a hidden path."
        )

if __name__ == "__main__":
    unittest.main() 
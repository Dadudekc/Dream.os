import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.services.prompt_context_synthesizer import PromptContextSynthesizer

class TestPromptContextSynthesizer(unittest.TestCase):
    def setUp(self):
        # Create temporary files for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory_dir = Path(self.temp_dir.name)
        
        # Initialize test paths
        self.memory_path = self.memory_dir / "dreamscape_memory.json"
        self.chain_path = self.memory_dir / "episode_chain.json"
        self.conversation_memory_path = self.memory_dir / "conversation_memory.json"
        
        # Create mock memory files
        self._create_test_memory_files()
        
        # Mock logger
        self.mock_logger = MagicMock()
        
        # Initialize synthesizer with test paths
        self.synthesizer = PromptContextSynthesizer(
            memory_path=self.memory_path,
            chain_path=self.chain_path,
            conversation_memory_path=self.conversation_memory_path,
            logger=self.mock_logger
        )
    
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def _create_test_memory_files(self):
        """Create mock memory files for testing"""
        # Create memory directory
        self.memory_dir.mkdir(exist_ok=True)
        
        # Create dreamscape memory file
        dreamscape_memory = {
            "protocols": ["Protocol Alpha", "Protocol Beta"],
            "quests": {
                "Find the Lost Artifact": "active",
                "Defeat the Shadow Guardian": "active",
                "Recover the Ancient Codex": "completed"
            },
            "realms": ["The Nexus", "Shadow Realm"],
            "artifacts": ["Crystal of Insight", "Time Weaver"],
            "characters": ["The Architect", "Echo"],
            "themes": ["convergence", "optimization"],
            "stabilized_domains": ["Memory Domain", "Automation Sector"]
        }
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(dreamscape_memory, f, indent=2)
        
        # Create episode chain file
        episode_chain = {
            "episode_count": 3,
            "last_episode": "Convergence of Shadows",
            "current_emotional_state": "Determined",
            "last_location": "The Nexus",
            "ongoing_quests": ["Find the Lost Artifact", "Defeat the Shadow Guardian"],
            "completed_quests": ["Recover the Ancient Codex"],
            "episodes": [
                {
                    "title": "Awakening",
                    "summary": "The Architect awakens in the Nexus",
                    "location": "The Nexus",
                    "emotional_state": "Curious",
                    "timestamp": "2023-01-01T12:00:00"
                },
                {
                    "title": "Discovery of Power",
                    "summary": "The Architect discovers the power of automation",
                    "location": "Automation Sector",
                    "emotional_state": "Excited",
                    "timestamp": "2023-02-01T12:00:00"
                },
                {
                    "title": "Convergence of Shadows",
                    "summary": "The Architect faces the Shadow Guardian",
                    "location": "The Nexus",
                    "emotional_state": "Determined",
                    "timestamp": "2023-03-01T12:00:00"
                }
            ],
            "last_updated": "2023-03-01T12:00:00"
        }
        with open(self.chain_path, "w", encoding="utf-8") as f:
            json.dump(episode_chain, f, indent=2)
        
        # Create conversation memory file
        conversation_memory = {
            "chat_memories": {
                "Memory Architecture Discussion": {
                    "themes": ["memory management", "system design"],
                    "goals": ["improve efficiency", "maintain narrative"],
                    "insights": ["hybrid memory systems are more robust"],
                    "summary": "Discussion about implementing an efficient memory system",
                    "last_updated": "2023-03-01T12:00:00"
                }
            },
            "global_memory": {
                "themes": ["automation", "convergence", "optimization"],
                "goals": ["narrative continuity", "dynamic storytelling"],
                "insights": ["memory persistence improves storytelling"],
                "last_updated": "2023-03-01T12:00:00"
            }
        }
        with open(self.conversation_memory_path, "w", encoding="utf-8") as f:
            json.dump(conversation_memory, f, indent=2)
    
    def test_initialization(self):
        """Test that the synthesizer initializes properly"""
        self.assertEqual(self.synthesizer.memory_path, self.memory_path)
        self.assertEqual(self.synthesizer.chain_path, self.chain_path)
        self.assertEqual(self.synthesizer.conversation_memory_path, self.conversation_memory_path)
    
    def test_load_memory_context(self):
        """Test loading memory context with confidence"""
        memory_context, confidence = self.synthesizer._load_memory_context_with_confidence()
        
        # Check that memory was loaded correctly
        self.assertIn("themes", memory_context)
        self.assertIn("protocols", memory_context)
        self.assertIn("memory_active_quests", memory_context)
        self.assertIn("memory_completed_quests", memory_context)
        
        # Check that active quests were processed correctly
        self.assertEqual(len(memory_context["memory_active_quests"]), 2)
        self.assertIn("Find the Lost Artifact", memory_context["memory_active_quests"])
        
        # Check that confidence score is reasonable
        self.assertGreater(confidence, 0.3)
        self.assertLess(confidence, 0.9)
    
    def test_load_chain_context(self):
        """Test loading episode chain context with confidence"""
        chain_context, confidence = self.synthesizer._load_chain_context_with_confidence()
        
        # Check that chain was loaded correctly
        self.assertEqual(chain_context["episode_count"], 3)
        self.assertEqual(chain_context["last_episode"], "Convergence of Shadows")
        self.assertEqual(chain_context["current_emotional_state"], "Determined")
        
        # Check that episode details were loaded
        self.assertIn("last_episode_summary", chain_context)
        
        # Check that confidence score is reasonable
        self.assertGreater(confidence, 0.2)
        self.assertLess(confidence, 0.95)
    
    def test_load_conversation_memory(self):
        """Test loading conversation memory with confidence"""
        conversation_context, confidence = self.synthesizer._load_conversation_memory_with_confidence("Memory Architecture Discussion")
        
        # Check that conversation memory was loaded correctly
        self.assertIn("semantic_themes", conversation_context)
        self.assertIn("semantic_goals", conversation_context)
        self.assertIn("semantic_insights", conversation_context)
        
        # Check specific content
        self.assertIn("memory management", conversation_context["semantic_themes"])
        
        # Check confidence
        self.assertGreater(confidence, 0.3)
        self.assertLess(confidence, 0.9)
    
    def test_synthesize_context_with_chat_history(self):
        """Test synthesizing context with chat history"""
        chat_history = [
            "User: How can I improve memory management?",
            "Assistant: Consider using a hybrid approach combining structured and semantic memory.",
            "User: What about conflicts between sources?",
            "Assistant: Use confidence scores to resolve conflicts between different memory sources."
        ]
        
        context = self.synthesizer.synthesize_context(
            chat_title="Memory Architecture Discussion",
            chat_history=chat_history
        )
        
        # Check context basics
        self.assertEqual(context["chat_title"], "Memory Architecture Discussion")
        self.assertIn("generation_timestamp", context)
        
        # Check quality metrics
        self.assertIn("context_quality", context)
        self.assertIn("contributions", context["context_quality"])
        self.assertIn("overall_confidence", context["context_quality"])
        
        # Check semantic summary
        self.assertIn("semantic_summary", context)
        
        # Verify data integration
        self.assertTrue(context["source_availability"]["structured_history"])
        self.assertTrue(context["source_availability"]["llm_history"])
        self.assertTrue(context["has_previous_episode"])
    
    def test_synthesize_context_with_web_content(self):
        """Test synthesizing context with web-scraped content"""
        web_content = """
        # Memory Management Discussion
        
        ## User
        How can I implement an efficient memory system?
        
        ## Assistant
        Use a tiered approach with different memory types.
        
        ## Summary
        Discussion about memory management strategies.
        """
        
        context = self.synthesizer.synthesize_context(
            chat_title="Memory Management Discussion",
            web_scraped_content=web_content
        )
        
        # Check web content integration
        self.assertTrue(context["source_availability"]["web_content"])
        self.assertIn("web_content", context["context_quality"]["sources_used"])
        
        # Check semantic summary contains web content
        self.assertIn("semantic_summary", context)
    
    def test_synthesize_context_with_custom_weights(self):
        """Test synthesizing context with custom weights"""
        chat_history = ["User: How can I improve memory management?"]
        
        # Create custom config with adjusted weights
        custom_config = {
            "context_weights": {
                "web_scraping": 0.1,
                "episode_chain": 0.7,
                "semantic_memory": 0.2
            }
        }
        
        context = self.synthesizer.synthesize_context(
            chat_title="Memory Architecture Discussion",
            chat_history=chat_history,
            config=custom_config
        )
        
        # Verify custom weights were applied
        self.assertEqual(context["context_weights"]["episode_chain"], 0.7)
        
        # Since we increased episode_chain weight, the narrative elements
        # should be more prominent in the summary
        self.assertIn("semantic_summary", context)
    
    def test_update_memory_with_context(self):
        """Test updating memory with synthesized context"""
        # Create a context with new elements to add to memory
        context = {
            "chat_title": "New Memory Discussion",
            "semantic_summary": "A discussion about new memory techniques",
            "semantic_themes": ["memory management", "new theme"],
            "semantic_goals": ["improve system", "new goal"],
            "semantic_insights": ["new insight"],
            "new_protocols": ["New Protocol"],
            "new_quests": ["New Quest"],
            "new_realms": ["New Realm"]
        }
        
        # Update memory with the context
        result = self.synthesizer.update_memory_with_synthesized_context(context)
        self.assertTrue(result)
        
        # Check that conversation memory was updated
        with open(self.conversation_memory_path, "r", encoding="utf-8") as f:
            memory_data = json.load(f)
        
        self.assertIn("New Memory Discussion", memory_data["chat_memories"])
        self.assertIn("new theme", memory_data["chat_memories"]["New Memory Discussion"]["themes"])
        
        # Check that structured memory was updated
        with open(self.memory_path, "r", encoding="utf-8") as f:
            memory_data = json.load(f)
        
        self.assertIn("New Protocol", memory_data["protocols"])
        self.assertIn("New Quest", memory_data["quests"])
        self.assertEqual(memory_data["quests"]["New Quest"], "active")

if __name__ == "__main__":
    unittest.main() 
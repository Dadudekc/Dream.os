import os
import sys
import unittest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeEpisodeGenerator import UnifiedDreamscapeGenerator

class TestUnifiedDreamscapeGenerator(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize UnifiedDreamscapeGenerator
        self.generator = UnifiedDreamscapeGenerator(
            output_dir=self.test_output_dir,
            max_dreamscapes=100,
            retention_days=7
        )
        
        # Test data
        self.test_dreamscape = {
            "id": "test_dreamscape_1",
            "timestamp": datetime.now().isoformat(),
            "type": "narrative",
            "data": {
                "title": "Test Dreamscape",
                "description": "A test dreamscape description",
                "elements": [
                    {
                        "type": "character",
                        "name": "Test Character",
                        "description": "A test character"
                    },
                    {
                        "type": "setting",
                        "name": "Test Setting",
                        "description": "A test setting"
                    }
                ],
                "mood": "mysterious",
                "theme": "adventure"
            }
        }
    
    def test_initialization(self):
        """Test if UnifiedDreamscapeGenerator initializes correctly."""
        self.assertIsNotNone(self.generator)
        self.assertEqual(self.generator.max_dreamscapes, 100)
        self.assertEqual(self.generator.retention_days, 7)
        self.assertTrue(os.path.exists(self.generator.output_dir))
        self.assertIsNotNone(self.generator.logger)
    
    def test_generate_dreamscape(self):
        """Test basic dreamscape generation functionality."""
        # Mock generation response
        mock_response = {
            "id": "test_dreamscape_1",
            "content": self.test_dreamscape,
            "metadata": {
                "generation_time": 1.5,
                "model": "dreamscape_model"
            }
        }
        
        with patch.object(self.generator, '_generate_content', return_value=mock_response):
            # Generate dreamscape
            dreamscape = self.generator.generate_dreamscape(
                prompt="Create a mysterious adventure",
                parameters={"mood": "mysterious", "theme": "adventure"}
            )
            
            # Verify dreamscape
            self.assertEqual(dreamscape["id"], "test_dreamscape_1")
            self.assertEqual(dreamscape["type"], "narrative")
            self.assertEqual(dreamscape["data"]["mood"], "mysterious")
    
    def test_generate_dreamscape_with_elements(self):
        """Test dreamscape generation with specific elements."""
        # Define element requirements
        elements = [
            {"type": "character", "role": "protagonist"},
            {"type": "setting", "environment": "fantasy"}
        ]
        
        # Mock generation response
        mock_response = {
            "id": "test_dreamscape_2",
            "content": {
                "id": "test_dreamscape_2",
                "type": "narrative",
                "data": {
                    "title": "Fantasy Adventure",
                    "elements": elements
                }
            }
        }
        
        with patch.object(self.generator, '_generate_content', return_value=mock_response):
            # Generate dreamscape with elements
            dreamscape = self.generator.generate_dreamscape(
                prompt="Create a fantasy adventure",
                elements=elements
            )
            
            # Verify dreamscape elements
            self.assertEqual(len(dreamscape["data"]["elements"]), 2)
            self.assertEqual(dreamscape["data"]["elements"][0]["type"], "character")
            self.assertEqual(dreamscape["data"]["elements"][1]["type"], "setting")
    
    def test_generate_dreamscape_with_style(self):
        """Test dreamscape generation with specific style."""
        # Define style parameters
        style = {
            "tone": "dark",
            "pacing": "fast",
            "complexity": "high"
        }
        
        # Mock generation response
        mock_response = {
            "id": "test_dreamscape_3",
            "content": {
                "id": "test_dreamscape_3",
                "type": "narrative",
                "data": {
                    "title": "Dark Fantasy",
                    "style": style
                }
            }
        }
        
        with patch.object(self.generator, '_generate_content', return_value=mock_response):
            # Generate dreamscape with style
            dreamscape = self.generator.generate_dreamscape(
                prompt="Create a dark fantasy story",
                style=style
            )
            
            # Verify dreamscape style
            self.assertEqual(dreamscape["data"]["style"]["tone"], "dark")
            self.assertEqual(dreamscape["data"]["style"]["pacing"], "fast")
    
    def test_generate_dreamscape_with_constraints(self):
        """Test dreamscape generation with constraints."""
        # Define constraints
        constraints = {
            "max_length": 1000,
            "required_elements": ["conflict", "resolution"],
            "forbidden_elements": ["violence", "romance"]
        }
        
        # Mock generation response
        mock_response = {
            "id": "test_dreamscape_4",
            "content": {
                "id": "test_dreamscape_4",
                "type": "narrative",
                "data": {
                    "title": "Family Adventure",
                    "constraints": constraints
                }
            }
        }
        
        with patch.object(self.generator, '_generate_content', return_value=mock_response):
            # Generate dreamscape with constraints
            dreamscape = self.generator.generate_dreamscape(
                prompt="Create a family-friendly adventure",
                constraints=constraints
            )
            
            # Verify dreamscape constraints
            self.assertEqual(dreamscape["data"]["constraints"]["max_length"], 1000)
            self.assertIn("conflict", dreamscape["data"]["constraints"]["required_elements"])
    
    def test_save_dreamscape(self):
        """Test dreamscape saving functionality."""
        # Save dreamscape
        file_path = self.generator.save_dreamscape(self.test_dreamscape)
        
        # Verify file exists
        self.assertTrue(os.path.exists(file_path))
        
        # Verify file content
        with open(file_path, 'r') as f:
            saved_content = json.load(f)
            self.assertEqual(saved_content["id"], "test_dreamscape_1")
            self.assertEqual(saved_content["type"], "narrative")
    
    def test_load_dreamscape(self):
        """Test dreamscape loading functionality."""
        # Save dreamscape
        file_path = self.generator.save_dreamscape(self.test_dreamscape)
        
        # Load dreamscape
        loaded_dreamscape = self.generator.load_dreamscape(file_path)
        
        # Verify loaded dreamscape
        self.assertEqual(loaded_dreamscape["id"], "test_dreamscape_1")
        self.assertEqual(loaded_dreamscape["type"], "narrative")
        self.assertEqual(loaded_dreamscape["data"]["title"], "Test Dreamscape")
    
    def test_list_dreamscapes(self):
        """Test dreamscape listing functionality."""
        # Generate multiple dreamscapes
        dreamscapes = []
        for i in range(3):
            dreamscape = self.test_dreamscape.copy()
            dreamscape["id"] = f"test_dreamscape_{i}"
            dreamscape["data"]["title"] = f"Test Dreamscape {i}"
            dreamscapes.append(self.generator.save_dreamscape(dreamscape))
        
        # List dreamscapes
        dreamscape_list = self.generator.list_dreamscapes()
        
        # Verify list
        self.assertEqual(len(dreamscape_list), 3)
        self.assertEqual(len(dreamscapes), 3)
    
    def test_search_dreamscapes(self):
        """Test dreamscape search functionality."""
        # Generate dreamscapes with different themes
        themes = ["adventure", "mystery", "romance"]
        for theme in themes:
            dreamscape = self.test_dreamscape.copy()
            dreamscape["id"] = f"test_dreamscape_{theme}"
            dreamscape["data"]["theme"] = theme
            self.generator.save_dreamscape(dreamscape)
        
        # Search dreamscapes
        search_results = self.generator.search_dreamscapes("mystery")
        
        # Verify search
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0]["data"]["theme"], "mystery")
    
    def test_cleanup_old_dreamscapes(self):
        """Test old dreamscape cleanup functionality."""
        # Create old dreamscape
        old_dreamscape = self.test_dreamscape.copy()
        old_dreamscape["timestamp"] = (datetime.now() - timedelta(days=8)).isoformat()
        self.generator.save_dreamscape(old_dreamscape)
        
        # Create recent dreamscape
        recent_dreamscape = self.test_dreamscape.copy()
        recent_dreamscape["id"] = "recent_dreamscape"
        recent_dreamscape["timestamp"] = datetime.now().isoformat()
        self.generator.save_dreamscape(recent_dreamscape)
        
        # Cleanup old dreamscapes
        self.generator.cleanup_old_dreamscapes()
        
        # Verify cleanup
        dreamscape_files = os.listdir(self.test_output_dir)
        self.assertEqual(len(dreamscape_files), 1)
        self.assertIn("recent_dreamscape", dreamscape_files[0])
    
    def test_validate_dreamscape(self):
        """Test dreamscape validation functionality."""
        # Create valid dreamscape
        valid_dreamscape = self.test_dreamscape.copy()
        
        # Create invalid dreamscape
        invalid_dreamscape = {
            "id": "test_dreamscape_2"
            # Missing required fields
        }
        
        # Verify validation
        self.assertTrue(self.generator._validate_dreamscape(valid_dreamscape))
        self.assertFalse(self.generator._validate_dreamscape(invalid_dreamscape))
    
    def test_preprocess_dreamscape(self):
        """Test dreamscape preprocessing functionality."""
        # Create dreamscape with preprocessing needed
        dreamscape = self.test_dreamscape.copy()
        dreamscape["data"]["title"] = "  Test Dreamscape  "  # Extra whitespace
        
        # Preprocess dreamscape
        processed_dreamscape = self.generator._preprocess_dreamscape(dreamscape)
        
        # Verify preprocessing
        self.assertEqual(processed_dreamscape["data"]["title"], "Test Dreamscape")
    
    def test_postprocess_dreamscape(self):
        """Test dreamscape postprocessing functionality."""
        # Create dreamscape with postprocessing needed
        dreamscape = self.test_dreamscape.copy()
        dreamscape["data"]["description"] = "  Test description  "  # Extra whitespace
        
        # Postprocess dreamscape
        processed_dreamscape = self.generator._postprocess_dreamscape(dreamscape)
        
        # Verify postprocessing
        self.assertEqual(processed_dreamscape["data"]["description"], "Test description")
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

if __name__ == '__main__':
    unittest.main() 

import os
import sys
import unittest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.AletheiaFeedbackLoopManager import AletheiaFeedbackLoopManager

class TestAletheiaFeedbackLoopManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize AletheiaFeedbackLoopManager
        self.feedback_manager = AletheiaFeedbackLoopManager(
            output_dir=self.test_output_dir,
            max_feedback_entries=1000,
            feedback_retention_days=7
        )
        
        # Test data
        self.test_feedback = {
            "id": "test_feedback_1",
            "timestamp": datetime.now().isoformat(),
            "type": "user_feedback",
            "data": {
                "user_id": "test_user_1",
                "message": "Test feedback message",
                "rating": 5,
                "category": "response_quality"
            }
        }
    
    def test_initialization(self):
        """Test if AletheiaFeedbackLoopManager initializes correctly."""
        self.assertIsNotNone(self.feedback_manager)
        self.assertEqual(self.feedback_manager.max_feedback_entries, 1000)
        self.assertEqual(self.feedback_manager.feedback_retention_days, 7)
        self.assertTrue(os.path.exists(self.feedback_manager.output_dir))
        self.assertIsNotNone(self.feedback_manager.logger)
    
    def test_store_feedback(self):
        """Test feedback storage functionality."""
        # Store feedback
        feedback_id = self.feedback_manager.store_feedback(self.test_feedback)
        
        # Verify feedback was stored
        self.assertEqual(feedback_id, "test_feedback_1")
        self.assertIn(feedback_id, self.feedback_manager.feedback_data)
        self.assertEqual(self.feedback_manager.feedback_data[feedback_id]["type"], "user_feedback")
    
    def test_get_feedback(self):
        """Test feedback retrieval functionality."""
        # Store feedback
        feedback_id = self.feedback_manager.store_feedback(self.test_feedback)
        
        # Get feedback
        feedback = self.feedback_manager.get_feedback(feedback_id)
        
        # Verify feedback data
        self.assertEqual(feedback["id"], feedback_id)
        self.assertEqual(feedback["type"], "user_feedback")
        self.assertEqual(feedback["data"]["rating"], 5)
    
    def test_update_feedback(self):
        """Test feedback update functionality."""
        # Store feedback
        feedback_id = self.feedback_manager.store_feedback(self.test_feedback)
        
        # Update feedback
        update_data = {
            "data": {
                "rating": 4,
                "message": "Updated feedback message"
            }
        }
        self.feedback_manager.update_feedback(feedback_id, update_data)
        
        # Verify update
        feedback = self.feedback_manager.get_feedback(feedback_id)
        self.assertEqual(feedback["data"]["rating"], 4)
        self.assertEqual(feedback["data"]["message"], "Updated feedback message")
    
    def test_delete_feedback(self):
        """Test feedback deletion functionality."""
        # Store feedback
        feedback_id = self.feedback_manager.store_feedback(self.test_feedback)
        
        # Delete feedback
        self.feedback_manager.delete_feedback(feedback_id)
        
        # Verify deletion
        self.assertNotIn(feedback_id, self.feedback_manager.feedback_data)
        with self.assertRaises(KeyError):
            self.feedback_manager.get_feedback(feedback_id)
    
    def test_list_feedback(self):
        """Test feedback listing functionality."""
        # Store multiple feedback entries
        feedback_entries = []
        for i in range(3):
            feedback = self.test_feedback.copy()
            feedback["id"] = f"test_feedback_{i}"
            feedback["data"]["rating"] = i + 1
            feedback_entries.append(self.feedback_manager.store_feedback(feedback))
        
        # List feedback
        feedback_list = self.feedback_manager.list_feedback()
        
        # Verify list
        self.assertEqual(len(feedback_list), 3)
        self.assertEqual(len(feedback_entries), 3)
    
    def test_filter_feedback(self):
        """Test feedback filtering functionality."""
        # Store feedback with different categories
        categories = ["response_quality", "system_performance", "user_experience"]
        for category in categories:
            feedback = self.test_feedback.copy()
            feedback["id"] = f"test_feedback_{category}"
            feedback["data"]["category"] = category
            self.feedback_manager.store_feedback(feedback)
        
        # Filter feedback by category
        filtered_feedback = self.feedback_manager.filter_feedback(
            category="response_quality"
        )
        
        # Verify filter
        self.assertEqual(len(filtered_feedback), 1)
        self.assertEqual(filtered_feedback[0]["data"]["category"], "response_quality")
    
    def test_analyze_feedback(self):
        """Test feedback analysis functionality."""
        # Store feedback with different ratings
        ratings = [1, 2, 3, 4, 5]
        for rating in ratings:
            feedback = self.test_feedback.copy()
            feedback["id"] = f"test_feedback_{rating}"
            feedback["data"]["rating"] = rating
            self.feedback_manager.store_feedback(feedback)
        
        # Analyze feedback
        analysis = self.feedback_manager.analyze_feedback()
        
        # Verify analysis
        self.assertIn("average_rating", analysis)
        self.assertIn("rating_distribution", analysis)
        self.assertIn("feedback_count", analysis)
    
    def test_generate_feedback_report(self):
        """Test feedback report generation."""
        # Store feedback
        self.feedback_manager.store_feedback(self.test_feedback)
        
        # Generate report
        report_path = self.feedback_manager.generate_feedback_report()
        
        # Verify report
        self.assertTrue(os.path.exists(report_path))
        
        with open(report_path, 'r') as f:
            report_content = f.read()
            self.assertIn("Feedback Analysis Report", report_content)
            self.assertIn("test_feedback_1", report_content)
    
    def test_cleanup_old_feedback(self):
        """Test old feedback cleanup functionality."""
        # Store old feedback
        old_feedback = self.test_feedback.copy()
        old_feedback["timestamp"] = (datetime.now() - timedelta(days=8)).isoformat()
        self.feedback_manager.store_feedback(old_feedback)
        
        # Store recent feedback
        recent_feedback = self.test_feedback.copy()
        recent_feedback["id"] = "recent_feedback"
        recent_feedback["timestamp"] = datetime.now().isoformat()
        self.feedback_manager.store_feedback(recent_feedback)
        
        # Cleanup old feedback
        self.feedback_manager.cleanup_old_feedback()
        
        # Verify cleanup
        self.assertNotIn("test_feedback_1", self.feedback_manager.feedback_data)
        self.assertIn("recent_feedback", self.feedback_manager.feedback_data)
    
    def test_feedback_aggregation(self):
        """Test feedback aggregation functionality."""
        # Store feedback with different categories and ratings
        categories = ["response_quality", "system_performance"]
        ratings = [4, 5]
        
        for category in categories:
            for rating in ratings:
                feedback = self.test_feedback.copy()
                feedback["id"] = f"test_feedback_{category}_{rating}"
                feedback["data"]["category"] = category
                feedback["data"]["rating"] = rating
                self.feedback_manager.store_feedback(feedback)
        
        # Aggregate feedback
        aggregation = self.feedback_manager.aggregate_feedback()
        
        # Verify aggregation
        self.assertIn("response_quality", aggregation)
        self.assertIn("system_performance", aggregation)
        self.assertEqual(len(aggregation["response_quality"]), 2)
        self.assertEqual(len(aggregation["system_performance"]), 2)
    
    def test_feedback_export(self):
        """Test feedback export functionality."""
        # Store feedback
        self.feedback_manager.store_feedback(self.test_feedback)
        
        # Export feedback
        export_path = self.feedback_manager.export_feedback()
        
        # Verify export
        self.assertTrue(os.path.exists(export_path))
        
        with open(export_path, 'r') as f:
            export_data = json.load(f)
            self.assertEqual(len(export_data), 1)
            self.assertEqual(export_data[0]["id"], "test_feedback_1")
    
    def test_feedback_import(self):
        """Test feedback import functionality."""
        # Create test export data
        export_data = [self.test_feedback]
        export_path = os.path.join(self.test_output_dir, "test_export.json")
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f)
        
        # Import feedback
        self.feedback_manager.import_feedback(export_path)
        
        # Verify import
        feedback = self.feedback_manager.get_feedback("test_feedback_1")
        self.assertEqual(feedback["type"], "user_feedback")
        self.assertEqual(feedback["data"]["rating"], 5)
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

if __name__ == '__main__':
    unittest.main() 

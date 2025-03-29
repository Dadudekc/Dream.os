import json
import os
import unittest
from unittest.mock import patch, MagicMock

# Import the class to test
from core.AletheiaFeedbackLoopManager import AletheiaFeedbackLoopManager

# Create dummy social_config for testing
class DummySocialConfig:
    def __init__(self):
        self.rate_limits = {
            "linkedin": {
                "post": {
                    "cooldown": 100  # initial value for testing
                }
            }
        }

# Dummy function to replace write_json_log
def dummy_write_json_log(platform, result, tags, ai_output, event_type):
    # Simply record the log in a dummy variable (or print for debugging)
    dummy_write_json_log.logged = {
        "platform": platform,
        "result": result,
        "tags": tags,
        "ai_output": ai_output,
        "event_type": event_type
    }

class TestAletheiaFeedbackLoopManager(unittest.TestCase):
    def setUp(self):
        # Patch social_config and write_json_log in the module where AletheiaFeedbackLoopManager is defined.
        patcher1 = patch('core.AletheiaFeedbackLoopManager.social_config', new=DummySocialConfig())
        self.addCleanup(patcher1.stop)
        self.mock_social_config = patcher1.start()
        
        patcher2 = patch('core.AletheiaFeedbackLoopManager.write_json_log', new=dummy_write_json_log)
        self.addCleanup(patcher2.stop)
        patcher2.start()

        # Create an instance of the feedback loop manager with a dummy log directory
        self.manager = AletheiaFeedbackLoopManager(log_dir="dummy/log/dir", verbose=True)

    def test_calculate_success_rate(self):
        # Test _calculate_success_rate with a sample summary
        summary = {"total_entries": 10, "successful": 8}
        success_rate = self.manager._calculate_success_rate(summary)
        self.assertAlmostEqual(success_rate, 0.8)

        # Also test division by one entry (to avoid division by zero)
        summary = {"total_entries": 1, "successful": 0}
        success_rate = self.manager._calculate_success_rate(summary)
        self.assertEqual(success_rate, 0)

    def test_get_top_tags(self):
        # Test _get_top_tags with a sample tag_distribution
        summary = {"tag_distribution": {"tagA": 5, "tagB": 2, "tagC": 10, "tagD": 1}}
        top_tags = self.manager._get_top_tags(summary, result_type="failed", top_n=3)
        # Expected sorted order: tagC (10), tagA (5), tagB (2)
        self.assertEqual(top_tags, [("tagC", 10), ("tagA", 5), ("tagB", 2)])

    def test_auto_adjust_rate_limits(self):
        # Setup a dummy top_failed_tags list containing a linkedin tag
        top_failed_tags = [("linkedin_post", 5), ("other", 2)]
        # Grab the initial cooldown from dummy social_config
        initial_cooldown = self.mock_social_config.rate_limits["linkedin"]["post"]["cooldown"]
        self.manager._auto_adjust_rate_limits(top_failed_tags)
        # Check that the cooldown has increased by a factor of 1.5 but does not exceed 3600.
        new_cooldown = self.mock_social_config.rate_limits["linkedin"]["post"]["cooldown"]
        self.assertEqual(new_cooldown, min(initial_cooldown * 1.5, 3600))

    def test_generate_feedback_loops(self):
        # Simulate analyzer.summarize() to return a test summary
        test_summary = {
            "total_entries": 20,
            "successful": 10,
            "tag_distribution": {"linkedin_post": 5, "other": 3}
        }
        self.manager.analyzer.summarize = MagicMock(return_value=test_summary)
        
        # Run the feedback loop generation
        feedback = self.manager.generate_feedback_loops()
        
        # Since success rate is 50% (< 75%), expect a high failure recommendation
        self.assertIn("🚨 High failure rate detected. Consider reducing post frequency or adjusting content.", feedback["new_feedback_loops"])
        
        # For the linkedin_post tag count 5 (> 3), expect a tag-specific recommendation
        self.assertTrue(any("linkedin_post" in rec for rec in feedback["new_feedback_loops"]))
        
        # Verify that the analyzer.summarize() was called
        self.manager.analyzer.summarize.assert_called_once()
        
        # Verify that the write_json_log function was called and logged a payload
        self.assertTrue(hasattr(dummy_write_json_log, "logged"))
        logged_payload = json.loads(dummy_write_json_log.logged["ai_output"])
        self.assertIn("new_feedback_loops", logged_payload)
    
    def test_export_feedback_report(self):
        # Test the export_feedback_report method by patching generate_feedback_loops to return a test value
        test_feedback = {"new_feedback_loops": ["test recommendation"], "optimized_processes": []}
        self.manager.generate_feedback_loops = MagicMock(return_value=test_feedback)
        
        output_file = "test_feedback_report.json"
        # Ensure no file exists before
        if os.path.exists(output_file):
            os.remove(output_file)
        
        # Run the export function
        self.manager.export_feedback_report(output_file=output_file)
        
        # Check that the file now exists and contains the expected JSON
        self.assertTrue(os.path.exists(output_file))
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, test_feedback)
        
        # Cleanup
        os.remove(output_file)

if __name__ == "__main__":
    unittest.main()
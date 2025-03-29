import os
import sys
import unittest
from datetime import datetime, timedelta
import json

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.NarrativeAnalytics import NarrativeAnalytics

class TestNarrativeAnalytics(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.analytics = NarrativeAnalytics()
        self.test_data = {
            'system_evolution': [
                {
                    'timestamp': datetime.now().isoformat(),
                    'architect_tier': 3,
                    'active_domains': ['AI', 'Data Science', 'Machine Learning'],
                    'unlocked_protocols': ['GPT-4', 'BERT', 'Transformer'],
                    'total_skills': 15,
                    'completed_quests': 5
                }
            ],
            'domain_expansion': {
                'AI': {'unlocked_at': (datetime.now() - timedelta(days=30)).isoformat()},
                'Data Science': {'unlocked_at': (datetime.now() - timedelta(days=20)).isoformat()},
                'Machine Learning': {'unlocked_at': (datetime.now() - timedelta(days=10)).isoformat()}
            },
            'protocol_unlocks': [
                {'protocol': 'GPT-4', 'unlocked_at': (datetime.now() - timedelta(days=25)).isoformat()},
                {'protocol': 'BERT', 'unlocked_at': (datetime.now() - timedelta(days=15)).isoformat()},
                {'protocol': 'Transformer', 'unlocked_at': (datetime.now() - timedelta(days=5)).isoformat()}
            ],
            'narrative_events': {
                'milestones': [
                    {'timestamp': (datetime.now() - timedelta(days=28)).isoformat(), 'description': 'First AI model deployed'},
                    {'timestamp': (datetime.now() - timedelta(days=18)).isoformat(), 'description': 'Data pipeline established'}
                ],
                'achievements': [
                    {'timestamp': (datetime.now() - timedelta(days=22)).isoformat(), 'description': 'Model accuracy > 95%'},
                    {'timestamp': (datetime.now() - timedelta(days=12)).isoformat(), 'description': 'Pipeline optimization complete'}
                ]
            }
        }

    def test_initialization(self):
        """Test if the analytics class initializes correctly."""
        self.assertIsNotNone(self.analytics)
        self.assertTrue(os.path.exists(self.analytics.analytics_dir))
        self.assertTrue(os.path.exists(self.analytics.visualizations_dir))

    def test_update_analytics(self):
        """Test updating analytics with test data."""
        self.analytics.update_analytics(self.test_data)
        
        # Check if analytics data was saved
        analytics_file = os.path.join(self.analytics.analytics_dir, 'analytics_data.json')
        self.assertTrue(os.path.exists(analytics_file))
        
        # Load and verify the data
        with open(analytics_file, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(len(saved_data['system_evolution']), 1)
        self.assertEqual(len(saved_data['domain_expansion']), 3)
        self.assertEqual(len(saved_data['protocol_unlocks']), 3)
        self.assertEqual(len(saved_data['narrative_events']['milestones']), 2)
        self.assertEqual(len(saved_data['narrative_events']['achievements']), 2)

    def test_generate_visualizations(self):
        """Test if visualizations are generated correctly."""
        self.analytics.update_analytics(self.test_data)
        self.analytics._generate_visualizations()
        
        # Check if visualization files were created
        self.assertTrue(os.path.exists(os.path.join(self.analytics.visualizations_dir, 'system_evolution.png')))
        self.assertTrue(os.path.exists(os.path.join(self.analytics.visualizations_dir, 'skill_progression.png')))
        self.assertTrue(os.path.exists(os.path.join(self.analytics.visualizations_dir, 'domain_network.png')))
        self.assertTrue(os.path.exists(os.path.join(self.analytics.visualizations_dir, 'narrative_events.png')))
        self.assertTrue(os.path.exists(os.path.join(self.analytics.visualizations_dir, 'protocol_timeline.png')))

    def test_generate_analytics_report(self):
        """Test if the analytics report is generated correctly."""
        self.analytics.update_analytics(self.test_data)
        self.analytics._generate_visualizations()
        
        report_path = self.analytics.generate_analytics_report()
        
        # Check if report was generated
        self.assertTrue(os.path.exists(report_path))
        
        # Check if report contains expected content
        with open(report_path, 'r') as f:
            report_content = f.read()
            
        self.assertIn('System Analytics Report', report_content)
        self.assertIn('System Evolution', report_content)
        self.assertIn('Skill Progression', report_content)
        self.assertIn('Domain Network', report_content)
        self.assertIn('Narrative Events', report_content)
        self.assertIn('Protocol Timeline', report_content)

    def tearDown(self):
        """Clean up after each test."""
        # Remove test files and directories
        if os.path.exists(self.analytics.analytics_dir):
            for file in os.listdir(self.analytics.analytics_dir):
                os.remove(os.path.join(self.analytics.analytics_dir, file))
            os.rmdir(self.analytics.analytics_dir)
        
        if os.path.exists(self.analytics.visualizations_dir):
            for file in os.listdir(self.analytics.visualizations_dir):
                os.remove(os.path.join(self.analytics.visualizations_dir, file))
            os.rmdir(self.analytics.visualizations_dir)

if __name__ == '__main__':
    unittest.main() 
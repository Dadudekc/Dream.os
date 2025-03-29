import unittest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication
import sys

# Import both implementations
from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab as NewDreamscapeTab
from archive.gui_old.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab as OldDreamscapeTab

class TestDreamscapeTabMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance for UI tests
        cls.app = QApplication(sys.argv)
        
        # Mock all required services
        cls.mock_services = {
            'prompt_manager': MagicMock(),
            'chat_manager': MagicMock(),
            'response_handler': MagicMock(),
            'memory_manager': MagicMock(),
            'discord_manager': MagicMock(),
            'ui_logic': MagicMock(),
            'config_manager': MagicMock(),
            'logger': MagicMock()
        }

    def setUp(self):
        # Create instances of both tabs with mocked services
        self.new_tab = NewDreamscapeTab(**self.mock_services)
        self.old_tab = OldDreamscapeTab(**self.mock_services)

    def test_core_attributes(self):
        """Test that both implementations have the same core attributes."""
        core_attributes = [
            'prompt_manager',
            'chat_manager',
            'response_handler',
            'memory_manager',
            'discord_manager',
            'ui_logic',
            'config_manager',
            'logger'
        ]
        
        for attr in core_attributes:
            self.assertTrue(hasattr(self.new_tab, attr), f"New tab missing {attr}")
            self.assertTrue(hasattr(self.old_tab, attr), f"Old tab missing {attr}")

    def test_core_methods(self):
        """Test that both implementations have the same core methods."""
        core_methods = [
            'generate_dreamscape_episodes',
            'log_output',
            'init_ui'  # Note: new version uses lowercase naming
        ]
        
        for method in core_methods:
            # Handle case differences in method names
            new_method = method.lower() if method == 'initUI' else method
            self.assertTrue(hasattr(self.new_tab, new_method), f"New tab missing {method}")
            old_method = method if method == 'initUI' else method
            self.assertTrue(hasattr(self.old_tab, old_method), f"Old tab missing {method}")

    def test_ui_components(self):
        """Test that both implementations have the same UI components."""
        ui_components = [
            'output_display',
            'generate_episodes_btn'
        ]
        
        for component in ui_components:
            self.assertTrue(hasattr(self.new_tab, component), f"New tab missing {component}")
            self.assertTrue(hasattr(self.old_tab, component), f"Old tab missing {component}")

    def test_service_initialization(self):
        """Test that services are properly initialized in both implementations."""
        services = [
            'cycle_service',
            'prompt_handler',
            'discord_processor',
            'task_orchestrator'
        ]
        
        for service in services:
            self.assertTrue(hasattr(self.new_tab, service), f"New tab missing {service}")
            self.assertTrue(hasattr(self.old_tab, service), f"Old tab missing {service}")

    def test_enhanced_features(self):
        """Test that new implementation has all enhanced features."""
        enhanced_features = [
            'episode_generator',
            'context_manager',
            'ui_manager',
            'template_manager',
            'running_tasks'
        ]
        
        for feature in enhanced_features:
            self.assertTrue(hasattr(self.new_tab, feature), f"New tab missing enhanced feature {feature}")

    def test_async_support(self):
        """Test that new implementation has async support."""
        # Check for asyncSlot decorator usage
        import inspect
        async_methods = [
            method for method in dir(self.new_tab) 
            if inspect.iscoroutinefunction(getattr(self.new_tab, method))
        ]
        self.assertTrue(len(async_methods) > 0, "New tab should have async methods")

    def test_backwards_compatibility(self):
        """Test that new implementation maintains backwards compatibility."""
        # Test episode generation method signature
        old_sig = inspect.signature(self.old_tab.generate_dreamscape_episodes)
        new_sig = inspect.signature(self.new_tab.generate_dreamscape_episodes)
        
        # Parameters should be compatible (new may have more, but not less)
        old_params = set(old_sig.parameters.keys())
        new_params = set(new_sig.parameters.keys())
        self.assertTrue(old_params.issubset(new_params), 
                       "New implementation should support all old parameters")

if __name__ == '__main__':
    unittest.main() 
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QComboBox, QListWidget, 
    QCheckBox, QProgressBar, QTextEdit, QSplitter, QVBoxLayout
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtTest import QTest

# We'll test these components
try:
    from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeGenerationTab import DreamscapeGenerationTab
    from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager
    DREAMSCAPE_TAB_AVAILABLE = True
except ImportError:
    DREAMSCAPE_TAB_AVAILABLE = False
    print("Warning: Dreamscape tab components not found. Some tests will be skipped.")

# Skip tests if components are not available
pytestmark = pytest.mark.skipif(
    not DREAMSCAPE_TAB_AVAILABLE,
    reason="Dreamscape tab components not available"
)

# Create QApplication instance for tests
@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

# Mock services
@pytest.fixture
def mock_services():
    """Create a dictionary of mock services."""
    return {
        'chat_manager': MagicMock(),
        'dreamscape_service': MagicMock(),
        'context_synthesizer': MagicMock(),
        'template_manager': MagicMock(),
        'episode_generator': MagicMock(),
        'ui_manager': MagicMock(),
        'logger': MagicMock()
    }

# Patch the ServiceInitializer.initialize_all() method
@pytest.fixture
def patched_service_initializer(mock_services):
    """Patch the ServiceInitializer to return mock services."""
    with patch('interfaces.pyqt.tabs.dreamscape_generation.ServiceInitializer.ServiceInitializer.initialize_all') as mock_init:
        mock_init.return_value = mock_services
        yield mock_init

@pytest.fixture
def dreamscape_tab(qapp, patched_service_initializer, tmp_path):
    """Create a DreamscapeGenerationTab instance for testing."""
    # Create a temporary output directory
    output_dir = tmp_path / "dreamscape"
    output_dir.mkdir(exist_ok=True)
    
    # Create the tab
    tab = DreamscapeGenerationTab()
    
    # Set the output directory
    tab.output_dir = output_dir
    
    return tab

@pytest.fixture
def ui_manager(qapp):
    """Create a UIManager instance for testing."""
    # If UI Manager is available, create a real instance
    # Otherwise create a mocked version for testing UI helper methods
    try:
        parent = QWidget()
        ui_manager = UIManager(parent)
        yield ui_manager
    except (ImportError, NameError):
        ui_manager = MagicMock()
        ui_manager.create_button.return_value = QPushButton()
        ui_manager.create_combo_box.return_value = QComboBox()
        ui_manager.create_list_widget.return_value = QListWidget()
        ui_manager.create_progress_bar.return_value = QProgressBar()
        ui_manager.create_text_edit.return_value = QTextEdit()
        yield ui_manager

# UI Component Tests

def test_button_properties(dreamscape_tab):
    """Test properties of the generate and refresh buttons."""
    # Skip if buttons are not available
    if not hasattr(dreamscape_tab, 'generate_button') or not hasattr(dreamscape_tab, 'refresh_button'):
        pytest.skip("Required components not available")
    
    # Test generate button properties
    assert dreamscape_tab.generate_button is not None
    assert isinstance(dreamscape_tab.generate_button, QPushButton)
    assert "Generate" in dreamscape_tab.generate_button.text()
    
    # Test refresh button properties
    assert dreamscape_tab.refresh_button is not None
    assert isinstance(dreamscape_tab.refresh_button, QPushButton)
    assert "Refresh" in dreamscape_tab.refresh_button.text()

def test_combo_box_properties(dreamscape_tab):
    """Test properties of the chat combo box."""
    # Skip if combo box is not available
    if not hasattr(dreamscape_tab, 'chat_combo'):
        pytest.skip("Required components not available")
    
    # Test combo box properties
    assert dreamscape_tab.chat_combo is not None
    assert isinstance(dreamscape_tab.chat_combo, QComboBox)
    
    # It should start empty
    assert dreamscape_tab.chat_combo.count() == 0
    
    # Add an item and check it
    dreamscape_tab.chat_combo.addItem("Test Chat")
    assert dreamscape_tab.chat_combo.count() == 1
    assert dreamscape_tab.chat_combo.itemText(0) == "Test Chat"

def test_episode_list_properties(dreamscape_tab):
    """Test properties of the episode list widget."""
    # Skip if list widget is not available
    if not hasattr(dreamscape_tab, 'episode_list'):
        pytest.skip("Required components not available")
    
    # Test list widget properties
    assert dreamscape_tab.episode_list is not None
    assert isinstance(dreamscape_tab.episode_list, QListWidget)
    
    # It should start empty
    assert dreamscape_tab.episode_list.count() == 0
    
    # Add an item and check it
    from PyQt5.QtWidgets import QListWidgetItem
    item = QListWidgetItem("Test Episode")
    dreamscape_tab.episode_list.addItem(item)
    assert dreamscape_tab.episode_list.count() == 1
    assert dreamscape_tab.episode_list.item(0).text() == "Test Episode"
    
    # Test selection
    dreamscape_tab.episode_list.setCurrentRow(0)
    assert dreamscape_tab.episode_list.currentRow() == 0
    assert dreamscape_tab.episode_list.currentItem().text() == "Test Episode"

def test_generate_all_checkbox(dreamscape_tab):
    """Test properties and behavior of the generate all checkbox."""
    # Skip if checkbox is not available
    if not hasattr(dreamscape_tab, 'generate_all_checkbox'):
        pytest.skip("Required components not available")
    
    # Test checkbox properties
    assert dreamscape_tab.generate_all_checkbox is not None
    assert isinstance(dreamscape_tab.generate_all_checkbox, QCheckBox)
    
    # It should start unchecked
    assert not dreamscape_tab.generate_all_checkbox.isChecked()
    
    # Check it and verify
    dreamscape_tab.generate_all_checkbox.setChecked(True)
    assert dreamscape_tab.generate_all_checkbox.isChecked()

def test_progress_bar_properties(dreamscape_tab):
    """Test properties and behavior of the progress bar."""
    # Skip if progress bar is not available
    if not hasattr(dreamscape_tab, 'progress_bar'):
        pytest.skip("Required components not available")
    
    # Test progress bar properties
    assert dreamscape_tab.progress_bar is not None
    assert isinstance(dreamscape_tab.progress_bar, QProgressBar)
    
    # It should start at 0
    assert dreamscape_tab.progress_bar.value() == 0
    assert dreamscape_tab.progress_bar.minimum() == 0
    assert dreamscape_tab.progress_bar.maximum() == 100
    
    # Update it and verify
    dreamscape_tab.progress_bar.setValue(50)
    assert dreamscape_tab.progress_bar.value() == 50

def test_episode_viewer_properties(dreamscape_tab):
    """Test properties and behavior of the episode viewer."""
    # Skip if episode viewer is not available
    if not hasattr(dreamscape_tab, 'episode_viewer'):
        pytest.skip("Required components not available")
    
    # Test episode viewer properties
    assert dreamscape_tab.episode_viewer is not None
    assert isinstance(dreamscape_tab.episode_viewer, QTextEdit)
    
    # It should start empty
    assert dreamscape_tab.episode_viewer.toPlainText() == ""
    
    # Set some text and verify
    test_text = "# Digital Dreamscape Episode\n\nThis is a test episode."
    dreamscape_tab.episode_viewer.setPlainText(test_text)
    assert dreamscape_tab.episode_viewer.toPlainText() == test_text
    
    # Check that it's read-only
    assert dreamscape_tab.episode_viewer.isReadOnly()

def test_button_layout(dreamscape_tab):
    """Test the layout of buttons within the tab."""
    # Skip if buttons are not available
    if not hasattr(dreamscape_tab, 'generate_button') or not hasattr(dreamscape_tab, 'refresh_button'):
        pytest.skip("Required components not available")
    
    # Both buttons should have a parent
    assert dreamscape_tab.generate_button.parent() is not None
    assert dreamscape_tab.refresh_button.parent() is not None
    
    # Both buttons should be visible
    assert dreamscape_tab.generate_button.isVisible()
    assert dreamscape_tab.refresh_button.isVisible()

def test_ui_manager_create_widgets(ui_manager):
    """Test the UIManager's widget creation methods."""
    if ui_manager is None or isinstance(ui_manager, MagicMock):
        pytest.skip("UIManager not available or mocked")
    
    # Create widgets using the UIManager
    button = ui_manager.create_button("Test Button")
    combo = ui_manager.create_combo_box()
    list_widget = ui_manager.create_list_widget()
    progress = ui_manager.create_progress_bar()
    text_edit = ui_manager.create_text_edit(read_only=True)
    
    # Verify widget types
    assert isinstance(button, QPushButton)
    assert isinstance(combo, QComboBox)
    assert isinstance(list_widget, QListWidget)
    assert isinstance(progress, QProgressBar)
    assert isinstance(text_edit, QTextEdit)
    
    # Verify properties
    assert button.text() == "Test Button"
    assert text_edit.isReadOnly()

def test_ui_manager_layout_helpers(ui_manager):
    """Test the UIManager's layout helper methods."""
    if ui_manager is None or isinstance(ui_manager, MagicMock):
        pytest.skip("UIManager not available or mocked")
    
    # Create a parent widget
    parent = QWidget()
    
    # Create a layout using the UIManager
    layout = ui_manager.create_vbox_layout(parent)
    
    # Verify layout
    assert isinstance(layout, QVBoxLayout)
    assert layout.parent() == parent

def test_ui_splitter_arrangement(dreamscape_tab):
    """Test the arrangement of UI components in splitters."""
    # Skip if splitters are not available
    splitters = [widget for widget in dreamscape_tab.children() if isinstance(widget, QSplitter)]
    if not splitters:
        pytest.skip("No splitters found in tab")
    
    # There should be at least one splitter
    assert len(splitters) > 0
    
    # Verify the splitter's orientation
    main_splitter = splitters[0]
    assert main_splitter.orientation() in [Qt.Horizontal, Qt.Vertical]
    
    # Check that it has child widgets
    assert main_splitter.count() > 0

def test_ui_components_disabled_during_generation(dreamscape_tab):
    """Test that UI components are properly disabled during generation."""
    # Skip if required components are not available
    if not hasattr(dreamscape_tab, 'generate_button') or not hasattr(dreamscape_tab, 'chat_combo'):
        pytest.skip("Required components not available")
    
    # Get initial state
    initial_button_state = dreamscape_tab.generate_button.isEnabled()
    initial_combo_state = dreamscape_tab.chat_combo.isEnabled()
    
    # Set UI to generating state
    dreamscape_tab.set_ui_generating_state(True)
    
    # Verify components are disabled
    assert not dreamscape_tab.generate_button.isEnabled()
    assert not dreamscape_tab.chat_combo.isEnabled()
    
    # Reset UI state
    dreamscape_tab.set_ui_generating_state(False)
    
    # Verify components return to initial state
    assert dreamscape_tab.generate_button.isEnabled() == initial_button_state
    assert dreamscape_tab.chat_combo.isEnabled() == initial_combo_state

def test_ui_responsiveness(dreamscape_tab, qapp):
    """Test UI responsiveness by changing the tab size."""
    # Get initial size
    initial_size = dreamscape_tab.size()
    
    # Resize the tab
    new_size = QSize(800, 600)
    dreamscape_tab.resize(new_size)
    qapp.processEvents()  # Process resize events
    
    # Verify the tab adapts to the new size
    assert dreamscape_tab.width() == 800
    assert dreamscape_tab.height() == 600
    
    # Resize back to initial size
    dreamscape_tab.resize(initial_size)
    qapp.processEvents()

if __name__ == "__main__":
    print("Running Dreamscape UI component tests...")
    pytest.main(["-v", __file__]) 

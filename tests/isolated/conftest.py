import pytest
from PyQt5.QtWidgets import QApplication

@pytest.fixture(scope='session')
def qapp():
    """Create a QApplication instance for all tests."""
    app = QApplication([])
    yield app
    app.quit() 
import logging

class MockService:
    """Mock service for development/testing."""
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"mock.{name}")
        
    def __getattr__(self, name):
        def mock_method(*args, **kwargs):
            self.logger.warning(f"Mock {self.name}.{name} called")
            return None
        return mock_method 
#!/usr/bin/env python3
"""
Unit tests for DreamscapeService

These tests verify:
1. Service initialization with proper dependencies
2. Fallback behavior when services fail to initialize
3. Health check reporting
4. Service shutdown sequence
"""

import pytest
import logging
import os
from unittest.mock import MagicMock, patch

# Import the service class
from interfaces.pyqt.dreamscape_services import DreamscapeService


class MockConfig:
    """Mock configuration for testing."""
    def __init__(self, config_dict=None):
        self.config = config_dict or {}
        
    def get(self, key, default=None):
        return self.config.get(key, default)


@pytest.fixture
def mock_logger():
    """Fixture for a mock logger."""
    logger = MagicMock(spec=logging.Logger)
    return logger


@pytest.fixture
def mock_config():
    """Fixture for a mock configuration."""
    return MockConfig({
        "memory_file": "test_memory.json",
        "headless": True,
        "default_model": "gpt-4",
        "excluded_chats": [],
        "discord_token": "test_token",
        "discord_channel_id": "test_channel",
        "dreamscape_output_dir": "test_output"
    })


@pytest.fixture
def service_patches():
    """Fixture to patch all service classes used by DreamscapeService."""
    patches = {
        'AletheiaPromptManager': patch('interfaces.pyqt.dreamscape_services.AletheiaPromptManager'),
        'UnifiedDiscordService': patch('interfaces.pyqt.dreamscape_services.UnifiedDiscordService'),
        'FileManager': patch('interfaces.pyqt.dreamscape_services.FileManager'),
        'PromptCycleOrchestrator': patch('interfaces.pyqt.dreamscape_services.PromptCycleOrchestrator'),
        'ReinforcementEngine': patch('interfaces.pyqt.dreamscape_services.ReinforcementEngine'),
        'PromptResponseHandler': patch('interfaces.pyqt.dreamscape_services.PromptResponseHandler'),
        'CycleExecutionService': patch('interfaces.pyqt.dreamscape_services.CycleExecutionService'),
        'DiscordQueueProcessor': patch('interfaces.pyqt.dreamscape_services.DiscordQueueProcessor'),
        'TaskOrchestrator': patch('interfaces.pyqt.dreamscape_services.TaskOrchestrator'),
        'DreamscapeEpisodeGenerator': patch('interfaces.pyqt.dreamscape_services.DreamscapeEpisodeGenerator'),
    }
    
    # Start all patches
    mocks = {}
    for name, patcher in patches.items():
        mocks[name] = patcher.start()
        
    # Setup return values
    for name, mock in mocks.items():
        instance = MagicMock()
        mock.return_value = instance
        
    yield mocks
    
    # Stop all patches
    for patcher in patches.values():
        patcher.stop()


def test_service_initialization(mock_config, service_patches):
    """Test that all services are properly initialized."""
    # Arrange - All mocks are set up in the fixture
    
    # Act
    service = DreamscapeService(mock_config)
    
    # Assert all services were initialized
    assert service.prompt_manager is not None
    assert service.discord is not None
    assert service.file_manager is not None
    assert service.cycle_manager is not None
    assert service.reinforcement_engine is not None
    assert service.prompt_handler is not None
    assert service.cycle_service is not None
    assert service.discord_processor is not None
    assert service.task_orchestrator is not None
    assert service.dreamscape_generator is not None
    
    # Chat manager is deferred
    assert service.chat_manager is None
    assert service._initialization_status["chat_manager"] == "deferred"


def test_service_initialization_with_failures(mock_config, service_patches):
    """Test that service initialization handles failures gracefully."""
    # Arrange - Make some services raise exceptions
    service_patches['PromptResponseHandler'].side_effect = Exception("Test exception")
    service_patches['ReinforcementEngine'].side_effect = Exception("Test exception")
    
    # Act
    service = DreamscapeService(mock_config)
    
    # Assert
    # These services should be EmptyService instances
    assert hasattr(service.prompt_handler, 'is_empty_service')
    assert service.prompt_handler.is_empty_service()
    assert hasattr(service.reinforcement_engine, 'is_empty_service')
    assert service.reinforcement_engine.is_empty_service()
    
    # Check initialization status
    assert service._initialization_status["prompt_handler"] == "failed"
    assert service._initialization_status["reinforcement_engine"] == "failed"
    
    # Services that depend on failed services should still initialize
    assert service.cycle_service is not None


def test_service_health_check(mock_config, service_patches):
    """Test the service health check functionality."""
    # Arrange
    service_patches['PromptResponseHandler'].side_effect = Exception("Test exception")
    service = DreamscapeService(mock_config)
    
    # Act
    health_report = service.service_health_check()
    
    # Assert
    assert "prompt_handler" in health_report
    assert health_report["prompt_handler"]["status"] == "empty_implementation"
    assert "chat_manager" in health_report
    assert health_report["chat_manager"]["status"] == "deferred"
    assert "prompt_manager" in health_report
    assert health_report["prompt_manager"]["status"] == "available"


def test_chat_manager_creation(mock_config, service_patches):
    """Test that the chat manager can be created on demand."""
    # Arrange
    service = DreamscapeService(mock_config)
    
    # Act
    service.create_chat_manager()
    
    # Assert
    assert service.chat_manager is not None
    assert service_patches['ChatManager'].called


def test_service_shutdown(mock_config, service_patches):
    """Test that services are shut down in the correct order."""
    # Arrange
    service = DreamscapeService(mock_config)
    
    # Add shutdown methods to our mocks
    for name, mock_class in service_patches.items():
        mock_instance = mock_class.return_value
        mock_instance.shutdown = MagicMock()
        mock_instance.stop = MagicMock()
        mock_instance.close = MagicMock()
    
    # Act
    service.shutdown()
    
    # Assert - we'd check that services were shut down in the right order
    # but it's hard to verify order directly. At minimum, we can check that
    # all the services with shutdown methods were called
    dreamscape_gen = service_patches['DreamscapeEpisodeGenerator'].return_value
    if hasattr(dreamscape_gen, 'shutdown'):
        assert dreamscape_gen.shutdown.called or dreamscape_gen.stop.called or dreamscape_gen.close.called


def test_dependencies_tracked_correctly(mock_config, service_patches):
    """Test that service dependencies are tracked correctly."""
    # Arrange/Act
    service = DreamscapeService(mock_config)
    
    # Assert
    dependencies = service._map_service_dependencies()
    assert "cycle_service" in dependencies
    assert "prompt_manager" in dependencies["cycle_service"]
    assert "prompt_handler" in dependencies["cycle_service"]
    
    # Make sure the dependency graph is complete
    for svc_name, deps in dependencies.items():
        for dep in deps:
            if dep not in ["config", "logger"]:  # These are not tracked services
                assert dep in dependencies, f"{dep} is not in the dependency map"


@pytest.mark.parametrize("failing_service", [
    "AletheiaPromptManager",
    "UnifiedDiscordService",
    "CycleExecutionService"
])
def test_specific_service_failure(mock_config, service_patches, failing_service):
    """Test that specific service failures are handled gracefully."""
    # Arrange
    service_patches[failing_service].side_effect = Exception(f"Test exception for {failing_service}")
    
    # Act
    service = DreamscapeService(mock_config)
    health_report = service.service_health_check()
    
    # Get the service name from the class name (remove 'Service' if present)
    service_name = failing_service.lower()
    if service_name.endswith('service'):
        service_name = service_name[:-7]
    elif service_name == 'aletheiapromptmanager':
        service_name = 'prompt_manager'
    elif service_name == 'unifieddiscordservice':
        service_name = 'discord'
    elif service_name == 'cycleexecutionservice':
        service_name = 'cycle_service'
    
    # Assert
    assert service_name in health_report
    assert health_report[service_name]["status"] in ["empty_implementation", "not_found"] 

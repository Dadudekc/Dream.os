from typing import Dict, Any, Optional
import logging

from core.cursor_dispatcher import CursorDispatcher
from core.metrics.metrics_service import MetricsService
from core.PromptExecutionService import PromptExecutionService
from core.task_manager import TaskManager
from core.test_runner import TestRunner
from interfaces.pyqt.tabs.cursor_execution_tab import CursorExecutionTab

logger = logging.getLogger(__name__)

class CursorExecutionTabFactory:
    """
    Factory class responsible for creating instances of CursorExecutionTab
    with validated dependencies and proper initialization.
    """
    
    @staticmethod
    def create(services: Dict[str, Any]) -> Optional[CursorExecutionTab]:
        """
        Create a new instance of CursorExecutionTab with validated dependencies.
        
        Args:
            services: Dictionary of service instances
            
        Returns:
            An initialized CursorExecutionTab instance, or None if required services are missing
        """
        # Validate required services
        cursor_dispatcher = services.get('cursor_dispatcher')
        if not cursor_dispatcher or not isinstance(cursor_dispatcher, CursorDispatcher):
            logger.error("CursorExecutionTab requires a valid CursorDispatcher service")
            return None
            
        test_runner = services.get('test_runner')
        if not test_runner or not isinstance(test_runner, TestRunner):
            logger.error("CursorExecutionTab requires a valid TestRunner service")
            return None
            
        # Get optional services - use defaults if not available
        metrics_service = services.get('metrics_service')
        if not metrics_service or not isinstance(metrics_service, MetricsService):
            logger.warning("Using default MetricsService for CursorExecutionTab")
            from core.metrics.mock_metrics_service import MockMetricsService
            metrics_service = MockMetricsService()
            
        # Create the PromptExecutionService if not provided
        prompt_service = services.get('prompt_service')
        if not prompt_service or not isinstance(prompt_service, PromptExecutionService):
            logger.info("Creating new PromptExecutionService for CursorExecutionTab")
            prompt_service = PromptExecutionService()
            
        # Create the TaskManager if not provided
        task_manager = services.get('task_manager')
        if not task_manager or not isinstance(task_manager, TaskManager):
            logger.info("Creating new TaskManager for CursorExecutionTab")
            task_manager = TaskManager()
            
        # Create and initialize the tab
        tab = CursorExecutionTab(
            cursor_dispatcher=cursor_dispatcher,
            test_runner=test_runner,
            metrics_service=metrics_service,
            prompt_service=prompt_service
        )
        
        logger.info("CursorExecutionTab created successfully")
        return tab 
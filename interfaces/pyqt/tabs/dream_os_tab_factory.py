#!/usr/bin/env python3
"""
Dream OS Tab Factory

This module provides factories for creating various tabs used in the Dream.OS UI,
with proper integration with system services.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional

# Add parent directory to path to allow importing from modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from PyQt5.QtWidgets import QWidget

from interfaces.pyqt.tabs.task_status_tab import TaskStatusTabFactory
from interfaces.pyqt.tabs.cursor_prompt_preview_tab import CursorPromptPreviewTabFactory
from interfaces.pyqt.tabs.success_dashboard_tab import SuccessDashboardTabFactory
from interfaces.pyqt.orchestrator_bridge import OrchestratorBridge
from core.prompt_cycle_orchestrator import PromptCycleOrchestrator
from core.system_loader import DreamscapeSystemLoader

logger = logging.getLogger(__name__)

class TaskStatusIntegrationFactory:
    """Factory for creating task status tabs integrated with the orchestration system."""
    
    @staticmethod
    def create(services: Dict[str, Any] = None, parent: Optional[QWidget] = None) -> QWidget:
        """
        Create a TaskStatusTab with OrchestratorBridge integration.
        
        Args:
            services: Dictionary of services
            parent: Parent widget
            
        Returns:
            Integrated TaskStatusTab
        """
        # Get system loader
        system_loader = None
        if services and 'system_loader' in services:
            system_loader = services['system_loader']
        else:
            # Try to get the singleton instance
            system_loader = DreamscapeSystemLoader.get_instance()
            
        # Get orchestrator from services or system loader
        orchestrator = None
        if services and 'prompt_cycle_orchestrator' in services:
            orchestrator = services['prompt_cycle_orchestrator']
        elif system_loader:
            orchestrator = system_loader.get_service('prompt_cycle_orchestrator')
            
        # Create new orchestrator if needed
        if not orchestrator:
            try:
                logger.info("Creating new PromptCycleOrchestrator")
                orchestrator = PromptCycleOrchestrator()
                # Register with system loader if available
                if system_loader:
                    system_loader.register_service('prompt_cycle_orchestrator', orchestrator)
            except Exception as e:
                logger.error(f"Failed to create PromptCycleOrchestrator: {e}")
                return TaskStatusTabFactory.create(parent=parent)  # Fallback to standalone tab
                
        # Create bridge
        try:
            logger.info("Creating OrchestratorBridge")
            bridge = OrchestratorBridge(orchestrator)
            
            # Create tab with bridge
            logger.info("Creating TaskStatusTab with OrchestratorBridge")
            tab = TaskStatusTabFactory.create(
                orchestrator_bridge=bridge,
                parent=parent
            )
            return tab
            
        except Exception as e:
            logger.error(f"Failed to create OrchestratorBridge: {e}")
            return TaskStatusTabFactory.create(parent=parent)  # Fallback to standalone tab


class PromptPreviewIntegrationFactory:
    """Factory for creating prompt preview tabs integrated with the orchestration system."""
    
    @staticmethod
    def create(services: Dict[str, Any] = None, parent: Optional[QWidget] = None) -> QWidget:
        """
        Create a CursorPromptPreviewTab with OrchestratorBridge integration.
        
        Args:
            services: Dictionary of services
            parent: Parent widget
            
        Returns:
            Integrated CursorPromptPreviewTab
        """
        # Get system loader
        system_loader = None
        if services and 'system_loader' in services:
            system_loader = services['system_loader']
        else:
            # Try to get the singleton instance
            system_loader = DreamscapeSystemLoader.get_instance()
            
        # Get orchestrator from services or system loader
        orchestrator = None
        if services and 'prompt_cycle_orchestrator' in services:
            orchestrator = services['prompt_cycle_orchestrator']
        elif system_loader:
            orchestrator = system_loader.get_service('prompt_cycle_orchestrator')
            
        # Create new orchestrator if needed
        if not orchestrator:
            try:
                logger.info("Creating new PromptCycleOrchestrator")
                orchestrator = PromptCycleOrchestrator()
                # Register with system loader if available
                if system_loader:
                    system_loader.register_service('prompt_cycle_orchestrator', orchestrator)
            except Exception as e:
                logger.error(f"Failed to create PromptCycleOrchestrator: {e}")
                return CursorPromptPreviewTabFactory.create(parent=parent)  # Fallback to standalone tab
                
        # Create bridge
        try:
            logger.info("Creating OrchestratorBridge")
            bridge = OrchestratorBridge(orchestrator)
            
            # Get template directory from path manager if available
            template_dir = "templates"  # Default
            if services and 'path_manager' in services:
                try:
                    template_dir = str(services['path_manager'].get_path('templates'))
                except:
                    pass
            
            # Create tab with bridge
            logger.info(f"Creating CursorPromptPreviewTab with OrchestratorBridge, template_dir={template_dir}")
            tab = CursorPromptPreviewTabFactory.create(
                orchestrator_bridge=bridge,
                template_dir=template_dir,
                parent=parent
            )
            
            # Connect signals
            if hasattr(bridge, 'orchestrator') and hasattr(bridge.orchestrator, 'execute_task'):
                tab.execute_task_signal.connect(lambda task_id: bridge.orchestrator.execute_task(task_id))
            
            return tab
            
        except Exception as e:
            logger.error(f"Failed to create OrchestratorBridge: {e}")
            return CursorPromptPreviewTabFactory.create(parent=parent)  # Fallback to standalone tab


class SuccessDashboardIntegrationFactory:
    """Factory for creating success dashboard tabs integrated with the orchestration system."""
    
    @staticmethod
    def create(services: Dict[str, Any] = None, parent: Optional[QWidget] = None) -> QWidget:
        """
        Create a SuccessDashboardTab with OrchestratorBridge integration.
        
        Args:
            services: Dictionary of services
            parent: Parent widget
            
        Returns:
            Integrated SuccessDashboardTab
        """
        # Get system loader
        system_loader = None
        if services and 'system_loader' in services:
            system_loader = services['system_loader']
        else:
            # Try to get the singleton instance
            system_loader = DreamscapeSystemLoader.get_instance()
            
        # Get orchestrator from services or system loader
        orchestrator = None
        if services and 'prompt_cycle_orchestrator' in services:
            orchestrator = services['prompt_cycle_orchestrator']
        elif system_loader:
            orchestrator = system_loader.get_service('prompt_cycle_orchestrator')
            
        # Create new orchestrator if needed
        if not orchestrator:
            try:
                logger.info("Creating new PromptCycleOrchestrator")
                orchestrator = PromptCycleOrchestrator()
                # Register with system loader if available
                if system_loader:
                    system_loader.register_service('prompt_cycle_orchestrator', orchestrator)
            except Exception as e:
                logger.error(f"Failed to create PromptCycleOrchestrator: {e}")
                return SuccessDashboardTabFactory.create(parent=parent)  # Fallback to standalone tab
                
        # Create bridge
        try:
            logger.info("Creating OrchestratorBridge")
            bridge = OrchestratorBridge(orchestrator)
            
            # Get memory file path from path manager if available
            memory_path = "memory/task_history.json"  # Default
            if services and 'path_manager' in services:
                try:
                    memory_path = str(services['path_manager'].get_path('memory') / 'task_history.json')
                except:
                    pass
            
            # Create tab with bridge
            logger.info(f"Creating SuccessDashboardTab with OrchestratorBridge, memory_path={memory_path}")
            tab = SuccessDashboardTabFactory.create(
                orchestrator_bridge=bridge,
                memory_path=memory_path,
                parent=parent
            )
            
            return tab
            
        except Exception as e:
            logger.error(f"Failed to create OrchestratorBridge: {e}")
            return SuccessDashboardTabFactory.create(parent=parent)  # Fallback to standalone tab 
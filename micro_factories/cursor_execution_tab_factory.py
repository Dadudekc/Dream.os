#!/usr/bin/env python3
"""
cursor_execution_tab_factory.py

Factory for creating CursorExecutionTab instances with proper dependency injection
and validation of required services.
"""

from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget

from interfaces.pyqt.tabs.cursor_execution_tab import CursorExecutionTab


class CursorExecutionTabFactory:
    """Factory for creating CursorExecutionTab instances with validated dependencies."""
    
    REQUIRED_SERVICES = [
        'cursor_dispatcher',
        'template_manager',
        'test_runner',
        'git_manager'
    ]
    
    @classmethod
    def create(cls, services: Dict[str, Any], parent: Optional[QWidget] = None) -> CursorExecutionTab:
        """
        Create a new CursorExecutionTab instance with validated services.
        
        Args:
            services: Dictionary of application services
            parent: Optional parent widget
            
        Returns:
            CursorExecutionTab: A new tab instance with injected dependencies
            
        Raises:
            ValueError: If required services are missing
        """
        cls._validate_services(services)
        return CursorExecutionTab(services=services, parent=parent)
    
    @classmethod
    def _validate_services(cls, services: Dict[str, Any]) -> None:
        """
        Validate that all required services are present.
        
        Args:
            services: Dictionary of application services
            
        Raises:
            ValueError: If any required service is missing
        """
        missing_services = [
            service for service in cls.REQUIRED_SERVICES 
            if service not in services
        ]
        
        if missing_services:
            raise ValueError(
                f"Missing required services for CursorExecutionTab: {', '.join(missing_services)}"
            ) 
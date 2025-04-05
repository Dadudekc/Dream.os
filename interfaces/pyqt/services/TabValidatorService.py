#!/usr/bin/env python3
"""
TabValidatorService.py

Service for validating PyQt tab constructors and dependencies on startup.
"""

import logging
from typing import Dict, Any, List, Type, Optional
from PyQt5.QtWidgets import QWidget

from interfaces.pyqt.tabs.cursor_execution_tab import CursorExecutionTab
from micro_factories.cursor_execution_tab_factory import CursorExecutionTabFactory

logger = logging.getLogger(__name__)


class TabValidatorService:
    """Service for validating tab constructors and dependencies."""
    
    def __init__(self, services: Dict[str, Any]):
        """
        Initialize the validator service.
        
        Args:
            services: Dictionary of application services
        """
        self.services = services
        self.validation_results = {}
        self.error_details = {}  # Added error_details dictionary
        self.error_messages = {}  # Added for backward compatibility
        
        # Register tab factories and their required services
        self.tab_factories = {
            'cursor_execution': {
                'factory': CursorExecutionTabFactory,
                'tab_class': CursorExecutionTab,
                'required_services': CursorExecutionTabFactory.REQUIRED_SERVICES
            }
            # Add more tab factories here as needed
        }
    
    def validate_all_tabs(self) -> Dict[str, bool]:
        """
        Validate all registered tab factories.
        
        Returns:
            Dict[str, bool]: Mapping of tab names to validation results
        """
        for tab_name, config in self.tab_factories.items():
            try:
                self._validate_tab_factory(tab_name, config)
                self.validation_results[tab_name] = True
                logger.info(f"✅ Tab '{tab_name}' validated successfully")
            except Exception as e:
                self.validation_results[tab_name] = False
                self.error_details[tab_name] = str(e)  # Store error details
                self.error_messages[tab_name] = str(e)  # Store in error_messages too for backward compatibility
                logger.error(f"❌ Tab '{tab_name}' validation failed: {str(e)}")
        
        return self.validation_results
    
    def _validate_tab_factory(self, tab_name: str, config: Dict[str, Any]) -> None:
        """
        Validate a specific tab factory.
        
        Args:
            tab_name: Name of the tab to validate
            config: Factory configuration dictionary
            
        Raises:
            ValueError: If validation fails
        """
        factory = config['factory']
        tab_class = config['tab_class']
        required_services = config['required_services']
        
        # Check required services
        missing_services = [
            service for service in required_services 
            if service not in self.services
        ]
        if missing_services:
            raise ValueError(
                f"Tab '{tab_name}' missing required services: {', '.join(missing_services)}"
            )
        
        # Try to instantiate the tab
        try:
            tab = factory.create(self.services)
            if not isinstance(tab, tab_class):
                raise ValueError(
                    f"Tab '{tab_name}' factory created wrong type: {type(tab)}"
                )
        except Exception as e:
            raise ValueError(f"Tab '{tab_name}' instantiation failed: {str(e)}")
    
    def get_validation_status(self, tab_name: str) -> Optional[bool]:
        """
        Get validation status for a specific tab.
        
        Args:
            tab_name: Name of the tab to check
            
        Returns:
            Optional[bool]: True if validated, False if failed, None if not validated
        """
        return self.validation_results.get(tab_name)
        
    def get_error_details(self, tab_name: str) -> Optional[str]:
        """
        Get detailed error information for a failed tab validation.
        
        Args:
            tab_name: Name of the tab to get error details for
            
        Returns:
            Optional[str]: Error details if available, None otherwise
        """
        return self.error_details.get(tab_name) 
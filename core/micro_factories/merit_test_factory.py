#!/usr/bin/env python3
"""
MeritTestFactory - Factory for MeritChain and Test-related services
==================================================================

This factory is responsible for creating and initializing:
1. MeritChainManager - Manages the storage and validation of merit chain entries
2. TestGeneratorService - Provides test generation capabilities with coverage analysis
3. TestCoverageAnalyzer - Analyzes test coverage and recommends improvements

These services are used for profile analysis persistence and test generation/analysis.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

from core.services.service_registry import ServiceRegistry
from core.meritchain.MeritChainManager import MeritChainManager
from core.services.TestGeneratorService import TestGeneratorService
from core.services.TestCoverageAnalyzer import TestCoverageAnalyzer


class MeritTestFactory:
    """
    Factory for creating MeritChain and Test-related services with proper dependencies.
    """
    
    @staticmethod
    def create_merit_chain_manager() -> Optional[MeritChainManager]:
        """
        Create and initialize a MeritChainManager with proper configuration.
        
        Returns:
            Initialized MeritChainManager or None if initialization fails
        """
        logger = logging.getLogger(__name__)
        try:
            # Get dependencies
            path_manager = ServiceRegistry.get("path_manager")
            
            # Determine file and schema paths
            data_dir = path_manager.get_path("data")
            meritchain_file = os.path.join(data_dir, "meritchain.json")
            schema_path = os.path.join(path_manager.get_path("core"), "schemas", "merit_chain_schema.json")
            
            # Create the manager
            manager = MeritChainManager(
                filepath=meritchain_file,
                schema_path=schema_path
            )
            
            logger.info("✅ MeritChainManager initialized successfully")
            return manager
        except Exception as e:
            logger.error(f"❌ Failed to initialize MeritChainManager: {e}")
            return None
    
    @staticmethod
    def create_test_coverage_analyzer() -> Optional[TestCoverageAnalyzer]:
        """
        Create and initialize a TestCoverageAnalyzer with proper configuration.
        
        Returns:
            Initialized TestCoverageAnalyzer or None if initialization fails
        """
        logger = logging.getLogger(__name__)
        try:
            # Get dependencies
            path_manager = ServiceRegistry.get("path_manager")
            
            # Determine project root and coverage directory
            project_root = path_manager.get_path("root")
            coverage_dir = os.path.join(project_root, ".coverage_data")
            
            # Ensure coverage directory exists
            os.makedirs(coverage_dir, exist_ok=True)
            
            # Create the analyzer
            analyzer = TestCoverageAnalyzer(
                project_root=project_root,
                coverage_dir=coverage_dir
            )
            
            logger.info("✅ TestCoverageAnalyzer initialized successfully")
            return analyzer
        except Exception as e:
            logger.error(f"❌ Failed to initialize TestCoverageAnalyzer: {e}")
            return None
    
    @staticmethod
    def create_test_generator_service() -> Optional[TestGeneratorService]:
        """
        Create and initialize a TestGeneratorService with proper dependencies.
        
        Returns:
            Initialized TestGeneratorService or None if initialization fails
        """
        logger = logging.getLogger(__name__)
        try:
            # Get dependencies
            path_manager = ServiceRegistry.get("path_manager")
            openai_client = ServiceRegistry.get("openai_client")
            
            # Get the test coverage analyzer or create it if not available
            coverage_analyzer = ServiceRegistry.get("test_coverage_analyzer")
            if coverage_analyzer is None:
                coverage_analyzer = MeritTestFactory.create_test_coverage_analyzer()
                if coverage_analyzer:
                    ServiceRegistry.register("test_coverage_analyzer", coverage_analyzer)
            
            # Determine history directory
            history_dir = os.path.join(path_manager.get_path("data"), "test_generation_history")
            os.makedirs(history_dir, exist_ok=True)
            
            # Create the service
            service = TestGeneratorService(
                openai_client=openai_client,
                project_root=path_manager.get_path("root"),
                history_dir=history_dir,
                coverage_analyzer=coverage_analyzer
            )
            
            logger.info("✅ TestGeneratorService initialized successfully")
            return service
        except Exception as e:
            logger.error(f"❌ Failed to initialize TestGeneratorService: {e}")
            return None
    
    @classmethod
    def create(cls) -> Dict[str, Any]:
        """
        Create all services managed by this factory.
        
        Returns:
            Dictionary containing all created services
        """
        services = {}
        
        # Create MeritChainManager
        merit_chain_manager = cls.create_merit_chain_manager()
        if merit_chain_manager:
            services["merit_chain_manager"] = merit_chain_manager
            ServiceRegistry.register("merit_chain_manager", merit_chain_manager)
        
        # Create TestCoverageAnalyzer
        test_coverage_analyzer = cls.create_test_coverage_analyzer()
        if test_coverage_analyzer:
            services["test_coverage_analyzer"] = test_coverage_analyzer
            ServiceRegistry.register("test_coverage_analyzer", test_coverage_analyzer)
        
        # Create TestGeneratorService
        test_generator_service = cls.create_test_generator_service()
        if test_generator_service:
            services["test_generator_service"] = test_generator_service
            ServiceRegistry.register("test_generator_service", test_generator_service)
        
        return services 
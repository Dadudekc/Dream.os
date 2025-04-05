#!/usr/bin/env python3
"""
Auto-Queue Improvements

This script identifies the top N modules based on priority weighting and
automatically queues them for improvement using the StatefulCursorManager.
"""

import os
import sys
import json
import logging
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/auto_queue.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutoQueueImprovements")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import required modules
try:
    from core.system_loader import initialize_system
    from core.StatefulCursorManager import StatefulCursorManager
    from priority_weighting_config import PriorityWeightingConfig
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)


class AutoImprovementQueue:
    """
    Manages automatic queuing of improvements for top modules.
    """
    
    def __init__(self, config_path: str = "config/system_config.yml"):
        """
        Initialize the auto improvement queue.
        
        Args:
            config_path: Path to system configuration
        """
        self.config_path = config_path
        self.system = None
        self.cursor_manager = None
        self.priority_config = None
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self) -> bool:
        """
        Initialize required components.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Initialize system
            logger.info(f"Initializing system from {self.config_path}")
            self.system = initialize_system(self.config_path)
            
            # Get cursor manager
            self.cursor_manager = self.system.get_service("stateful_cursor_manager")
            if not self.cursor_manager:
                logger.error("StatefulCursorManager not found in system")
                return False
                
            # Get priority config
            self.priority_config = PriorityWeightingConfig()
            
            logger.info("Components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    def get_top_modules(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the top modules based on priority weighting.
        
        Args:
            count: Number of modules to return
            
        Returns:
            List[Dict[str, Any]]: List of top modules with scores
        """
        if not self.cursor_manager:
            logger.error("CursorManager not initialized")
            return []
            
        try:
            # Get candidates using cursor manager
            candidates = self.cursor_manager.get_improvement_candidates(count)
            
            logger.info(f"Found {len(candidates)} candidates for improvement")
            for i, candidate in enumerate(candidates):
                logger.info(f"Candidate {i+1}: {candidate['module']} (Score: {candidate.get('score', 'N/A')})")
                
            return candidates
            
        except Exception as e:
            logger.error(f"Error getting top modules: {e}")
            return []
    
    def generate_improvement_prompt(self, module: str) -> str:
        """
        Generate an improvement prompt for a module.
        
        Args:
            module: Module name
            
        Returns:
            str: Generated prompt
        """
        # Get module context from cursor manager
        context = self.cursor_manager.get_latest_prompt_context(module)
        
        # Get module metrics
        metrics = self.cursor_manager.get_latest_metrics(module)
        
        # Construct the improvement prompt
        prompt = (
            f"I need you to improve the code quality of the module '{module}'.\n\n"
            f"Here is the current context and metrics information:\n\n{context}\n\n"
            "Please analyze the code and make improvements to:\n"
            "1. Reduce cyclomatic complexity\n"
            "2. Improve code readability and maintainability\n"
            "3. Fix any potential bugs or code smells\n"
            "4. Improve test coverage where applicable\n\n"
            "Make specific, targeted changes rather than rewriting the entire module.\n"
            "Explain your reasoning for each change made."
        )
        
        logger.debug(f"Generated improvement prompt for {module}")
        return prompt
    
    def queue_module_for_improvement(self, module: str, prompt: Optional[str] = None, 
                                    timeout: int = 1800) -> str:
        """
        Queue a module for improvement.
        
        Args:
            module: Module name
            prompt: Optional custom prompt (if None, one will be generated)
            timeout: Timeout in seconds
            
        Returns:
            str: Session ID if successful, empty string otherwise
        """
        if not self.cursor_manager:
            logger.error("CursorManager not initialized")
            return ""
            
        try:
            # Generate prompt if not provided
            if not prompt:
                prompt = self.generate_improvement_prompt(module)
            
            # Queue the prompt
            session_id = self.cursor_manager.queue_stateful_prompt(
                module=module,
                prompt=prompt,
                isolation_level="high",
                timeout=timeout
            )
            
            logger.info(f"Queued {module} for improvement with session ID: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error queuing module {module} for improvement: {e}")
            return ""
    
    def auto_queue_improvements(self, count: int = 3, delay_between: int = 0) -> List[str]:
        """
        Automatically queue improvements for the top N modules.
        
        Args:
            count: Number of modules to queue
            delay_between: Delay between queueing modules in seconds
            
        Returns:
            List[str]: List of session IDs
        """
        session_ids = []
        
        # Get top modules
        top_modules = self.get_top_modules(count)
        
        # Queue each module for improvement
        for i, candidate in enumerate(top_modules):
            module = candidate["module"]
            score = candidate.get("score", "N/A")
            
            logger.info(f"Queueing improvement {i+1}/{len(top_modules)}: {module} (Score: {score})")
            
            # Queue the module
            session_id = self.queue_module_for_improvement(module)
            
            if session_id:
                session_ids.append(session_id)
                logger.info(f"Successfully queued {module} with session ID: {session_id}")
            else:
                logger.warning(f"Failed to queue {module} for improvement")
            
            # Add delay if specified and not the last item
            if delay_between > 0 and i < len(top_modules) - 1:
                logger.info(f"Waiting {delay_between} seconds before queueing next module")
                import time
                time.sleep(delay_between)
        
        # Log summary
        logger.info(f"Auto-queued {len(session_ids)}/{count} modules for improvement")
        
        return session_ids


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Auto-queue improvements for top modules')
    
    parser.add_argument('--count', type=int, default=3,
                       help='Number of modules to queue for improvement (default: 3)')
    parser.add_argument('--config', type=str, default='config/system_config.yml',
                       help='Path to system configuration file')
    parser.add_argument('--delay', type=int, default=0,
                       help='Delay between queueing modules in seconds (default: 0)')
    parser.add_argument('--timeout', type=int, default=1800,
                       help='Timeout for each improvement task in seconds (default: 1800)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show modules that would be queued without actually queueing them')
    
    args = parser.parse_args()
    
    try:
        # Create auto improvement queue
        auto_queue = AutoImprovementQueue(config_path=args.config)
        
        if args.dry_run:
            # Just show the modules that would be queued
            logger.info("DRY RUN: Showing modules that would be queued without actually queueing them")
            top_modules = auto_queue.get_top_modules(args.count)
            
            print("\nTop Modules for Improvement (Dry Run):")
            print("=====================================")
            for i, candidate in enumerate(top_modules):
                module = candidate["module"]
                score = candidate.get("score", "N/A")
                days = candidate.get("days_since_improvement", "N/A")
                
                print(f"{i+1}. {module}")
                print(f"   Score: {score}")
                print(f"   Days since last improvement: {days}")
                print()
                
            print(f"Found {len(top_modules)} candidate modules")
            print("Dry run completed, no modules were queued.")
            
        else:
            # Actually queue the improvements
            print(f"\nAuto-queueing improvements for top {args.count} modules:")
            print("="*50)
            
            session_ids = auto_queue.auto_queue_improvements(
                count=args.count,
                delay_between=args.delay
            )
            
            print(f"\nSuccessfully queued {len(session_ids)}/{args.count} modules for improvement.")
            print("Check the logs for more details: logs/auto_queue.log")
            
        return 0
        
    except Exception as e:
        logger.error(f"Error in auto-queue improvements: {e}")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
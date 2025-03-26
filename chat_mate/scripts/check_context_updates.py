#!/usr/bin/env python3
"""
Dreamscape Context Update Checker

This script checks if a scheduled context update to ChatGPT is due,
and runs it if necessary. It's designed to be run periodically 
(e.g., via a cron job or Windows Task Scheduler).

Usage:
    python scripts/check_context_updates.py [--force]
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.ConfigManager import ConfigManager
from interfaces.pyqt.dreamscape_services import DreamscapeService


def setup_logging():
    """Set up logging for the context update script."""
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "context_updates.log")),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("context_update_checker")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Check and run scheduled context updates.")
    parser.add_argument("--force", action="store_true", 
                        help="Force update regardless of schedule")
    parser.add_argument("--config", type=str, default="dreamscape_config.yaml", 
                       help="Path to configuration file")
    return parser.parse_args()


def is_update_due(schedule_file):
    """Check if an update is due based on the schedule file."""
    if not os.path.exists(schedule_file):
        return False
        
    try:
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
            
        if not schedule.get('enabled', False):
            return False
            
        # Parse next update time
        next_update = datetime.fromisoformat(schedule['next_update'].replace('Z', '+00:00'))
        now = datetime.now()
        
        return now >= next_update
        
    except Exception as e:
        logging.error(f"Error checking schedule: {e}")
        return False


def update_schedule_after_run(schedule_file):
    """Update the schedule file after a successful run."""
    try:
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
            
        # Update timestamps
        schedule['last_update'] = datetime.now().isoformat()
        
        # Calculate next update time based on interval
        next_update = datetime.now() + timedelta(days=schedule.get('interval_days', 7))
        schedule['next_update'] = next_update.isoformat()
        
        # Save back to file
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, indent=2)
            
        return True
        
    except Exception as e:
        logging.error(f"Error updating schedule: {e}")
        return False


def main():
    """Main entry point for the script."""
    # Set up logging and parse arguments
    logger = setup_logging()
    args = parse_args()
    
    logger.info("Starting Dreamscape Context Update Checker")
    
    # Load configuration
    try:
        config = ConfigManager(config_name=args.config)
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
        
    # Get schedule file path
    output_dir = config.get("dreamscape_output_dir", "outputs/dreamscape")
    schedule_file = os.path.join(output_dir, "context_update_schedule.json")
    
    # Check if update is due or forced
    update_needed = args.force or is_update_due(schedule_file)
    
    if not update_needed:
        logger.info("No context update needed at this time")
        sys.exit(0)
        
    logger.info("Context update is due - initiating update")
    
    # Initialize the Dreamscape service
    try:
        service = DreamscapeService(config=config)
        logger.info("DreamscapeService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DreamscapeService: {e}")
        sys.exit(1)
        
    # Load target chat from schedule
    target_chat = None
    try:
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
            target_chat = schedule.get('target_chat')
    except Exception:
        # Will use default targeting behavior
        pass
        
    # Get the next episode number for logging
    next_episode = None
    try:
        if service.dreamscape_generator:
            next_episode = service.dreamscape_generator.get_episode_number()
            logger.info(f"Preparing to update context for Episode #{next_episode}")
    except Exception as e:
        logger.warning(f"Could not determine next episode number: {e}")
        
    # Run the context update
    try:
        result = service.send_context_to_chatgpt(chat_name=target_chat)
        
        if result:
            episode_msg = f" for Episode #{next_episode}" if next_episode else ""
            logger.info(f"Context update{episode_msg} sent successfully")
            
            # Update schedule for next run
            if update_schedule_after_run(schedule_file):
                logger.info("Schedule updated for next run")
            else:
                logger.warning("Failed to update schedule for next run")
        else:
            logger.error("Failed to send context update")
            
    except Exception as e:
        logger.error(f"Error during context update: {e}")
    finally:
        # Ensure proper shutdown
        logger.info("Shutting down services...")
        if service:
            service.shutdown()
    
    logger.info("Context update check completed")


if __name__ == "__main__":
    main() 
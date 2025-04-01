#!/usr/bin/env python3
"""
Digital Dreamscape Content Generator

This script runs the original Digital Dreamscape lore generation process
using the centralized DreamscapeService. It will:

1. Initialize the service with config
2. Create a ChatManager instance
3. Generate dreamscape episodes for each chat
4. Save the results and optionally post to Discord

Usage:
    python scripts/run_dreamscape.py [--headless] [--skip-discord]
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.config.config_manager import ConfigManager
from interfaces.pyqt.dreamscape_services import DreamscapeService


def setup_logging():
    """Set up logging for the Dreamscape script."""
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "dreamscape.log")),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("dreamscape_script")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate Dreamscape content from ChatGPT chats.")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--skip-discord", action="store_true", help="Skip posting to Discord")
    parser.add_argument("--config", type=str, default="dreamscape_config.yaml", 
                       help="Path to configuration file")
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    # Set up logging and parse arguments
    logger = setup_logging()
    args = parse_args()
    
    logger.info("Starting Digital Dreamscape Content Generator")
    
    # Load configuration
    try:
        config = ConfigManager(config_name=args.config)
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
        
    # Set headless mode from arguments
    headless = args.headless
    logger.info(f"Headless mode: {headless}")
    
    # Initialize the Dreamscape service
    try:
        service = DreamscapeService(config=config)
        logger.info("DreamscapeService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DreamscapeService: {e}")
        sys.exit(1)
        
    # Skip Discord if requested
    if args.skip_discord and service.discord:
        logger.info("Discord integration disabled by command line argument")
        service.discord = None
        
    # Run the Dreamscape generation
    try:
        entries = service.generate_dreamscape_content(headless=headless)
        if entries:
            logger.info(f"Successfully generated {len(entries)} dreamscape entries")
            
            # Print a preview of entries
            for i, entry in enumerate(entries):
                preview = entry[:100] + "..." if len(entry) > 100 else entry
                logger.info(f"Entry {i+1}: {preview}")
        else:
            logger.warning("No dreamscape entries were generated")
    except Exception as e:
        logger.error(f"Error generating dreamscape content: {e}")
    finally:
        # Ensure proper shutdown
        logger.info("Shutting down services...")
        if service:
            service.shutdown()
    
    logger.info("Dreamscape content generation completed")


if __name__ == "__main__":
    main() 

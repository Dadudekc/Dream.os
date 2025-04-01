#!/usr/bin/env python3

"""
Scheduled Dreamscape Episode Generator
--------------------------------------

This script is designed to be run on a schedule (e.g., via cron, Task Scheduler, or systemd timer).
It runs the dreamscape_automation.py script with appropriate arguments to:
1. Generate episodes for all non-excluded chats
2. Update memory and episode chain for narrative continuity
3. Post the results to Discord
4. Update a status file with information about the run

Usage:
    python scheduled_dreamscape.py [--discord] [--force] [--web] [--count N]
    
    --discord: Post the generated episodes to Discord
    --force: Run even if the minimum interval hasn't passed
    --web: Scrape chats directly from the ChatGPT web interface instead of memory
    --count N: Generate up to N episodes in this run (default: 1)
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Setup logging
log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, "scheduled_dreamscape.log"))
    ]
)
logger = logging.getLogger("scheduled_dreamscape")

# Constants
STATUS_FILE = "dreamscape_schedule_status.json"
DEFAULT_MIN_INTERVAL_HOURS = 12  # Minimum time between runs
CHAIN_FILE = os.path.join("memory", "episode_chain.json")

def read_status_file():
    """Read the status file to determine when the last run occurred."""
    if not os.path.exists(STATUS_FILE):
        return None
    
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            status = json.load(f)
        return status
    except Exception as e:
        logger.error(f"Error reading status file: {e}")
        return None

def write_status_file(success, episodes_generated=0, error=None, chain_info=None):
    """Write the current status to the status file."""
    status = {
        "last_run": datetime.now().isoformat(),
        "success": success,
        "episodes_generated": episodes_generated,
        "error": error
    }
    
    # Add episode chain information if available
    if chain_info:
        status["chain_info"] = chain_info
    
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
        logger.info("Status file updated")
    except Exception as e:
        logger.error(f"Error writing status file: {e}")

def should_run(status, min_interval_hours, force=False):
    """Determine if enough time has passed since the last run."""
    if force:
        logger.info("Force flag set, running regardless of interval")
        return True
    
    if not status or "last_run" not in status:
        logger.info("No previous run found, proceeding")
        return True
    
    try:
        last_run = datetime.fromisoformat(status["last_run"])
        min_interval = timedelta(hours=min_interval_hours)
        time_since_last_run = datetime.now() - last_run
        
        if time_since_last_run >= min_interval:
            logger.info(f"Sufficient time elapsed since last run ({time_since_last_run}), proceeding")
            return True
        else:
            logger.info(f"Insufficient time since last run (only {time_since_last_run}), skipping")
            return False
    except Exception as e:
        logger.error(f"Error checking run interval: {e}")
        return True  # Default to running if there's an error

def count_generated_episodes():
    """Count the number of episodes generated in this run by checking processed_dreamscape_chats.json."""
    if not os.path.exists("processed_dreamscape_chats.json"):
        return 0
    
    try:
        with open("processed_dreamscape_chats.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data.get("processed_chats", []))
    except Exception as e:
        logger.error(f"Error counting generated episodes: {e}")
        return 0

def get_chain_info():
    """Get information about the current episode chain state."""
    if not os.path.exists(CHAIN_FILE):
        logger.info(f"Episode chain file does not exist: {CHAIN_FILE}")
        return None
    
    try:
        with open(CHAIN_FILE, "r", encoding="utf-8") as f:
            chain_data = json.load(f)
            
        # Extract relevant information
        chain_info = {
            "episode_count": chain_data.get("episode_count", 0),
            "last_episode": chain_data.get("last_episode", ""),
            "current_location": chain_data.get("last_location", ""),
            "active_quests": len(chain_data.get("ongoing_quests", [])),
            "completed_quests": len(chain_data.get("completed_quests", [])),
            "last_updated": chain_data.get("last_updated", "")
        }
        
        return chain_info
    except Exception as e:
        logger.error(f"Error getting episode chain info: {e}")
        return None

def notify_discord(success, episodes_count, error=None, chain_info=None):
    """Send a status notification to Discord if the service is available."""
    try:
        # Try to import the Discord service
        from core.services.service_registry import ServiceRegistry
        service_registry = ServiceRegistry()
        discord_service = service_registry.get("discord_manager")
        
        if not discord_service:
            logger.warning("Discord service not available")
            return False
        
        # Construct the message
        status_emoji = "✅" if success else "❌"
        status_text = "successful" if success else "failed"
        message = f"{status_emoji} **Dreamscape Episode Generation** {status_text}.\n"
        
        if success:
            message += f"Generated {episodes_count} episode(s) at {datetime.now().strftime('%Y-%m-%d %H:%M')}.\n"
            
            # Add chain information if available
            if chain_info:
                total_episodes = chain_info.get("episode_count", 0)
                last_episode = chain_info.get("last_episode", "Unknown")
                current_loc = chain_info.get("current_location", "The Nexus")
                
                message += f"\n**Episode Chain Status:**\n"
                message += f"📚 Total Episodes: {total_episodes}\n"
                message += f"📜 Last Episode: {last_episode}\n"
                message += f"🗺️ Current Location: {current_loc}\n"
                
                active_quests = chain_info.get("active_quests", 0)
                completed_quests = chain_info.get("completed_quests", 0)
                if active_quests or completed_quests:
                    message += f"🔄 Active Quests: {active_quests}\n"
                    message += f"✅ Completed Quests: {completed_quests}\n"
        else:
            message += f"Error: {error}"
            
        # Send the message
        discord_service.send_message(message)
        logger.info("Discord notification sent")
        return True
        
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
        return False

def main():
    """Main entry point for the scheduled script."""
    parser = argparse.ArgumentParser(description="Run scheduled dreamscape episode generation")
    parser.add_argument("--discord", action="store_true", help="Post the generated episodes to Discord")
    parser.add_argument("--force", action="store_true", help="Run even if the minimum interval hasn't passed")
    parser.add_argument("--interval", type=int, default=DEFAULT_MIN_INTERVAL_HOURS, 
                        help=f"Minimum hours between runs (default: {DEFAULT_MIN_INTERVAL_HOURS})")
    parser.add_argument("--web", action="store_true", help="Scrape chats directly from ChatGPT web interface instead of memory")
    parser.add_argument("--count", type=int, default=1, help="Generate up to N episodes in this run (default: 1)")
    parser.add_argument("--status", action="store_true", help="Show chain status and exit without generating episodes")
    args = parser.parse_args()
    
    # Just show status if requested
    if args.status:
        chain_info = get_chain_info()
        if chain_info:
            print("\n=== Episode Chain Status ===")
            print(f"Total Episodes: {chain_info.get('episode_count', 0)}")
            print(f"Last Episode: {chain_info.get('last_episode', 'Unknown')}")
            print(f"Current Location: {chain_info.get('current_location', 'Unknown')}")
            print(f"Active Quests: {chain_info.get('active_quests', 0)}")
            print(f"Completed Quests: {chain_info.get('completed_quests', 0)}")
            print(f"Last Updated: {chain_info.get('last_updated', 'Unknown')}")
            print("============================\n")
        else:
            print("No episode chain found or chain file is invalid.")
        return 0
    
    # Check if we should run based on the last run time
    status = read_status_file()
    if not should_run(status, args.interval, args.force):
        logger.info("Skipping run due to interval constraint")
        return 0
    
    # Build the command to run the dreamscape automation
    cmd = [sys.executable, "dreamscape_automation.py", "--all"]
    
    # Add count if specified
    if args.count and args.count > 1:
        cmd.extend(["--count", str(args.count)])
        
    # Add other flags
    if args.discord:
        cmd.append("--discord")
    if args.web:
        cmd.append("--web")
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    # Run the automation script
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        success = result.returncode == 0
        episodes_count = count_generated_episodes()
        
        # Get episode chain information after running
        chain_info = get_chain_info()
        
        if success:
            logger.info(f"Dreamscape automation completed successfully, generated {episodes_count} episodes")
            if chain_info:
                logger.info(f"Episode chain now has {chain_info.get('episode_count', 0)} total episodes")
        else:
            logger.error(f"Dreamscape automation failed with exit code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
        
        # Update the status file
        write_status_file(
            success=success,
            episodes_generated=episodes_count,
            error=result.stderr if not success else None,
            chain_info=chain_info
        )
        
        # Send notification to Discord about the status
        if args.discord:
            notify_discord(
                success=success,
                episodes_count=episodes_count,
                error=result.stderr if not success else None,
                chain_info=chain_info
            )
        
        return result.returncode
    
    except Exception as e:
        logger.error(f"Error running dreamscape automation: {e}")
        write_status_file(success=False, error=str(e))
        if args.discord:
            notify_discord(success=False, episodes_count=0, error=str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main()) 

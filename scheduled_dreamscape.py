#!/usr/bin/env python3

"""
DigitalDreamscapeEpisodes Scheduler
-----------------------------------

This script runs the dreamscape_automation.py script on a schedule,
combining both LLM-based semantic memory and web-scraped context.
It maintains a log of runs and can send status reports via Discord.

Usage:
    python scheduled_dreamscape.py --interval 6 --discord
"""

import os
import sys
import time
import logging
import argparse
import random
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scheduled_dreamscape.log")
    ]
)
logger = logging.getLogger("scheduled_dreamscape")

def send_discord_status(status_message: str) -> bool:
    """Send a status message to Discord using the DiscordBot service."""
    try:
        # Try to import and use DiscordBot directly
        try:
            from discord_integration.DiscordBot import DiscordBot
            from config.ConfigManager import ConfigManager
            
            config = ConfigManager()
            discord_token = config.get("discord_token")
            discord_channel = config.get("discord_channel")
            
            if not discord_token:
                logger.warning("Discord token not found in config")
                return False
                
            discord_bot = DiscordBot(token=discord_token, default_channel=discord_channel)
            discord_bot.send_message(status_message)
            logger.info("Status sent to Discord")
            return True
            
        except ImportError:
            # Fall back to subprocess call
            logger.info("Using subprocess to send Discord message")
            discord_script = Path("scripts") / "send_discord_message.py"
            
            if not discord_script.exists():
                logger.warning(f"Discord script not found at {discord_script}")
                return False
                
            subprocess.run([
                sys.executable, 
                str(discord_script), 
                status_message
            ])
            logger.info("Status sent to Discord via script")
            return True
            
    except Exception as e:
        logger.error(f"Failed to send Discord status: {e}")
        return False

def get_chain_status() -> Dict[str, Any]:
    """Get current status of the episode chain."""
    chain_path = Path("memory") / "episode_chain.json"
    status = {
        "episode_count": 0,
        "last_episode": "None",
        "last_generated": "Never",
        "ongoing_quests": [],
        "completed_quests": [],
        "last_location": "The Nexus",
        "current_emotional_state": "Neutral"
    }
    
    if not chain_path.exists():
        return status
        
    try:
        with open(chain_path, "r", encoding="utf-8") as f:
            chain_data = json.load(f)
            
        # Update status with chain data
        status["episode_count"] = chain_data.get("episode_count", 0)
        status["last_episode"] = chain_data.get("last_episode", "None")
        status["ongoing_quests"] = chain_data.get("ongoing_quests", [])
        status["completed_quests"] = chain_data.get("completed_quests", [])
        status["last_location"] = chain_data.get("last_location", "The Nexus")
        status["current_emotional_state"] = chain_data.get("current_emotional_state", "Neutral")
        
        # Get timestamp from the last episode
        episodes = chain_data.get("episodes", [])
        if episodes:
            last_episode = episodes[-1]
            status["last_generated"] = last_episode.get("timestamp", "Unknown")
            
        return status
        
    except Exception as e:
        logger.error(f"Error getting chain status: {e}")
        return status

def format_status_message(status: Dict[str, Any], next_run: datetime) -> str:
    """Format the chain status into a Discord message."""
    # Format quest list
    ongoing_quests = status.get("ongoing_quests", [])
    quest_text = ""
    if ongoing_quests:
        quest_items = [f"- {quest}" for quest in ongoing_quests[:3]]
        quest_text = "\n".join(quest_items)
        if len(ongoing_quests) > 3:
            quest_text += f"\n- ...and {len(ongoing_quests) - 3} more"
    else:
        quest_text = "- No active quests"
        
    # Format last generated time
    last_gen = status.get("last_generated", "Never")
    if last_gen != "Never":
        try:
            last_time = datetime.fromisoformat(last_gen)
            time_ago = datetime.now() - last_time
            if time_ago.days > 0:
                last_gen = f"{time_ago.days} days ago"
            elif time_ago.seconds > 3600:
                last_gen = f"{time_ago.seconds // 3600} hours ago"
            else:
                last_gen = f"{time_ago.seconds // 60} minutes ago"
        except:
            pass
    
    # Format next run time
    next_run_text = next_run.strftime("%Y-%m-%d %H:%M:%S")
    time_until = next_run - datetime.now()
    if time_until.days > 0:
        next_run_text += f" (in {time_until.days} days)"
    elif time_until.seconds > 3600:
        next_run_text += f" (in {time_until.seconds // 3600} hours)"
    else:
        next_run_text += f" (in {time_until.seconds // 60} minutes)"
        
    # Build the message
    message = f"📊 **Dreamscape Chain Status Report**\n\n"
    message += f"📚 **Episodes**: {status.get('episode_count', 0)}\n"
    message += f"🕰️ **Last Generated**: {last_gen}\n"
    message += f"📍 **Current Location**: {status.get('last_location', 'The Nexus')}\n"
    message += f"🌡️ **Emotional State**: {status.get('current_emotional_state', 'Neutral')}\n\n"
    
    message += f"**📋 Active Quests**:\n{quest_text}\n\n"
    
    if status.get("last_episode", ""):
        message += f"**📜 Last Episode**: {status.get('last_episode', '')}\n\n"
        
    message += f"⏰ **Next Scheduled Run**: {next_run_text}"
    
    return message

def run_dreamscape_automation(use_web: bool = False, send_discord: bool = False) -> bool:
    """Run the dreamscape_automation.py script with specified options."""
    try:
        script_path = Path("dreamscape_automation.py")
        if not script_path.exists():
            logger.error(f"Automation script not found at {script_path}")
            return False
            
        # Build command with arguments
        cmd = [sys.executable, str(script_path)]
        
        # Add a random chance of using web scraping for diverse context sources
        if use_web or random.random() < 0.5:  # 50% chance of using web
            cmd.append("--web")
            logger.info("Using web scraping for this run")
        else:
            logger.info("Using memory-based context for this run")
            
        # Add Discord notification if requested
        if send_discord:
            cmd.append("--discord")
            
        # Always use analysis for better logging
        cmd.append("--analysis")
        
        # Execute the command
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Log the output
        logger.info(f"Exit code: {result.returncode}")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
        if result.stderr:
            logger.error(f"Error: {result.stderr}")
            
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Failed to run dreamscape automation: {e}")
        return False

def calculate_next_run_time(interval_hours: int, jitter_minutes: int = 30) -> datetime:
    """Calculate the next run time with a random jitter."""
    next_time = datetime.now() + timedelta(hours=interval_hours)
    
    # Add random jitter to avoid predictable patterns
    if jitter_minutes > 0:
        jitter = random.randint(-jitter_minutes, jitter_minutes)
        next_time += timedelta(minutes=jitter)
        
    return next_time

def save_schedule_state(next_run: datetime, runs: List[Dict[str, Any]]):
    """Save the current schedule state to a JSON file."""
    try:
        state = {
            "last_updated": datetime.now().isoformat(),
            "next_scheduled_run": next_run.isoformat(),
            "recent_runs": runs[-10:] if runs else []  # Keep last 10 runs
        }
        
        # Save to file
        with open("dreamscape_schedule_state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            
        logger.info(f"Schedule state saved, next run at {next_run}")
        
    except Exception as e:
        logger.error(f"Failed to save schedule state: {e}")

def load_schedule_state() -> Dict[str, Any]:
    """Load the schedule state from the JSON file."""
    state_file = Path("dreamscape_schedule_state.json")
    default_state = {
        "next_scheduled_run": None,
        "recent_runs": []
    }
    
    if not state_file.exists():
        logger.info("No schedule state file found, using defaults")
        return default_state
        
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
            
        # Convert next run time string to datetime
        if state.get("next_scheduled_run"):
            try:
                state["next_scheduled_run"] = datetime.fromisoformat(state["next_scheduled_run"])
            except:
                state["next_scheduled_run"] = None
                
        return state
        
    except Exception as e:
        logger.error(f"Failed to load schedule state: {e}")
        return default_state

def main():
    """Main entry point for the scheduler."""
    parser = argparse.ArgumentParser(description="Schedule dreamscape episode generation")
    parser.add_argument("--interval", type=int, default=6, help="Hours between runs (default: 6)")
    parser.add_argument("--jitter", type=int, default=30, help="Random minutes of jitter to add (default: 30)")
    parser.add_argument("--discord", action="store_true", help="Send status updates to Discord")
    parser.add_argument("--run-now", action="store_true", help="Run immediately, then schedule")
    parser.add_argument("--web", action="store_true", help="Force web scraping for initial run")
    parser.add_argument("--continuous", action="store_true", help="Run continuously (daemon mode)")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    args = parser.parse_args()
    
    # Load existing schedule state
    state = load_schedule_state()
    runs = state.get("recent_runs", [])
    
    # Get current chain status
    chain_status = get_chain_status()
    
    # Show status if requested
    if args.status:
        next_run = state.get("next_scheduled_run")
        if not next_run:
            next_run = calculate_next_run_time(args.interval, args.jitter)
            
        status_message = format_status_message(chain_status, next_run)
        print("\n" + status_message + "\n")
        
        if args.discord:
            send_discord_status(status_message)
            
        sys.exit(0)
    
    # Determine next run time
    next_run = state.get("next_scheduled_run")
    if not next_run or args.run_now:
        next_run = datetime.now() if args.run_now else calculate_next_run_time(args.interval, args.jitter)
    
    logger.info(f"Next run scheduled for: {next_run}")
    
    # Send initial status if requested
    if args.discord:
        status_message = format_status_message(chain_status, next_run)
        send_discord_status(status_message)
    
    # Run continuously if requested
    while True:
        # Check if it's time to run
        current_time = datetime.now()
        
        if current_time >= next_run or args.run_now:
            logger.info("Running dreamscape automation...")
            
            # Run the automation
            success = run_dreamscape_automation(use_web=args.web, send_discord=args.discord)
            
            # Record the run
            run_record = {
                "timestamp": current_time.isoformat(),
                "success": success,
                "use_web": args.web,
                "discord": args.discord
            }
            runs.append(run_record)
            
            # Get updated chain status
            chain_status = get_chain_status()
            
            # Calculate next run time
            next_run = calculate_next_run_time(args.interval, args.jitter)
            logger.info(f"Next run scheduled for: {next_run}")
            
            # Send status update
            if args.discord:
                status_message = format_status_message(chain_status, next_run)
                send_discord_status(status_message)
                
            # Save schedule state
            save_schedule_state(next_run, runs)
            
            # Reset run-now flag
            args.run_now = False
            args.web = False  # Reset web flag too
        
        # Exit if not in continuous mode
        if not args.continuous:
            break
            
        # Sleep for a bit before checking again
        time.sleep(60)  # Check every minute
        
if __name__ == "__main__":
    main() 
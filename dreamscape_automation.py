#!/usr/bin/env python3

"""
DigitalDreamscapeEpisodes Automation
------------------------------------

This script integrates with your existing Dream.OS architecture to:
1. Get the list of available chats (excluding specified ones)
2. For each chat:
   - Retrieve the chat history (from memory or via web scraping)
   - Generate a dreamscape episode with dynamic context continuity
   - Update memory and episode chain for narrative coherence
   - Save it to the output directory
   - Optionally post it to Discord

The script uses your service registry and dependency injection system,
combining both semantic LLM-based context and structured data.
"""

import os
import sys
import time
import logging
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("dreamscape_automation.log")
    ]
)
logger = logging.getLogger("dreamscape_automation")

def initialize_services():
    """Initialize required services from the service registry."""
    try:
        from core.services.service_registry import ServiceRegistry
        from core.config.config_manager import ConfigManager
        from core.ChatManager import ChatManager
        from core.PathManager import PathManager
        from core.TemplateManager import TemplateManager
        from core.services.dreamscape_generator_service import DreamscapeGenerationService
        from core.services.prompt_context_synthesizer import PromptContextSynthesizer
        from discord_integration.DiscordBot import DiscordBot
        
        logger.info("Initializing services...")
        
        # Get service registry
        service_registry = ServiceRegistry()
        
        # Try to get services from registry first
        config_manager = service_registry.get("config_manager")
        chat_manager = service_registry.get("chat_manager")
        discord_service = service_registry.get("discord_service")
        
        # If not available, initialize directly
        if not config_manager:
            config_manager = ConfigManager()
            logger.info("ConfigManager initialized directly")
            
        if not chat_manager:
            # Configure headless mode for automation
            driver_options = {
                "headless": True,
                "window_size": (1920, 1080),
                "disable_gpu": True,
                "no_sandbox": True,
                "disable_dev_shm": True
            }
            
            chat_manager = ChatManager(
                driver_options=driver_options,
                model="gpt-4o",
                headless=True,
                memory_file=config_manager.get("memory_path", "memory/chat_memory.json")
            )
            logger.info("ChatManager initialized directly")
        
        # Initialize the dreamscape service
        path_manager = PathManager()
        template_manager = TemplateManager(
            template_dir=os.path.join(os.getcwd(), "templates", "dreamscape_templates")
        )
         
        # Initialize the context synthesizer
        memory_path = path_manager.get_path("memory") / "dreamscape_memory.json"
        chain_path = path_manager.get_path("memory") / "episode_chain.json"
        conversation_memory_path = path_manager.get_path("memory") / "conversation_memory.json"
        
        context_synthesizer = PromptContextSynthesizer(
            memory_path=memory_path,
            chain_path=chain_path,
            conversation_memory_path=conversation_memory_path,
            logger=logger
        )
        
        # Initialize dreamscape service with context synthesizer
        dreamscape_service = DreamscapeGenerationService(
            path_manager=path_manager,
            template_manager=template_manager,
            logger=logger
        )
        
        # Set the dreamscape service on the chat manager
        chat_manager.dreamscape_service = dreamscape_service
        
        # Initialize Discord service if not available and configured
        if not discord_service and config_manager.get("discord_enabled", False):
            try:
                discord_token = config_manager.get("discord_token")
                discord_channel = config_manager.get("discord_channel")
                if discord_token:
                    discord_service = DiscordBot(token=discord_token, default_channel=discord_channel)
                    logger.info("Discord service initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Discord service: {e}")
        
        # Check for memory and chain files and create if needed
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not memory_path.exists():
            # Create initial memory structure
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump({
                    "protocols": [],
                    "quests": {},
                    "realms": [],
                    "artifacts": [],
                    "characters": [],
                    "themes": [],
                    "stabilized_domains": []
                }, f, indent=2)
            logger.info(f"Created initial memory file at {memory_path}")
            
        # Initialize conversation memory if needed
        if not conversation_memory_path.exists():
            # Create initial conversation memory structure
            with open(conversation_memory_path, "w", encoding="utf-8") as f:
                json.dump({
                    "chat_memories": {},
                    "global_memory": {
                        "themes": ["automation", "convergence", "optimization"],
                        "goals": ["narrative continuity", "dynamic storytelling", "memory persistence"],
                        "insights": [],
                        "last_updated": datetime.now().isoformat()
                    }
                }, f, indent=2)
            logger.info(f"Created initial conversation memory file at {conversation_memory_path}")
        
        logger.info("Services initialized successfully")
        return {
            "config_manager": config_manager,
            "chat_manager": chat_manager,
            "dreamscape_service": dreamscape_service,
            "context_synthesizer": context_synthesizer,
            "discord_service": discord_service
        }
        
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        return None

def get_excluded_chats(config_manager):
    """Get the list of chats to exclude from processing."""
    excluded_chats = [
        "ChatGPT", "Sora", "Explore GPTs", "Axiom", 
        "work project", "prompt library", "Bot", "smartstock-pro"
    ]
    
    # If available in config, use that instead
    if hasattr(config_manager, "get"):
        config_excluded = config_manager.get("excluded_chats", [])
        if config_excluded:
            excluded_chats = config_excluded
            
    return excluded_chats

def get_available_chats(chat_manager, excluded_chats, use_web=False):
    """
    Get all available chats, filtering out excluded ones.
    
    Args:
        chat_manager: The chat manager instance
        excluded_chats: List of chat titles to exclude
        use_web: Whether to scrape chats from web interface instead of memory
    """
    try:
        # Use the web scraper if specified
        if use_web and hasattr(chat_manager, 'web_scraper') and chat_manager.web_scraper:
            logger.info("Getting chats from web interface")
            all_chats = chat_manager.web_scraper.scrape_chat_list()
        else:
            logger.info("Getting chats from memory")
            all_chats = chat_manager.get_all_chat_titles()
            
        if not all_chats:
            logger.warning("No chats found")
            return []
            
        # Filter out excluded chats
        available_chats = []
        for chat in all_chats:
            title = chat.get("title", "") if isinstance(chat, dict) else chat
            if title and not any(excluded in title for excluded in excluded_chats):
                available_chats.append(chat)
                
        logger.info(f"Found {len(available_chats)} chats after filtering {len(all_chats)} total chats")
        return available_chats
        
    except Exception as e:
        logger.error(f"Error getting available chats: {e}")
        return []

def get_previously_processed_chats():
    """Get the list of chats that have already been processed."""
    archive_file = Path("processed_dreamscape_chats.json")
    if not archive_file.exists():
        return []
        
    try:
        with open(archive_file, "r", encoding="utf-8") as f:
            archive = json.load(f)
        return archive.get("processed_chats", [])
    except Exception as e:
        logger.error(f"Error reading archive: {e}")
        return []

def process_chat(chat_manager, chat_title, use_web=False, context_synthesizer=None):
    """
    Process a single chat to generate a dreamscape episode.
    
    Args:
        chat_manager: The chat manager instance
        chat_title: The title of the chat to process
        use_web: Whether to use web scraping for chat history
        context_synthesizer: Optional context synthesizer for enhanced processing
        
    Returns:
        Dictionary with processing results or None if failed
    """
    try:
        logger.info(f"Processing chat: {chat_title}")
        
        # Determine the source (web or memory)
        source = "web" if use_web else "memory"
        logger.info(f"Using source: {source}")
        
        # Get chat history based on source
        chat_history = []
        web_content = None
        
        if use_web:
            # Use web scraper to get detailed content
            if hasattr(chat_manager, 'web_scraper') and chat_manager.web_scraper:
                chat_history = chat_manager.web_scraper.scrape_chat_history(chat_title)
                # Optionally get raw HTML content for additional context
                web_content = chat_manager.web_scraper.get_last_raw_content()
        else:
            # Use memory to get chat history
            chat_history = chat_manager.get_chat_history(chat_title)
        
        if not chat_history:
            logger.warning(f"No chat history found for '{chat_title}'")
            return None
            
        # Generate the episode (with source information)
        episode_path = chat_manager.generate_dreamscape_episode(
            chat_title, 
            chat_history,
            source=source
        )
        
        if episode_path and episode_path.exists():
            logger.info(f"Successfully generated episode: {episode_path}")
            
            # Extract metadata for archiving
            metadata = extract_episode_metadata(episode_path)
            
            return {
                "path": episode_path,
                "title": chat_title,
                "timestamp": datetime.now().isoformat(),
                "summary": metadata.get("summary", f"Episode generated from chat: {chat_title}"),
                "emotional_state": metadata.get("emotional_state", "Neutral"),
                "location": metadata.get("location", "The Nexus"),
                "source": source
            }
        else:
            logger.warning(f"Failed to generate episode for chat: {chat_title}")
            return None
            
    except Exception as e:
        logger.error(f"Error processing chat '{chat_title}': {e}")
        return None

def extract_episode_metadata(episode_path: Path) -> Dict[str, Any]:
    """Extract key metadata from a generated episode file."""
    metadata = {
        "summary": "",
        "emotional_state": "Neutral",
        "location": "The Nexus"
    }
    
    try:
        if not episode_path.exists():
            return metadata
            
        with open(episode_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract summary
        summary_section = False
        summary_lines = []
        
        # Extract emotional state
        emotional_match = re.search(r"Emotional State:\s*(.+?)(?:\n|$)", content)
        if emotional_match:
            metadata["emotional_state"] = emotional_match.group(1).strip()
            
        # Extract location
        location_match = re.search(r"Location:\s*(.+?)(?:\n|$)", content)
        if location_match:
            metadata["location"] = location_match.group(1).strip()
            
        # Extract summary from dedicated section
        lines = content.split("\n")
        for line in lines:
            if line.strip().startswith("## 📝 Summary"):
                summary_section = True
                continue
            elif summary_section and line.strip().startswith("##"):
                summary_section = False
            elif summary_section and line.strip():
                summary_lines.append(line.strip())
                
        if summary_lines:
            metadata["summary"] = " ".join(summary_lines)
        else:
            # Try to extract a title as fallback summary
            title_match = re.search(r"# (.+?)(?:\n|$)", content)
            if title_match:
                metadata["summary"] = f"Episode: {title_match.group(1).strip()}"
                
    except Exception as e:
        logger.error(f"Error extracting metadata from episode: {e}")
        
    return metadata

def send_to_discord(discord_service, episode_data):
    """Send the generated episode to Discord if the service is available."""
    if not discord_service:
        logger.warning("Discord service not available")
        return False
    
    if not episode_data or not episode_data.get("path"):
        logger.warning("Invalid episode data for Discord")
        return False
        
    try:
        episode_path = episode_data["path"]
        # Read the episode content
        with open(episode_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract title for the message
        title = episode_data.get("title", "Dreamscape Episode")
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
        
        # Get summary if available
        summary = episode_data.get("summary", "")
        emotional_state = episode_data.get("emotional_state", "")
        location = episode_data.get("location", "")
        
        # Format a rich Discord message
        discord_message = f"📜 **New Dreamscape Episode**: {title}\n\n"
        
        if summary:
            discord_message += f"> {summary}\n\n"
        
        if emotional_state and location:
            discord_message += f"**Current State**: {emotional_state} in {location}\n\n"
        
        # Add a preview of the content (truncated)
        discord_message += "```md\n"
        # Get the first 1500 characters, but ensure we don't cut in the middle of a line
        preview_lines = []
        total_length = 0
        for line in content.split('\n'):
            if total_length + len(line) + 1 > 1500:  # +1 for newline
                preview_lines.append("...")
                break
            preview_lines.append(line)
            total_length += len(line) + 1
        
        discord_message += "\n".join(preview_lines) + "\n```"
        
        # Send the message with preview
        discord_service.send_message(discord_message)
        
        # Also send the file
        discord_service.send_file(
            file_path=str(episode_path),
            content=f"📚 Full episode: **{title}**",
            channel_id=None  # Uses default channel
        )
        
        logger.info(f"Episode sent to Discord: {title}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending to Discord: {e}")
        return False

def save_archive(processed_chats, archive_file="processed_dreamscape_chats.json"):
    """Save the list of processed chats to an archive file."""
    try:
        # Load existing archive if it exists
        existing_processed = []
        if os.path.exists(archive_file):
            try:
                with open(archive_file, "r", encoding="utf-8") as f:
                    existing_archive = json.load(f)
                    existing_processed = existing_archive.get("processed_chats", [])
            except:
                pass
                
        # Merge with new processed chats
        all_processed = existing_processed.copy()
        
        # Convert processed_chats to list if it's a single item
        if not isinstance(processed_chats, list):
            processed_chats = [processed_chats]
            
        # Add new chats, avoiding duplicates
        for chat in processed_chats:
            # Skip if None or invalid
            if not chat:
                continue
                
            # Normalize to dict if just a string
            if isinstance(chat, str):
                chat = {"title": chat, "timestamp": datetime.now().isoformat()}
                
            # Check if chat is already in archive by title
            if not any(pc.get("title") == chat.get("title") for pc in all_processed):
                all_processed.append(chat)
        
        # Create archive structure
        archive = {
            "last_updated": datetime.now().isoformat(),
            "processed_chats": all_processed
        }
        
        # Save to file
        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump(archive, f, indent=2)
            
        logger.info(f"Archive saved to {archive_file} with {len(all_processed)} chats")
        return True
        
    except Exception as e:
        logger.error(f"Error saving archive: {e}")
        return False

def analyze_episode_chain(chain_path):
    """
    Analyze the episode chain and print interesting statistics.
    
    Args:
        chain_path: Path to the episode chain JSON file
    """
    if not os.path.exists(chain_path):
        logger.info(f"Episode chain not found at: {chain_path}")
        return
        
    try:
        with open(chain_path, "r", encoding="utf-8") as f:
            chain_data = json.load(f)
            
        episode_count = chain_data.get("episode_count", 0)
        ongoing_quests = chain_data.get("ongoing_quests", [])
        completed_quests = chain_data.get("completed_quests", [])
        last_episode = chain_data.get("last_episode", "")
        last_location = chain_data.get("last_location", "")
        current_emotional_state = chain_data.get("current_emotional_state", "")
        
        logger.info(f"===== Episode Chain Analysis =====")
        logger.info(f"Total episodes: {episode_count}")
        logger.info(f"Last episode: {last_episode}")
        logger.info(f"Current location: {last_location}")
        logger.info(f"Current emotional state: {current_emotional_state}")
        logger.info(f"Ongoing quests: {len(ongoing_quests)}")
        logger.info(f"Completed quests: {len(completed_quests)}")
        
        if ongoing_quests or completed_quests:
            quest_completion_rate = len(completed_quests)/(len(ongoing_quests) + len(completed_quests)) * 100 
            logger.info(f"Quest completion rate: {quest_completion_rate:.1f}%")
        
        # Analyze episode progression
        episodes = chain_data.get("episodes", [])
        if episodes:
            earliest_date = datetime.fromisoformat(episodes[0].get("timestamp", datetime.now().isoformat()))
            latest_date = datetime.fromisoformat(episodes[-1].get("timestamp", datetime.now().isoformat()))
            
            # Calculate days of narrative
            days_elapsed = (latest_date - earliest_date).days
            if days_elapsed > 0:
                episodes_per_day = episode_count / days_elapsed
                logger.info(f"Narrative spans {days_elapsed} days ({episodes_per_day:.2f} episodes/day)")
                
            # Emotional journey analysis if we have enough episodes
            if episode_count >= 3:
                emotional_states = [ep.get("emotional_state", "Unknown") for ep in episodes[-3:]]
                logger.info(f"Recent emotional arc: {' → '.join(emotional_states)}")
                
            # Location journey
            recent_locations = []
            for ep in episodes[-5:]:
                location = ep.get("location", "")
                if location and location not in recent_locations:
                    recent_locations.append(location)
            
            if recent_locations:
                logger.info(f"Recent locations: {' → '.join(recent_locations)}")
        
        logger.info(f"================================")
        
    except Exception as e:
        logger.error(f"Error analyzing episode chain: {e}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Generate dreamscape episodes from chat histories")
    parser.add_argument("--chat", help="Title of specific chat to generate episode from")
    parser.add_argument("--all", action="store_true", help="Generate episodes for all chats")
    parser.add_argument("--list", action="store_true", help="List available chats and exit")
    parser.add_argument("--discord", action="store_true", help="Send generated episodes to Discord")
    parser.add_argument("--web", action="store_true", help="Use web scraping for chat retrieval")
    parser.add_argument("--status", action="store_true", help="Show episode chain status and exit")
    parser.add_argument("--force", action="store_true", help="Process chats even if already processed")
    parser.add_argument("--count", type=int, default=1, help="Number of episodes to generate (default: 1)")
    parser.add_argument("--analysis", action="store_true", help="Perform detailed narrative analysis on the episode chain")
    args = parser.parse_args()
    
    # Initialize services
    services = initialize_services()
    if not services:
        logger.error("Failed to initialize services")
        sys.exit(1)
        
    chat_manager = services.get("chat_manager")
    config_manager = services.get("config_manager")
    dreamscape_service = services.get("dreamscape_service")
    context_synthesizer = services.get("context_synthesizer")
    discord_service = services.get("discord_service")
    
    # Show episode chain status if requested
    if args.status or args.analysis:
        chain_path = Path("memory") / "episode_chain.json"
        analyze_episode_chain(chain_path)
        if args.status:  # Exit if only status requested
            sys.exit(0)
    
    # Get excluded chats
    excluded_chats = get_excluded_chats(config_manager)
    
    # Get available chats
    available_chats = get_available_chats(chat_manager, excluded_chats, use_web=args.web)
    
    # Get previously processed chats to avoid duplicate processing
    previously_processed = get_previously_processed_chats()
    previously_processed_titles = [p.get("title") if isinstance(p, dict) else p for p in previously_processed]
    
    # List chats if requested
    if args.list:
        logger.info("=== Available Chats ===")
        for i, chat in enumerate(available_chats):
            title = chat.get("title", "") if isinstance(chat, dict) else chat
            processed = "✓" if title in previously_processed_titles else " "
            logger.info(f"{i+1}. [{processed}] {title}")
        logger.info(f"Total: {len(available_chats)} chats")
        sys.exit(0)
    
    processed_count = 0
    processed_chats = []
    
    # Process a single chat if specified
    if args.chat:
        # Find the chat by title
        chat_title = args.chat
        
        # Check if already processed and not forcing
        if chat_title in previously_processed_titles and not args.force:
            logger.info(f"Chat already processed: {chat_title}. Use --force to process again.")
            sys.exit(0)
            
        # Process the chat
        episode_data = process_chat(
            chat_manager, 
            chat_title, 
            use_web=args.web,
            context_synthesizer=context_synthesizer
        )
        if episode_data:
            processed_chats.append(episode_data)
            processed_count += 1
            
            # Send to Discord if requested
            if args.discord:
                send_to_discord(discord_service, episode_data)
                
    # Process all chats if requested
    elif args.all:
        # Filter out already processed chats unless forcing
        if not args.force:
            original_count = len(available_chats)
            available_chats = [
                chat for chat in available_chats 
                if (chat.get("title", "") if isinstance(chat, dict) else chat) not in previously_processed_titles
            ]
            logger.info(f"Filtered out {original_count - len(available_chats)} already processed chats")
            
        # Process each chat
        for i, chat in enumerate(available_chats):
            # Only process up to the specified count
            if processed_count >= args.count:
                break
                
            chat_title = chat.get("title", "") if isinstance(chat, dict) else chat
            episode_data = process_chat(
                chat_manager, 
                chat_title, 
                use_web=args.web,
                context_synthesizer=context_synthesizer
            )
            
            if episode_data:
                processed_chats.append(episode_data)
                processed_count += 1
                
                # Send to Discord if requested
                if args.discord:
                    send_to_discord(discord_service, episode_data)
                    
                # Small sleep to avoid rate limiting
                time.sleep(1)
                
    else:
        # Default action: process one random chat
        if available_chats:
            import random
            
            if not args.force:
                # Filter out already processed chats
                unprocessed_chats = [
                    chat for chat in available_chats 
                    if (chat.get("title", "") if isinstance(chat, dict) else chat) not in previously_processed_titles
                ]
                
                if unprocessed_chats:
                    chosen_chat = random.choice(unprocessed_chats)
                else:
                    logger.info("All chats have been processed. Use --force to process again.")
                    sys.exit(0)
            else:
                chosen_chat = random.choice(available_chats)
                
            chat_title = chosen_chat.get("title", "") if isinstance(chosen_chat, dict) else chosen_chat
            episode_data = process_chat(
                chat_manager, 
                chat_title, 
                use_web=args.web,
                context_synthesizer=context_synthesizer
            )
            
            if episode_data:
                processed_chats.append(episode_data)
                processed_count += 1
                
                # Send to Discord if requested
                if args.discord:
                    send_to_discord(discord_service, episode_data)
        else:
            logger.warning("No available chats to process")
            
    # Save the processed chats to archive
    if processed_chats:
        save_archive(processed_chats)
        
    # Show episode chain status after processing
    if processed_count > 0:
        chain_path = Path("memory") / "episode_chain.json"
        analyze_episode_chain(chain_path)
        
    logger.info(f"Processed {processed_count} chats")
    
if __name__ == "__main__":
    main() 

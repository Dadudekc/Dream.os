#!/usr/bin/env python3
"""
DigitalDreamscapeEpisodes Pipeline Class

This class integrates with your existing Dream.OS architecture to:
1. Get the list of available chats (excluding specified ones)
2. For each chat:
   - Retrieve the chat history
   - Generate a dreamscape episode
   - Save it to the output directory
   - Optionally post it to Discord

The class uses your service registry and dependency injection system.
"""

import os
import sys
import time
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Setup logging (you can later move this to a dedicated logging setup)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("dreamscape_automation.log")
    ]
)
logger = logging.getLogger("dreamscape_automation")


class DigitalDreamscapeEpisodesPipeline:
    def __init__(self):
        self.logger = logger
        self.services = self.initialize_services()
        if self.services:
            self.chat_manager = self.services.get("chat_manager")
            self.config_manager = self.services.get("config_manager")
            self.discord_service = None
        else:
            self.chat_manager = None
            self.config_manager = None

    def initialize_services(self) -> Optional[Dict[str, Any]]:
        """Initialize required services from the service registry or directly."""
        try:
            from core.services.service_registry import ServiceRegistry
            from config.ConfigManager import ConfigManager
            from core.ChatManager import ChatManager
            from core.PathManager import PathManager
            from core.TemplateManager import TemplateManager
            from core.services.dreamscape_generator_service import DreamscapeGenerationService

            self.logger.info("Initializing services...")

            # Get service registry
            service_registry = ServiceRegistry()

            # Try to get services from registry first
            config_manager = service_registry.get("config_manager")
            chat_manager = service_registry.get("chat_manager")

            # If not available, initialize directly
            if not config_manager:
                config_manager = ConfigManager()
                self.logger.info("ConfigManager initialized directly")
            if not chat_manager:
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
                self.logger.info("ChatManager initialized directly")

            # Initialize the dreamscape service
            path_manager = PathManager()
            template_manager = TemplateManager(
                template_dir=os.path.join(os.getcwd(), "templates", "dreamscape_templates")
            )
            dreamscape_service = DreamscapeGenerationService(
                path_manager=path_manager,
                template_manager=template_manager,
                logger=self.logger
            )
            # Set the dreamscape service on the chat manager
            chat_manager.dreamscape_service = dreamscape_service

            self.logger.info("Services initialized successfully")
            return {
                "config_manager": config_manager,
                "chat_manager": chat_manager,
                "dreamscape_service": dreamscape_service
            }
        except Exception as e:
            self.logger.error(f"Error initializing services: {e}")
            return None

    def get_excluded_chats(self) -> List[str]:
        """Get the list of chats to exclude from processing."""
        excluded_chats = [
            "ChatGPT", "Sora", "Explore GPTs", "Axiom",
            "work project", "prompt library", "Bot", "smartstock-pro"
        ]
        if self.config_manager and hasattr(self.config_manager, "get"):
            config_excluded = self.config_manager.get("excluded_chats", [])
            if config_excluded:
                excluded_chats = config_excluded
        return excluded_chats

    def get_available_chats(self) -> List[Dict[str, Any]]:
        """Get all available chats, filtering out excluded ones."""
        try:
            all_chats = self.chat_manager.get_all_chat_titles()
            if not all_chats:
                self.logger.warning("No chats found")
                return []
            excluded = self.get_excluded_chats()
            available = []
            for chat in all_chats:
                title = chat.get("title", "")
                if title and not any(excluded_str in title for excluded_str in excluded):
                    available.append(chat)
            self.logger.info(f"Found {len(available)} chats after filtering {len(all_chats)} total chats")
            return available
        except Exception as e:
            self.logger.error(f"Error getting available chats: {e}")
            return []

    def process_chat(self, chat_title: str) -> Optional[Path]:
        """Process a single chat to generate a dreamscape episode."""
        try:
            self.logger.info(f"Processing chat: {chat_title}")
            episode_path = self.chat_manager.generate_dreamscape_episode(chat_title)
            if episode_path and episode_path.exists():
                self.logger.info(f"Successfully generated episode: {episode_path}")
                return episode_path
            else:
                self.logger.warning(f"Failed to generate episode for chat: {chat_title}")
                return None
        except Exception as e:
            self.logger.error(f"Error processing chat '{chat_title}': {e}")
            return None

    def send_to_discord(self, episode_path: Path) -> bool:
        """Send the generated episode to Discord if the service is available."""
        if not self.discord_service:
            self.logger.warning("Discord service not available")
            return False
        try:
            with open(episode_path, "r", encoding="utf-8") as f:
                content = f.read()
            title = "Dreamscape Episode"
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            self.discord_service.send_message(
                f"📜 **New Dreamscape Episode**: {title}\n\n```md\n{content[:1900]}...\n```",
                channel_id=None  # Uses default channel
            )
            self.discord_service.send_file(
                file_path=str(episode_path),
                content=f"📚 Full episode: **{title}**",
                channel_id=None
            )
            self.logger.info(f"Episode sent to Discord: {title}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending to Discord: {e}")
            return False

    def save_archive(self, processed_chats: List[Dict[str, Any]], archive_file: str = "processed_dreamscape_chats.json") -> bool:
        """Save the list of processed chats to an archive file."""
        try:
            archive = {
                "last_updated": datetime.now().isoformat(),
                "processed_chats": processed_chats
            }
            with open(archive_file, "w", encoding="utf-8") as f:
                json.dump(archive, f, indent=2)
            self.logger.info(f"Archive saved to {archive_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving archive: {e}")
            return False

    def run(self, args: argparse.Namespace) -> int:
        """Main method to run the pipeline based on command-line arguments."""
        if args.discord:
            try:
                from core.services.service_registry import ServiceRegistry
                service_registry = ServiceRegistry()
                self.discord_service = service_registry.get("discord_manager")
                if not self.discord_service:
                    self.logger.warning("Discord service not available, continuing without Discord integration")
            except Exception as e:
                self.logger.error(f"Error obtaining Discord service: {e}")
        
        if args.list:
            available = self.get_available_chats()
            if available:
                print("Available chats:")
                for i, chat in enumerate(available, 1):
                    print(f"{i}. {chat.get('title', 'Untitled')}")
            else:
                print("No chats found")
            return 0

        if args.chat:
            episode_path = self.process_chat(args.chat)
            if episode_path:
                print(f"Successfully generated episode: {episode_path}")
                if args.discord and self.discord_service:
                    self.send_to_discord(episode_path)
                return 0
            else:
                print(f"Failed to generate episode for chat: {args.chat}")
                return 1

        if args.all:
            available = self.get_available_chats()
            if not available:
                print("No chats available to process")
                return 1
            processed = []
            for i, chat in enumerate(available, 1):
                chat_title = chat.get("title", "")
                print(f"Processing {i}/{len(available)}: {chat_title}")
                episode_path = self.process_chat(chat_title)
                if episode_path:
                    processed.append({
                        "title": chat_title,
                        "episode_path": str(episode_path),
                        "timestamp": datetime.now().isoformat()
                    })
                    if args.discord and self.discord_service:
                        self.send_to_discord(episode_path)
                    time.sleep(2)
            self.save_archive(processed)
            print(f"Successfully processed {len(processed)} of {len(available)} chats")
            return 0

        # If no arguments, show help
        print("No valid arguments provided. Use --help for usage instructions.")
        return 1

    def shutdown(self):
        """Shut down services and clean up."""
        if self.chat_manager:
            self.chat_manager.shutdown_driver()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate dreamscape episodes from chat histories")
    parser.add_argument("--chat", help="Title of specific chat to generate episode from")
    parser.add_argument("--all", action="store_true", help="Generate episodes for all chats")
    parser.add_argument("--list", action="store_true", help="List available chats")
    parser.add_argument("--discord", action="store_true", help="Send episodes to Discord")
    return parser.parse_args()


def main():
    args = parse_args()
    pipeline = DigitalDreamscapeEpisodesPipeline()
    ret = pipeline.run(args)
    pipeline.shutdown()
    sys.exit(ret)


if __name__ == "__main__":
    main()

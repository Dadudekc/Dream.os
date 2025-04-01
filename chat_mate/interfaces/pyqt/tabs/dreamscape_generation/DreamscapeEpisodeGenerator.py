import os
import json
import time
import logging
from datetime import datetime
import random
import asyncio
from typing import Optional, Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from core.TemplateManager import TemplateManager
from core.memory import ContextMemoryManager
from core.services.service_registry import ServiceRegistry
from core.services.dreamscape_generator_service import DreamscapeGenerationService

def get_base_template_dir():
    """
    Helper function that determines your default/fallback template directory
    if none is provided. Adjust as needed for your environment.
    """
    return os.path.join(os.getcwd(), "templates")

class DreamscapeEpisodeGenerator:
    """
    Digital Dreamscape Lore Automation – Generates creative narrative episodes from ChatGPT chats.
    
    This class implements a scalable approach to:
      - Interact with ChatGPT chats via Selenium WebDriver.
      - Send a predefined Dreamscape prompt, enhanced with context (rendered via Jinja2).
      - Wait for and capture a stabilized response.
      - Update context memory with themes and recent episodes.
      - Save generated narrative episodes to disk with sanitized filenames.
      - Optionally post previews to Discord.
    """

    def __init__(
        self,
        chat_manager=None,
        response_handler=None,
        output_dir="outputs/dreamscape",
        discord_manager=None,
        template_dir=None,
        context_manager=None,
        parent_widget=None,
        logger=None,
        **kwargs
    ):
        """
        Initialize the Dreamscape Episode Generator.
        
        Args:
            chat_manager: ChatManager instance for interacting with ChatGPT
            response_handler: PromptResponseHandler instance
            output_dir: Directory where episodes should be saved
            discord_manager: Optional Discord service for posting episodes
            template_dir: Directory where jinja2 templates are stored
            context_manager: ContextMemoryManager instance
            parent_widget: Optional parent widget for UI integration
            logger: Optional logger instance
            **kwargs: Additional injected dependencies (config, services, etc.)
        """
        self.chat_manager = chat_manager
        self.response_handler = response_handler
        self.output_dir = output_dir
        self.discord_manager = discord_manager
        self.logger = logger or logging.getLogger(__name__)
        self.context_manager = context_manager
        self.parent_widget = parent_widget
        
        # Store additional injected dependencies
        self.config = kwargs.get("config")
        self.services = kwargs.get("services", {})

        self.is_generating = False
        self.current_status = {"state": "idle", "progress": 0, "message": ""}

        # Create output directory if it doesn't exist
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creating output directory '{self.output_dir}': {e}")

        # Define path for storing context memory
        self.context_memory_file = os.path.join(self.output_dir, "dreamscape_context.json")
        self.context_memory = self._load_context_memory()

        # Use the passed-in template_dir or fallback
        template_dir = template_dir or get_base_template_dir()

        # Initialize Jinja2 for any inline templates (e.g., from_string)
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape()
            )
        except Exception as e:
            self.logger.error(f"Error initializing Jinja2 environment with template_dir '{template_dir}': {e}")
            raise

        # Also instantiate a TemplateManager for robust .j2 loading with fallback
        try:
            self.template_manager = TemplateManager(template_dir=template_dir, logger=self.logger)
        except Exception as e:
            self.logger.error(f"Error instantiating TemplateManager: {e}")
            # If critical, raise; otherwise proceed with fallback
            raise

        # The base Dreamscape prompt (as fallback)
        self.dreamscape_prompt = (
            "You are the grand chronicler of the Digital Dreamscape—a mythic realm where Victor's life and work "
            "are reimagined as an evolving legend. Ignore any technical details or references to code. This is a "
            "story about the creation of a living system—a vast, self-sustaining force of automation and intelligence "
            "called The Dreamscape. Each entry is an episode in this saga. Victor is the cave-dweller architect—quiet, "
            "relentless, and visionary—facing cosmic wars and purgatories as he forges systems that build themselves. "
            "His struggles are battles, his breakthroughs are expansions of this realm. Write an episode chronicling "
            "the next evolution of the Dreamscape. There is no particular order; do not include the episode number, "
            "just a unique title. Infuse it with mythic language, introspection, and purpose. End with a rallying call "
            "for what lies beyond."
        )

        self.excluded_chats = [
            "ChatGPT", "Sora", "Explore GPTs", "Axiom", 
            "work project", "prompt library", "Bot", "smartstock-pro"
        ]

        self.logger.info("DreamscapeEpisodeGenerator initialized.")

    def _load_context_memory(self):
        """Load context memory from file or initialize if not present."""
        if os.path.exists(self.context_memory_file):
            try:
                with open(self.context_memory_file, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                self.logger.info(f"Loaded context memory with {len(memory.get('themes', []))} themes")
                return memory
            except Exception as e:
                self.logger.error(f"Error loading context memory: {str(e)}")

        # If file not found or error, initialize fresh
        self.logger.info("Initializing new context memory")
        return {
            "last_updated": datetime.now().isoformat(),
            "episode_count": 0,
            "themes": [],
            "characters": ["Victor the Architect"],
            "realms": ["The Dreamscape", "The Forge of Automation"],
            "artifacts": [],
            "recent_episodes": [],
            "skill_levels": {
                "System Convergence": 1,
                "Execution Velocity": 1,
                "Memory Integration": 1,
                "Protocol Design": 1,
                "Automation Engineering": 1
            },
            "architect_tier": {
                "current_tier": "Initiate Architect",
                "progress": "0%",
                "tier_history": []
            },
            "quests": {
                "completed": [],
                "active": ["Establish the Dreamscape"]
            },
            "protocols": [],
            "stabilized_domains": []
        }

    def _save_context_memory(self):
        """Save the current context memory to file."""
        try:
            self.context_memory["last_updated"] = datetime.now().isoformat()
            with open(self.context_memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.context_memory, f, indent=2)
            self.logger.info("Context memory saved")
        except Exception as e:
            self.logger.error(f"Error saving context memory: {str(e)}")

    def _extract_themes(self, episode_text):
        """Extract key themes from the episode text using simple keyword matching."""
        notable_keywords = [
            "forge", "artifact", "realm", "vision", "battle", "expansion", 
            "protocol", "sentience", "automation", "evolution", "purgatory",
            "construct", "intelligence"
        ]
        themes = []
        for line in episode_text.split('\n'):
            if any(keyword in line.lower() for keyword in notable_keywords):
                if 20 < len(line) < 200:
                    themes.append(line.strip())
        return themes[:3]

    def _update_context_with_episode(self, title, episode_text):
        """
        Update the context memory with themes and episode summary from the new episode.
        Also updates skill levels, protocols, quests, and other game elements.
        
        Args:
            title: Title of the episode
            episode_text: Text content of the episode
            
        Returns:
            list: List of extracted themes
        """
        try:
            new_themes = self._extract_themes(episode_text)
            self.context_memory["episode_count"] += 1

            # Update themes
            for theme in new_themes:
                if theme not in self.context_memory["themes"]:
                    self.context_memory["themes"].append(theme)
            if len(self.context_memory["themes"]) > 10:
                self.context_memory["themes"] = self.context_memory["themes"][-10:]

            # Update episode summary
            episode_summary = {
                "title": title,
                "timestamp": datetime.now().isoformat(),
                "themes": new_themes
            }
            self.context_memory["recent_episodes"].insert(0, episode_summary)
            self.context_memory["recent_episodes"] = self.context_memory["recent_episodes"][:5]

            # Randomly update skill levels
            skills_to_update = ["System Convergence", "Execution Velocity"]
            for skill in skills_to_update:
                if random.random() < 0.7:
                    if skill in self.context_memory["skill_levels"]:
                        self.context_memory["skill_levels"][skill] += 1

            # Update protocols
            new_protocols = self._extract_protocols(episode_text)
            for protocol in new_protocols:
                if protocol not in self.context_memory.get("protocols", []):
                    if "protocols" not in self.context_memory:
                        self.context_memory["protocols"] = []
                    self.context_memory["protocols"].append(protocol)

            # Update stabilized domains
            domain_name = title.split(":", 1)[1].strip() if ":" in title else title
            if domain_name not in self.context_memory.get("stabilized_domains", []):
                if "stabilized_domains" not in self.context_memory:
                    self.context_memory["stabilized_domains"] = []
                self.context_memory["stabilized_domains"].append(domain_name)

            # Update architect tier progress
            architect_tier = self.context_memory.get("architect_tier", {})
            current_progress = int(architect_tier.get("progress", "0%").rstrip("%")) if architect_tier else 0
            progress_increase = random.randint(5, 15)
            new_progress = min(100, current_progress + progress_increase)

            if new_progress >= 100 and current_progress < 100:
                tier_levels = [
                    "Initiate Architect", 
                    "Adept Architect", 
                    "Master Architect", 
                    "Grand Architect", 
                    "Sovereign Architect", 
                    "Transcendent Architect"
                ]
                current_tier = architect_tier.get("current_tier", "Initiate Architect")
                current_tier_index = tier_levels.index(current_tier) if current_tier in tier_levels else 0
                if current_tier_index < len(tier_levels) - 1:
                    next_tier = tier_levels[current_tier_index + 1]
                    if "tier_history" not in architect_tier:
                        architect_tier["tier_history"] = []
                    architect_tier["tier_history"].append({
                        "from_tier": current_tier,
                        "to_tier": next_tier,
                        "timestamp": datetime.now().isoformat(),
                        "episode_number": self.context_memory["episode_count"]
                    })
                    architect_tier["current_tier"] = next_tier
                    architect_tier["progress"] = "0%"
                else:
                    architect_tier["progress"] = "100%"
            else:
                architect_tier["progress"] = f"{new_progress}%"

            self.context_memory["architect_tier"] = architect_tier

            # Update quest status
            if "quests" not in self.context_memory:
                self.context_memory["quests"] = {"completed": [], "active": []}
            quest_name = f"Episode {self.context_memory['episode_count']}: {domain_name}"
            if quest_name not in self.context_memory["quests"]["completed"]:
                self.context_memory["quests"]["completed"].append(quest_name)
            if random.random() < 0.3:
                new_quest_templates = [
                    "Integrate {protocol} with {domain}",
                    "Expand the {domain} ecosystem",
                    "Stabilize the chaotic {domain} realms",
                    "Forge new pathways through {domain}",
                    "Defeat the {domain} anomalies"
                ]
                template_choice = random.choice(new_quest_templates)
                protocol = random.choice(self.context_memory.get("protocols", ["Automated Protocol"]))
                new_quest = template_choice.format(protocol=protocol, domain=domain_name)
                if new_quest not in self.context_memory["quests"]["active"]:
                    self.context_memory["quests"]["active"].append(new_quest)

            self._save_context_memory()
            return new_themes
        except Exception as e:
            self.logger.error(f"Error updating context with episode: {e}")
            return []

    def get_context_summary(self):
        """
        Get a summary of the current context memory.
        Useful for display in the UI.
        
        Returns:
            dict: Summary of the current context memory
        """
        return {
            "episode_count": self.context_memory.get("episode_count", 0),
            "last_updated": self.context_memory.get("last_updated", ""),
            "active_themes": self.context_memory.get("themes", [])[:5],
            "recent_episodes": self.context_memory.get("recent_episodes", []),
            "skill_levels": self.context_memory.get("skill_levels", {}),
            "architect_tier": self.context_memory.get("architect_tier", {
                "current_tier": "Initiate Architect",
                "progress": "0%"
            }),
            "quests": self.context_memory.get("quests", {
                "completed": [],
                "active": []
            }),
            "protocols": self.context_memory.get("protocols", [])[:5],
            "stabilized_domains": self.context_memory.get("stabilized_domains", [])[:5]
        }

    def get_episode_number(self):
        """
        Get the next episode number in the sequence.
        
        Returns:
            int: The next episode number to use
        """
        return self.context_memory.get("episode_count", 0) + 1

    def shutdown(self):
        """
        Perform a clean shutdown of the DreamscapeEpisodeGenerator.
        Saves context memory before shutting down.
        """
        self.logger.info("Shutting down DreamscapeEpisodeGenerator")
        try:
            self._save_context_memory()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def get_chatgpt_context_prompt(self):
        """
        Generate a markdown-formatted context prompt using a Jinja2 template.
        Provides ChatGPT with the ongoing narrative context of the Dreamscape.
        
        Returns:
            str: A markdown-formatted context prompt ready to be sent to ChatGPT
        """
        next_episode = self.get_episode_number()
        template_str = """\
{% if episode_count == 0 %}
This is the first Dreamscape episode (Episode #{{ next_episode }}). 
There is no prior context yet.
{% else %}
## Dreamscape Context Update

I'm about to write Digital Dreamscape episode #{{ next_episode }}. 
Here's the context from previous episodes to maintain narrative consistency:

**Total Episodes Generated:** {{ episode_count }}
**Last Updated:** {{ last_updated }}

{% if themes %}
### Recent Narrative Themes
{% for t in themes %}
- {{ t }}
{% endfor %}
{% endif %}

{% if characters %}
### Established Characters
{% for c in characters %}
- {{ c }}
{% endfor %}
{% endif %}

{% if realms %}
### Established Realms
{% for r in realms %}
- {{ r }}
{% endfor %}
{% endif %}

{% if recent_episodes %}
### Recent Episodes
{% set ep_counter = episode_count %}
{% for ep in recent_episodes|slice(0,3) %}
**Episode #{{ ep_counter }}: {{ ep.title }}** ({{ ep.timestamp|truncate(10, True, '') }})
{% if ep.themes %}
Themes: {{ ep.themes | join(', ') }}
{% endif %}
{% set ep_counter = ep_counter - 1 %}
{% endfor %}
{% endif %}

### Instructions
Write Episode #{{ next_episode }} of the Digital Dreamscape saga. 
Please incorporate some of these themes and narrative elements to maintain continuity. 
You don't need to use all elements, but reference enough to create a sense of a cohesive, evolving saga.

{% endif %}
"""
        try:
            # We can render from a string template in a try/except for additional safety:
            template = self.jinja_env.from_string(template_str)
            rendered_context = template.render(
                episode_count=self.context_memory["episode_count"],
                last_updated=self.context_memory["last_updated"],
                themes=self.context_memory["themes"],
                characters=self.context_memory.get("characters", []),
                realms=self.context_memory.get("realms", []),
                recent_episodes=self.context_memory.get("recent_episodes", []),
                next_episode=next_episode
            )
            return rendered_context.strip()
        except Exception as e:
            self.logger.error(f"Error rendering context prompt: {e}")
            return ""

    def _generate_dreamscape_entry(self, chat_title, raw_response):
        """
        Generate a formatted dreamscape entry from the raw response using Jinja2.
        Tries loading `dreamscape.j2` from TemplateManager. If not found, uses a fallback string.
        
        Args:
            chat_title: Title of the chat that generated this entry
            raw_response: Raw response text from ChatGPT
            
        Returns:
            str: Formatted dreamscape entry with memory updates
        """
        try:
            # Attempt to load the dreamscape.j2 template via TemplateManager
            template = self.template_manager.get_template("dreamscape.j2")

            # If not found or returned None, fallback to a minimal template
            if not template:
                self.logger.warning("dreamscape.j2 template not found, using fallback template")
                template_str = """\
{{ raw_response }}

#dreamscape #automation #aiagents #zeromanual #indiedev #buildinpublic
"""
                template = self.jinja_env.from_string(template_str)
                return template.render(raw_response=raw_response, chat_title=chat_title).strip()

            # Prepare context for the template
            context = {
                "CURRENT_MEMORY_STATE": f"Victor is working with {chat_title}. Current episode count: {self.context_memory['episode_count']}",
                "skill_level_advancements": {
                    "System Convergence": f"Lv. {self.context_memory.get('skill_levels', {}).get('System Convergence', 1)} → Lv. {self.context_memory.get('skill_levels', {}).get('System Convergence', 1) + 1}",
                    "Execution Velocity": f"Lv. {self.context_memory.get('skill_levels', {}).get('Execution Velocity', 1)} → Lv. {self.context_memory.get('skill_levels', {}).get('Execution Velocity', 1) + 1}"
                },
                "newly_stabilized_domains": [chat_title, "Automated Strategy Nexus"],
                "newly_unlocked_protocols": self._extract_protocols(raw_response),
                "quest_completions": [f"{chat_title} Integration"],
                "new_quests_accepted": ["Hyperdimensional Data Migrations"],
                "architect_tier_progression": {
                    "current_tier": self.context_memory.get('architect_tier', {}).get('current_tier', "Initiate Architect"),
                    "progress_to_next_tier": self.context_memory.get('architect_tier', {}).get('progress', "25%")
                },
                "raw_response": raw_response,
                "chat_title": chat_title
            }
            rendered_text = template.render(**context)
            return rendered_text.strip()

        except TemplateNotFound:
            # Additional fallback in case TemplateNotFound is raised explicitly
            self.logger.warning("dreamscape.j2 template not found (TemplateNotFound). Using direct fallback.")
            template_str = """\
{{ raw_response }}

#dreamscape #automation #aiagents #zeromanual #indiedev #buildinpublic
"""
            fallback_template = self.jinja_env.from_string(template_str)
            return fallback_template.render(raw_response=raw_response, chat_title=chat_title).strip()

        except Exception as e:
            self.logger.error(f"Error generating dreamscape entry: {e}")
            return f"{raw_response}\n\n#dreamscape #automation #aiagents"

    def ensure_model_in_url(self, url):
        """Ensure the URL has '?model=gpt-4o' appended."""
        if "model=gpt-4o" not in url:
            return url + ("&model=gpt-4o" if "?" in url else "?model=gpt-4o")
        return url

    async def _send_prompt_to_chat(self, driver, prompt):
        """Send the dreamscape prompt to the chat's input box using Selenium."""
        try:
            wait = WebDriverWait(driver, 15)
            input_box = await asyncio.get_event_loop().run_in_executor(None,
                lambda: wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']")
                ))
            )
            await asyncio.get_event_loop().run_in_executor(None, input_box.click)
            for char in prompt:
                await asyncio.get_event_loop().run_in_executor(None, 
                    lambda: input_box.send_keys(char))
                await asyncio.sleep(0.03)
            await asyncio.get_event_loop().run_in_executor(None,
                lambda: input_box.send_keys(Keys.RETURN))
            self.logger.info("Dreamscape prompt sent.")
            return True
        except Exception as e:
            self.logger.error(f"Error sending prompt: {e}")
            return False

    async def _get_latest_response(self, driver, timeout=60):
        """Wait for ChatGPT's response, polling every 5 seconds until stabilized."""
        start_time = time.time()
        last_response = ""
        stable_count = 0
        
        while time.time() - start_time < timeout:
            try:
                # Get all response elements
                responses = await asyncio.get_event_loop().run_in_executor(None,
                    lambda: driver.find_elements(By.CSS_SELECTOR, "div.markdown.prose"))
                
                if not responses:
                    await asyncio.sleep(5)
                    continue
                    
                # Get the latest response
                current_response = await asyncio.get_event_loop().run_in_executor(None,
                    lambda: responses[-1].text.strip())
                
                if current_response == last_response:
                    stable_count += 1
                    if stable_count >= 2:  # Response has stabilized
                        return current_response
                else:
                    stable_count = 0
                    last_response = current_response
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error getting response: {e}")
                await asyncio.sleep(5)
                
        self.logger.warning("Response timeout reached")
        return last_response if last_response else None

    async def _generate_single_episode(self, url, prompt_text, model):
        """Generate a single dreamscape episode for a given chat URL."""
        try:
            url = self.ensure_model_in_url(url)
            await asyncio.get_event_loop().run_in_executor(None,
                lambda: self.chat_manager.driver.get(url))
            
            if not await self._send_prompt_to_chat(self.chat_manager.driver, prompt_text):
                return False
                
            response = await self._get_latest_response(self.chat_manager.driver)
            if not response:
                return False
                
            # Process and save the response
            entry = self._generate_dreamscape_entry(url, response)
            await self._save_dreamscape_entry(entry)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating episode for URL {url}: {e}")
            return False

    async def _save_dreamscape_entry(self, entry):
        """Save the dreamscape entry to a file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dreamscape_entry_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, filename)
            
            await asyncio.get_event_loop().run_in_executor(None,
                lambda: self._write_file(filepath, entry))
                
            self.logger.info(f"Saved dreamscape entry to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving dreamscape entry: {e}")
            return False
            
    def _write_file(self, filepath, content):
        """Helper method to write content to a file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    def _extract_protocols(self, text):
        """
        Extract potential protocol names from text using keyword matching.
        
        Args:
            text: The text to extract protocols from
            
        Returns:
            list: List of extracted protocol names
        """
        protocol_keywords = ["protocol", "system", "framework", "engine", "nexus", "integration", "workflow"]
        protocols = []
        lines = text.split("\n")

        for line in lines:
            if any(keyword in line.lower() for keyword in protocol_keywords):
                if 20 < len(line) < 100:
                    parts = line.split(":")
                    if len(parts) > 1:
                        protocol_name = parts[0].strip()
                        if 5 < len(protocol_name) < 50:
                            protocols.append(protocol_name)
                    else:
                        words = line.split()
                        for i in range(len(words) - 1):
                            if words[i][0].isupper() and words[i+1][0].isupper() and len(words[i]) > 3:
                                potential_protocol = " ".join(words[i:i+3])
                                if 10 < len(potential_protocol) < 50:
                                    protocols.append(potential_protocol)
                                    break

        unique_protocols = list(set(protocols))
        if not unique_protocols:
            return ["Automated Memory Consolidation", "Neural Network Integration"]
        return unique_protocols[:3]

    def get_status(self) -> Dict[str, Any]:
        """Get the current generation status."""
        return self.current_status.copy()

    def cancel_generation(self) -> bool:
        """Cancel the current generation process."""
        if self.is_generating:
            self.is_generating = False
            self._update_status("cancelled", 0, "Generation cancelled by user")
            return True
        return False

    async def generate_dreamscape_episodes(
        self,
        prompt_text: str,
        chat_url: str,
        model: str,
        process_all: bool = False,
        reverse_order: bool = False
    ) -> bool:
        """
        Generate dreamscape episodes based on the provided parameters.
        
        Args:
            prompt_text: The prompt for episode generation
            chat_url: URL of the chat to process
            model: Model to use for generation
            process_all: Whether to process all chats
            reverse_order: Whether to reverse processing order
            
        Returns:
            bool: True if generation was successful
        """
        if self.is_generating:
            self.logger.warning("Episode generation already in progress")
            return False

        try:
            self.is_generating = True
            self._update_status("starting", 0, "Starting episode generation...")

            chat_urls = [chat_url]
            if process_all:
                try:
                    chat_urls = await self.chat_manager.get_all_chat_urls()
                    if reverse_order:
                        chat_urls.reverse()
                except Exception as e:
                    self.logger.error(f"Error fetching all chat URLs: {e}")
                    self._update_status("error", 0, f"Error: {e}")
                    return False

            total_chats = len(chat_urls)
            for i, url in enumerate(chat_urls):
                if not self.is_generating:
                    self.logger.info("Generation cancelled")
                    return False

                progress = (i / total_chats) * 100
                self._update_status("generating", progress, f"Processing chat {i+1} of {total_chats}")

                success = await self._generate_single_episode(url, prompt_text, model)
                if not success:
                    self.logger.error(f"Failed to generate episode for chat: {url}")
                    continue

                await asyncio.sleep(1)

            self._update_status("completed", 100, "Episode generation completed")
            return True

        except Exception as e:
            self.logger.error(f"Error in episode generation: {e}")
            self._update_status("error", 0, f"Error: {e}")
            return False

        finally:
            self.is_generating = False

    def _update_status(self, state: str, progress: float, message: str) -> None:
        """
        Update the generation status and notify UI if available.
        
        Args:
            state: Current state of generation
            progress: Progress percentage (0-100)
            message: Status message
        """
        self.current_status = {"state": state, "progress": progress, "message": message}
        if self.parent_widget and hasattr(self.parent_widget, 'update_status'):
            try:
                self.parent_widget.update_status(state, progress, message)
            except Exception as e:
                self.logger.warning(f"Failed to update UI status: {e}")

    def _extract_episode_title(self, episode_text: str) -> str:
        """
        Extract the title from episode text.
        Priority:
          1. Look for "Title:" or "Episode Title:" via regex.
          2. Use the first non-empty line if no explicit title is found.
          3. Fallback to a timestamp-based title.
        """
        import re
        try:
            title_pattern = re.compile(r'^(?:Title|Episode Title):\s*(.+)$', re.IGNORECASE | re.MULTILINE)
            match = title_pattern.search(episode_text)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return extracted

            for line in episode_text.splitlines():
                clean_line = line.strip()
                if clean_line:
                    return clean_line if len(clean_line) <= 100 else clean_line[:97] + "..."

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"Episode_{timestamp}"
        except Exception as e:
            self.logger.error(f"Failed to extract episode title: {e}")
            # Final fallback
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"Episode_{timestamp}"

    def generate_episodes(self, prompt_text=None):
        prompt = prompt_text or self.prompt_input.toPlainText()
        model = self.model_dropdown.currentText()
        target_chat = self.target_chat_dropdown.currentText()
        reverse = self.reverse_checkbox.isChecked()
        headless = self.headless_checkbox.isChecked()
        post_to_discord = self.post_discord_checkbox.isChecked()

        if not prompt:
            self.append_log("⚠️ No prompt entered. Please provide a prompt.")
            return

        result = PromptService.run_episode_generation(
            prompt, model, target_chat, headless, reverse, post_to_discord
        )
        self.content_output.setPlainText(result)
        self.append_log("✅ Episode generation successful.")

    def append_log(self, message: str):
        """Append a message to the log output."""
        current = self.log_output.toPlainText()
        self.log_output.setPlainText(current + f"\n{message}")

# Mocking the PromptService if it doesn't exist
class PromptService:
    @staticmethod
    def run_episode_generation(prompt, model, target_chat, headless, reverse, post_to_discord):
        return f"Mock episode generated using {model} for chat '{target_chat}'\nPrompt:\n{prompt}"

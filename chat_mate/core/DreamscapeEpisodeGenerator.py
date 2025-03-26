import os
import json
import time
import logging
from datetime import datetime
import random

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# JINJA2: import the Jinja2 environment classes and template loader
from jinja2 import Environment, FileSystemLoader, select_autoescape
from core.template_loader import load_template, get_base_template_dir

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

    def __init__(self, chat_manager, response_handler, output_dir,
                 discord_manager=None, template_dir=None):
        """
        Initialize the Dreamscape Episode Generator.
        
        Args:
            chat_manager: ChatManager instance for interacting with ChatGPT.
            response_handler: PromptResponseHandler instance.
            output_dir: Directory where episodes should be saved.
            discord_manager: Optional Discord service for posting episodes.
            template_dir: Directory where jinja2 templates are stored 
                          (defaults to 'templates' if None).
        """
        self.chat_manager = chat_manager
        self.response_handler = response_handler
        self.output_dir = output_dir
        self.discord_manager = discord_manager
        self.logger = logging.getLogger("DreamscapeEpisodeGenerator")
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Define path for storing context memory
        self.context_memory_file = os.path.join(self.output_dir, "dreamscape_context.json")
        self.context_memory = self._load_context_memory()
        
        # JINJA2: Set up Jinja2 environment using base template directory
        template_dir = template_dir or get_base_template_dir()
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape()
        )
        
        # Alternatively: If you prefer everything inline, you can do:
        # self.jinja_env = Environment(loader=BaseLoader()) and load templates from string.

        # The base Dreamscape prompt (still stored as a Python string for fallback).
        # We'll use Jinja2 in get_prompt_with_context to inject context dynamically.
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

    # ------------------------------------------------------------------------
    # JINJA2: Example Template Content
    # For reference, you might store these in separate .jinja2 files:
    #
    #  (1) context_prompt.jinja2
    #  (2) dreamscape_entry.jinja2
    #
    # You can then load them with: self.jinja_env.get_template('context_prompt.jinja2')
    # ------------------------------------------------------------------------

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
        # Extract themes from episode text
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
        
        # Update skill levels - randomly increase some skills
        skills_to_update = ["System Convergence", "Execution Velocity"]
        for skill in skills_to_update:
            if random.random() < 0.7:  # 70% chance to level up
                if skill in self.context_memory["skill_levels"]:
                    self.context_memory["skill_levels"][skill] += 1
        
        # Look for new protocols in the text
        new_protocols = self._extract_protocols(episode_text)
        for protocol in new_protocols:
            if protocol not in self.context_memory.get("protocols", []):
                if "protocols" not in self.context_memory:
                    self.context_memory["protocols"] = []
                self.context_memory["protocols"].append(protocol)
        
        # Add any domain name mentioned in the title as a newly stabilized domain
        domain_name = title.split(":", 1)[1].strip() if ":" in title else title
        if domain_name not in self.context_memory.get("stabilized_domains", []):
            if "stabilized_domains" not in self.context_memory:
                self.context_memory["stabilized_domains"] = []
            self.context_memory["stabilized_domains"].append(domain_name)
        
        # Update architect tier progress
        architect_tier = self.context_memory.get("architect_tier", {})
        current_progress = int(architect_tier.get("progress", "0%").rstrip("%")) if architect_tier else 0
        # Increment progress by 5-15%
        progress_increase = random.randint(5, 15)
        new_progress = min(100, current_progress + progress_increase)
        
        # If progress hits 100%, advance to next tier
        if new_progress >= 100 and current_progress < 100:
            # Define architect tier progression
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
            
            # Advance to next tier if not at max
            if current_tier_index < len(tier_levels) - 1:
                next_tier = tier_levels[current_tier_index + 1]
                
                # Record tier advancement
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
                # At max tier, stay at 100%
                architect_tier["progress"] = "100%"
        else:
            # Not hitting 100% yet, just update progress
            architect_tier["progress"] = f"{new_progress}%"
        
        self.context_memory["architect_tier"] = architect_tier
        
        # Update quest status
        # Add the current episode/domain as a completed quest
        if "quests" not in self.context_memory:
            self.context_memory["quests"] = {"completed": [], "active": []}
        
        quest_name = f"Episode {self.context_memory['episode_count']}: {domain_name}"
        
        if quest_name not in self.context_memory["quests"]["completed"]:
            self.context_memory["quests"]["completed"].append(quest_name)
        
        # Generate a new active quest occasionally
        if random.random() < 0.3:  # 30% chance for new quest
            new_quest_templates = [
                "Integrate {protocol} with {domain}",
                "Expand the {domain} ecosystem",
                "Stabilize the chaotic {domain} realms",
                "Forge new pathways through {domain}",
                "Defeat the {domain} anomalies"
            ]
            
            template = random.choice(new_quest_templates)
            protocol = random.choice(self.context_memory.get("protocols", ["Automated Protocol"]))
            new_quest = template.format(protocol=protocol, domain=domain_name)
            
            if new_quest not in self.context_memory["quests"]["active"]:
                self.context_memory["quests"]["active"].append(new_quest)
        
        # Save all updates
        self._save_context_memory()
        return new_themes

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
        self._save_context_memory()

    # ------------------------------------------------------------------------
    # JINJA2-based method to generate a context prompt
    # ------------------------------------------------------------------------
    def get_chatgpt_context_prompt(self):
        """
        Generate a markdown-formatted context prompt using a Jinja2 template.
        Provides ChatGPT with the ongoing narrative context of the Dreamscape.
        
        Returns:
            str: A markdown-formatted context prompt ready to be sent to ChatGPT
        """
        next_episode = self.get_episode_number()

        # If you have an external file like 'context_prompt.jinja2', do:
        #
        # template = self.jinja_env.get_template("context_prompt.jinja2")
        #
        # But here we'll inline a small Jinja2 string for example:
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

    # ------------------------------------------------------------------------
    # JINJA2-based method to generate a Dreamscape episode entry from raw text
    # ------------------------------------------------------------------------
    def _generate_dreamscape_entry(self, chat_title, raw_response):
        """
        Generate a formatted dreamscape entry from the raw response using Jinja2.
        
        Args:
            chat_title: Title of the chat that generated this entry
            raw_response: Raw response text from ChatGPT
            
        Returns:
            str: Formatted dreamscape entry with memory updates
        """
        try:
            # Try to load the dreamscape.j2 template using template_loader
            template = load_template("dreamscape.j2")
            
            # If no template found, use inline template
            if not template:
                self.logger.warning("dreamscape.j2 template not found, using fallback template")
                template_str = """\
{{ raw_response }}

#dreamscape #automation #aiagents #zeromanual #indiedev #buildinpublic
"""
                template = self.jinja_env.from_string(template_str)
                return template.render(raw_response=raw_response, chat_title=chat_title).strip()
            
            # Prepare data to inject for the full template
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
            
            # Render with full context
            rendered_text = template.render(**context)
            return rendered_text.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating dreamscape entry: {str(e)}")
            # Fallback to basic format if template rendering fails
            return f"{raw_response}\n\n#dreamscape #automation #aiagents"

    def ensure_model_in_url(self, url):
        """Ensure the URL has '?model=gpt-4o' appended."""
        if "model=gpt-4o" not in url:
            return url + ("&model=gpt-4o" if "?" in url else "?model=gpt-4o")
        return url

    def _send_prompt_to_chat(self, driver, prompt):
        """Send the dreamscape prompt to the chat's input box using Selenium."""
        try:
            wait = WebDriverWait(driver, 15)
            input_box = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']")
            ))
            input_box.click()
            # Optional: slow typing effect 
            for char in prompt:
                input_box.send_keys(char)
                time.sleep(0.03)
            input_box.send_keys(Keys.RETURN)
            self.logger.info("Dreamscape prompt sent.")
            return True
        except Exception as e:
            self.logger.error(f"Error sending prompt: {str(e)}")
            return False

    def _get_latest_response(self, driver, timeout=180, stable_period=10):
        """
        Wait for ChatGPT's dreamscape response:
          - Poll every 5 seconds until the response is stable for 'stable_period' seconds or until timeout.
        """
        self.logger.info("Waiting for Dreamscape response...")
        start_time = time.time()
        last_response = ""
        stable_start = None

        while time.time() - start_time < timeout:
            time.sleep(5)
            try:
                messages = driver.find_elements(By.CSS_SELECTOR, ".markdown.prose.w-full.break-words")
                if messages:
                    current_response = messages[-1].text.strip()
                    if current_response != last_response:
                        last_response = current_response
                        stable_start = time.time()
                        self.logger.info("Updated response received...")
                    else:
                        if stable_start and (time.time() - stable_start) >= stable_period:
                            self.logger.info("Response stabilized.")
                            break
            except Exception as e:
                self.logger.error(f"Error fetching response: {str(e)}")
        return last_response

    def _save_dreamscape_entry(self, entry_text, chat_title):
        """Save the dreamscape entry as a text file with a sanitized, timestamped filename."""
        try:
            safe_title = "".join(c for c in chat_title if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_").lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{safe_title}.txt"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(entry_text)
            self.logger.info(f"Dreamscape entry saved: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving dreamscape entry: {str(e)}")
            return None

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
                # Extract meaningful phrases that could be protocols
                if 20 < len(line) < 100:  # Reasonable length for a protocol name
                    parts = line.split(":")
                    if len(parts) > 1:
                        protocol_name = parts[0].strip()
                        if 5 < len(protocol_name) < 50:  # Reasonable length for just the name
                            protocols.append(protocol_name)
                    else:
                        # Try to extract based on capitalization patterns (e.g. "The Quantum Protocol")
                        words = line.split()
                        for i in range(len(words) - 1):
                            if words[i][0].isupper() and words[i+1][0].isupper() and len(words[i]) > 3:
                                potential_protocol = " ".join(words[i:i+3])
                                if 10 < len(potential_protocol) < 50:
                                    protocols.append(potential_protocol)
                                    break
        
        # Deduplicate and limit to 3 most promising protocols
        unique_protocols = list(set(protocols))
        if not unique_protocols:
            # Fallback to predefined protocols if none found
            return ["Automated Memory Consolidation", "Neural Network Integration"]
            
        return unique_protocols[:3]

    # ------------------------------------------------------------------------
    # MAIN METHOD: generate_dreamscape_episodes
    # ------------------------------------------------------------------------
    def generate_dreamscape_episodes(self, reverse_order=False, delay_between_chats=5):
        """
        Generate dreamscape episodes for each valid chat.
        
        Process:
          - Retrieve chats via the chat_manager.
          - Filter out excluded chats (now partial-match).
          - For each chat, navigate to its URL, send the context prompt, wait for stable response.
          - Then ask for the next Dreamscape episode, wait for stable response, update context, and save.
          - Optionally post a preview to Discord.
          
        Args:
            reverse_order (bool): Whether to process chats in reverse order
            delay_between_chats (int): Seconds to wait before/after each chat action.
          
        Returns:
            list: List of generated episode entries (strings).
        """
        self.logger.info(f"Starting Digital Dreamscape Lore Automation (Reverse order: {reverse_order})...")
        
        if not self.chat_manager:
            self.logger.error("Chat manager not initialized. Cannot generate episodes.")
            return []
        
        driver = self.chat_manager.driver_manager.get_driver()
        if not driver:
            self.logger.error("No driver available. Cannot generate episodes.")
            return []
        
        all_chats = self.chat_manager.get_all_chat_titles()
        if not all_chats:
            self.logger.error("No chats found. Aborting dreamscape generation.")
            return []
        
        chat_links = []
        for chat in all_chats:
            title = chat.get('title', '')
            # partial-match filter
            if any(ex.lower() in title.lower() for ex in self.excluded_chats):
                self.logger.info(f"Skipping excluded chat: {title}")
                continue
            link = chat.get('link', '')
            if link:
                chat_links.append({
                    "title": title,
                    "link": self.ensure_model_in_url(link)
                })
        
        # Reverse order if requested
        if reverse_order:
            chat_links.reverse()
            self.logger.info("Processing chats in REVERSE order")
                
        self.logger.info(f"Found {len(chat_links)} chats to process for dreamscape content.")
        all_entries = []
        
        # STEP 1: Send context update to all chats
        for chat_info in chat_links:
            title = chat_info['title']
            chat_url = chat_info['link']
            self.logger.info(f"Sending context update to chat: {title}")
            driver.get(chat_url)
            time.sleep(delay_between_chats)
            
            context_prompt = self.get_chatgpt_context_prompt()
            if not self._send_prompt_to_chat(driver, context_prompt):
                self.logger.error(f"Failed to send context update to chat: {title}")
            else:
                # wait for a response
                self._get_latest_response(driver, timeout=60, stable_period=5)
                self.logger.info(f"Context update sent to chat: {title}")
                time.sleep(delay_between_chats)
                
        # STEP 2: Generate episodes
        base_episode_number = self.context_memory["episode_count"]
        for i, chat_info in enumerate(chat_links):
            title = chat_info['title']
            chat_url = chat_info['link']
            self.logger.info(f"Processing chat for episode generation: {title}")
            
            driver.get(chat_url)
            time.sleep(delay_between_chats)
            
            episode_number = base_episode_number + i + 1
            episode_prompt = (
                f"Now, create Digital Dreamscape Episode #{episode_number}, "
                f"based on the context I just shared and themes from this chat titled: {title}"
            )
            
            if self._send_prompt_to_chat(driver, episode_prompt):
                response_text = self._get_latest_response(driver)
                if response_text:
                    dreamscape_entry = self._generate_dreamscape_entry(title, response_text)
                    all_entries.append(dreamscape_entry)
                    
                    episode_title = f"Episode #{episode_number}: {title}"
                    self._save_dreamscape_entry(dreamscape_entry, episode_title)
                    
                    # Update context to increment the official count + store new themes
                    episode_themes = self._update_context_with_episode(episode_title, response_text)
                    self.logger.info(f"Updated context memory with themes: {episode_themes}")
                    
                    # Optionally post to Discord
                    if self.discord_manager:
                        try:
                            self.discord_manager.send_message(
                                f"New Dreamscape Episode #{episode_number} from '{title}':\n"
                                f"{dreamscape_entry[:1500]}..."
                            )
                        except Exception as e:
                            self.logger.error(f"Error posting to Discord: {str(e)}")
                else:
                    self.logger.error(f"No dreamscape response for chat: {title}")
            else:
                self.logger.error(f"Failed to send dreamscape prompt for chat: {title}")
                
        self.logger.info(f"Dreamscape content generation complete. Generated {len(all_entries)} episodes.")
        return all_entries

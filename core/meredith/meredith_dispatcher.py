#!/usr/bin/env python3
"""
meredith_dispatcher.py

Processes public profiles through the Meredith resonance matcher engine.
Renders the `MeredithPrompt.jtime` template, dispatches it to LLM,
and parses the result into actionable intelligence.
Validates results against the MeritChain schema and logs high resonance matches.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Local imports
from core.chatgpt_automation.OpenAIClient import OpenAIClient
from core.TemplateManager import TemplateManager
from core.memory.MeritChainManager import MeritChainManager
# Removed internal PathManager import, expect it from services
# from core.PathManager import PathManager 

# Removed global ServiceRegistry import
# from core.registry.ServiceRegistry import ServiceRegistry 

logger = logging.getLogger(__name__)

class MeredithDispatcher:
    """
    Dispatches profiles to an LLM for analysis based on a template,
    parses the response, and optionally saves matches to MeritChain.
    Relies on injected services for dependencies.
    """
    def __init__(self, services: Dict[str, Any]):
        self.services = services
        self.logger = services.get('logger', logger) # Use injected logger or module default
        
        # Get required services
        self.path_manager = services.get('path_manager')
        self.engine = services.get('template_manager')
        self.chat_client = services.get('openai_client') # Assuming OpenAIClient is registered
        self.memory = services.get('merit_chain_manager') # Assuming MeritChainManager is registered
        config_manager = services.get('config_manager')

        # --- Validate required services ---
        if not self.path_manager:
            self.logger.error("PathManager service is missing. MeredithDispatcher may fail.")
            # Cannot proceed without path manager for essential paths
            raise ValueError("PathManager service is required for MeredithDispatcher")
            
        if not self.engine:
            self.logger.warning("TemplateManager service is missing. Creating local instance.")
            self.engine = TemplateManager() # Fallback, less ideal
            
        if not self.chat_client:
            self.logger.error("OpenAIClient service is missing. MeredithDispatcher cannot communicate with LLM.")
            # Cannot proceed without chat client
            raise ValueError("OpenAIClient service is required for MeredithDispatcher")
            
        if not self.memory:
            self.logger.error("MeritChainManager service is missing. Matches cannot be saved/retrieved.")
             # Cannot proceed without memory manager
            raise ValueError("MeritChainManager service is required for MeredithDispatcher")
            
        if not config_manager:
             self.logger.error("ConfigManager service is missing. Using default configurations.")
             # Set default values directly if config is missing
             self.model = "gpt-4" 
             prompt_template_name = "MeredithPrompt.jtime"
             self.resonance_threshold = 75.0
        else:
             # Get config values using the .get() method
             meredith_config = config_manager.get('meredith', {}) # Use .get instead of .get_config
             self.model = meredith_config.get('model', "gpt-4")
             prompt_template_name = meredith_config.get('prompt_template', "MeredithPrompt.jtime")
             self.resonance_threshold = float(meredith_config.get('resonance_threshold', 75.0))
        
        # Resolve template path using injected PathManager
        try:
            # Ensure the key exists before getting it
            if not self.path_manager.has_path("meredith_prompts"):
                 self.logger.warning("Path key 'meredith_prompts' not found in PathManager. Attempting fallback relative path.")
                 # Define a fallback relative path if the key doesn't exist
                 meredith_prompts_dir = Path("templates/meredith") 
            else:
                meredith_prompts_dir = self.path_manager.get_path("meredith_prompts")
            
            self.template_path = meredith_prompts_dir / prompt_template_name
            self.logger.info(f"Using template path: {self.template_path}")
            # Optionally check if the template file actually exists now
            if not self.template_path.exists():
                 self.logger.error(f"Template file does not exist at resolved path: {self.template_path}")
                 # Decide how to handle - raise error or try to continue?
                 # For now, log error and continue, hoping template isn't needed immediately

        except Exception as e: # Catch potential errors during path resolution
            self.logger.error(f"Error resolving template path: {e}. Dispatcher may fail.")
            # Cannot proceed reliably without a template path
            raise ValueError(f"Could not resolve template path: {e}")

        # Removed internal initializations of PathManager, OpenAIClient, MeritChainManager
        # Removed reliance on global ServiceRegistry

        self.logger.info(f"MeredithDispatcher initialized with model: {self.model}, threshold: {self.resonance_threshold}")

    def process_profile(self,
                        profile_data: Dict[str, Any],
                        source_platform: str = None,
                        target_role: str = "love") -> Optional[Dict[str, Any]]:
        """
        Analyzes a single profile for resonance and logs it if aligned.
        
        Args:
            profile_data: Dictionary containing profile information
            source_platform: The platform where the profile was found (optional)
            target_role: The relationship type to analyze for ("love", "friend", etc.)
            
        Returns:
            Parsed LLM response or None on failure.
        """
        # Extract platform from profile data if not provided
        if not source_platform and "platform" in profile_data:
            source_platform = profile_data["platform"]
        
        # If we still don't have a platform, use a default
        if not source_platform:
            source_platform = "Unknown"
            
        # Extract username for logging
        username = profile_data.get("username", "unknown")
        
        try:
            self.logger.info(f"Processing profile: {username} from {source_platform}")

            # Render the template
            rendered_prompt = self.engine.render_file(
                self.template_path,
                {
                    "source_platform": source_platform,
                    "profile_data": profile_data,
                    "target_role": target_role,
                    "current_time": datetime.now().isoformat()
                }
            )

            # Dispatch to ChatGPT or your LLM backend
            response = self.chat_client.get_chatgpt_response(rendered_prompt)

            # Extract and parse JSON from the response
            parsed = self._extract_json(response)

            if not parsed:
                self.logger.warning(f"Failed to parse JSON from response for {username}")
                return None

            # Add platform if not already in the response
            if "platform" not in parsed:
                parsed["platform"] = source_platform
                
            # Add username if not already in the response
            if "username" not in parsed:
                parsed["username"] = username
                
            # Add timestamp if not already in the response
            if "timestamp" not in parsed:
                parsed["timestamp"] = datetime.now().isoformat()
            
            # Auto-set should_save_to_meritchain based on resonance score
            if "resonance_score" in parsed and parsed.get("should_save_to_meritchain") is None:
                resonance_score = float(parsed["resonance_score"])
                parsed["should_save_to_meritchain"] = resonance_score >= self.resonance_threshold
                self.logger.info(f"Auto-set should_save_to_meritchain={parsed['should_save_to_meritchain']} based on score {resonance_score}")
            
            # Ensure matching_traits is a list
            if "matching_traits" not in parsed or parsed["matching_traits"] is None:
                parsed["matching_traits"] = []
            
            # Ensure merit_tags is a list
            if "merit_tags" not in parsed or parsed["merit_tags"] is None:
                parsed["merit_tags"] = []

            # Save to memory if should_save_to_meritchain is true
            if parsed.get("should_save_to_meritchain"):
                saved = self.memory.save(parsed)
                if saved:
                    self.logger.info(f"✅ Resonance match saved to MeritChain: {username}")
                else:
                    self.logger.warning(f"❌ Failed to save {username} to MeritChain - validation failed")
            else:
                self.logger.info(f"Profile {username} not saved to MeritChain (should_save_to_meritchain=False)")

            return parsed

        except Exception as e:
            self.logger.error(f"Error processing profile {username}: {e}")
            return None

    def get_previous_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns the most recent matches from the MeritChain.
        
        Args:
            limit: Maximum number of matches to return
            
        Returns:
            List of match entries
        """
        try:
            all_matches = self.memory.all()
            # Sort by timestamp descending
            sorted_matches = sorted(
                all_matches, 
                key=lambda x: x.get("timestamp", ""), 
                reverse=True
            )
            return sorted_matches[:limit]
        except Exception as e:
            self.logger.error(f"Error retrieving previous matches: {e}")
            return []

    def find_match_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Finds a match in the MeritChain by username.
        
        Args:
            username: The username to search for
            
        Returns:
            The match entry or None if not found
        """
        return self.memory.get_by_username(username)

    def _extract_json(self, raw_response: str) -> Optional[Dict[str, Any]]:
        """
        Extracts the first valid JSON object from a string.
        
        Args:
            raw_response: The raw text response from the LLM
            
        Returns:
            Parsed JSON object or None if extraction failed
        """
        try:
            # Try to find JSON content between triple backticks
            if "```json" in raw_response and "```" in raw_response.split("```json", 1)[1]:
                json_content = raw_response.split("```json", 1)[1].split("```", 1)[0].strip()
                return json.loads(json_content)
            
            # If that fails, try standard JSON object detection
            start = raw_response.find("{")
            end = raw_response.rfind("}")
            if start == -1 or end == -1:
                self.logger.warning("No JSON object found in response")
                return None

            json_str = raw_response[start:end+1]
            return json.loads(json_str)
        except Exception as e:
            self.logger.warning(f"JSON parse error: {e}")
            # Try to find and fix common JSON parsing issues
            try:
                # Handle single quotes instead of double quotes
                if "'" in json_str:
                    json_str = json_str.replace("'", '"')
                    # But fix any double-quoted values
                    json_str = json_str.replace('""', "'")
                return json.loads(json_str)
            except:
                return None

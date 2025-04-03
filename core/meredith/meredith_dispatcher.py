#!/usr/bin/env python3
"""
meredith_dispatcher.py

Processes public profiles through the Meredith resonance matcher engine.
Renders the `MeredithPrompt.jtime` template, dispatches it to LLM,
and parses the result into actionable intelligence.
Validates results against the MeritChain schema and logs high resonance matches.
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from core.TemplateManager import TemplateManager
from core.chatgpt_automation.OpenAIClient import OpenAIClient  # Replace if you use a different LLM client
from core.meritchain.MeritChainManager import MeritChainManager
from core.PathManager import PathManager
from core.services.service_registry import ServiceRegistry

logger = logging.getLogger("MeredithDispatcher")

class MeredithDispatcher:
    def __init__(self,
                 model: str = "gpt-4",
                 prompt_template: str = "MeredithPrompt.jtime",
                 memory_path: str = None,
                 schema_path: str = None,
                 resonance_threshold: float = 75.0):
        self.engine = TemplateManager()
        # Fix: Use a safe path for profile_dir (use 'cache' path which is guaranteed to exist)
        try:
            profile_dir = Path(PathManager().get_path("cache")) / "browser_profiles" / "default"
            # Ensure the directory exists
            profile_dir.mkdir(parents=True, exist_ok=True)
            self.chat_client = OpenAIClient(profile_dir=str(profile_dir))
        except Exception as e:
            logger.error(f"Error initializing OpenAIClient: {e}")
            # Use a safe fallback (current directory)
            self.chat_client = OpenAIClient(profile_dir="browser_profiles")
            
        # Store the model for use in chat completion
        self.model = model
        
        try:
            self.template_path = PathManager().get_path("meredith_prompts") / prompt_template
        except ValueError:
            # Fallback if meredith_prompts path is not registered
            self.template_path = Path("templates") / "meredith_prompts" / prompt_template
            logger.warning(f"Using fallback template path: {self.template_path}")
        
        self.resonance_threshold = resonance_threshold
        
        # Try to get MeritChainManager from service registry
        self.memory = ServiceRegistry.get("merit_chain_manager")
        
        # If not available, create a new instance
        if not self.memory:
            try:
                if not memory_path:
                    memory_path = PathManager().get_path("data") / "meritchain.json"
                if not schema_path:
                    schema_path = PathManager().get_path("core") / "schemas" / "merit_chain_schema.json"
            except ValueError as e:
                # Fallback paths if PathManager keys are not available
                logger.warning(f"PathManager error: {e}. Using fallback paths.")
                memory_path = memory_path or "data/meritchain.json"
                schema_path = schema_path or "core/schemas/merit_chain_schema.json"
            
            self.memory = MeritChainManager(str(memory_path), str(schema_path))
            logger.info(f"Created standalone MeritChainManager (not from registry)")
        else:
            logger.info(f"Using MeritChainManager from service registry")
            
        logger.info(f"MeredithDispatcher initialized with model: {model}, threshold: {resonance_threshold}")

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
            logger.info(f"Processing profile: {username} from {source_platform}")

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
                logger.warning(f"Failed to parse JSON from response for {username}")
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
                logger.info(f"Auto-set should_save_to_meritchain={parsed['should_save_to_meritchain']} based on score {resonance_score}")
            
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
                    logger.info(f"✅ Resonance match saved to MeritChain: {username}")
                else:
                    logger.warning(f"❌ Failed to save {username} to MeritChain - validation failed")
            else:
                logger.info(f"Profile {username} not saved to MeritChain (should_save_to_meritchain=False)")

            return parsed

        except Exception as e:
            logger.error(f"Error processing profile {username}: {e}")
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
            logger.error(f"Error retrieving previous matches: {e}")
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
                logger.warning("No JSON object found in response")
                return None

            json_str = raw_response[start:end+1]
            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"JSON parse error: {e}")
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

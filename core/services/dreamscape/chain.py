"""
Dynamic Episode Chain - Memory Persistence for Dreamscape Episodes

This module handles the persistence and retrieval of contextual information
between Dreamscape episodes, creating a continuous narrative experience.

Key components:
- Writeback to memory: Extract episode data and update memory file
- Episode summary parsing: Extract context from previous episodes
- Episode chain tracking: Maintain persistent chain of episode data
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

def _extract_section_list(content: str, header: str) -> List[str]:
    """Extracts list items following a specific markdown header."""
    items = []
    try:
        # Regex to find the header and capture the content until the next header or end of string
        # Use re.DOTALL to make '.' match newlines
        # Use re.IGNORECASE for the header matching
        pattern = re.compile(rf"^{re.escape(header)}\s*\n(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
        match = pattern.search(content)
        if match:
            section_content = match.group(1).strip()
            # Extract bullet points (lines starting with '-' or '*')
            list_pattern = re.compile(r"^[\s]*[\-\*]\s+(.+)", re.MULTILINE)
            items = [item.strip() for item in list_pattern.findall(section_content)]
    except Exception as e:
        logger.error(f"Error extracting section list for header '{header}': {e}")
    return items

def writeback_to_memory(episode_path: Path, memory_path: Path) -> bool:
    """
    Extract key information from a generated episode and write it to the memory file.
    
    Args:
        episode_path: Path to the episode file to extract data from
        memory_path: Path to the memory JSON file to update
    
    Returns:
        True if successful, False otherwise
    """
    if not episode_path.exists():
        logger.error(f"Episode file does not exist: {episode_path}")
        return False
        
    try:
        # Load the episode content
        with open(episode_path, "r", encoding="utf-8") as f:
            episode_content = f.read()
        # --- REMOVED TEMPORARY DEBUG LOGGING --- #
            
        # --- Load existing memory or initialize --- #
        if memory_path.exists() and memory_path.stat().st_size > 0:
             try:
                 with open(memory_path, "r", encoding="utf-8") as f:
                     memory_data = json.load(f)
                 if not isinstance(memory_data, dict):
                     logger.warning(f"Memory file {memory_path} contained non-dict data. Resetting.")
                     memory_data = {}
             except json.JSONDecodeError:
                 logger.warning(f"Failed to decode JSON from {memory_path}. Resetting memory.")
                 memory_data = {}
        else:
            memory_data = {}

        # Initialize keys if they don't exist
        default_keys = {
            "protocols": [],
            "quests": {},
            "realms": [],
            "artifacts": [],
            "characters": [],
            "themes": [],
            "stabilized_domains": [],
            "skills_upgraded": {}
        }
        for key, default_value in default_keys.items():
            memory_data.setdefault(key, default_value)

        # --- Extract data using new section-based approach --- #
        memory_updates = {
            "last_updated": datetime.now().isoformat(),
            "last_episode": episode_path.stem,
        }
        memory_data.update(memory_updates) # Update timestamp and last episode name

        # Extract based on Markdown headers
        protocols = _extract_section_list(episode_content, "## 🔓 Protocols Unlocked")
        skills_upgraded_list = _extract_section_list(episode_content, "## 🧬 Skills Upgraded")
        stabilized_domains = _extract_section_list(episode_content, "### 🌐 Domains Stabilized")
        # --- REMOVED TEMPORARY DEBUG LOGGING --- #
        new_lore_nodes = _extract_section_list(episode_content, "## 🧩 New Lore Nodes") # Example for another section
        active_quests = _extract_section_list(episode_content, "## 🔄 Active Quests")
        new_quests = _extract_section_list(episode_content, "## 🚀 New Quests")
        completed_quests_list = _extract_section_list(episode_content, "## ✅ Completed Quests")
        locations = _extract_section_list(episode_content, "## 🗺️ Event Type") # Location might be under here or status
        status_location_match = re.search(r"^\*\*Location:\*\*\s*(.+)$", episode_content, re.MULTILINE)
        if status_location_match:
             locations.append(status_location_match.group(1).strip())

        # --- Update Memory --- #
        # Protocols
        if protocols:
            memory_data["protocols"].extend([p for p in protocols if p not in memory_data["protocols"]])

        # Stabilized Domains
        if stabilized_domains:
            memory_data["stabilized_domains"].extend([d for d in stabilized_domains if d not in memory_data["stabilized_domains"]])

        # Skills Upgraded (assuming format "Skill Name → Level X")
        if skills_upgraded_list:
            skills_dict = memory_data.get("skills_upgraded", {})
            for skill_entry in skills_upgraded_list:
                if "→" in skill_entry:
                    skill_name, new_level = [s.strip() for s in skill_entry.split("→", 1)]
                    skills_dict[skill_name] = new_level # Store the latest level
            memory_data["skills_upgraded"] = skills_dict

        # Quests
        quests_dict = memory_data.get("quests", {})
        for quest in new_quests:
            quests_dict[quest] = "active"
        for quest in active_quests: # Mark active just in case
             if quest not in quests_dict or quests_dict[quest] != "completed":
                 quests_dict[quest] = "active"
        for quest in completed_quests_list:
            quests_dict[quest] = "completed"
        memory_data["quests"] = quests_dict

        # Realms/Locations
        if locations:
             memory_data["realms"].extend([loc for loc in locations if loc not in memory_data["realms"]])

        # Add other extracted data (lore nodes, artifacts etc.) similarly if needed

        # --- Write updated memory back to file --- #
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, indent=2)
            
        logger.info(f"Memory updated from episode: {episode_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating memory from episode: {e}", exc_info=True) # Add traceback
        return False

def parse_last_episode_summary(episode_path: Path) -> Dict[str, Any]:
    """
    Extract context summary from the last episode.
    
    Args:
        episode_path: Path to the episode file to extract summary from
        
    Returns:
        Dict containing context data extracted from the episode
    """
    if not episode_path.exists():
        logger.error(f"Episode file does not exist: {episode_path}")
        return {}
        
    try:
        # Load the episode content
        with open(episode_path, "r", encoding="utf-8") as f:
            episode_content = f.read()
            
        # Extract episode title
        title_match = re.search(r"#\s+(.+?)(?:\n|$)", episode_content)
        episode_title = title_match.group(1) if title_match else episode_path.stem
        
        # Extract emotional state
        emotion_match = re.search(r"(?:Emotional State|State of Mind|Mood):\s*(.+?)(?:\n|$)", episode_content)
        emotional_state = emotion_match.group(1) if emotion_match else "Neutral"
        
        # Extract last location
        location_match = re.search(r"(?:Location|Realm|Domain):\s*(.+?)(?:\n|$)", episode_content)
        last_location = location_match.group(1) if location_match else "The Nexus"
        
        # Extract summary section
        summary_match = re.search(r"## Summary\s+(.+?)(?:\n\n|\n##|$)", episode_content, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""
        
        # Extract ongoing and completed quests
        ongoing_quests = _extract_with_pattern(episode_content, r"(?:Quest|Mission|Task)(?:\s+started|initiated|active):\s*(.+?)(?:\n|$)")
        completed_quests = _extract_with_pattern(episode_content, r"(?:Quest|Mission|Task)(?:\s+completed|finished|resolved):\s*(.+?)(?:\n|$)")
        
        # Construct the context dictionary
        context = {
            "episode_title": episode_title,
            "summary": summary,
            "current_emotional_state": emotional_state,
            "last_location": last_location,
            "ongoing_quests": ongoing_quests,
            "completed_quests": completed_quests
        }
        
        return context
        
    except Exception as e:
        logger.error(f"Error parsing episode summary: {e}")
        return {}

def update_episode_chain(episode_path: Path, chain_path: Path) -> bool:
    """Update the episode chain JSON file with a new entry."""
    logger.info(f"Attempting to update episode chain: {chain_path}")
    try:
        # Load existing chain data or initialize safely
        chain_data = {}  # Default empty dict
        if chain_path.exists() and chain_path.stat().st_size > 0:
            try:
                with open(chain_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                # Ensure loaded data is a dictionary
                if isinstance(loaded_data, dict):
                    chain_data = loaded_data
                else:
                    logger.warning(f"Chain file {chain_path} contained non-dict data ({type(loaded_data)}). Resetting.")
                    # Initialize with the expected structure
                    chain_data = {"episodes": [], "episode_count": 0}
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode JSON from {chain_path}. Resetting chain.")
                chain_data = {"episodes": [], "episode_count": 0}
        else:
             logger.info(f"Chain file {chain_path} not found or empty. Initializing.")
             # Initialize the structure expected later
             chain_data = {"episodes": [], "episode_count": 0}

        # Extract context from the episode file (ensure it returns a dict)
        episode_context = parse_last_episode_summary(episode_path) or {}

        # Calculate next episode ID safely
        episode_count = chain_data.get("episode_count", 0) + 1

        # Prepare new entry using .get() for safety
        episode_entry = {
            "id": episode_count,
            "timestamp": datetime.now().isoformat(),
            "filename": episode_path.name,
            "title": episode_context.get("episode_title", episode_path.stem),
            "summary": episode_context.get("summary", ""),
            "location": episode_context.get("last_location", "Unknown"),
            "emotional_state": episode_context.get("current_emotional_state", "Neutral"),
            "ongoing_quests": episode_context.get("ongoing_quests", []),
            "completed_quests": episode_context.get("completed_quests", [])
        }

        # Update chain metadata safely
        chain_data["episode_count"] = episode_count
        chain_data["last_episode"] = episode_entry.get("title", "Unknown Title")
        chain_data["current_emotional_state"] = episode_entry.get("emotional_state", "Neutral")
        chain_data["last_location"] = episode_entry.get("location", "Unknown")
        chain_data["last_updated"] = episode_entry.get("timestamp", datetime.now().isoformat())

        # Ensure 'episodes' list exists and is a list before appending
        if not isinstance(chain_data.get("episodes"), list):
            chain_data["episodes"] = []
        chain_data["episodes"].append(episode_entry)

        # Handle quests safely
        ongoing_quests = chain_data.get("ongoing_quests", [])
        completed_quests_chain = chain_data.get("completed_quests", [])
        new_ongoing = episode_entry.get("ongoing_quests", [])
        new_completed = episode_entry.get("completed_quests", [])

        # Ensure lists exist before extending/appending
        if not isinstance(ongoing_quests, list): ongoing_quests = []
        if not isinstance(completed_quests_chain, list): completed_quests_chain = []

        ongoing_quests.extend([q for q in new_ongoing if isinstance(q, str) and q not in ongoing_quests])
        for quest in new_completed:
            if isinstance(quest, str):
                if quest in ongoing_quests:
                    ongoing_quests.remove(quest)
                if quest not in completed_quests_chain:
                    completed_quests_chain.append(quest)

        chain_data["ongoing_quests"] = ongoing_quests
        chain_data["completed_quests"] = completed_quests_chain

        # Ensure the parent directory exists
        chain_path.parent.mkdir(parents=True, exist_ok=True)

        # Write updated chain back to file
        with open(chain_path, "w", encoding="utf-8") as f:
            json.dump(chain_data, f, indent=2)

        logger.info(f"Episode chain updated with episode {episode_count}: {episode_entry.get('title', 'Unknown Title')}")
        return True

    except Exception as e:
        logger.error(f"Error updating episode chain: {e}", exc_info=True) # Add traceback
        return False

def get_context_from_chain(chain_path: Path) -> Dict[str, Any]:
    """
    Retrieve context from the episode chain for use in generating the next episode.
    
    Args:
        chain_path: Path to the episode chain JSON file
        
    Returns:
        Dict containing context data from the chain or empty dict if no chain exists
    """
    if not chain_path.exists():
        logger.info(f"Episode chain file does not exist: {chain_path}")
        return {}
        
    try:
        # Load the chain data
        with open(chain_path, "r", encoding="utf-8") as f:
            chain_data = json.load(f)
            
        # Extract the needed context
        context = {
            "episode_count": chain_data.get("episode_count", 0),
            "last_episode": chain_data.get("last_episode", ""),
            "current_emotional_state": chain_data.get("current_emotional_state", "Neutral"),
            "last_location": chain_data.get("last_location", "The Nexus"),
            "ongoing_quests": chain_data.get("ongoing_quests", []),
            "completed_quests": chain_data.get("completed_quests", [])
        }
        
        # Add last episode summary if available
        episodes = chain_data.get("episodes", [])
        if episodes:
            last_episode = episodes[-1]
            context["last_episode_summary"] = last_episode.get("summary", "")
            
        return context
        
    except Exception as e:
        logger.error(f"Error getting context from episode chain: {e}")
        return {}

def _extract_with_pattern(content: str, pattern: str) -> List[str]:
    """
    Helper function to extract text using regex patterns.
    
    Args:
        content: Text content to extract from
        pattern: Regex pattern with a capturing group
        
    Returns:
        List of extracted strings
    """
    matches = re.finditer(pattern, content)
    return [match.group(1).strip() for match in matches if match.group(1).strip()] 

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
            
        # Extract key information using regex patterns
        memory_updates = {
            "last_updated": datetime.now().isoformat(),
            "last_episode": episode_path.stem,
        }
        
        # Extract from content using regex
        protocols = _extract_with_pattern(episode_content, r"(?:New Protocol(?:s)?|Protocol Activated):\s*(.+?)(?:\n|$)")
        quests = _extract_with_pattern(episode_content, r"(?:Quest|Mission|Task)(?:\s+started|initiated|active):\s*(.+?)(?:\n|$)")
        completed = _extract_with_pattern(episode_content, r"(?:Quest|Mission|Task)(?:\s+completed|finished|resolved):\s*(.+?)(?:\n|$)")
        locations = _extract_with_pattern(episode_content, r"(?:Location|Realm|Domain):\s*(.+?)(?:\n|$)")
        artifacts = _extract_with_pattern(episode_content, r"(?:Artifact|Item|Tool)(?:\s+discovered|found|acquired):\s*(.+?)(?:\n|$)")
        
        # Load current memory file or create if it doesn't exist
        if memory_path.exists():
            with open(memory_path, "r", encoding="utf-8") as f:
                memory_data = json.load(f)
        else:
            memory_data = {
                "protocols": [],
                "quests": {},
                "realms": [],
                "artifacts": [],
                "characters": [],
                "themes": [],
                "stabilized_domains": [],
            }
            
        # Update memory with new information
        if protocols:
            if "protocols" not in memory_data:
                memory_data["protocols"] = []
            memory_data["protocols"].extend([p for p in protocols if p not in memory_data["protocols"]])
            
        if quests:
            if "quests" not in memory_data:
                memory_data["quests"] = {}
            for quest in quests:
                memory_data["quests"][quest] = "active"
                
        if completed:
            if "quests" not in memory_data:
                memory_data["quests"] = {}
            for quest in completed:
                memory_data["quests"][quest] = "completed"
                
        if locations:
            if "realms" not in memory_data:
                memory_data["realms"] = []
            memory_data["realms"].extend([loc for loc in locations if loc not in memory_data["realms"]])
            
        if artifacts:
            if "artifacts" not in memory_data:
                memory_data["artifacts"] = []
            memory_data["artifacts"].extend([art for art in artifacts if art not in memory_data["artifacts"]])
            
        # Write updated memory back to file
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, indent=2)
            
        logger.info(f"Memory updated from episode: {episode_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating memory from episode: {e}")
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
    """
    Update the episode chain with information from a newly generated episode.
    
    Args:
        episode_path: Path to the new episode file
        chain_path: Path to the episode chain JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract context from the episode
        episode_context = parse_last_episode_summary(episode_path)
        if not episode_context:
            logger.warning(f"Could not extract context from episode: {episode_path}")
            return False
            
        # Load current chain or create new one
        chain_data = {}
        if chain_path.exists():
            with open(chain_path, "r", encoding="utf-8") as f:
                chain_data = json.load(f)
                
            # Increment episode count
            episode_count = chain_data.get("episode_count", 0) + 1
        else:
            # Initialize new chain data
            episode_count = 1
            chain_data = {
                "episodes": []
            }
            
        # Create new episode entry
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
        
        # Update chain data
        chain_data["episode_count"] = episode_count
        chain_data["last_episode"] = episode_entry["title"]
        chain_data["current_emotional_state"] = episode_entry["emotional_state"]
        chain_data["last_location"] = episode_entry["location"]
        chain_data["last_updated"] = episode_entry["timestamp"]
        
        # Maintain ongoing and completed quests
        if "ongoing_quests" not in chain_data:
            chain_data["ongoing_quests"] = []
        if "completed_quests" not in chain_data:
            chain_data["completed_quests"] = []
            
        # Add new ongoing quests and remove completed ones
        chain_data["ongoing_quests"].extend([q for q in episode_entry["ongoing_quests"] 
                                           if q not in chain_data["ongoing_quests"]])
        for quest in episode_entry["completed_quests"]:
            if quest in chain_data["ongoing_quests"]:
                chain_data["ongoing_quests"].remove(quest)
            if quest not in chain_data["completed_quests"]:
                chain_data["completed_quests"].append(quest)
                
        # Add the episode to the chain
        if "episodes" not in chain_data:
            chain_data["episodes"] = []
        chain_data["episodes"].append(episode_entry)
        
        # Ensure the parent directory exists
        chain_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write updated chain back to file
        with open(chain_path, "w", encoding="utf-8") as f:
            json.dump(chain_data, f, indent=2)
            
        logger.info(f"Episode chain updated with episode {episode_count}: {episode_entry['title']}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating episode chain: {e}")
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

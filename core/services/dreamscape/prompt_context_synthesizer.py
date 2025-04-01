"""
PromptContextSynthesizer

This module synthesizes context from multiple sources:
1. LLM-based memory and conversation history
2. Structured data from episode chains and memory files
3. Web-scraped content (when available)

It provides a unified context object for generating more coherent and
contextually-aware Dreamscape episodes with persistent narrative elements.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

class PromptContextSynthesizer:
    """
    Combines multiple context sources into a unified context object for
    generating coherent Dreamscape episodes with narrative continuity.
    """
    
    def __init__(
        self,
        memory_path: Optional[Union[str, Path]] = None,
        chain_path: Optional[Union[str, Path]] = None,
        conversation_memory_path: Optional[Union[str, Path]] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize paths
        base_path = Path(os.getcwd())
        memory_dir = base_path / "memory"
        
        self.memory_path = Path(memory_path) if memory_path else memory_dir / "dreamscape_memory.json"
        self.chain_path = Path(chain_path) if chain_path else memory_dir / "episode_chain.json"
        self.conversation_memory_path = Path(conversation_memory_path) if conversation_memory_path else memory_dir / "conversation_memory.json"
        
        # Ensure directories exist
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"PromptContextSynthesizer initialized with memory path: {self.memory_path}")
    
    def synthesize_context(self, 
                          chat_title: str, 
                          chat_history: Optional[List[str]] = None,
                          web_scraped_content: Optional[str] = None,
                          additional_context: Optional[Dict[str, Any]] = None,
                          config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a unified context object by combining:
        1. Memory file context (persistent narrative elements)
        2. Episode chain context (narrative continuity between episodes)
        3. Conversation memory (semantic understanding)
        4. Current chat content (from memory or web scraping)
        5. Any additional context provided
        
        Args:
            chat_title: Title of the chat
            chat_history: List of messages in the chat (optional)
            web_scraped_content: Raw content from web scraping (optional)
            additional_context: Any additional context to include (optional)
            config: Configuration for context weighting and limits
            
        Returns:
            A unified context dictionary
        """
        # Default configuration
        default_config = {
            "context_weights": {
                "web_scraping": 0.3,
                "episode_chain": 0.3,
                "semantic_memory": 0.4
            },
            "context_max_episodes": 3,
            "context_max_quests": 5,
            "max_recent_messages": 5,
            "use_llm_summarization": False  # Set to True to use LLM for summary generation
        }
        
        # Merge with provided config
        context_config = default_config.copy()
        if config:
            for key, value in config.items():
                if key in context_config:
                    if isinstance(value, dict) and isinstance(context_config[key], dict):
                        context_config[key].update(value)
                    else:
                        context_config[key] = value
        
        # Initialize context with metadata
        context = {
            "chat_title": chat_title,
            "generation_timestamp": datetime.now().isoformat(),
            "source_availability": {
                "structured_history": False,
                "llm_history": False,
                "web_content": bool(web_scraped_content),
                "chat_history": bool(chat_history)
            },
            "context_weights": context_config["context_weights"]
        }
        
        # Track contribution confidence for each source
        contribution_scores = {}
        
        # 1. Load structured memory context with confidence score
        memory_context, memory_confidence = self._load_memory_context_with_confidence()
        if memory_context:
            context.update(memory_context)
            context["source_availability"]["structured_history"] = True
            contribution_scores["structured_memory"] = memory_confidence
        
        # 2. Load episode chain context with confidence score
        chain_context, chain_confidence = self._load_chain_context_with_confidence(
            max_episodes=context_config["context_max_episodes"],
            max_quests=context_config["context_max_quests"]
        )
        if chain_context:
            context.update(chain_context)
            context["has_previous_episode"] = bool(chain_context.get("last_episode"))
            contribution_scores["episode_chain"] = chain_confidence
        
        # 3. Load conversation memory context (LLM-based) with confidence score
        llm_context, llm_confidence = self._load_conversation_memory_with_confidence(chat_title)
        if llm_context:
            context.update(llm_context)
            context["source_availability"]["llm_history"] = True
            contribution_scores["semantic_memory"] = llm_confidence
        
        # 4. Process current chat content with confidence score
        current_context = {}
        current_confidence = 0.0
        
        if chat_history:
            current_context, current_confidence = self._process_chat_history_with_confidence(
                chat_history, 
                max_recent=context_config["max_recent_messages"]
            )
            context.update(current_context)
            contribution_scores["chat_history"] = current_confidence
        elif web_scraped_content:
            scraped_context, scraped_confidence = self._process_web_content_with_confidence(web_scraped_content)
            context.update(scraped_context)
            contribution_scores["web_content"] = scraped_confidence
        
        # 5. Add any additional context
        if additional_context:
            context.update(additional_context)
        
        # 6. Generate a semantic summary based on weighted contributions
        if context_config["use_llm_summarization"]:
            context["semantic_summary"] = self._generate_llm_semantic_summary(
                context, 
                contribution_scores, 
                context_config["context_weights"]
            )
        else:
            context["semantic_summary"] = self._generate_weighted_summary(
                context, 
                contribution_scores, 
                context_config["context_weights"]
            )
        
        # Add context quality metrics
        context["context_quality"] = {
            "contributions": contribution_scores,
            "overall_confidence": sum(contribution_scores.values()) / max(1, len(contribution_scores)),
            "sources_used": list(contribution_scores.keys())
        }
        
        self.logger.info(f"Synthesized context for '{chat_title}' with {len(context)} keys and {len(contribution_scores)} sources")
        return context
    
    def _load_memory_context_with_confidence(self) -> tuple[Dict[str, Any], float]:
        """Load context from the memory file with confidence score."""
        try:
            if self.memory_path.exists():
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    memory_data = json.load(f)
                
                # Extract relevant elements from memory
                context = {
                    "themes": memory_data.get("themes", []),
                    "characters": memory_data.get("characters", []),
                    "realms": memory_data.get("realms", []),
                    "artifacts": memory_data.get("artifacts", []),
                    "protocols": memory_data.get("protocols", []),
                    "stabilized_domains": memory_data.get("stabilized_domains", []),
                }
                
                # Process quests from memory
                active_quests = []
                completed_quests = []
                for quest, status in memory_data.get("quests", {}).items():
                    if status == "active":
                        active_quests.append(quest)
                    elif status == "completed":
                        completed_quests.append(quest)
                
                context["memory_active_quests"] = active_quests
                context["memory_completed_quests"] = completed_quests
                
                # Calculate confidence based on richness of data
                # More data elements = higher confidence
                elements_count = sum(len(context.get(key, [])) for key in context)
                confidence = min(0.9, 0.3 + (elements_count / 100))  # Cap at 0.9
                
                self.logger.info(f"Loaded memory context with {elements_count} elements (confidence: {confidence:.2f})")
                return context, confidence
            else:
                self.logger.warning(f"Memory file not found: {self.memory_path}")
                return {}, 0.0
        except Exception as e:
            self.logger.error(f"Error loading memory context: {e}")
            return {}, 0.0
    
    def _load_chain_context_with_confidence(self, max_episodes: int = 3, max_quests: int = 5) -> tuple[Dict[str, Any], float]:
        """Load context from the episode chain file with confidence score."""
        try:
            if self.chain_path.exists():
                with open(self.chain_path, "r", encoding="utf-8") as f:
                    chain_data = json.load(f)
                
                # Extract key narrative continuity elements
                context = {
                    "episode_count": chain_data.get("episode_count", 0),
                    "last_episode": chain_data.get("last_episode", ""),
                    "current_emotional_state": chain_data.get("current_emotional_state", "Neutral"),
                    "last_location": chain_data.get("last_location", "The Nexus"),
                }
                
                # Limit quests to max_quests
                ongoing_quests = chain_data.get("ongoing_quests", [])
                completed_quests = chain_data.get("completed_quests", [])
                
                if len(ongoing_quests) > max_quests:
                    ongoing_quests = ongoing_quests[:max_quests]
                
                context["ongoing_quests"] = ongoing_quests
                context["completed_quests"] = completed_quests[:max_quests]
                
                # Add last episode summary if available
                episodes = chain_data.get("episodes", [])
                
                # Get the most recent episodes up to max_episodes
                recent_episodes = episodes[-max_episodes:] if episodes else []
                
                if recent_episodes:
                    # Add the most recent episode's details
                    last_episode = recent_episodes[-1]
                    context["last_episode_summary"] = last_episode.get("summary", "")
                    context["last_episode_location"] = last_episode.get("location", context["last_location"])
                    context["last_episode_emotional_state"] = last_episode.get("emotional_state", context["current_emotional_state"])
                    
                    # Add additional episode summaries if available for "Previously in the Dreamscape" section
                    if len(recent_episodes) > 1:
                        previous_episodes = []
                        for ep in recent_episodes[:-1]:  # All except the very latest
                            previous_episodes.append({
                                "title": ep.get("title", "Untitled Episode"),
                                "summary": ep.get("summary", "No summary available"),
                                "location": ep.get("location", "Unknown"),
                                "emotional_state": ep.get("emotional_state", "Neutral"),
                            })
                        context["previous_episodes"] = previous_episodes
                
                # Calculate confidence based on episode count and recency
                episode_count = chain_data.get("episode_count", 0)
                confidence = min(0.95, 0.2 + (episode_count / 20))  # Cap at 0.95
                
                # Adjust confidence based on how recent the last episode is
                if episodes and episode_count > 0:
                    try:
                        last_timestamp = episodes[-1].get("timestamp")
                        if last_timestamp:
                            last_time = datetime.fromisoformat(last_timestamp)
                            days_since = (datetime.now() - last_time).days
                            # Reduce confidence for older episodes
                            if days_since > 7:
                                confidence *= 0.8
                            elif days_since > 30:
                                confidence *= 0.6
                    except (ValueError, TypeError):
                        pass
                
                self.logger.info(f"Loaded chain context with episode count: {episode_count} (confidence: {confidence:.2f})")
                return context, confidence
            else:
                self.logger.warning(f"Episode chain file not found: {self.chain_path}")
                return {}, 0.0
        except Exception as e:
            self.logger.error(f"Error loading chain context: {e}")
            return {}, 0.0
    
    def _load_conversation_memory_with_confidence(self, chat_title: str) -> tuple[Dict[str, Any], float]:
        """Load LLM-based memory from conversation history with confidence score."""
        try:
            if self.conversation_memory_path.exists():
                with open(self.conversation_memory_path, "r", encoding="utf-8") as f:
                    memory_data = json.load(f)
                
                # Look for this specific chat in memory
                chat_memories = memory_data.get("chat_memories", {})
                if chat_title in chat_memories:
                    chat_memory = chat_memories[chat_title]
                    
                    # Extract key semantic elements
                    context = {
                        "semantic_themes": chat_memory.get("themes", []),
                        "semantic_goals": chat_memory.get("goals", []),
                        "semantic_insights": chat_memory.get("insights", []),
                        "semantic_summary": chat_memory.get("summary", ""),
                    }
                    
                    # Calculate confidence based on memory richness and recency
                    elements_count = sum(len(context.get(key, [])) for key in context 
                                         if isinstance(context.get(key), list))
                    
                    # Add points for having a summary
                    has_summary = 5 if context.get("semantic_summary") else 0
                    
                    # Calculate confidence
                    confidence = min(0.9, 0.3 + ((elements_count + has_summary) / 30))
                    
                    # Adjust for recency
                    last_updated = chat_memory.get("last_updated")
                    if last_updated:
                        try:
                            update_time = datetime.fromisoformat(last_updated)
                            days_since = (datetime.now() - update_time).days
                            if days_since > 7:
                                confidence *= 0.8
                            elif days_since > 30:
                                confidence *= 0.6
                        except (ValueError, TypeError):
                            pass
                    
                    self.logger.info(f"Loaded conversation memory for chat: {chat_title} (confidence: {confidence:.2f})")
                    return context, confidence
                else:
                    # Get global memories if available
                    global_memory = memory_data.get("global_memory", {})
                    if global_memory:
                        context = {
                            "global_themes": global_memory.get("themes", []),
                            "global_goals": global_memory.get("goals", []),
                            "global_insights": global_memory.get("insights", []),
                        }
                        
                        # Global memory is less specific, so lower confidence
                        elements_count = sum(len(context.get(key, [])) for key in context 
                                          if isinstance(context.get(key), list))
                        confidence = min(0.6, 0.2 + (elements_count / 40))
                        
                        return context, confidence
                    
                    self.logger.info(f"No specific memory found for chat: {chat_title}")
                    return {}, 0.0
            else:
                self.logger.warning(f"Conversation memory file not found: {self.conversation_memory_path}")
                return {}, 0.0
        except Exception as e:
            self.logger.error(f"Error loading conversation memory: {e}")
            return {}, 0.0
    
    def _process_chat_history_with_confidence(self, chat_history: List[str], max_recent: int = 5) -> tuple[Dict[str, Any], float]:
        """Process chat history into usable context elements with confidence score."""
        if not chat_history:
            return {}, 0.0
        
        # Basic processing - extract key content from recent messages
        recent_messages = chat_history[-max_recent:] if len(chat_history) > max_recent else chat_history
        combined_content = "\n\n".join(recent_messages)
        
        context = {
            "raw_response": combined_content,
            "chat_history_length": len(chat_history),
            "recent_messages": recent_messages,
        }
        
        # Calculate confidence based on message count and content length
        message_count = len(chat_history)
        content_length = len(combined_content)
        
        # More messages and longer content increase confidence
        confidence = min(0.85, 0.2 + (message_count / 30) + (content_length / 10000))
        
        return context, confidence
    
    def _process_web_content_with_confidence(self, web_content: str) -> tuple[Dict[str, Any], float]:
        """Extract key information from web-scraped content with confidence score."""
        if not web_content:
            return {}, 0.0
        
        # Simple approach - try to identify key sections in the scraped content
        lines = web_content.split("\n")
        
        # Look for content sections
        current_section = None
        sections = {}
        
        for line in lines:
            if not line.strip():
                continue
                
            # Check for potential section headers
            if line.startswith("# ") or line.startswith("## "):
                current_section = line.lstrip("#").strip()
                sections[current_section] = []
            elif current_section and line.strip():
                sections[current_section].append(line.strip())
        
        # Extract potential summary or key content
        web_context = {
            "web_scraped_sections": list(sections.keys()),
            "has_web_content": True,
        }
        
        # Look for summary section
        if "Summary" in sections:
            web_context["web_summary"] = "\n".join(sections["Summary"])
        
        # Calculate confidence based on content structure and length
        section_count = len(sections)
        content_length = len(web_content)
        
        # More structured content (more sections) increases confidence
        confidence = min(0.8, 0.3 + (section_count / 10) + (content_length / 15000))
        
        return web_context, confidence
    
    def _generate_weighted_summary(self, 
                                  context: Dict[str, Any], 
                                  contribution_scores: Dict[str, float],
                                  weights: Dict[str, float]) -> str:
        """Generate a weighted summary of the context based on source contributions."""
        if not contribution_scores:
            return "Insufficient context available for this episode."
        
        summary_parts = []
        
        # Adjust confidence scores with configured weights
        weighted_scores = {}
        for source, score in contribution_scores.items():
            source_type = self._map_source_to_type(source)
            if source_type in weights:
                weighted_scores[source] = score * weights.get(source_type, 1.0)
            else:
                weighted_scores[source] = score
        
        # Normalize weighted scores
        total_weight = sum(weighted_scores.values())
        if total_weight > 0:
            for source in weighted_scores:
                weighted_scores[source] /= total_weight
        
        # Add narrative continuity if available (from episode chain)
        if context.get("has_previous_episode") and weighted_scores.get("episode_chain", 0) > 0.2:
            last_episode = context.get("last_episode", "")
            last_location = context.get("last_location", "The Nexus")
            emotional_state = context.get("current_emotional_state", "Neutral")
            
            summary_parts.append(f"Continuing from '{last_episode}' where we left off in {last_location}.")
            summary_parts.append(f"The protagonist's current emotional state is {emotional_state}.")
            
            # Add ongoing quests with higher weight if score is high
            if weighted_scores.get("episode_chain", 0) > 0.4:
                ongoing_quests = context.get("ongoing_quests", [])
                if ongoing_quests:
                    quest_list = ", ".join([f"'{q}'" for q in ongoing_quests[:3]])
                    if len(ongoing_quests) > 3:
                        quest_list += f", and {len(ongoing_quests) - 3} more"
                    summary_parts.append(f"Currently pursuing quests: {quest_list}.")
        
        # Add semantic memory with higher weight if available
        if context.get("semantic_summary") and weighted_scores.get("semantic_memory", 0) > 0.3:
            summary_parts.append(context.get("semantic_summary"))
        
        # Add current context from chat or web
        chat_title = context.get("chat_title", "")
        summary_parts.append(f"This episode draws from '{chat_title}'.")
        
        if context.get("web_summary") and weighted_scores.get("web_content", 0) > 0.3:
            summary_parts.append(context.get("web_summary"))
        elif context.get("raw_response") and weighted_scores.get("chat_history", 0) > 0.3:
            # Extract a simple summary from raw content
            raw_text = context.get("raw_response", "")
            if len(raw_text) > 200:
                raw_text = raw_text[:200] + "..."
            summary_parts.append(f"Based on recent discussion: {raw_text}")
        
        return " ".join(summary_parts)
    
    def _generate_llm_semantic_summary(self, 
                                      context: Dict[str, Any], 
                                      contribution_scores: Dict[str, float],
                                      weights: Dict[str, float]) -> str:
        """
        Generate a semantic summary using an LLM.
        This is a placeholder - in a real implementation, this would call an LLM service.
        """
        # Placeholder - would call LLM API in real implementation
        self.logger.info("LLM summarization requested but not implemented - using weighted summary instead")
        return self._generate_weighted_summary(context, contribution_scores, weights)
    
    def _map_source_to_type(self, source: str) -> str:
        """Map a specific source to its general type for weighting."""
        source_type_mapping = {
            "structured_memory": "episode_chain",
            "episode_chain": "episode_chain",
            "semantic_memory": "semantic_memory",
            "chat_history": "semantic_memory",
            "web_content": "web_scraping"
        }
        return source_type_mapping.get(source, "semantic_memory")
    
    def update_memory_with_synthesized_context(self, context: Dict[str, Any]) -> bool:
        """
        Update memory files with insights from synthesized context.
        This serves as a reinforcement mechanism to improve future context.
        
        Args:
            context: The synthesized context dictionary
            
        Returns:
            True if memory was updated successfully, False otherwise
        """
        try:
            # 1. Update conversation memory with semantic insights
            self._update_conversation_memory(context)
            
            # 2. Selectively update structured memory if needed
            if context.get("new_protocols") or context.get("new_quests") or context.get("new_realms"):
                self._update_structured_memory(context)
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating memory with synthesized context: {e}")
            return False
    
    def _update_conversation_memory(self, context: Dict[str, Any]) -> None:
        """Update the conversation memory with semantic insights."""
        try:
            if self.conversation_memory_path.exists():
                with open(self.conversation_memory_path, "r", encoding="utf-8") as f:
                    memory_data = json.load(f)
            else:
                memory_data = {"chat_memories": {}, "global_memory": {}}
            
            chat_title = context.get("chat_title", "unknown_chat")
            
            # Initialize chat memory if it doesn't exist
            if chat_title not in memory_data["chat_memories"]:
                memory_data["chat_memories"][chat_title] = {
                    "themes": [],
                    "goals": [],
                    "insights": [],
                    "summary": "",
                    "last_updated": datetime.now().isoformat()
                }
            
            # Update with new semantic insights if available
            chat_memory = memory_data["chat_memories"][chat_title]
            
            if context.get("semantic_themes"):
                chat_memory["themes"] = list(set(chat_memory["themes"] + context.get("semantic_themes", [])))
            
            if context.get("semantic_goals"):
                chat_memory["goals"] = list(set(chat_memory["goals"] + context.get("semantic_goals", [])))
            
            if context.get("semantic_insights"):
                chat_memory["insights"] = list(set(chat_memory["insights"] + context.get("semantic_insights", [])))
            
            if context.get("semantic_summary"):
                chat_memory["summary"] = context.get("semantic_summary")
            
            chat_memory["last_updated"] = datetime.now().isoformat()
            
            # Save updated memory
            with open(self.conversation_memory_path, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, indent=2)
                
            self.logger.info(f"Updated conversation memory for chat: {chat_title}")
        except Exception as e:
            self.logger.error(f"Error updating conversation memory: {e}")
    
    def _update_structured_memory(self, context: Dict[str, Any]) -> None:
        """Update the structured memory with new narrative elements."""
        try:
            if self.memory_path.exists():
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    memory_data = json.load(f)
            else:
                memory_data = {
                    "protocols": [],
                    "quests": {},
                    "realms": [],
                    "artifacts": [],
                    "characters": [],
                    "themes": [],
                    "stabilized_domains": []
                }
            
            # Update with new elements
            if context.get("new_protocols"):
                memory_data["protocols"] = list(set(memory_data["protocols"] + context.get("new_protocols", [])))
            
            if context.get("new_quests"):
                for quest in context.get("new_quests", []):
                    if quest not in memory_data["quests"]:
                        memory_data["quests"][quest] = "active"
            
            if context.get("completed_quests"):
                for quest in context.get("completed_quests", []):
                    memory_data["quests"][quest] = "completed"
            
            if context.get("new_realms"):
                memory_data["realms"] = list(set(memory_data["realms"] + context.get("new_realms", [])))
            
            if context.get("new_artifacts"):
                memory_data["artifacts"] = list(set(memory_data["artifacts"] + context.get("new_artifacts", [])))
            
            if context.get("new_characters"):
                memory_data["characters"] = list(set(memory_data["characters"] + context.get("new_characters", [])))
            
            if context.get("new_themes"):
                memory_data["themes"] = list(set(memory_data["themes"] + context.get("new_themes", [])))
            
            if context.get("new_stabilized_domains"):
                memory_data["stabilized_domains"] = list(set(memory_data["stabilized_domains"] + context.get("new_stabilized_domains", [])))
            
            # Save updated memory
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, indent=2)
                
            self.logger.info(f"Updated structured memory with new narrative elements")
        except Exception as e:
            self.logger.error(f"Error updating structured memory: {e}")


# Example usage:
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("context_test")
    
    synthesizer = PromptContextSynthesizer(logger=logger)
    context = synthesizer.synthesize_context(
        chat_title="Test Chat",
        chat_history=["Hello!", "This is a test message."]
    )
    
    print(json.dumps(context, indent=2)) 

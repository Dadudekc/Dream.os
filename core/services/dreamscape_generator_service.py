import json
import logging
import re
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

from core.PathManager import PathManager
from core.TemplateManager import TemplateManager
from core.interfaces.IDreamscapeService import IDreamscapeService
from core.services.dreamscape_episode_chain import (
    writeback_to_memory,
    parse_last_episode_summary,
    update_episode_chain,
    get_context_from_chain
)
from core.services.prompt_context_synthesizer import PromptContextSynthesizer


class DreamscapeGenerationService(IDreamscapeService):
    """
    Backend-only service for generating Dreamscape episodes.
    Supports rendering from templates or raw memory injection.
    """

    MEMORY_FILE = "memory/dreamscape_memory.json"
    CHAIN_FILE = "memory/episode_chain.json"

    def __init__(
        self,
        path_manager: Optional[PathManager] = None,
        template_manager: Optional[TemplateManager] = None,
        logger: Optional[logging.Logger] = None,
        memory_data: Optional[Dict[str, Any]] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.path_manager = path_manager or PathManager()
        self.template_manager = template_manager or TemplateManager()
        self.memory_data = memory_data or {}

        self.output_dir = self.path_manager.get_path("dreamscape")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"[DreamscapeService] Output directory set to: {self.output_dir}")
        
        # Load memory path
        try:
            self.memory_path = self.path_manager.get_path("memory") / "dreamscape_memory.json"
            self.chain_path = self.path_manager.get_path("memory") / "episode_chain.json"
        except Exception as e:
            self.logger.warning(f"Error getting memory paths, using default: {e}")
            self.memory_path = Path(self.MEMORY_FILE)
            self.chain_path = Path(self.CHAIN_FILE)
            
        # Initialize the context synthesizer
        self.context_synthesizer = PromptContextSynthesizer(
            memory_path=self.memory_path,
            chain_path=self.chain_path,
            logger=self.logger
        )

    def load_context_from_file(self, json_path: str) -> Dict[str, Any]:
        """Load rendering context from JSON file."""
        try:
            path = Path(json_path)
            if not path.exists():
                raise FileNotFoundError(f"Context file not found: {json_path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.logger.info(f"[Context Loaded] {json_path}")
            return data
        except Exception as e:
            self.logger.error(f"[Error] Failed to load context: {e}")
            return {}

    def generate_context_from_memory(self) -> Dict[str, Any]:
        """
        Constructs a context dict from the injected memory structure and episode chain.
        Now includes dynamic context from previous episodes.
        """
        # Base context from injected memory
        context = {
            "themes": self.memory_data.get("themes", []),
            "characters": self.memory_data.get("characters", []),
            "realms": self.memory_data.get("realms", []),
            "artifacts": self.memory_data.get("artifacts", []),
            "skill_levels": self.memory_data.get("skill_levels", {}),
            "architect_tier": self.memory_data.get("architect_tier", {}),
            "quests": self.memory_data.get("quests", {}),
            "protocols": self.memory_data.get("protocols", []),
            "stabilized_domains": self.memory_data.get("stabilized_domains", []),
        }
        
        # Add dynamic context from episode chain if available
        try:
            chain_context = get_context_from_chain(self.chain_path)
            if chain_context:
                # Merge the dynamic context
                context.update({
                    "last_episode": chain_context.get("last_episode"),
                    "current_emotional_state": chain_context.get("current_emotional_state"),
                    "last_location": chain_context.get("last_location"),
                    "ongoing_quests": chain_context.get("ongoing_quests", []),
                    "completed_quests": chain_context.get("completed_quests", []),
                    "episode_count": chain_context.get("episode_count", 0),
                    "has_previous_episode": True
                })
                self.logger.info(f"Added dynamic context from episode chain: episode count {chain_context.get('episode_count', 0)}")
            else:
                context["has_previous_episode"] = False
        except Exception as e:
            self.logger.warning(f"Error loading episode chain context: {e}")
            context["has_previous_episode"] = False
        
        return context

    def render_episode(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Dreamscape episode from a template and context."""
        try:
            output = self.template_manager.render_general_template(template_name, context)
            self.logger.info(f"[Rendered] Template: {template_name}")
            return output
        except Exception as e:
            self.logger.error(f"[Error] Rendering failed: {e}")
            return f"# Error rendering template\n\n{e}"

    def save_episode(self, name: str, content: str, format: str = "md") -> Path:
        """Save the rendered episode to disk."""
        try:
            path = self.output_dir / f"{name}.{format}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info(f"[Saved] Episode → {path}")
            return path
        except Exception as e:
            self.logger.error(f"[Error] Saving episode failed: {e}")
            return Path()

    def generate_episode_from_template(self, template_name: str, context_path: str, output_name: str) -> Optional[Path]:
        """Load context from JSON, render it with template, and save output."""
        context = self.load_context_from_file(context_path)
        if not context:
            return None
        rendered = self.render_episode(template_name, context)
        return self.save_episode(output_name, rendered)

    def generate_episode_from_memory(self, template_name: str, output_name: Optional[str] = None) -> Optional[Path]:
        """Render and save an episode using memory-driven context."""
        context = self.generate_context_from_memory()
        rendered = self.render_episode(template_name, context)

        if not output_name:
            output_name = f"episode_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        episode_path = self.save_episode(output_name, rendered)
        
        # Update memory and episode chain after generation
        self._update_memory_and_chain(episode_path)
        
        return episode_path

    def generate_dreamscape_episode(self, chat_title: str, chat_history: List[str], source: str = "memory") -> Optional[Path]:
        """
        Generate a dreamscape episode from a chat history.
        
        Args:
            chat_title: Title of the chat
            chat_history: List of messages in the chat
            source: Source of the chat history ("memory" or "web")
            
        Returns:
            Path to the generated episode file or None if generation failed
        """
        try:
            self.logger.info(f"Generating dreamscape episode from chat: {chat_title} (source: {source})")
            
            # Use the context synthesizer to create a rich, unified context
            # that combines structured memory, episode chain, and chat content
            unified_context = self.context_synthesizer.synthesize_context(
                chat_title=chat_title,
                chat_history=chat_history,
                additional_context={
                    "source": source,
                    "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            )
            
            # Extract a potential episode title
            episode_title = self._extract_episode_title(
                unified_context.get("raw_response", ""),
                chat_title
            )
            unified_context["episode_title"] = episode_title
            
            # Extract potential protocols from the content
            protocols = self._extract_protocols(unified_context.get("raw_response", ""))
            unified_context["newly_unlocked_protocols"] = protocols
            
            # Add specific elements for template rendering
            unified_context.update({
                "memory_updates": [
                    f"Interaction with {chat_title} yielded new insights",
                    f"Episode '{episode_title}' recorded to memory banks"
                ],
                "skill_level_advancements": {
                    "System Convergence": "Level 3 → Level 4",
                    "Automation Engineering": "Level 2 → Level 3"
                },
                "newly_stabilized_domains": [
                    chat_title.replace("ChatGPT - ", ""),
                    "Dream Sequence Generator"
                ],
                "tags": ["#dreamscape", "#digitalchronicles", "#" + self._slugify(chat_title)]
            })
            
            # Render the episode using the unified context
            rendered_episode = self.render_episode("dreamscape_episode.j2", unified_context)
            
            # Create a slugified filename
            date_str = datetime.now().strftime("%Y%m%d")
            output_name = f"{self._slugify(chat_title)}_{date_str}"
            
            # Save the episode
            episode_path = self.save_episode(output_name, rendered_episode)
            
            # Update memory and episode chain
            self._update_memory_and_chain(episode_path)
            
            # Update the context synthesizer's memory with insights from this episode
            self.context_synthesizer.update_memory_with_synthesized_context(unified_context)
            
            # Archive the episode (implementing this would require AletheiaPromptManager integration)
            self._archive_episode(episode_path)
            
            self.logger.info(f"Dreamscape episode generated and saved to {episode_path}")
            return episode_path
            
        except Exception as e:
            self.logger.error(f"Error generating dreamscape episode: {e}")
            return None
    
    def _update_memory_and_chain(self, episode_path: Path) -> None:
        """
        Update the memory file and episode chain with information from the generated episode.
        
        Args:
            episode_path: Path to the generated episode file
        """
        if not episode_path or not episode_path.exists():
            self.logger.warning(f"Cannot update memory: episode path invalid or doesn't exist: {episode_path}")
            return
            
        try:
            # Update memory with episode content
            writeback_to_memory(episode_path, self.memory_path)
            
            # Update episode chain
            update_episode_chain(episode_path, self.chain_path)
            
            self.logger.info(f"Memory and episode chain updated from episode: {episode_path.name}")
        except Exception as e:
            self.logger.error(f"Error updating memory or episode chain: {e}")
    
    def _extract_episode_title(self, content: str, fallback_title: str) -> str:
        """Extract a potential episode title from content or generate one from fallback title."""
        # Look for lines with likely title patterns
        lines = content.split("\n")
        title_patterns = [
            r"^#\s+(.+)$",  # Markdown titles
            r"^(.+:)$",     # Lines ending with colon
            r"^(?:The|A)\s+(.+)$"  # Lines starting with "The" or "A"
        ]
        
        for line in lines:
            line = line.strip()
            if not line or len(line) > 80:
                continue
                
            for pattern in title_patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(1).strip()
        
        # If no good title found, use fallback with creative enhancements
        prefix = random.choice([
            "The Chronicles of", 
            "Convergence:", 
            "Architect's Journey:", 
            "Digital Realm:", 
            "System Evolution:"
        ])
        return f"{prefix} {fallback_title.replace('ChatGPT - ', '')}"
    
    def _generate_summary(self, content: str) -> str:
        """Generate a brief summary of the content."""
        # Simple approach: take first line or paragraph that's not too long
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if 20 < len(line) < 200 and not line.startswith("#") and not line.startswith("```"):
                return line
        
        # Fallback summary if nothing suitable found
        return "A new chapter in the Digital Dreamscape unfolds, revealing pathways through the architecture of thought."
    
    def _extract_protocols(self, content: str) -> List[str]:
        """Extract potential protocol names from the content."""
        protocol_keywords = ["protocol", "system", "framework", "engine", "nexus"]
        protocols = []
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in protocol_keywords):
                if 20 < len(line) < 100:
                    # Clean up the line to create a protocol name
                    protocol = re.sub(r'[^\w\s-]', '', line)
                    protocol = re.sub(r'\s+', ' ', protocol).strip()
                    protocols.append(protocol)
        
        # Limit to 3 protocols
        return protocols[:3]
    
    def _slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug format."""
        # Remove special characters and replace spaces with underscores
        text = re.sub(r'[^\w\s-]', '', text.lower())
        text = re.sub(r'[\s-]+', '_', text).strip('_')
        return text
    
    def _archive_episode(self, episode_path: Path) -> None:
        """
        Archive the episode in the memory system.
        This would typically call AletheiaPromptManager.archive_episode() or similar.
        """
        # For now, just log the archiving
        self.logger.info(f"Episode archived: {episode_path}")
        
        # In a real implementation, would call:
        # if hasattr(self, 'prompt_manager') and self.prompt_manager:
        #     self.prompt_manager.archive_episode(str(episode_path))

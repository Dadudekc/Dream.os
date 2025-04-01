from typing import Dict, Any
import json
import os
from datetime import datetime
from jinja2 import Template
from .utils import get_timestamp, logger, ensure_directory, BASE_OUTPUT_PATH, TEMPLATE_DIR

class NarrativeManager:
    """Manages narrative tracking and updates for the prompt cycle system."""
    
    def __init__(self, system_state, discord_service=None):
        """
        Initialize the narrative manager.
        
        Args:
            system_state: Reference to the system state manager
            discord_service: Optional Discord service for broadcasting updates
        """
        self.system_state = system_state
        self.discord_service = discord_service
        ensure_directory(BASE_OUTPUT_PATH)
        
        # Load narrative templates
        self.template_env = self._setup_template_env()
    
    def _setup_template_env(self):
        """Set up Jinja2 template environment."""
        try:
            from jinja2 import Environment, FileSystemLoader
            return Environment(
                loader=FileSystemLoader(TEMPLATE_DIR),
                autoescape=True
            )
        except Exception as e:
            logger.error(f"Failed to setup template environment: {e}")
            return None
    
    def extract_narrative_elements(self, response: str) -> Dict[str, Any]:
        """
        Extract narrative elements from a response.
        
        Args:
            response: The response text to analyze
            
        Returns:
            Dictionary containing extracted narrative elements
        """
        try:
            # Look for narrative update blocks
            narrative_pattern = r"NARRATIVE_UPDATE:?\s*({[\s\S]*?})"
            import re
            match = re.search(narrative_pattern, response)
            
            if match:
                narrative_data = json.loads(match.group(1))
                logger.info(f"Extracted narrative data: {narrative_data}")
                return narrative_data
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to extract narrative elements: {e}")
            return {}
    
    def process_response(self, prompt_type: str, prompt_text: str, response: str, chat_title: str) -> Dict[str, Any]:
        """
        Process a response and extract narrative elements.
        
        Args:
            prompt_type: Type of prompt that generated the response
            prompt_text: The prompt text used
            response: The response text
            chat_title: Title of the chat
            
        Returns:
            Dictionary containing feedback and narrative data
        """
        try:
            # Extract narrative elements
            narrative_data = self.extract_narrative_elements(response)
            
            # Generate feedback
            feedback = {
                "prompt_type": prompt_type,
                "chat_title": chat_title,
                "timestamp": get_timestamp(),
                "narrative_elements": narrative_data
            }
            
            # Update system state with narrative data
            if narrative_data:
                self.system_state.update(narrative_data)
            
            return feedback
            
        except Exception as e:
            logger.error(f"Failed to process response: {e}")
            return {}
    
    def broadcast_update(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Broadcast a narrative update to Discord.
        
        Args:
            event_type: Type of narrative event
            event_data: Data associated with the event
        """
        try:
            if not self.discord_service:
                return
                
            message = self._format_narrative_message(event_type, event_data)
            if message:
                self.discord_service.send_message(message)
                
        except Exception as e:
            logger.error(f"Failed to broadcast narrative update: {e}")
    
    def _format_narrative_message(self, event_type: str, event_data: Dict[str, Any]) -> str:
        """
        Format a narrative message for Discord.
        
        Args:
            event_type: Type of narrative event
            event_data: Data associated with the event
            
        Returns:
            Formatted message string
        """
        try:
            # Get appropriate template
            template_name = f"{event_type}_message.j2"
            template = self.template_env.get_template(template_name)
            
            # Prepare context
            context = {
                "event_data": event_data,
                "system_state": self.system_state.get_state(),
                "timestamp": get_timestamp()
            }
            
            # Render message
            return template.render(**context)
            
        except Exception as e:
            logger.error(f"Failed to format narrative message: {e}")
            return ""
    
    def generate_narrative_report(self) -> None:
        """Generate and save a narrative report."""
        try:
            # Create report directory if it doesn't exist
            report_dir = os.path.join(BASE_OUTPUT_PATH, "narrative_reports")
            ensure_directory(report_dir)
            
            # Generate report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(report_dir, f"narrative_report_{timestamp}.json")
            
            # Prepare report data
            report_data = {
                "system_state": self.system_state.get_state(),
                "narrative_events": self.system_state.get_narrative_events(),
                "timestamp": get_timestamp()
            }
            
            # Save report
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"Narrative report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate narrative report: {e}")
    
    def add_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Add a new narrative event.
        
        Args:
            event_type: Type of event
            event_data: Data associated with the event
        """
        try:
            self.system_state.add_narrative_event(event_type, event_data)
            self.broadcast_update(event_type, event_data)
            logger.info(f"Added {event_type} event to narrative tracking")
            
        except Exception as e:
            logger.error(f"Failed to add narrative event: {e}") 

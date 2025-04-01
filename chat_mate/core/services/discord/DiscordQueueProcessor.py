from typing import Dict, Any
from core.config.config_manager import ConfigManager
from core.logging.CompositeLogger import CompositeLogger
from core.UnifiedDiscordService import UnifiedDiscordService

class DiscordQueueProcessor:
    """Queues processed responses for Discord or other destinations."""

    def __init__(self, config_manager: ConfigManager, logger: CompositeLogger):
        self.config_manager = config_manager
        self.logger = logger
        self.discord_service = UnifiedDiscordService(config_manager)

    def queue_response(self, response: Dict[str, Any]) -> None:
        """
        Queue response for Discord delivery.

        Args:
            response: Processed response data.
        """
        self.logger.log("Queuing response for Discord...", domain="DiscordQueueProcessor")

        if not response:
            self.logger.log_error("Empty response provided to DiscordQueueProcessor.")
            return

        # Push to Discord
        self.discord_service.send_message(content=response.get("reinforced_response", "No content available"))
        self.logger.log("Response queued to Discord successfully.", domain="DiscordQueueProcessor")

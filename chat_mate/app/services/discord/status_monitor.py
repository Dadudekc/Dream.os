from typing import Optional, List
from app.schemas.discord_schema import BotStatus
from .bot_manager import BotManager

class StatusMonitor:
    def __init__(self, bot_manager: BotManager):
        self.bot_manager = bot_manager

    async def get_status(self) -> BotStatus:
        if not self.bot_manager.is_running:
            return BotStatus(
                status="stopped",
                message="Bot is not running"
            )

        bot = self.bot_manager.bot
        return BotStatus(
            status="running" if bot.is_ready() else "connecting",
            message="Bot is operational" if bot.is_ready() else "Bot is connecting",
            uptime=self.bot_manager.uptime,
            last_heartbeat=bot.last_heartbeat,
            connected_servers=len(bot.guilds) if bot.is_ready() else 0,
            active_channels=list(bot.active_channels) if hasattr(bot, 'active_channels') else None
        ) 
from discord.DreamscapeDiscordBot import DreamscapeDiscordBot
from config.ConfigManager import ConfigManager

if __name__ == "__main__":
    config = ConfigManager()
    token = config.get("discord_token")
    channel_id = int(config.get("discord_channel"))

    bot = DreamscapeDiscordBot(token=token, default_channel_id=channel_id)
    bot.run_bot()

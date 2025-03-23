# app/core/discord_bot.py

import discord
from discord.ext import commands

class DreamscapeBot(commands.Bot):
    def __init__(self, command_prefix='!', intents=None):
        if intents is None:
            intents = discord.Intents.default()
            intents.messages = True
            intents.guilds = True
        
        super().__init__(command_prefix=command_prefix, intents=intents)
        
    async def on_ready(self):
        print(f'DreamscapeBot is online. Logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        await self.process_commands(message)

# Instantiate the bot
dreamscape_bot = DreamscapeBot(command_prefix="!")

#!/usr/bin/env python3
"""
Chat Mate - Discord bot and automation tool for chatbot interactions
"""

import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Discord bot
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set. Please check your .env file.")
    sys.exit(1)

# Configure Discord bot
intents = discord.Intents.default()
intents.messages = True
client = commands.Bot(command_prefix="!", intents=intents)

@client.event
async def on_ready():
    """Run when the bot has successfully connected."""
    print(f'Logged in as {client.user}')

@client.command()
async def hello(ctx):
    """Simple command to test the bot."""
    await ctx.send("Hello! I'm Chat Mate bot.")

def main():
    """Main entry point for the application."""
    try:
        client.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Invalid Discord token. Please check your .env file.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

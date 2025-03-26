import discord
from discord.ext import commands
from character_parser import CharacterParser
import json
import os

# === CONFIGURATION ===
TOKEN = "YOUR_DISCORD_BOT_TOKEN"
UPLOAD_CHANNEL_NAME = "submit-character"
CHARACTER_OUTPUT_DIR = "./parsed_characters"
ROSTER_PATH = "./characters.json"

# === OOP ARCHITECTURE ===

class CharacterBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parser = CharacterParser()
        os.makedirs(CHARACTER_OUTPUT_DIR, exist_ok=True)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Character Parser Bot ready as {self.bot.user}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.name != UPLOAD_CHANNEL_NAME:
            return

        for attachment in message.attachments:
            if attachment.filename.endswith(".md"):
                await self.process_character_upload(attachment, message)

    async def process_character_upload(self, attachment, message):
        try:
            raw_bytes = await attachment.read()
            markdown = raw_bytes.decode("utf-8")

            profile = self.parser.parse_profile(markdown)
            filename = self._format_filename(profile["name"])
            filepath = os.path.join(CHARACTER_OUTPUT_DIR, filename)

            self._save_json(profile, filepath)
            self._update_roster(profile)

            await message.reply(
                f"✅ Parsed character: **{profile['name']}**\nDownload below:",
                file=discord.File(filepath)
            )

            os.remove(filepath)

        except Exception as e:
            await message.reply(f"❌ Error parsing character: `{str(e)}`")

    def _format_filename(self, name):
        return name.replace(" ", "_").lower() + ".json"

    def _save_json(self, profile, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)

    def _update_roster(self, profile):
        roster = []
        if os.path.exists(ROSTER_PATH):
            with open(ROSTER_PATH, "r", encoding="utf-8") as f:
                roster = json.load(f)
        roster.append(profile)
        with open(ROSTER_PATH, "w", encoding="utf-8") as f:
            json.dump(roster, f, indent=2)

# === BOT BOOTSTRAP ===

def main():
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    bot.add_cog(CharacterBot(bot))
    bot.run(TOKEN)

if __name__ == "__main__":
    main()

import discord
from discord.ext import commands
from core.ChatManager import ChatManager
from core.PathManager import PathManager
from core.services.dreamscape_generator_service import DreamscapeGenerationService
from core.TemplateManager import TemplateManager
from pathlib import Path
import json
import logging

logger = logging.getLogger("DreamscapeDiscordBot")
logger.setLevel(logging.INFO)

class DreamscapeDiscordBot(commands.Bot):
    """
    Discord bot specialized for interacting with Dreamscape episodes.
    """

    def __init__(self, token: str, default_channel_id: int, command_prefix='!'):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True

        super().__init__(command_prefix=command_prefix, intents=intents)
        
        self.token = token
        self.default_channel_id = default_channel_id
        self.path_manager = PathManager()
        
        # Set up Dreamscape generation service
        self.template_manager = TemplateManager(
            template_dir=self.path_manager.get_path("templates") / "dreamscape_templates"
        )
        self.dreamscape_service = DreamscapeGenerationService(
            path_manager=self.path_manager,
            template_manager=self.template_manager
        )

        # Set up Chat Manager
        self.chat_manager = ChatManager(
            driver_options={
                "headless": True,
                "disable_gpu": True,
                "no_sandbox": True
            },
            model="gpt-4o",
            headless=True
        )
        self.chat_manager.dreamscape_service = self.dreamscape_service

        self.episode_dir = self.path_manager.get_path("dreamscape")
        self.memory_file = self.path_manager.get_path("memory") / "episode_chain.json"

        self._setup_commands()

    def _setup_commands(self):

        @self.command(name='play')
        async def play(ctx, *, chat_title: str = None):
            """Generate a Dreamscape episode from a specific chat or the latest one."""
            await ctx.send("⚔️ Generating your Dreamscape episode...")
            try:
                if not chat_title:
                    chats = self.chat_manager.get_all_chat_titles()
                    chat_title = chats[0].get('title', 'Untitled') if chats else "Default Adventure"
                
                episode_path = self.chat_manager.generate_dreamscape_episode(chat_title)

                if episode_path and Path(episode_path).exists():
                    content = Path(episode_path).read_text(encoding='utf-8')[:1800]
                    await ctx.send(f"🎉 **New Dreamscape Episode:** {Path(episode_path).name}\n```markdown\n{content}...\n```")
                else:
                    await ctx.send("❌ Could not generate episode.")
            except Exception as e:
                logger.exception(f"Error during episode generation: {e}")
                await ctx.send(f"❌ An error occurred: {e}")

        @self.command(name='episode_latest')
        async def episode_latest(ctx):
            """Retrieve the latest generated episode."""
            try:
                episodes = sorted(self.episode_dir.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)
                if episodes:
                    content = episodes[0].read_text(encoding='utf-8')[:1800]
                    await ctx.send(f"📝 **Latest Episode:** `{episodes[0].name}`\n```markdown\n{content}...\n```")
                else:
                    await ctx.send("⚠️ No episodes found.")
            except Exception as e:
                logger.exception(f"Error retrieving latest episode: {e}")
                await ctx.send(f"❌ An error occurred: {e}")

        @self.command(name='episodes')
        async def episodes(ctx, count: int = 5):
            """List recent Dreamscape episodes."""
            try:
                episodes = sorted(self.episode_dir.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)[:count]
                if episodes:
                    episode_list = "\n".join(f"- {ep.name}" for ep in episodes)
                    await ctx.send(f"📜 **Recent Episodes:**\n{episode_list}")
                else:
                    await ctx.send("⚠️ No episodes found.")
            except Exception as e:
                logger.exception(f"Error listing episodes: {e}")
                await ctx.send(f"❌ An error occurred: {e}")

        @self.command(name='status')
        async def status(ctx):
            """Show bot and Dreamscape status."""
            if self.memory_file.exists():
                memory = json.loads(self.memory_file.read_text())
                total_episodes = memory.get("episode_count", 0)
                ongoing = len(memory.get("ongoing_quests", []))
                completed = len(memory.get("completed_quests", []))

                await ctx.send(
                    f"🛡️ **Dreamscape Status:**\n"
                    f"- Total Episodes: `{total_episodes}`\n"
                    f"- Ongoing Quests: `{ongoing}`\n"
                    f"- Completed Quests: `{completed}`"
                )
            else:
                await ctx.send("⚠️ Dreamscape memory file not found.")

    def run_bot(self):
        logger.info("Launching Dreamscape Discord Bot...")
        super().run(self.token)


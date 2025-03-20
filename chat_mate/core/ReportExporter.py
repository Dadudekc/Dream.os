import os
import asyncio
from datetime import datetime
from core.PathManager import PathManager
from core.DiscordTemplateManager import DiscordTemplateManager
from jinja2 import Environment, FileSystemLoader, select_autoescape

class ReportExporter:
    """
    Handles multi-template export (Markdown, HTML, Discord) from summaries.
    """
    def __init__(self, discord_manager: DiscordTemplateManager = None):
        self.discord_manager = discord_manager

        self.env = Environment(
            loader=FileSystemLoader(PathManager.templates_dir),
            autoescape=select_autoescape(['html', 'xml', 'md'])
        )

    def export_markdown(self, summary: dict, output_filename: str):
        """Export Markdown report."""
        template = self.env.get_template("ai_summary_report.md.j2")
        report = template.render(summary=summary, generated_on=datetime.now().isoformat())

        output_path = os.path.join(PathManager.reinforcement_logs_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"✅ Markdown report exported: {output_path}")
        return output_path

    def export_html(self, summary: dict, output_filename: str):
        """Export HTML report."""
        template = self.env.get_template("ai_summary_report.html.j2")
        report = template.render(summary=summary, generated_on=datetime.now().isoformat())

        output_path = os.path.join(PathManager.reinforcement_logs_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"✅ HTML report exported: {output_path}")
        return output_path

    async def send_discord_report(self, summary: dict):
        """Send report to Discord (DiscordTemplateManager)."""
        if not self.discord_manager:
            print("❌ Discord manager not initialized.")
            return

        message = self.discord_manager.render_message("ai_summary_discord", summary)
        await self.discord_manager.send_message(message)
        print("📤 Discord report sent.")

    def send_discord_report_sync(self, summary: dict):
        asyncio.run(self.send_discord_report(summary))

import os
import json
import asyncio
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from core.UnifiedDiscordService import UnifiedDiscordService

class ReportExporter:
    """
    Handles exporting reports in various formats (Markdown, HTML, Discord).
    Uses templates for consistent formatting.
    """

    def __init__(self, discord_service: UnifiedDiscordService = None, template_dir: str = "templates/reports"):
        """
        Initialize ReportExporter.
        
        Args:
            discord_service: Optional UnifiedDiscordService instance for Discord integration
            template_dir: Directory containing report templates
        """
        self.discord = discord_service
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def export_markdown(self, summary: dict, output_file: str) -> str:
        """Export report as Markdown."""
        try:
            template = self.template_env.get_template("report_markdown.j2")
            content = template.render(summary)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
                
            print(f"📝 Markdown report saved to {output_file}")
            return content
        except Exception as e:
            print(f"❌ Failed to export Markdown report: {e}")
            return ""

    def export_html(self, summary: dict, output_file: str) -> str:
        """Export report as HTML."""
        try:
            template = self.template_env.get_template("report_html.j2")
            content = template.render(summary)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
                
            print(f"📝 HTML report saved to {output_file}")
            return content
        except Exception as e:
            print(f"❌ Failed to export HTML report: {e}")
            return ""

    def send_discord_report(self, summary: dict) -> None:
        """Send report to Discord using UnifiedDiscordService."""
        if not self.discord:
            print("❌ Discord service not initialized.")
            return
            
        try:
            self.discord.send_template("ai_summary_discord", summary)
            print("📤 Discord report sent.")
        except Exception as e:
            print(f"❌ Failed to send Discord report: {e}")

    def send_discord_report_sync(self, summary: dict) -> None:
        """Synchronous wrapper for sending Discord report."""
        self.send_discord_report(summary)

import os
import threading
import time
import logging
import json
import re
import asyncio
import queue
from datetime import datetime
from typing import List, Dict, Any

import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget,
    QPushButton, QListWidgetItem, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt

# Core Imports (assumed available in your project)
from core.ResponseHandler import ResponseHandler
from core.ChatManager import ChatManager
from core.FileManager import FileManager
from core.ReinforcementEngine import ReinforcementEngine
from core.TemplateManager import TemplateManager

# Selenium helpers for file upload
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Jinja2 templating for archival reports and Discord messages
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound, select_autoescape

# New imports for UnifiedDiscordService
from core.UnifiedDiscordService import UnifiedDiscordService
from core.UnifiedDriverManager import UnifiedDriverManager

# --------------------------------------------------------------------
# Project Root & Template Path Handling
# --------------------------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(ROOT_DIR, "templates", "discord_templates")

# --------------------------------------------------------------------
# Configuration Constants (moved to config if available)
# --------------------------------------------------------------------
try:
    from config import RATE_LIMIT_DELAY, MAX_ACTIONS_BEFORE_COOLDOWN, COOLDOWN_PERIOD, BASE_OUTPUT_PATH
except ImportError:
    RATE_LIMIT_DELAY = 10
    MAX_ACTIONS_BEFORE_COOLDOWN = 5
    COOLDOWN_PERIOD = 60
    BASE_OUTPUT_PATH = "prompt_cycle_outputs"

# --------------------------------------------------------------------
# Logging Setup and Icon Definitions
# --------------------------------------------------------------------
logger = logging.getLogger("PromptCycle")
logging.basicConfig(level=logging.INFO)

LOG_ICONS = {
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌",
    "success": "✅",
    "cooldown": "⏳",
    "upload": "📤",
}

# --------------------------------------------------------------------
# Utility Functions
# --------------------------------------------------------------------
def sanitize(text: str) -> str:
    """Utility to sanitize file names or strings if needed."""
    return "".join(c for c in text if c.isalnum() or c in (' ', '_', '-')).rstrip()

# --------------------------------------------------------------------
# Prompt Cycle Dialog (UI)
# --------------------------------------------------------------------
class PromptCycleDialog(QDialog):
    """
    Dialog for selecting prompts to include in the cycle.
    """
    def __init__(self, prompt_manager, start_cycle_callback):
        """
        :param prompt_manager: Manager that lists or retrieves available prompts.
        :param start_cycle_callback: Callback function that takes selected prompt names and begins the cycle.
        """
        super().__init__()
        self.prompt_manager = prompt_manager
        self.start_cycle_callback = start_cycle_callback

        self.setWindowTitle("Prompt Cycle Mode")
        self.setGeometry(200, 200, 400, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select prompts to include in the cycle:"))

        self.prompt_list_widget = QListWidget()
        self.prompt_list_widget.setSelectionMode(QListWidget.MultiSelection)

        # Load prompt types from the manager
        for prompt_type in self.prompt_manager.list_available_prompts():
            item = QListWidgetItem(prompt_type)
            self.prompt_list_widget.addItem(item)

        layout.addWidget(self.prompt_list_widget)

        start_button = QPushButton("Start Cycle")
        start_button.clicked.connect(self.start_cycle)
        layout.addWidget(start_button)

        self.setLayout(layout)

    def start_cycle(self):
        selected_prompts = [item.text() for item in self.prompt_list_widget.selectedItems()]
        if not selected_prompts:
            QMessageBox.warning(self, "No Prompts Selected", "Please select at least one prompt.")
            return

        self.start_cycle_callback(selected_prompts)
        self.accept()

# --------------------------------------------------------------------
# Prompt Cycle Manager (Unified, Full Sync Mode)
# --------------------------------------------------------------------
class PromptCycleManager:
    """
    Manages and executes prompt cycles in both single-chat and multi-chat modes.
    Implements full sync mode improvements: standardized logging, error handling,
    asynchronous Discord message batching, and dynamic rate-limit adjustments.
    """
    def __init__(
        self,
        prompt_manager,
        memory_manager=None,
        discord_service=None,
        append_output=None,
        driver_options=None,
        base_output_dir=None,
        discord_templates_dir=None,
        dry_run=False,
        verbose=False
    ):
        """
        :param prompt_manager: Manager for retrieving prompt text and associated models.
        :param memory_manager: (Optional) For persisting structured memory updates.
        :param discord_service: (Optional) For posting messages to Discord.
        :param append_output: Callback for logging output (e.g. GUI or console).
        :param driver_options: Optional dictionary of WebDriver configuration options.
        :param base_output_dir: Directory for storing text responses.
        :param discord_templates_dir: Directory for external Discord message templates.
        :param dry_run: If True, simulate operations without actual side effects.
        :param verbose: If True, enable detailed logging.
        """
        self.prompt_manager = prompt_manager
        self.memory_manager = memory_manager
        self.discord = discord_service
        self.append_output = append_output or (lambda msg: print(msg))
        self.driver_manager = UnifiedDriverManager(driver_options)
        self.chat_manager = None
        self.response_handler = None
        self.dry_run = dry_run
        self.verbose = verbose

        # Initialize file management
        self.file_manager = FileManager()
        
        # Initialize reinforcement engine
        self.reinforcement_engine = ReinforcementEngine()

        # Instantiate TemplateManager
        self.template_manager = TemplateManager()
        self.log(f"{LOG_ICONS['info']} TemplateManager initialized.")

        # Event hooks for external callback integrations.
        self.on_prompt_sent = None
        self.on_response_received = None

        # Initialize Discord message queue for batching.
        self.discord_queue = queue.Queue()
        if self.discord:
            self._start_discord_queue_processor()

        # Initialize current cycle speed for dynamic adjustments.
        self.current_cycle_speed = RATE_LIMIT_DELAY

    def log(self, message: str):
        """
        Unified logging method: logs to both logger and output callback.
        """
        logger.info(message)
        self.append_output(message)

    def _lazy_init(self):
        """
        Ensure ChatManager and ResponseHandler are initialized.
        """
        if not self.chat_manager:
            self.chat_manager = ChatManager(
                driver=self.driver_manager.get_driver(),
                model="gpt-4o"
            )
        if not self.response_handler:
            self.response_handler = ResponseHandler(driver=self.driver_manager.get_driver())

    def _manual_login(self):
        """
        Prompts for manual ChatGPT login if required.
        """
        self.log(f"{LOG_ICONS['warning']} Manual login required. Opening ChatGPT login page...")
        try:
            self.driver_manager.get_driver().get("https://chat.openai.com/auth/login")
        except Exception as e:
            self.log(f"{LOG_ICONS['error']} Driver error during manual login: {e}")
            self.attempt_relogin()
        input(">> Press ENTER after logging in... <<")
        self.response_handler.save_cookies()

    def attempt_relogin(self, retries=3):
        """
        Attempts to re-login if session expires without exiting the thread.
        """
        for i in range(retries):
            self.log(f"{LOG_ICONS['warning']} Attempting re-login... (Attempt {i+1})")
            self._manual_login()
            if self.response_handler.is_logged_in():
                self.log(f"{LOG_ICONS['success']} Re-login successful.")
                return True
            time.sleep(5)
        self.log(f"{LOG_ICONS['error']} Re-login failed after {retries} attempts.")
        return False

    def _wait_for_page_load(self, driver, timeout=10):
        """
        Waits for the page to load completely using document.readyState.
        """
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
        except Exception as e:
            self.log(f"{LOG_ICONS['warning']} Page load wait error: {e}")

    def _start_discord_queue_processor(self):
        """
        Starts a background thread to process and batch Discord messages.
        """
        thread = threading.Thread(target=self._process_discord_queue, daemon=True)
        thread.start()
        self.log(f"{LOG_ICONS['info']} Discord message processor started.")

    def _process_discord_queue(self):
        """
        Processes Discord messages from the queue and sends them in batch.
        """
        while True:
            try:
                template_filename, data = self.discord_queue.get(timeout=5)
                message = self.template_manager.render_discord_template(template_filename, data)
                self.discord.send_template(template_filename, data)
                self.log(f"{LOG_ICONS['upload']} Sent templated Discord message using '{template_filename}'.")
            except queue.Empty:
                continue
            except Exception as e:
                self.log(f"{LOG_ICONS['error']} Error processing discord message: {e}")

    def _process_prompt(self, prompt_type: str, chat: Dict[str, Any] = None, files_to_send=None, paste_files=False, upload_files=False) -> float:
        """
        Processes a single prompt: sends prompt, waits for response, saves and logs results.
        Returns the response time in seconds.
        """
        start_time = time.time()
        try:
            prompt_text = self.prompt_manager.get_prompt(prompt_type)
            model = self.prompt_manager.get_model(prompt_type)

            if files_to_send and (paste_files or upload_files):
                prompt_text = self._build_prompt_with_files(prompt_text, files_to_send)

            self.log(f"{LOG_ICONS['send']} Sending prompt '{prompt_type}' (Model: {model})")

            if self.on_prompt_sent:
                self.on_prompt_sent(prompt_type, prompt_text)

            if not self.response_handler.send_prompt(prompt_text):
                self.log(f"{LOG_ICONS['error']} Failed to send prompt '{prompt_type}'")
                return 0

            response = self.response_handler.wait_for_stable_response()

            if response:
                elapsed = time.time() - start_time
                self.log(f"[{prompt_type} - {model}]: {response}")
                self._save_prompt_response(prompt_type, response)
                
                if self.memory_manager:
                    self.memory_manager.update(prompt_type, response)
                    self.log(f"{LOG_ICONS['info']} Persistent memory updated for '{prompt_type}'")
                    
                detailed_feedback = self.detailed_reinforcement_feedback(prompt_type, prompt_text, response)
                self.log(f"{LOG_ICONS['info']} Detailed reinforcement feedback: {detailed_feedback}")

                # Call event hook
                if self.on_response_received:
                    self.on_response_received(prompt_type, response)

                # Send to Discord if available
                if self.discord:
                    template_file = "dreamscape.j2" if prompt_type.lower() == "dreamscape" else "status_update.j2"
                    data = {"prompt": prompt_type, "response": response}
                    if chat:
                        data["chat_title"] = chat.get("title", "Untitled")
                    self.send_templated_discord_message(template_file, data)
            else:
                self.log(f"{LOG_ICONS['warning']} No stable response for '{prompt_type}' (Model: {model}).")
                
            return time.time() - start_time
        except Exception as e:
            self.log(f"{LOG_ICONS['error']} Error processing prompt '{prompt_type}': {e}")
            logger.exception(e)
            return 0

    def run_cycle(self, prompts, files_to_send=None, paste_files=False, upload_files=False, cycle_speed=RATE_LIMIT_DELAY):
        """
        Creates a new chat session for each prompt in single-chat mode.
        """
        self._lazy_init()
        thread = threading.Thread(
            target=self._cycle_thread_single,
            args=(prompts, files_to_send, paste_files, upload_files, cycle_speed),
            daemon=True
        )
        thread.start()

    def _cycle_thread_single(self, prompts, files_to_send, paste_files, upload_files, cycle_speed):
        self.log(f"{LOG_ICONS['info']} Starting SINGLE-chat cycle for {len(prompts)} prompts...")

        if not self.response_handler.is_logged_in():
            self._manual_login()

        actions = 0
        for prompt_type in prompts:
            response_time = self._process_prompt(prompt_type, files_to_send=files_to_send, paste_files=paste_files, upload_files=upload_files)
            actions += 1
            # Dynamic rate-limit adjustment based on response time.
            if response_time > 10:
                self.current_cycle_speed = min(self.current_cycle_speed + 2, 30)
            elif response_time < 5:
                self.current_cycle_speed = max(self.current_cycle_speed - 1, 3)

            if actions % MAX_ACTIONS_BEFORE_COOLDOWN == 0:
                self.log(f"{LOG_ICONS['cooldown']} Cooldown triggered. Waiting {COOLDOWN_PERIOD} seconds...")
                time.sleep(COOLDOWN_PERIOD)
            else:
                self.log(f"{LOG_ICONS['cooldown']} Rate-limited delay: {self.current_cycle_speed} seconds...")
                time.sleep(self.current_cycle_speed)

        self.log(f"{LOG_ICONS['success']} SINGLE-chat cycle complete!")
        self.response_handler.shutdown()
        self.generate_and_dispatch_reports({
            "total_prompts": len(prompts),
            "timestamp": datetime.now().isoformat(),
            "export_dir": self.base_output_dir
        })

    def run_cycle_on_all_chats(self, prompts, cycle_speed=RATE_LIMIT_DELAY):
        """
        Iterates over all existing ChatGPT history, sending each prompt in turn.
        """
        self._lazy_init()
        thread = threading.Thread(
            target=self._cycle_thread_multi,
            args=(prompts, cycle_speed),
            daemon=True
        )
        thread.start()

    def _cycle_thread_multi(self, prompts, cycle_speed):
        self.log(f"{LOG_ICONS['info']} Starting MULTI-chat cycle for {len(prompts)} prompts...")

        if not self.response_handler.is_logged_in():
            self._manual_login()

        all_chats = self.chat_manager.get_all_chat_titles()
        # Validate and filter chats with valid link.
        valid_chats = [chat for chat in all_chats if chat.get("link")]
        self.log(f"{LOG_ICONS['info']} Found {len(valid_chats)} valid chats in history.")

        actions = 0
        for chat in valid_chats:
            chat_title = chat.get("title", "Untitled")
            self.log(f"\n=== Processing Chat: {chat_title} ===")
            self.response_handler.driver.get(chat.get("link"))
            self._wait_for_page_load(self.response_handler.driver)

            for prompt_type in prompts:
                response_time = self._process_prompt(prompt_type, chat=chat)
                actions += 1
                if actions % MAX_ACTIONS_BEFORE_COOLDOWN == 0:
                    self.log(f"{LOG_ICONS['cooldown']} Cooldown triggered. Waiting {COOLDOWN_PERIOD} seconds...")
                    time.sleep(COOLDOWN_PERIOD)
                else:
                    self.log(f"{LOG_ICONS['cooldown']} Rate-limited delay: {cycle_speed} seconds...")
                    time.sleep(cycle_speed)

        self.log(f"{LOG_ICONS['success']} MULTI-chat cycle complete!")
        self.response_handler.shutdown()
        self.generate_and_dispatch_reports({
            "total_prompts": len(prompts),
            "timestamp": datetime.now().isoformat(),
            "export_dir": self.base_output_dir
        })

    def generate_and_dispatch_reports(self, summary: dict):
        """
        Generates summary reports in Markdown and HTML, dispatches them via Discord,
        and generates a feedback visualization chart.
        """
        from core.ReportExporter import ReportExporter  # Import from your project
        exporter = ReportExporter(discord_manager=self.discord)
        md_report = exporter.export_markdown(summary, "prompt_cycle_summary.md")
        html_report = exporter.export_html(summary, "prompt_cycle_summary.html")
        exporter.send_discord_report_sync(summary)
        self.log(f"{LOG_ICONS['info']} Reports generated: {md_report}, {html_report}")
        self._generate_feedback_chart(summary)

    def _generate_feedback_chart(self, summary: dict):
        """
        Generates a basic bar chart summarizing feedback metrics.
        """
        try:
            plt.figure()
            plt.bar(["Total Prompts"], [summary.get("total_prompts", 0)])
            chart_filename = f"feedback_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = os.path.join(self.base_output_dir, chart_filename)
            plt.savefig(chart_path)
            plt.close()
            self.log(f"{LOG_ICONS['info']} Feedback chart generated: {chart_path}")
        except Exception as e:
            self.log(f"{LOG_ICONS['error']} Error generating feedback chart: {e}")

    def send_templated_discord_message(self, template_name: str, data: dict) -> None:
        """Send a templated message to Discord."""
        if not self.discord:
            self.log(f"{LOG_ICONS['warning']} Discord service not available.")
            return
            
        try:
            self.discord.send_template(template_name, data)
            self.log(f"{LOG_ICONS['upload']} Sent templated Discord message using '{template_name}'.")
        except Exception as e:
            self.log(f"{LOG_ICONS['error']} Error sending Discord message: {e}")

    def detailed_reinforcement_feedback(self, prompt_type: str, prompt: str, response: str) -> Dict[str, Any]:
        """
        Analyzes the response using the reinforcement engine and returns feedback metrics.
        """
        base_score = self.reinforcement_engine.analyze_response(prompt_type, prompt, response)
        additional_metrics = self.reinforcement_engine.get_additional_metrics(prompt, response)
        feedback = {"base_score": base_score, **additional_metrics}
        return feedback

    def _upload_file_to_chatgpt(self, file_path):
        """
        Automates attaching a file by clicking the paperclip icon, sending the file path,
        and waiting briefly for ChatGPT to register the file.
        """
        driver = self.response_handler.driver
        try:
            attach_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Attach a file']"))
            )
            attach_button.click()
            time.sleep(1)
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(os.path.abspath(file_path))
            time.sleep(2)
            self.log(f"{LOG_ICONS['success']} Uploaded file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file '{file_path}': {e}")
            return False

    def _build_prompt_with_files(self, base_prompt_text, files_to_send):
        """
        Inserts each file's contents as a code block appended to the prompt.
        """
        lines = [base_prompt_text.strip(), "\n\n== Attached Files ==\n"]
        for fpath in files_to_send:
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    file_content = fh.read()
                fname = os.path.basename(fpath)
                lines.append(f"\n--- File: {fname} ---\n```python\n{file_content}\n```\n")
            except Exception as e:
                logger.error(f"Could not read file '{fpath}': {e}")
                lines.append(f"\n[File read error: {fpath} -> {e}]\n")
        return "\n".join(lines).strip()

    def _save_prompt_response(self, prompt_type, response_text, chat_title=None):
        """
        Saves the response text using the unified FileManager.
        """
        try:
            filepath = self.file_manager.save_response(
                content=response_text,
                prompt_type=prompt_type,
                chat_title=chat_title
            )
            if filepath:
                self.log(f"{LOG_ICONS['success']} Saved response for '{prompt_type}' in {filepath}")
            else:
                self.log(f"{LOG_ICONS['error']} Failed to save response for {prompt_type}")
        except Exception as e:
            err_msg = f"Failed to save response for {prompt_type}: {e}"
            logger.error(err_msg)
            self.log(err_msg)

    def generate_dreamscape_episodes(self, output_dir=None, cycle_speed=0):
        """
        Generates Dreamscape episodes for all chats.
        Now uses FileManager for file operations.
        """
        if not self.is_logged_in():
            self.log("Not logged in. Please log in first.")
            return

        chat_titles = self.chat_manager.get_all_chat_titles()
        if not chat_titles:
            self.log("No chats found to process.")
            return

        self.log(f"Starting Dreamscape episode generation for {len(chat_titles)} chats...")
        episode_counter = 1

        for chat_title in chat_titles:
            self.log(f"Processing chat: {chat_title}")
            
            try:
                episode_response = self._process_chat_for_dreamscape(chat_title)
                if not episode_response:
                    continue

                # Save episode using FileManager
                filepath = self.file_manager.save_response(
                    content=episode_response,
                    prompt_type="dreamscape",
                    chat_title=chat_title
                )
                
                if filepath:
                    self.log(f"{LOG_ICONS['success']} Saved Dreamscape episode for chat '{chat_title}'")
                    
                    if self.discord:
                        self.send_templated_discord_message(
                            "dreamscape.j2",
                            {"episode_text": episode_response, "chat_title": chat_title}
                        )
                else:
                    self.log(f"{LOG_ICONS['error']} Failed to save Dreamscape episode for chat '{chat_title}'")

            except Exception as e:
                self.log(f"Error processing chat '{chat_title}': {e}")
                continue

            episode_counter += 1
            time.sleep(cycle_speed)

        self.log(f"{LOG_ICONS['success']} Completed Dreamscape episode generation.")

    # ---------------------------
    # GUI & UTILITY HOOKS
    # ---------------------------
    def run_single_chat_mode(self):
        """
        Runs a single chat session using the first available prompt.
        """
        self._lazy_init()
        prompt_text = self.prompt_manager.get_prompt(self.prompt_manager.list_available_prompts()[0]) if self.prompt_manager else ""
        if not prompt_text:
            self.log("No prompt text provided. Aborting single-chat execution.")
            return
        self.log("Launching single-chat execution...")
        def single_chat_thread():
            prompts = [prompt_text]
            responses = self.chat_manager.execute_prompts_single_chat(prompts, cycle_speed=2)
            for i, resp in enumerate(responses, start=1):
                self.log(f"Prompt #{i} => {resp}")
            self.log("Single-chat execution complete.")
        threading.Thread(target=single_chat_thread, daemon=True).start()

    def run_multi_chat_mode(self):
        """
        Iterates over all chats and sends each line of the first prompt.
        """
        self._lazy_init()
        raw_prompt_text = self.prompt_manager.get_prompt(self.prompt_manager.list_available_prompts()[0]) if self.prompt_manager else ""
        if not raw_prompt_text:
            self.log("No prompt text provided. Aborting multi-chat execution.")
            return
        prompts = [line.strip() for line in raw_prompt_text.splitlines() if line.strip()]
        if not prompts:
            self.log("No valid prompts extracted from the editor.")
            return
        self.log("Launching multi-chat sequential execution...")
        def multi_chat_thread():
            all_chats = self.chat_manager.get_all_chat_titles()
            if hasattr(self.chat_manager, "reverse_checkbox") and self.chat_manager.reverse_checkbox.isChecked():
                all_chats.reverse()
            if not all_chats:
                self.log("No chats found. Aborting multi-chat execution.")
                return
            for chat in all_chats:
                chat_title = chat.get("title", "Untitled")
                self.log(f"\n--- Processing Chat: {chat_title} ---")
                for idx, prompt in enumerate(prompts, start=1):
                    self.log(f"Sending Prompt #{idx} to {chat_title}: {prompt}")
                    response = self.chat_manager.execute_prompt_cycle(prompt)
                    self.log(f"Response for Prompt #{idx} in {chat_title}: {response}")
                if hasattr(self.chat_manager, "archive_checkbox") and self.chat_manager.archive_checkbox.isChecked():
                    self.log(f"Archiving chat: {chat_title}")
                    self.chat_manager.archive_chat(chat)
            self.log("Multi-chat sequential execution complete.")
        threading.Thread(target=multi_chat_thread, daemon=True).start()

    def start_scraping(self, keep_driver_open: bool = False):
        """
        Demonstrates scraping chat titles or content from ChatGPT history.
        """
        self.log("Initializing scraping session...")
        exclusions = [item.text() for item in self.exclusion_list.selectedItems()] if hasattr(self, "exclusion_list") else []
        self.excluded_chats = exclusions

        if self.chat_manager and self.chat_manager.is_logged_in():
            self.log("Login detected. Proceeding with scraping.")
        else:
            self.log("Not logged in. Manual login required...")
            self.driver_manager.get_driver().get("https://chat.openai.com/auth/login")
            input(">> Press ENTER after logging in... <<")
            if self.chat_manager.is_logged_in():
                self.log("Manual login successful.")
            else:
                self.log("Login unsuccessful. Exiting scraping session.")
                if not keep_driver_open:
                    self.driver_manager.quit()
                return

        self.log("Starting chat scraping process...")
        all_chats = self.chat_manager.get_all_chat_titles()
        self.log(f"Found {len(all_chats)} chats to process.")
        if hasattr(self.chat_manager, "reverse_checkbox") and self.chat_manager.reverse_checkbox.isChecked():
            all_chats.reverse()
            self.log("Processing chats in reverse order.")

        for chat in all_chats:
            self.log(f"Scrape found chat: {chat['title']} => {chat['link']}")
        self.log("Scraping session complete!")
        if not keep_driver_open:
            self.driver_manager.quit()

    # ---------------------------
    # Additional Utility Methods
    # ---------------------------
    def load_selected_prompt(self, prompt_type: str):
        try:
            prompt_text = self.prompt_manager.get_prompt(prompt_type)
            model = self.prompt_manager.get_model(prompt_type)
            self.log(f"Loaded prompt '{prompt_type}' with model '{model}'.")
        except Exception as e:
            QMessageBox.warning(self, "Prompt Error", str(e))

    def save_prompt(self):
        self.log("Prompt saved (GUI placeholder).")

    def reset_prompts(self):
        self.prompt_manager.reset_to_defaults()
        self.log("Prompts have been reset to defaults.")

    def add_exclusion(self, title: str):
        self.log(f"Exclusion '{title}' added.")

    def remove_exclusion(self):
        self.log("Selected exclusions removed.")

    def browse_output_dir(self):
        self.log("Output directory set (GUI placeholder).")

    def archive_chat(self, chat: Dict[str, str]):
        try:
            logger.info(f"Archiving chat: {chat.get('title', 'Untitled')}")
            self.log(f"Archiving chat: {chat.get('title', 'Untitled')}")
        except Exception as e:
            logger.error(f"Error archiving chat: {e}")
            self.log(f"Error archiving chat: {e}")

    # ---------------------------
    # Discord & Reinforcement Integration
    # ---------------------------
    def open_discord_settings(self):
        from core.DiscordManager import DiscordSettingsDialog
        dialog = DiscordSettingsDialog(parent=self)
        dialog.exec_()

    def launch_discord_bot(self, bot_token: str, channel_id: int):
        self.log("Launching Discord bot...")
        self.discord = __import__("core.DiscordManager", fromlist=["DiscordManager"]).DiscordManager(bot_token, channel_id)
        def run_bot():
            self.discord.run_bot()
        self.discord_thread = threading.Thread(target=run_bot, daemon=True)
        self.discord_thread.start()
        self.log("Discord bot launched in background.")

    def open_reinforcement_tools(self):
        from core.ReinforcementEngine import ReinforcementToolsDialog
        dialog = ReinforcementToolsDialog(parent=self)
        dialog.exec_()

    def run_prompt_tuning(self):
        if not hasattr(self, "reinforcement_engine"):
            from core.ReinforcementEngine import ReinforcementEngine
            self.reinforcement_engine = ReinforcementEngine()
        self.reinforcement_engine.auto_tune_prompts(self.prompt_manager)
        self.log("Prompts auto-tuned via reinforcement feedback.")

    def launch_dashboard(self):
        self.log("Launching feedback dashboard... (stub)")

    def show_log_analysis(self):
        self.log("Showing log analysis... (stub)")

    def handle_hybrid_response(self, raw_response: str, prompt_manager: Any, chat_title: str = "Unknown Chat") -> None:
        """
        Parses the raw response to extract narrative text and a MEMORY_UPDATE JSON block,
        renders an archival report via Jinja2, saves the report, and updates persistent memory.
        """
        self.log("Handling hybrid response...")
        from core.ResponseHandler import HybridResponseHandler
        hybrid_handler = HybridResponseHandler()
        narrative_text, memory_update_json = hybrid_handler.parse_hybrid_response(raw_response)

        archive_template_str = (
            "--- Hybrid Response Archive ---\n"
            "Timestamp: {{ timestamp }}\n"
            "Chat Title: {{ chat_title }}\n\n"
            "=== Narrative Text ===\n"
            "{{ narrative_text }}\n\n"
            "=== MEMORY_UPDATE JSON ===\n"
            "{{ memory_update_json | tojson(indent=2) }}\n"
            "-------------------------------\n"
        )
        template = Template(archive_template_str)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rendered_report = template.render(
            timestamp=timestamp,
            chat_title=chat_title,
            narrative_text=narrative_text,
            memory_update_json=memory_update_json
        )
        archive_file = os.path.join("chat_mate", "content_logs", f"hybrid_response_{timestamp}.txt")
        with open(archive_file, 'w', encoding='utf-8') as f:
            f.write(rendered_report)
        self.log(f"Archived hybrid response to: {archive_file}")

        if memory_update_json:
            try:
                prompt_manager.parse_memory_updates(memory_update_json)
                self.log("Persistent memory updated via hybrid response.")
            except Exception as e:
                self.log(f"Failed to update persistent memory: {e}")
        else:
            self.log("No MEMORY_UPDATE JSON found in the response.")

    def __del__(self):
        """Cleanup when the manager is destroyed."""
        if hasattr(self, 'driver_manager'):
            self.driver_manager.quit()

# --------------------------------------------------------------------
# Main Entry Point - Launch the GUI
# --------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    from core.DreamscapeGUI import DreamscapeGUI

    app = QApplication(sys.argv)
    window = DreamscapeGUI()
    window.show()
    sys.exit(app.exec_())

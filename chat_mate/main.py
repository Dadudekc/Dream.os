#!/usr/bin/env python3
import sys
import os
import json
import time
import logging
import threading
import re
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLineEdit, QLabel, QTextEdit, QFileDialog,
    QListWidget, QListWidgetItem, QMessageBox, QCheckBox, QComboBox,
    QTabWidget, QDialog, QStackedWidget, QScrollArea, QInputDialog
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QTextCursor

# ---------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('log_output.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ---------------------------------------------------------------------
# Core Module Imports (assumed updated versions)
# ---------------------------------------------------------------------
from core.ChatManager import ChatManager
from core.AletheiaPromptManager import AletheiaPromptManager
from core.FileManager import FileManager
from core.DiscordManager import DiscordManager
from core.PromptCycleManager import PromptCycleManager
from core.PromptEngine import PromptEngine
from utils.prompt_tuner import tune_prompt, load_reinforcement_feedback
from core.AIOutputLogAnalyzer import AIOutputLogAnalyzer
from core.ReinforcementEngine import ReinforcementEngine
from core.UnifiedDreamscapeGenerator import DreamscapeEpisodeGenerator, OpenAIPromptEngine
from core.ResponseHandler import ResponseHandler

# Example excluded chat titles
DEFAULT_EXCLUDED_CHATS = [
    "ChatGPT", "Sora", "Freeride Investor", "Tbow Tactic Generator",
    "Explore GPTs", "Axiom", "work project", "prompt library", "Bot",
    "smartstock-pro", "Code Copilot"
]

# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------
def sanitize(text: str) -> str:
    """Sanitize a string for safe filename usage."""
    return re.sub(r'[\\/*?:"<>|]', "_", text).strip().replace(" ", "_")[:50]

def get_excluded_chats(widget: QListWidget) -> list:
    """Retrieve excluded chat titles from a QListWidget."""
    return [widget.item(i).text() for i in range(widget.count())]

def generate_full_run_json(chat_title: str, chat_link: str, prompt_executions: list, run_metadata: dict, output_dir: str) -> None:
    """Generate a summary JSON file for a run across multiple prompts."""
    full_run_data = {
        "run_metadata": {
            "timestamp": run_metadata.get("timestamp", datetime.now().isoformat()),
            "model": run_metadata.get("model", "gpt-4o-mini"),
            "chat_count": run_metadata.get("chat_count", 1),
            "prompt_count": len(prompt_executions),
            "execution_time": run_metadata.get("execution_time", "N/A"),
            "bottlenecks_detected": run_metadata.get("bottlenecks", [])
        },
        "prompts": prompt_executions,
        "overall_ai_learnings": run_metadata.get("overall_ai_learnings", {})
    }
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{sanitize(chat_title)}_full_run.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(full_run_data, f, indent=4, ensure_ascii=False)
        logger.info(f"✅ Saved full_run.json for '{chat_title}' at {file_path}")
    except Exception as e:
        logger.error(f"❌ Error saving full_run.json for '{chat_title}': {e}")

# ---------------------------------------------------------------------
# Reinforcement Tools Dialog (Popout)
# ---------------------------------------------------------------------
class ReinforcementToolsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reinforcement Tools")
        self.parent_gui = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        btn_tune = QPushButton("Run Prompt Tuning")
        btn_tune.clicked.connect(self.parent_gui.run_prompt_tuning)
        layout.addWidget(btn_tune)

        btn_dashboard = QPushButton("Launch Feedback Dashboard")
        btn_dashboard.clicked.connect(self.parent_gui.launch_dashboard)
        layout.addWidget(btn_dashboard)

        btn_logs = QPushButton("Show Log Analysis")
        btn_logs.clicked.connect(self.parent_gui.show_log_analysis)
        layout.addWidget(btn_logs)

        self.setLayout(layout)

# ---------------------------------------------------------------------
# Main GUI: DreamscapeGUI (Updated for Chat Threading)
# ---------------------------------------------------------------------
class DreamscapeGUI(QWidget):
    append_output_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Dreamscape Automation")
        self.setGeometry(100, 100, 1000, 800)

        # Initialize core managers
        self.prompt_manager = AletheiaPromptManager(prompt_file="prompts.json", memory_file="memory/persistent_memory.json")
        self.reinforcement_engine = ReinforcementEngine()
        self.discord_manager = None  # To be set via configuration or GUI
        self.chat_manager = None     # Will be created during execution

        self.cycle_manager = PromptCycleManager(prompt_manager=self.prompt_manager, append_output=self.append_output)
        self.initUI()
        self.append_output_signal.connect(self.append_output_handler)

    def initUI(self):
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_prompt_execution_tab(), "Prompt Execution")
        self.tabs.addTab(self._build_dreamscape_tab(), "Dreamscape Generation")
        self.tabs.addTab(self._build_configuration_tab(), "Configuration & Discord")
        self.tabs.addTab(self._build_logs_tab(), "Logs")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    # -------------------------------
    # Tab: Prompt Execution (Updated with Chat Threading)
    # -------------------------------
    def _build_prompt_execution_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        prompt_group = QGroupBox("Prompts")
        p_layout = QVBoxLayout()

        self.exclusion_list = QListWidget()
        for chat_name in DEFAULT_EXCLUDED_CHATS:
            self.exclusion_list.addItem(QListWidgetItem(chat_name))
        p_layout.addWidget(QLabel("Excluded Chats"))
        p_layout.addWidget(self.exclusion_list)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Exclusion")
        btn_add.clicked.connect(self.add_exclusion)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self.remove_exclusion)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        p_layout.addLayout(btn_layout)
        prompt_group.setLayout(p_layout)
        layout.addWidget(prompt_group)

        prompt_group2 = QGroupBox("Prompt Execution Controls")
        p_layout2 = QVBoxLayout()
        p_layout2.addWidget(QLabel("Select Prompt Type:"))
        self.prompt_selector = QComboBox()
        self.prompt_selector.addItems(self.prompt_manager.list_available_prompts())
        self.prompt_selector.currentTextChanged.connect(self.load_selected_prompt)
        p_layout2.addWidget(self.prompt_selector)

        self.prompt_stack = QStackedWidget()
        self.prompt_editor = QTextEdit()
        default_prompt = self.prompt_manager.get_prompt(self.prompt_selector.currentText())
        self.prompt_editor.setPlainText(default_prompt)
        self.prompt_stack.addWidget(self.prompt_editor)
        self.prompt_cycle_list = QListWidget()
        self.prompt_cycle_list.setSelectionMode(QListWidget.MultiSelection)
        for p in self.prompt_manager.list_available_prompts():
            self.prompt_cycle_list.addItem(QListWidgetItem(p))
        self.prompt_stack.addWidget(self.prompt_cycle_list)
        p_layout2.addWidget(QLabel("Prompt Input:"))
        p_layout2.addWidget(self.prompt_stack)

        mode_layout = QHBoxLayout()
        self.execution_mode_combo = QComboBox()
        self.execution_mode_combo.addItems(["Direct Execution", "Prompt Cycle Mode"])
        self.execution_mode_combo.currentTextChanged.connect(self.update_execution_mode)
        mode_layout.addWidget(QLabel("Execution Mode:"))
        mode_layout.addWidget(self.execution_mode_combo)
        p_layout2.addLayout(mode_layout)

        # New Chat Mode toggle integration
        self.mode_toggle_btn = QPushButton("Switch to New Chat Mode")
        self.mode_toggle_btn.clicked.connect(self.toggle_chat_mode)
        self.chat_mode_label = QLabel("Current Mode: Chat History")
        p_layout2.addWidget(self.mode_toggle_btn)
        p_layout2.addWidget(self.chat_mode_label)

        checkbox_layout = QHBoxLayout()
        self.headless_checkbox = QCheckBox("Run Headless Browser")
        checkbox_layout.addWidget(self.headless_checkbox)
        self.reverse_checkbox = QCheckBox("Process in Reverse Order")
        checkbox_layout.addWidget(self.reverse_checkbox)
        self.archive_checkbox = QCheckBox("Archive Chats")
        checkbox_layout.addWidget(self.archive_checkbox)
        p_layout2.addLayout(checkbox_layout)

        self.execute_prompt_btn = QPushButton("Execute Prompt")
        self.execute_prompt_btn.clicked.connect(self.execute_prompt)
        p_layout2.addWidget(self.execute_prompt_btn)

        btn_layout2 = QHBoxLayout()
        self.save_prompt_btn = QPushButton("Save Prompt")
        self.save_prompt_btn.clicked.connect(self.save_prompt)
        self.reset_prompts_btn = QPushButton("Reset Prompts")
        self.reset_prompts_btn.clicked.connect(self.reset_prompts)
        btn_layout2.addWidget(self.save_prompt_btn)
        btn_layout2.addWidget(self.reset_prompts_btn)
        p_layout2.addLayout(btn_layout2)

        btn_generate_dreamscape = QPushButton("Generate Dreamscape Episodes")
        btn_generate_dreamscape.clicked.connect(self.generate_dreamscape_episodes_ui)
        p_layout2.addWidget(btn_generate_dreamscape)

        prompt_group2.setLayout(p_layout2)
        layout.addWidget(prompt_group2)
        tab.setLayout(layout)
        return tab

    # -------------------------------
    # Tab: Dreamscape Generation
    # -------------------------------
    def _build_dreamscape_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        info_label = QLabel("Click the button below to run the unified Dreamscape generator.\n(This will process chats using ChatGPT and post-process with Ollama.)")
        layout.addWidget(info_label)
        btn_generate = QPushButton("Generate Dreamscape Episodes")
        btn_generate.clicked.connect(self.generate_dreamscape_episodes_ui)
        layout.addWidget(btn_generate)
        tab.setLayout(layout)
        return tab

    # -------------------------------
    # Tab: Configuration & Discord
    # -------------------------------
    def _build_configuration_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        output_dir_layout = QHBoxLayout()
        self.output_dir = QLineEdit(FileManager().base_folder)
        output_dir_layout.addWidget(self.output_dir)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(btn_browse)
        config_layout.addWidget(QLabel("Output Directory:"))
        config_layout.addLayout(output_dir_layout)

        model_layout = QHBoxLayout()
        self.model_selector = QComboBox()
        self.model_selector.addItems(["gpt-4o-mini", "gpt-4o", "gpt-4o-jawbone", "gpt-4-5", "o3-mini-high", "o1"])
        self.model_selector.setCurrentText("gpt-4o-mini")
        model_layout.addWidget(QLabel("Select Model:"))
        model_layout.addWidget(self.model_selector)
        config_layout.addLayout(model_layout)

        config_layout.addWidget(QLabel("Discord Bot Settings:"))
        config_layout.addLayout(self._create_discord_controls())
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        tab.setLayout(layout)
        return tab

    # -------------------------------
    # Tab: Logs
    # -------------------------------
    def _build_logs_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        layout.addWidget(QLabel("Application Logs:"))
        layout.addWidget(self.log_viewer)
        tab.setLayout(layout)
        return tab

    # -------------------------------
    # Discord Controls (Configuration Tab)
    # -------------------------------
    def _create_discord_controls(self) -> QVBoxLayout:
        discord_layout = QVBoxLayout()
        self.discord_token_input = QLineEdit()
        self.discord_token_input.setPlaceholderText("Enter Discord Bot Token")
        discord_layout.addWidget(QLabel("Discord Bot Token:"))
        discord_layout.addWidget(self.discord_token_input)

        self.discord_channel_input = QLineEdit()
        self.discord_channel_input.setPlaceholderText("Enter Default Channel ID")
        discord_layout.addWidget(QLabel("Default Channel ID:"))
        discord_layout.addWidget(self.discord_channel_input)

        btn_launch = QPushButton("Launch Discord Bot")
        btn_launch.clicked.connect(self.launch_discord_bot_from_gui)
        discord_layout.addWidget(btn_launch)

        btn_stop = QPushButton("Stop Discord Bot")
        btn_stop.clicked.connect(self.stop_discord_bot_from_gui)
        discord_layout.addWidget(btn_stop)

        self.discord_status_label = QLabel("Status: 🔴 Disconnected")
        discord_layout.addWidget(self.discord_status_label)
        self.discord_log_viewer = QTextEdit()
        self.discord_log_viewer.setReadOnly(True)
        discord_layout.addWidget(QLabel("Discord Bot Logs:"))
        discord_layout.addWidget(self.discord_log_viewer)
        return discord_layout

    # -------------------------------
    # Logging / Output Methods
    # -------------------------------
    def append_output_handler(self, message: str) -> None:
        logger.info(message)
        self.log_viewer.append(message)

    def append_output(self, message: str) -> None:
        self.append_output_signal.emit(str(message))

    # -------------------------------
    # UI Control Methods
    # -------------------------------
    def toggle_chat_mode(self) -> None:
        if self.chat_mode_label.text() == "Current Mode: Chat History":
            self.chat_mode_label.setText("Current Mode: New Chat")
            self.mode_toggle_btn.setText("Switch to Chat History Mode")
        else:
            self.chat_mode_label.setText("Current Mode: Chat History")
            self.mode_toggle_btn.setText("Switch to New Chat Mode")

    def update_execution_mode(self, mode_text: str) -> None:
        if mode_text == "Prompt Cycle Mode":
            self.prompt_stack.setCurrentIndex(1)
            self.execute_prompt_btn.setText("Start Prompt Cycle")
        else:
            self.prompt_stack.setCurrentIndex(0)
            self.execute_prompt_btn.setText("Execute Prompt")

    # -------------------------------
    # Execution Logic Methods (Integrated with Chat Threading)
    # -------------------------------
    def execute_prompt(self) -> None:
        # Restart ChatManager for a fresh session
        if self.chat_manager:
            self.chat_manager.shutdown_driver()
            self.chat_manager = None

        headless = self.headless_checkbox.isChecked()
        self.chat_manager = ChatManager(
            driver_manager=None,
            excluded_chats=get_excluded_chats(self.exclusion_list),
            model=self.model_selector.currentText(),
            timeout=180,
            stable_period=10,
            poll_interval=5,
            headless=headless
        )
        self.chat_manager.headless = headless

        mode = self.execution_mode_combo.currentText()
        if mode == "Prompt Cycle Mode":
            selected_items = self.prompt_cycle_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "No Prompts Selected", "Please select one or more prompt types for the cycle.")
                return
            selected_prompts = [item.text() for item in selected_items]
            self.start_prompt_cycle(selected_prompts)
        else:
            # In New Chat mode, each prompt execution creates a new conversation thread.
            if self.chat_mode_label.text() == "Current Mode: New Chat":
                self.run_single_chat_mode(new_chat=True)
            else:
                self.run_multi_chat_mode()

    def run_single_chat_mode(self, new_chat: bool = False) -> None:
        prompt_text = self.prompt_editor.toPlainText().strip()
        if not prompt_text:
            self.append_output("No prompt text provided. Aborting single-chat execution.")
            return
        self.append_output("Launching single-chat execution...")
        def single_chat_thread() -> None:
            # If new_chat is True, initialize a new chat thread with a unique ID.
            interaction_id = None
            if new_chat:
                interaction_id = "chat_" + datetime.now().strftime("%Y%m%d%H%M%S")
                self.append_output(f"Initializing new chat thread with ID: {interaction_id}")
            responses = self.chat_manager.execute_prompts_single_chat([prompt_text], cycle_speed=2, interaction_id=interaction_id)
            for i, resp in enumerate(responses, start=1):
                self.append_output(f"Prompt #{i} => {resp}")
            self.append_output("Single-chat execution complete.")
        threading.Thread(target=single_chat_thread, daemon=True).start()

    def run_multi_chat_mode(self) -> None:
        raw_prompt_text = self.prompt_editor.toPlainText().strip()
        if not raw_prompt_text:
            self.append_output("No prompt text provided. Aborting multi-chat execution.")
            return
        prompts = [line.strip() for line in raw_prompt_text.splitlines() if line.strip()]
        if not prompts:
            self.append_output("No valid prompts extracted from the editor.")
            return
        self.append_output("Launching multi-chat sequential execution...")
        def multi_chat_thread() -> None:
            all_chats = self.chat_manager.get_all_chat_titles()
            if self.reverse_checkbox.isChecked():
                all_chats.reverse()
            if not all_chats:
                self.append_output("No chats found. Aborting multi-chat execution.")
                return
            for chat in all_chats:
                chat_title = chat.get("title", "Untitled")
                self.append_output(f"\n--- Processing Chat: {chat_title} ---")
                for idx, prompt in enumerate(prompts, start=1):
                    self.append_output(f"Sending Prompt #{idx} to {chat_title}: {prompt}")
                    response = self.chat_manager.execute_prompt_cycle(prompt)
                    self.append_output(f"Response for Prompt #{idx} in {chat_title}: {response}")
                if self.archive_checkbox.isChecked():
                    self.append_output(f"Archiving chat: {chat_title}")
                    self.chat_manager.archive_chat(chat)
            self.append_output("Multi-chat sequential execution complete.")
        threading.Thread(target=multi_chat_thread, daemon=True).start()

    def start_prompt_cycle(self, selected_prompt_names: list) -> None:
        all_chats = self.chat_manager.get_all_chat_titles()
        if not all_chats:
            self.append_output("❗ No chats in queue. Aborting prompt cycle.")
            return
        filtered_chats = [chat for chat in all_chats if chat["title"] not in get_excluded_chats(self.exclusion_list)]
        if self.reverse_checkbox.isChecked():
            filtered_chats.reverse()
            self.append_output("🔄 Processing chats in reverse order.")
        self.append_output(f"✅ {len(filtered_chats)} chats ready for processing.")
        for chat in filtered_chats:
            chat_title = chat.get("title", "Unknown Chat")
            chat_link = chat.get("link")
            self.append_output(f"\n--- Processing Chat: {chat_title} ---")
            if not chat_link:
                self.append_output(f"⚠️ Skipping chat '{chat_title}' due to missing link.")
                continue
            self.chat_manager.driver.get(chat_link)
            time.sleep(3)
            chat_responses = []
            cycle_start_time = time.time()
            for prompt_name in selected_prompt_names:
                prompt_text = self.prompt_manager.get_prompt(prompt_name)
                if not prompt_text:
                    self.append_output(f"⚠️ Empty prompt for '{prompt_name}'. Skipping.")
                    continue
                self.append_output(f"📝 Sending prompt '{prompt_name}' to chat '{chat_title}'")
                if not self.chat_manager.prompt_engine.send_prompt(prompt_text):
                    self.append_output(f"❌ Failed to send prompt '{prompt_name}' in chat '{chat_title}'")
                    continue
                response = self.chat_manager.prompt_engine.wait_for_stable_response()
                if not response:
                    self.append_output(f"⚠️ No stable response for '{prompt_name}' in chat '{chat_title}'")
                    continue
                if prompt_name.lower() == "dreamscape":
                    chat_filename = f"episode_{self.prompt_manager.prompts['dreamscape'].get('episode_counter', 1) - 1}_{sanitize(chat_title)}.txt"
                    if self.discord_manager:
                        self.discord_manager.send_message("dreamscape", f"🛡️ New Dreamscape Episode from '{chat_title}':\n{response}")
                        self.append_output(f"📤 Posted new Dreamscape episode to Discord for '{chat_title}'")
                else:
                    chat_filename = f"{sanitize(chat_title)}.txt"
                prompt_dir = os.path.join("responses", sanitize(chat_title), sanitize(prompt_name))
                os.makedirs(prompt_dir, exist_ok=True)
                chat_file_path = os.path.join(prompt_dir, chat_filename)
                try:
                    with open(chat_file_path, 'w', encoding='utf-8') as f:
                        f.write(response)
                    self.append_output(f"✅ Saved response for chat '{chat_title}' to {chat_file_path}")
                except Exception as e:
                    self.append_output(f"❌ Error saving response for '{chat_title}': {e}")
                chat_responses.append({
                    "prompt_name": prompt_name,
                    "prompt_text": prompt_text,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "ai_observations": self.chat_manager.analyze_execution_response(response, prompt_text)
                })
                time.sleep(1)
            cycle_end_time = time.time()
            run_metadata = {
                "timestamp": datetime.now().isoformat(),
                "model": self.chat_manager.model,
                "chat_count": 1,
                "execution_time": f"{round(cycle_end_time - cycle_start_time, 2)}s",
                "bottlenecks": []
            }
            output_dir = os.path.join("responses", sanitize(chat_title))
            generate_full_run_json(chat_title, chat_link, chat_responses, run_metadata, output_dir)
            self.append_output(f"✅ Saved full_run.json for chat '{chat_title}'.")
            if self.archive_checkbox.isChecked():
                self.append_output(f"📦 Archiving chat '{chat_title}'...")
                self.chat_manager.archive_chat(chat)
        self.append_output("✅ Completed full prompt cycle across all chats.")

    def run_single_chat_mode(self) -> None:
        prompt_text = self.prompt_editor.toPlainText().strip()
        if not prompt_text:
            self.append_output("No prompt text provided. Aborting single-chat execution.")
            return
        self.append_output("Launching single-chat execution...")
        def single_chat_thread() -> None:
            responses = self.chat_manager.execute_prompts_single_chat([prompt_text], cycle_speed=2)
            for i, resp in enumerate(responses, start=1):
                self.append_output(f"Prompt #{i} => {resp}")
            self.append_output("Single-chat execution complete.")
        threading.Thread(target=single_chat_thread, daemon=True).start()

    def run_multi_chat_mode(self) -> None:
        raw_prompt_text = self.prompt_editor.toPlainText().strip()
        if not raw_prompt_text:
            self.append_output("No prompt text provided. Aborting multi-chat execution.")
            return
        prompts = [line.strip() for line in raw_prompt_text.splitlines() if line.strip()]
        if not prompts:
            self.append_output("No valid prompts extracted from the editor.")
            return
        self.append_output("Launching multi-chat sequential execution...")
        def multi_chat_thread() -> None:
            all_chats = self.chat_manager.get_all_chat_titles()
            if self.reverse_checkbox.isChecked():
                all_chats.reverse()
            if not all_chats:
                self.append_output("No chats found. Aborting multi-chat execution.")
                return
            for chat in all_chats:
                chat_title = chat.get("title", "Untitled")
                self.append_output(f"\n--- Processing Chat: {chat_title} ---")
                for idx, prompt in enumerate(prompts, start=1):
                    self.append_output(f"Sending Prompt #{idx} to {chat_title}: {prompt}")
                    response = self.chat_manager.execute_prompt_cycle(prompt)
                    self.append_output(f"Response for Prompt #{idx} in {chat_title}: {response}")
                if self.archive_checkbox.isChecked():
                    self.append_output(f"Archiving chat: {chat_title}")
                    self.chat_manager.archive_chat(chat)
            self.append_output("Multi-chat sequential execution complete.")
        threading.Thread(target=multi_chat_thread, daemon=True).start()

    # -------------------------------
    # Additional Features: Scraping & Prompt Saving
    # -------------------------------
    def start_scraping(self, keep_driver_open: bool = False) -> None:
        self.append_output("Initializing scraping session...")
        exclusions = get_excluded_chats(self.exclusion_list)
        self.excluded_chats = exclusions
        if self.chat_manager and self.chat_manager.is_logged_in():
            self.append_output("Login detected. Proceeding with scraping.")
        else:
            self.append_output("Not logged in. Manual login required...")
            self.chat_manager.driver.get("https://chat.openai.com/auth/login")
            input(">> Press ENTER after logging in... <<")
            if self.chat_manager.is_logged_in():
                self.append_output("Manual login successful.")
            else:
                self.append_output("Login unsuccessful. Exiting scraping session.")
                self.chat_manager.shutdown_driver()
                return
        self.append_output("Starting chat scraping process...")
        all_chats = self.chat_manager.get_all_chat_titles()
        self.append_output(f"Found {len(all_chats)} chats to process.")
        if self.reverse_checkbox.isChecked():
            all_chats.reverse()
            self.append_output("Processing chats in reverse order.")
        for chat in all_chats:
            self.append_output(f"Scrape found chat: {chat['title']} => {chat['link']}")
        self.append_output("Scraping session complete!")
        if not keep_driver_open:
            self.chat_manager.shutdown_driver()

    def load_selected_prompt(self, prompt_type: str) -> None:
        try:
            prompt_text = self.prompt_manager.get_prompt(prompt_type)
            model = self.prompt_manager.get_model(prompt_type)
            self.append_output(f"Loaded prompt '{prompt_type}' with model '{model}'.")
        except Exception as e:
            QMessageBox.warning(self, "Prompt Error", str(e))

    def save_prompt(self) -> None:
        self.append_output("Prompt saved (GUI placeholder).")

    def reset_prompts(self) -> None:
        self.prompt_manager.reset_to_defaults()
        self.append_output("Prompts have been reset to defaults.")

    def add_exclusion(self) -> None:
        chat_title, ok = QInputDialog.getText(self, "Add Exclusion", "Enter chat title to exclude:")
        if ok and chat_title.strip():
            self.exclusion_list.addItem(QListWidgetItem(chat_title.strip()))
            self.append_output(f"Added exclusion: {chat_title.strip()}")

    def remove_exclusion(self) -> None:
        selected_items = self.exclusion_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.exclusion_list.takeItem(self.exclusion_list.row(item))
            self.append_output(f"Removed exclusion: {item.text()}")

    def browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", os.getcwd())
        if directory:
            self.output_dir.setText(directory)
            self.append_output(f"Output directory set to {directory}")

    # -------------------------------
    # Unified Dreamscape Generator Integration
    # -------------------------------
    def generate_dreamscape_episodes_ui(self) -> None:
        self.append_output("🚀 Starting Dreamscape episode generation cycle...")
        response_handler = ResponseHandler(timeout=180, stable_period=10)
        headless = self.headless_checkbox.isChecked() if hasattr(self, "headless_checkbox") else False
        self.chat_manager = ChatManager(
            driver_manager=None,
            excluded_chats=get_excluded_chats(self.exclusion_list),
            model=self.model_selector.currentText(),
            timeout=180,
            stable_period=10,
            poll_interval=5,
            headless=headless
        )
        self.chat_manager.headless = headless
        output_dir = self.output_dir.text() if self.output_dir.text() else os.getcwd()
        # Initialize the Dreamscape generator with the new OpenAIPromptEngine that supports chat threading.
        generator = DreamscapeEpisodeGenerator(
            chat_manager=self.chat_manager,
            response_handler=response_handler,
            output_dir=output_dir,
            prompt_engine=OpenAIPromptEngine(),  # Uses our updated OpenAIPromptEngine with chat thread support.
            discord_manager=self.discord_manager,
            ollama_model="mistral"
        )
        generator.generate_dreamscape_episodes()
        self.append_output("✅ Dreamscape episodes generated.")

    # -------------------------------
    # Discord Bot Management
    # -------------------------------
    def launch_discord_bot(self, bot_token: str, channel_id: int) -> None:
        if self.discord_manager and self.discord_manager.is_running:
            self.append_output("⚠️ Discord bot is already running.")
            return
        self.append_output("🚀 Launching Discord bot...")
        self.discord_manager = DiscordManager(bot_token=bot_token, channel_id=channel_id)
        self.discord_manager.set_log_callback(self.append_discord_log)
        def run_bot():
            self.discord_manager.run_bot()
        self.discord_thread = threading.Thread(target=run_bot, daemon=True)
        self.discord_thread.start()
        self.update_discord_status(connected=True)
        self.append_output("✅ Discord bot launched in the background.")

    def launch_discord_bot_from_gui(self):
        bot_token = self.discord_token_input.text().strip()
        channel_id_text = self.discord_channel_input.text().strip()
        if not bot_token or not channel_id_text:
            self.append_output("🔍 Discord inputs are empty. Loading stored config...")
            self.discord_manager = DiscordManager()
            bot_token = self.discord_manager.bot_token
            channel_id_text = str(self.discord_manager.default_channel_id)
            self.discord_token_input.setText(bot_token)
            self.discord_channel_input.setText(channel_id_text)
        if not bot_token or not channel_id_text.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Please ensure a valid Discord Bot Token and numeric Channel ID exist.")
            return
        self.launch_discord_bot(bot_token, int(channel_id_text))
        QMessageBox.information(self, "Discord Bot Launched", "✅ Discord bot launched successfully in the background!")

    def stop_discord_bot_from_gui(self):
        if not self.discord_manager or not self.discord_manager.is_running:
            self.append_discord_log("⚠️ Discord bot is not running.")
            return
        self.discord_manager.stop_bot()
        self.update_discord_status(connected=False)
        self.append_discord_log("🛑 Discord bot stopped.")
        QMessageBox.information(self, "Discord Bot Stopped", "🛑 Discord bot stopped successfully.")

    def open_discord_settings(self) -> None:
        from core.DiscordManager import DiscordSettingsDialog
        if not self.discord_manager or not self.discord_manager.is_running:
            QMessageBox.warning(self, "Discord Bot Not Running", "Please launch the Discord bot before accessing settings.")
            return
        dialog = DiscordSettingsDialog(parent=self, discord_manager=self.discord_manager)
        dialog.exec_()

    def update_discord_status(self, connected: bool):
        self.discord_status_label.setText("Status: 🟢 Connected" if connected else "Status: 🔴 Disconnected")

    def append_discord_log(self, message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.discord_log_viewer.append(f"[{timestamp}] {message}")

    # -------------------------------
    # Reinforcement Tools Integration
    # -------------------------------
    def open_reinforcement_tools(self) -> None:
        dialog = ReinforcementToolsDialog(parent=self)
        dialog.exec_()

    def run_prompt_tuning(self) -> None:
        if not hasattr(self, "reinforcement_engine"):
            self.reinforcement_engine = ReinforcementEngine()
        self.append_output("🔍 Analyzing prompt feedback for tuning...")
        self.reinforcement_engine.auto_tune_prompts(self.prompt_manager)
        self.append_output("✅ Prompts auto-tuned via reinforcement feedback.")
        self.append_output(f"📝 Memory updated on {self.reinforcement_engine.memory_data.get('last_updated')}")

    def launch_dashboard(self) -> None:
        if not hasattr(self, "reinforcement_engine"):
            self.reinforcement_engine = ReinforcementEngine()
        feedback_data = self.reinforcement_engine.memory_data.get("reinforcement_feedback", {})
        execution_logs = self.reinforcement_engine.memory_data.get("execution_logs", [])
        self.append_output("📊 Reinforcement Learning Dashboard Summary:")
        self.append_output(f"  - Total Prompts Tracked: {len(feedback_data)}")
        self.append_output(f"  - Last Updated: {self.reinforcement_engine.memory_data.get('last_updated')}")
        if not execution_logs:
            self.append_output("  - No execution logs found.")
            return
        for log in execution_logs[-5:]:
            prompt = log.get("prompt_name", "N/A")
            score = log.get("score", "N/A")
            hallucination = log.get("hallucination", False)
            timestamp = log.get("timestamp", "N/A")
            self.append_output(f"    → Prompt: {prompt} | Score: {score} | Hallucination: {'❗ Yes' if hallucination else '✅ No'} | Time: {timestamp}")

    def show_log_analysis(self) -> None:
        if not hasattr(self, "reinforcement_engine"):
            self.reinforcement_engine = ReinforcementEngine()
        execution_logs = self.reinforcement_engine.memory_data.get("execution_logs", [])
        if not execution_logs:
            self.append_output("⚠️ No logs available for analysis.")
            return
        hallucination_count = sum(1 for log in execution_logs if log.get("hallucination"))
        total_logs = len(execution_logs)
        hallucination_rate = (hallucination_count / total_logs) * 100 if total_logs > 0 else 0
        avg_score = (sum(log.get("score", 0) for log in execution_logs) / total_logs) if total_logs > 0 else 0
        self.append_output("📈 AI Output Log Analysis:")
        self.append_output(f"  - Total Executions Logged: {total_logs}")
        self.append_output(f"  - Hallucination Rate: {hallucination_rate:.2f}%")
        self.append_output(f"  - Average Prompt Score: {avg_score:.2f}")
        low_score_prompts = [log for log in execution_logs if log.get("score", 1) < 0.5]
        if low_score_prompts:
            self.append_output(f"⚠️ {len(low_score_prompts)} prompts scored consistently below 0.5:")
            for log in low_score_prompts[-3:]:
                self.append_output(f"    → {log['prompt_name']} | Score: {log['score']} | Time: {log['timestamp']}")
        else:
            self.append_output("✅ No prompts below performance threshold.")

    # -------------------------------
    # Main Entry Point: Launch the GUI
    # -------------------------------
    def run_bot(self):
        # Placeholder for bot logic or other final steps.
        pass

# ---------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DreamscapeGUI()
    window.show()
    sys.exit(app.exec_())

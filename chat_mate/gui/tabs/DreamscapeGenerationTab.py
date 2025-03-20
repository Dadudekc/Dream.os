from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog
)
import threading
import os

# Core Managers
from core.PromptCycleManager import PromptCycleManager, PromptCycleDialog
from core.UnifiedDreamscapeGenerator import DreamscapeEpisodeGenerator


class DreamscapeGenerationTab(QWidget):
    """
    Dreamscape Generation Tab that integrates both:
    1. PromptCycleManager for Single/Multi Chat Cycles
    2. UnifiedDreamscapeGenerator for advanced Dreamscape episode creation
    """

    def __init__(self, prompt_manager, chat_manager, response_handler, memory_manager=None, discord_manager=None):
        super().__init__()

        # Managers
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.response_handler = response_handler
        self.memory_manager = memory_manager
        self.discord_manager = discord_manager

        # PromptCycleManager Initialization
        self.prompt_cycle_manager = PromptCycleManager(
            prompt_manager=self.prompt_manager,
            memory_manager=self.memory_manager,
            discord_manager=self.discord_manager,
            append_output=self.log_output
        )

        # UnifiedDreamscapeGenerator Initialization
        self.output_dir = "exports"
        self.unified_generator = DreamscapeEpisodeGenerator(
            chat_manager=self.chat_manager,
            response_handler=self.response_handler,
            output_dir=self.output_dir,
            discord_manager=self.discord_manager
        )

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Section Title
        layout.addWidget(QLabel("Dreamscape Prompt Cycle & Episode Generator"))

        # BUTTON ROWS ----------------------------------------------------------------

        btn_layout = QHBoxLayout()

        # SINGLE-CHAT CYCLE BUTTON
        self.single_chat_btn = QPushButton("Run Single-Chat Cycle")
        self.single_chat_btn.clicked.connect(self.run_single_chat_cycle_dialog)
        btn_layout.addWidget(self.single_chat_btn)

        # MULTI-CHAT CYCLE BUTTON
        self.multi_chat_btn = QPushButton("Run Multi-Chat Cycle")
        self.multi_chat_btn.clicked.connect(self.run_multi_chat_cycle_dialog)
        btn_layout.addWidget(self.multi_chat_btn)

        layout.addLayout(btn_layout)

        btn_layout_2 = QHBoxLayout()

        # PROMPT CYCLE: DREAMSCAPE EPISODES BUTTON (uses PromptCycleManager)
        self.generate_cycle_episodes_btn = QPushButton("Generate Dreamscape Episodes (Cycle Manager)")
        self.generate_cycle_episodes_btn.clicked.connect(self.generate_dreamscape_episodes_via_cycle_manager)
        btn_layout_2.addWidget(self.generate_cycle_episodes_btn)

        # UNIFIED GENERATOR EPISODES BUTTON (uses DreamscapeEpisodeGenerator)
        self.generate_unified_episodes_btn = QPushButton("Generate Unified Dreamscape Episodes (GPT + Ollama)")
        self.generate_unified_episodes_btn.clicked.connect(self.generate_unified_dreamscape_episodes)
        btn_layout_2.addWidget(self.generate_unified_episodes_btn)

        layout.addLayout(btn_layout_2)

        # LOG DISPLAY ----------------------------------------------------------------
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_display)

        self.setLayout(layout)

    # -------------------------------------------------------------------------
    # Single / Multi Prompt Cycle Dialogs
    # -------------------------------------------------------------------------

    def run_single_chat_cycle_dialog(self):
        dlg = PromptCycleDialog(
            prompt_manager=self.prompt_manager,
            start_cycle_callback=self.run_single_chat_cycle
        )
        dlg.exec_()

    def run_multi_chat_cycle_dialog(self):
        dlg = PromptCycleDialog(
            prompt_manager=self.prompt_manager,
            start_cycle_callback=self.run_multi_chat_cycle
        )
        dlg.exec_()

    # -------------------------------------------------------------------------
    # Prompt Cycle Manager Actions
    # -------------------------------------------------------------------------

    def run_single_chat_cycle(self, selected_prompts):
        self.log_output(f"Starting Single-Chat Cycle for prompts: {selected_prompts}")
        self.prompt_cycle_manager.run_cycle(
            prompts=selected_prompts,
            files_to_send=None,
            paste_files=False,
            upload_files=False,
            cycle_speed=5
        )

    def run_multi_chat_cycle(self, selected_prompts):
        self.log_output(f"Starting Multi-Chat Cycle for prompts: {selected_prompts}")
        self.prompt_cycle_manager.run_cycle_on_all_chats(
            prompts=selected_prompts,
            cycle_speed=5
        )

    def generate_dreamscape_episodes_via_cycle_manager(self):
        """
        Trigger Dreamscape episode generation via PromptCycleManager (multi-prompt).
        """
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", os.getcwd())
        if not output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select a valid directory to save episodes.")
            return

        self.log_output(f"Generating Dreamscape Episodes (PromptCycleManager) in {output_dir}...")

        def thread_func():
            self.prompt_cycle_manager.generate_dreamscape_episodes(output_dir=output_dir, cycle_speed=2)
            self.log_output("✅ Dreamscape Episode Generation Complete! (Cycle Manager)")

        threading.Thread(target=thread_func, daemon=True).start()

    # -------------------------------------------------------------------------
    # Unified Dreamscape Generator Actions (GPT + Ollama)
    # -------------------------------------------------------------------------

    def generate_unified_dreamscape_episodes(self):
        """
        Trigger UnifiedDreamscapeGenerator (OpenAI GPT + Ollama).
        """
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", os.getcwd())
        if not output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select a valid directory to save episodes.")
            return

        self.log_output(f"Generating Dreamscape Episodes (Unified Generator) in {output_dir}...")

        def thread_func():
            self.unified_generator.output_dir = output_dir
            self.unified_generator.generate_dreamscape_episodes()
            self.log_output("✅ Unified Dreamscape Episode Generation Complete! (GPT + Ollama)")

        threading.Thread(target=thread_func, daemon=True).start()

    # -------------------------------------------------------------------------
    # Logging Output
    # -------------------------------------------------------------------------

    def log_output(self, message: str):
        """
        Append messages to the output display and print to console.
        """
        self.output_display.append(message)
        print(message)

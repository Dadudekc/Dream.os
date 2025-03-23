from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog
)
import threading
import os
import logging

# Core Services
from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator
from core.UnifiedDreamscapeGenerator import DreamscapeEpisodeGenerator


class DreamscapeGenerationTab(QWidget):
    """
    Dreamscape Generation Tab that integrates both:
    1. CycleExecutionService for Single/Multi Chat Cycles
    2. UnifiedDreamscapeGenerator for advanced Dreamscape episode creation
    """

    def __init__(self, prompt_manager=None, chat_manager=None, response_handler=None, 
                 memory_manager=None, discord_manager=None, ui_logic=None, 
                 config_manager=None, logger=None):
        """
        Initialize the DreamscapeGenerationTab.
        
        Supports two initialization styles:
        1. Service-based: Directly pass service instances (prompt_manager, chat_manager, etc.)
        2. UI logic-based: Pass ui_logic, config_manager and logger
        
        Args:
            prompt_manager: Service for managing prompts
            chat_manager: Service for chat interactions
            response_handler: Service for handling prompt responses
            memory_manager: Service for memory management
            discord_manager: Service for Discord integration
            ui_logic: UI logic controller (alternative initialization)
            config_manager: Configuration manager (alternative initialization)
            logger: Logger instance (alternative initialization)
        """
        super().__init__()

        # Store references based on initialization style
        self.ui_logic = ui_logic
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # If UI logic is provided, try to get services from it
        if ui_logic and hasattr(ui_logic, 'get_service'):
            self.prompt_manager = ui_logic.get_service('prompt_manager') or prompt_manager
            self.chat_manager = ui_logic.get_service('chat_manager') or chat_manager
            self.response_handler = ui_logic.get_service('response_handler') or response_handler
            self.memory_manager = ui_logic.get_service('memory_manager') or memory_manager
            self.discord_manager = ui_logic.get_service('discord_service') or discord_manager
        else:
            # Direct service initialization
            self.prompt_manager = prompt_manager
            self.chat_manager = chat_manager
            self.response_handler = response_handler
            self.memory_manager = memory_manager
            self.discord_manager = discord_manager

        # Initialize new services
        self.cycle_service = CycleExecutionService(
            prompt_manager=self.prompt_manager,
            chat_manager=self.chat_manager,
            response_handler=self.response_handler,
            memory_manager=self.memory_manager,
            discord_manager=self.discord_manager
        )
        self.prompt_handler = PromptResponseHandler()
        self.discord_processor = DiscordQueueProcessor()
        self.task_orchestrator = TaskOrchestrator()

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Section Title
        layout.addWidget(QLabel("Dreamscape Episode Generator"))

        # BUTTON ROWS ----------------------------------------------------------------
        btn_layout = QHBoxLayout()

        # GENERATE DREAMSCAPE EPISODES BUTTON
        self.generate_episodes_btn = QPushButton("Generate Dreamscape Episodes")
        self.generate_episodes_btn.clicked.connect(self.generate_dreamscape_episodes)
        btn_layout.addWidget(self.generate_episodes_btn)

        layout.addLayout(btn_layout)

        # LOG DISPLAY ----------------------------------------------------------------
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_display)

        self.setLayout(layout)

    def log_output(self, message: str):
        """
        Append messages to the output display and print to console.
        """
        self.output_display.append(message)
        if self.logger:
            self.logger.info(message)
        else:
            print(message)

    def generate_dreamscape_episodes(self):
        """
        Generate Dreamscape episodes using the chat manager.
        """
        if not self.chat_manager:
            self.log_output("Error: Chat manager not initialized")
            return

        if not self.prompt_manager:
            self.log_output("Error: Prompt manager not initialized")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", os.getcwd())
        if not output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select a valid directory to save episodes.")
            return

        self.log_output(f"Starting Dreamscape episode generation in {output_dir}...")

        def thread_func():
            try:
                self.chat_manager.generate_dreamscape_episodes(output_dir=output_dir, cycle_speed=2)
                self.log_output("✅ Dreamscape Episode Generation Complete!")
            except Exception as e:
                self.log_output(f"Error generating episodes: {str(e)}")

        threading.Thread(target=thread_func, daemon=True).start()

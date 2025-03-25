from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog
)
import os
import logging
import asyncio
from qasync import asyncSlot

# Core Services
from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator
from core.UnifiedDreamscapeGenerator import DreamscapeEpisodeGenerator


class DreamscapeGenerationTab(QWidget):
    """
    Dreamscape Generation Tab integrates:
    1. CycleExecutionService for Single/Multi Chat Cycles.
    2. UnifiedDreamscapeGenerator for advanced Dreamscape episode creation.
    """

    def __init__(self, dispatcher=None, prompt_manager=None, chat_manager=None, response_handler=None, 
                 memory_manager=None, discord_manager=None, ui_logic=None, 
                 config_manager=None, logger=None):
        """
        Initialize the DreamscapeGenerationTab.
        Supports:
        - Direct service injection.
        - UI logic service delegation.
        """
        super().__init__()

        # Service References
        self.dispatcher = dispatcher
        self.ui_logic = ui_logic
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)

        # Inject Services
        self._inject_services(prompt_manager, chat_manager, response_handler, memory_manager, discord_manager)

        # Initialize Core Engines
        self._initialize_services()

        # Initialize UI
        self.init_ui()
        
        # Track current running tasks
        self.running_tasks = {}

    def _inject_services(self, prompt_manager, chat_manager, response_handler, memory_manager, discord_manager):
        """Inject services directly or fetch from ui_logic controller."""
        if self.ui_logic and hasattr(self.ui_logic, 'get_service'):
            self.prompt_manager = self.ui_logic.get_service('prompt_manager') or prompt_manager
            self.chat_manager = self.ui_logic.get_service('chat_manager') or chat_manager
            self.response_handler = self.ui_logic.get_service('response_handler') or response_handler
            self.memory_manager = self.ui_logic.get_service('memory_manager') or memory_manager
            self.discord_manager = self.ui_logic.get_service('discord_service') or discord_manager
        else:
            self.prompt_manager = prompt_manager
            self.chat_manager = chat_manager
            self.response_handler = response_handler
            self.memory_manager = memory_manager
            self.discord_manager = discord_manager

    def _initialize_services(self):
        """Initialize processing engines with the provided services."""
        self.cycle_service = CycleExecutionService(
            prompt_manager=self.prompt_manager,
            chat_manager=self.chat_manager,
            response_handler=self.response_handler,
            memory_manager=self.memory_manager,
            discord_manager=self.discord_manager,
            config_manager=self.config_manager,  
            logger=self.logger 
        )

        self.prompt_handler = PromptResponseHandler(
            config_manager=self.config_manager,
            logger=self.logger
        )
        self.discord_processor = DiscordQueueProcessor(
            config_manager=self.config_manager,
            logger=self.logger
        )
        self.task_orchestrator = TaskOrchestrator(
            logger=self.logger
        )


    def init_ui(self):
        """Set up the layout and buttons for the Dreamscape tab."""
        layout = QVBoxLayout()

        # Title
        layout.addWidget(QLabel("Dreamscape Episode Generator"))

        # Buttons
        button_row = QHBoxLayout()

        self.generate_episodes_btn = QPushButton("Generate Dreamscape Episodes")
        self.generate_episodes_btn.clicked.connect(self.generate_dreamscape_episodes)

        button_row.addWidget(self.generate_episodes_btn)
        layout.addLayout(button_row)

        # Output Log
        layout.addWidget(QLabel("Output Log:"))
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)

        self.setLayout(layout)

    def log_output(self, message: str):
        """Log messages to the UI and console/log file."""
        self.output_display.append(message)
        if self.logger:
            self.logger.info(message)
        else:
            print(message)
            
        # Use dispatcher to broadcast message if available
        if self.dispatcher:
            self.dispatcher.emit_log_output(message)
            
    def handle_prompt_executed(self, prompt_name, response_data):
        """Handle prompt_executed signal from the dispatcher."""
        self.log_output(f"Prompt '{prompt_name}' executed with response.")
        
    def handle_discord_event(self, event_type, event_data):
        """Handle discord_event signal from the dispatcher."""
        self.log_output(f"Discord event '{event_type}' received.")

    @asyncSlot()
    async def generate_dreamscape_episodes(self):
        """Trigger Dreamscape episode generation with validation and async handling."""

        # Validate Dependencies
        if not self.chat_manager:
            self.log_output("❌ Error: Chat manager not initialized.")
            return
        if not self.prompt_manager:
            self.log_output("❌ Error: Prompt manager not initialized.")
            return

        # Select Output Directory
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", os.getcwd())
        if not output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select a valid directory to save episodes.")
            return

        self.log_output(f"🚀 Starting Dreamscape episode generation in: {output_dir}")
        
        # Generate a unique task ID
        task_id = f"dreamscape_gen_{id(output_dir)}"
        
        # Notify via dispatcher that task is starting
        if self.dispatcher:
            self.dispatcher.emit_task_started(task_id)
        
        # Create and track the task
        task = asyncio.create_task(self._generate_episodes_async(task_id, output_dir))
        self.running_tasks[task_id] = task
        
        # Add done callback to clean up and handle errors
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))

    async def _generate_episodes_async(self, task_id, output_dir):
        """Async function for episode generation that reports progress."""
        try:
            # Simulate progress updates (in a real implementation, this would come from the actual generation process)
            total_episodes = 5  # Example - would be determined by your actual generation logic
            
            for i in range(total_episodes):
                # Perform part of the work
                await asyncio.sleep(1)  # Simulate work
                
                # Calculate progress percentage
                progress = int((i + 1) / total_episodes * 100)
                
                # Report progress
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(
                        task_id, 
                        progress, 
                        f"Generating episode {i+1}/{total_episodes}"
                    )
                
                self.log_output(f"✅ Generated episode {i+1}/{total_episodes}")
            
            # In a real implementation, this would call your actual episode generation method
            # result = await asyncio.to_thread(
            #     self.chat_manager.generate_dreamscape_episodes,
            #     output_dir=output_dir,
            #     cycle_speed=2
            # )
            
            # For now, return a mock result
            return {
                "episodes_created": total_episodes,
                "output_directory": output_dir,
                "success": True
            }
            
        except Exception as e:
            self.log_output(f"❌ Error generating episodes: {str(e)}")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, str(e))
            raise e
            
    def _on_task_done(self, task_id, task):
        """Handle task completion or failure."""
        # Remove task from tracking
        self.running_tasks.pop(task_id, None)
        
        try:
            # Get the result (will raise exception if the task failed)
            result = task.result()
            
            # Log success
            self.log_output(f"✅ Task {task_id} completed successfully!")
            
            # Emit completion signal
            if self.dispatcher:
                self.dispatcher.emit_task_completed(task_id, result)
                
                # If this was a dreamscape generation, also emit that special signal
                if task_id.startswith("dreamscape_gen_"):
                    self.dispatcher.emit_dreamscape_generated(result)
                    
        except asyncio.CancelledError:
            self.log_output(f"❌ Task {task_id} was cancelled.")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, "Task was cancelled.")
                
        except Exception as e:
            self.log_output(f"❌ Task {task_id} failed with error: {str(e)}")
            # Task failure will already have been emitted in the task itself


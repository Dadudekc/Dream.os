from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox
import logging
from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator

class PromptExecutionTab(QWidget):
    """
    Tab for executing prompts through various services.
    Provides a unified interface for prompt selection, editing, and execution.
    """
    
    def __init__(
        self,
        prompt_manager=None, 
        config_manager=None, 
        logger=None, 
        chat_manager=None, 
        memory_manager=None, 
        discord_manager=None,
        ui_logic=None,
        **kwargs
    ):
        """
        Initialize the PromptExecutionTab with required dependencies.
        
        Supports two initialization styles:
        1. Service-based: Directly pass service instances
        2. UI logic-based: Pass ui_logic which can access services
        
        Args:
            prompt_manager: An instance providing prompt-related methods.
            config_manager: Configuration manager instance.
            logger: A logger instance for logging messages.
            chat_manager: A chat manager instance.
            memory_manager: A memory manager instance.
            discord_manager: A discord manager instance.
            ui_logic: UI logic controller (alternative initialization).
            **kwargs: Additional dependencies.
        """
        super().__init__()
        
        # Store references based on initialization style
        self.ui_logic = ui_logic
        self.logger = logger or logging.getLogger(__name__)
        
        # If UI logic is provided, try to get services from it
        if ui_logic and hasattr(ui_logic, 'get_service'):
            self.prompt_manager = ui_logic.get_service('prompt_manager') or prompt_manager
            self.config_manager = config_manager  # Config manager typically isn't a service
            self.chat_manager = ui_logic.get_service('chat_manager') or chat_manager
            self.memory_manager = ui_logic.get_service('memory_manager') or memory_manager
            self.discord_manager = ui_logic.get_service('discord_service') or discord_manager
        else:
            # Direct service initialization
            self.prompt_manager = prompt_manager
            self.config_manager = config_manager
            self.chat_manager = chat_manager
            self.memory_manager = memory_manager
            self.discord_manager = discord_manager

        # Initialize services with dependency injection
        self.cycle_service = CycleExecutionService(
            prompt_manager=self.prompt_manager,
            config_manager=self.config_manager,
            logger=self.logger,
            chat_manager=self.chat_manager,
            memory_manager=self.memory_manager,
            discord_manager=self.discord_manager
        )
        self.prompt_handler = PromptResponseHandler(self.config_manager, self.logger)
        self.discord_processor = DiscordQueueProcessor()
        self.task_orchestrator = TaskOrchestrator()

        self.initUI()

    def initUI(self):
        """Initialize the user interface components."""
        # Set up the layout and widgets
        layout = QVBoxLayout()

        # Prompt selector
        layout.addWidget(QLabel("Select Prompt:"))
        self.prompt_selector = QComboBox()
        
        if self.prompt_manager and hasattr(self.prompt_manager, 'list_prompts'):
            self.prompt_selector.addItems(self.prompt_manager.list_prompts())
        
        self.prompt_selector.currentTextChanged.connect(self.load_prompt)
        layout.addWidget(self.prompt_selector)

        # Prompt editor
        layout.addWidget(QLabel("Edit Prompt:"))
        self.prompt_editor = QTextEdit()
        layout.addWidget(self.prompt_editor)

        # Execute button
        execute_btn = QPushButton("Execute")
        execute_btn.clicked.connect(self.execute_prompt)
        layout.addWidget(execute_btn)
        
        # Output area
        layout.addWidget(QLabel("Output:"))
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)

        self.setLayout(layout)
    
    def load_prompt(self, prompt_name):
        """
        Load the selected prompt's text into the editor.
        
        Args:
            prompt_name (str): The name of the prompt to load.
        """
        if not self.prompt_manager or not hasattr(self.prompt_manager, 'get_prompt'):
            self.log_output("Error: Prompt manager not available")
            return
            
        prompt_text = self.prompt_manager.get_prompt(prompt_name)
        self.prompt_editor.setPlainText(prompt_text)
        self.log_output(f"Loaded prompt: {prompt_name}")

    def execute_prompt(self):
        """
        Execute the current prompt text and display the results.
        """
        # Get the prompt text from the editor
        selected_prompt = self.prompt_editor.toPlainText()
        if not selected_prompt.strip():
            self.log_output("Error: No prompt text provided")
            return
            
        self.log_output(f"Executing prompt...")
        
        try:
            # Execute a single prompt cycle via the cycle service
            if self.ui_logic and hasattr(self.ui_logic, 'execute_prompt'):
                # Use UI logic if available
                response = self.ui_logic.execute_prompt(selected_prompt)
                self.log_output(f"Response: {response}")
            elif hasattr(self.cycle_service, 'run_cycle'):
                # Otherwise use cycle service directly
                response = self.cycle_service.run_cycle({"prompt": selected_prompt}, cycle_type="single")
                self.log_output(f"Cycle executed successfully.")
                self.log_output(f"Response: {response}")
            else:
                self.log_output("Error: No execution service available")
        except Exception as e:
            self.log_output(f"Error executing prompt cycle: {e}")
            
    def log_output(self, message):
        """
        Log a message to the output display and logger.
        
        Args:
            message (str): The message to log.
        """
        if hasattr(self, 'output_display'):
            self.output_display.append(message)
            
        if self.logger:
            self.logger.info(message)
        else:
            print(message)

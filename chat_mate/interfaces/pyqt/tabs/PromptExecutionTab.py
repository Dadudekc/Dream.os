from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal
import logging
import asyncio
from qasync import asyncSlot

# Core Services
from core.PromptCycleOrchestrator import PromptCycleOrchestrator
from core.AletheiaPromptManager import AletheiaPromptManager
from core.PromptResponseHandler import PromptResponseHandler
from core.DiscordQueueProcessor import DiscordQueueProcessor
from core.ConfigManager import ConfigManager


class PromptExecutionTab(QWidget):
    """
    Tab for executing prompts through various services.
    Provides a unified interface for prompt selection, editing, and execution.
    """

    # PyQt signals for thread-safe UI updates
    prompt_loaded = pyqtSignal(str)
    execution_started = pyqtSignal()
    execution_finished = pyqtSignal(str)
    execution_error = pyqtSignal(str)

    def __init__(self, dispatcher=None, parent=None, config=None, logger=None, prompt_manager=None):
        super().__init__(parent)

        self.parent = parent
        self.config = config or ConfigManager()
        self.logger = logger or logging.getLogger("PromptExecutionTab")
        self.dispatcher = dispatcher
        self.prompt_manager = prompt_manager

        # Internal services
        self.prompt_orchestrator = PromptCycleOrchestrator(self.config)
        self.template_manager = AletheiaPromptManager()
        self.response_handler = PromptResponseHandler(self.config, self.logger)
        self.discord_processor = DiscordQueueProcessor(self.config, self.logger)
        
        # Track running tasks
        self.running_tasks = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Prompt selector
        layout.addWidget(QLabel("Select Prompt:"))
        self.prompt_selector = QComboBox()
        prompts = self.prompt_orchestrator.list_prompts() if hasattr(self.prompt_orchestrator, 'list_prompts') else []
        self.prompt_selector.addItems(prompts)
        layout.addWidget(self.prompt_selector)

        # Prompt editor
        layout.addWidget(QLabel("Edit Prompt:"))
        self.prompt_editor = QTextEdit()
        layout.addWidget(self.prompt_editor)

        # Execute button
        self.execute_btn = QPushButton("Execute")
        layout.addWidget(self.execute_btn)

        # Output display
        layout.addWidget(QLabel("Output:"))
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)

        self.setLayout(layout)

    def _connect_signals(self):
        """Connect PyQt signals and slots."""
        self.prompt_selector.currentTextChanged.connect(self.load_prompt)
        self.execute_btn.clicked.connect(self.execute_prompt)

        # Connect custom signals
        self.prompt_loaded.connect(self.on_prompt_loaded)
        self.execution_started.connect(lambda: self.log_output("🚀 Executing prompt..."))
        self.execution_finished.connect(lambda msg: self.log_output(f"✅ {msg}"))
        self.execution_error.connect(lambda err: self.log_output(f"❌ {err}"))

    @asyncSlot(str)
    async def load_prompt(self, prompt_name):
        """Load the selected prompt into editor asynchronously."""
        try:
            # Generate task ID for tracking
            task_id = f"load_prompt_{prompt_name}"
            
            # Signal task start
            if self.dispatcher:
                self.dispatcher.emit_task_started(task_id)
            
            # Create and track task
            task = asyncio.create_task(self._load_prompt_async(task_id, prompt_name))
            self.running_tasks[task_id] = task
            
            # Add done callback
            task.add_done_callback(lambda t: self._on_task_done(task_id, t))
            
        except Exception as e:
            self.execution_error.emit(f"Error starting prompt load: {str(e)}")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(f"load_prompt_{prompt_name}", str(e))

    async def _load_prompt_async(self, task_id, prompt_name):
        """Async prompt loading task."""
        try:
            # Report progress
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 25, "Loading prompt template")
            
            # In a real implementation, this might be an async operation
            # You could use asyncio.to_thread if the operation is CPU-bound
            if hasattr(self.prompt_orchestrator, 'get_prompt'):
                # Simulate async operation
                await asyncio.sleep(0.5)
                
                # Report progress
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(task_id, 75, "Processing template")
                
                prompt_text = self.prompt_orchestrator.get_prompt(prompt_name)
                
                # Report completion
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(task_id, 100, "Template loaded")
                
                self.prompt_loaded.emit(prompt_text)
                return {'prompt_name': prompt_name, 'prompt_text': prompt_text}
            else:
                raise ValueError("Prompt orchestrator unavailable.")
        except Exception as e:
            self.execution_error.emit(f"Error loading prompt: {str(e)}")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, str(e))
            raise e

    @pyqtSlot(str)
    def on_prompt_loaded(self, prompt_text):
        """Safely update prompt editor from the UI thread."""
        self.prompt_editor.setPlainText(prompt_text)
        self.log_output("✅ Prompt loaded successfully.")

    @asyncSlot()
    async def execute_prompt(self):
        """Execute prompt asynchronously."""
        prompt_text = self.prompt_editor.toPlainText().strip()
        prompt_name = self.prompt_selector.currentText()
        
        if not prompt_text:
            self.execution_error.emit("No prompt provided.")
            return

        self.execution_started.emit()
        
        # Create unique task ID
        task_id = f"execute_prompt_{id(prompt_text)}"
        
        # Signal task start
        if self.dispatcher:
            self.dispatcher.emit_task_started(task_id)
            
        # Create and track task
        task = asyncio.create_task(self._execute_prompt_async(task_id, prompt_name, prompt_text))
        self.running_tasks[task_id] = task
        
        # Add done callback
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))

    async def _execute_prompt_async(self, task_id, prompt_name, prompt_text):
        """Async prompt execution task."""
        try:
            # Report initial progress
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 10, "Preparing prompt execution")
            
            # Simulate task progress
            await asyncio.sleep(0.5)
            
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 30, "Processing prompt")
            
            # Simulate different execution paths with proper progress reporting
            if self.parent and hasattr(self.parent, 'execute_prompt'):
                # Report progress
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(task_id, 50, "Executing through parent")
                
                # Simulate processing time
                await asyncio.sleep(1)
                
                # In a real implementation, use asyncio.to_thread for blocking calls
                # response = await asyncio.to_thread(self.parent.execute_prompt, prompt_text)
                response = f"Simulated response for {prompt_text[:20]}..."
                
                # Report progress
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(task_id, 90, "Processing response")
                
                result = {"prompt": prompt_text, "response": response}
                
            elif hasattr(self.prompt_orchestrator, 'run_cycle'):
                # Report progress
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(task_id, 50, "Running prompt cycle")
                
                # Simulate processing time
                await asyncio.sleep(1)
                
                # In a real implementation, use asyncio.to_thread for blocking calls
                # response = await asyncio.to_thread(
                #     self.prompt_orchestrator.run_cycle,
                #     {"prompt": prompt_text},
                #     cycle_type="single"
                # )
                response = f"Cycle response for {prompt_text[:20]}..."
                
                # Report progress
                if self.dispatcher:
                    self.dispatcher.emit_task_progress(task_id, 90, "Processing cycle results")
                
                result = {"prompt": prompt_text, "response": response}
            else:
                raise ValueError("No execution service available.")
            
            # Final processing
            await asyncio.sleep(0.3)
            
            # Report completion
            if self.dispatcher:
                self.dispatcher.emit_task_progress(task_id, 100, "Execution complete")
                
            # Signal execution finished through local signal
            self.execution_finished.emit(f"Prompt executed successfully")
            
            # Return result for task completion handler
            return result
            
        except Exception as e:
            self.execution_error.emit(f"Exception during execution: {str(e)}")
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
            
            # Log success if not already logged by the execution_finished signal
            if not task_id.startswith("execute_prompt_"):
                self.log_output(f"✅ Task {task_id} completed successfully!")
            
            # Emit completion signal through dispatcher
            if self.dispatcher:
                self.dispatcher.emit_task_completed(task_id, result)
                
                # If this was a prompt execution, also emit the prompt_executed signal
                if task_id.startswith("execute_prompt_") and 'prompt' in result:
                    prompt_name = self.prompt_selector.currentText()
                    self.dispatcher.emit_prompt_executed(prompt_name, result)
                    
        except asyncio.CancelledError:
            self.log_output(f"❌ Task {task_id} was cancelled.")
            if self.dispatcher:
                self.dispatcher.emit_task_failed(task_id, "Task was cancelled.")
                
        except Exception as e:
            self.log_output(f"❌ Task {task_id} failed with error: {str(e)}")
            # Task failure will already have been emitted in the task itself

    def log_output(self, message: str):
        """Log to UI and logger."""
        self.output_display.append(message)
        self.logger.info(message)
        
        # Use dispatcher if available
        if self.dispatcher:
            self.dispatcher.emit_log_output(message)
            
    def handle_discord_event(self, event_type, event_data):
        """Handle discord events if needed."""
        # Only respond to specific events that are relevant to this tab
        if event_type == "prompt_request":
            self.log_output(f"Received prompt request from Discord: {event_data.get('prompt', '')}")
            # Could automatically load the prompt here if desired

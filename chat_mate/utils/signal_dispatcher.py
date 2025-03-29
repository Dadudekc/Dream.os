from PyQt5.QtCore import QObject, pyqtSignal

class SignalDispatcher(QObject):
    """
    Centralized dispatcher for decoupled, scalable tab communication.
    """
    # Define your signals clearly here
    log_output = pyqtSignal(str)
    prompt_executed = pyqtSignal(str, dict)  # prompt_name, response data
    dreamscape_generated = pyqtSignal(dict)
    discord_event = pyqtSignal(str, dict)    # event_type, event_data
    
    # Additional signals for async operations
    task_started = pyqtSignal(str)  # task_id
    task_progress = pyqtSignal(str, int, str)  # task_id, progress percentage, status message
    task_completed = pyqtSignal(str, dict)  # task_id, result data
    task_failed = pyqtSignal(str, str)  # task_id, error message
    
    # Status update signals
    status_update = pyqtSignal(str)  # status message
    append_output = pyqtSignal(str)  # output message
    discord_log = pyqtSignal(str)  # discord message
    
    # Chat automation signals
    automation_result = pyqtSignal(str)  # automation result message

    def __init__(self):
        super().__init__()
        # Keep track of registered listeners for manual callbacks
        self._listeners = {
            'log_output': [],
            'prompt_executed': [],
            'dreamscape_generated': [],
            'discord_event': [],
            'task_started': [],
            'task_progress': [],
            'task_completed': [],
            'task_failed': [],
            'status_update': [],
            'append_output': [],
            'discord_log': [],
            'automation_result': []
        }
        
    def emit_log_output(self, message):
        """Emit log_output signal with message."""
        self.log_output.emit(message)
        
    def emit_prompt_executed(self, prompt_name, response_data):
        """Emit prompt_executed signal with prompt_name and response_data."""
        self.prompt_executed.emit(prompt_name, response_data)
        
    def emit_dreamscape_generated(self, data):
        """Emit dreamscape_generated signal with data."""
        self.dreamscape_generated.emit(data)
        
    def emit_discord_event(self, event_type, event_data):
        """Emit discord_event signal with event_type and event_data."""
        self.discord_event.emit(event_type, event_data)
        
    def emit_task_started(self, task_id):
        """Emit task_started signal with task_id."""
        self.task_started.emit(task_id)
        
    def emit_task_progress(self, task_id, progress, message):
        """Emit task_progress signal with task_id, progress, and message."""
        self.task_progress.emit(task_id, progress, message)
        
    def emit_task_completed(self, task_id, result):
        """Emit task_completed signal with task_id and result."""
        self.task_completed.emit(task_id, result)
        
    def emit_task_failed(self, task_id, error):
        """Emit task_failed signal with task_id and error."""
        self.task_failed.emit(task_id, error)
        
    def emit_status_update(self, message):
        """Emit status_update signal with message."""
        self.status_update.emit(message)
        
    def emit_append_output(self, message):
        """Emit append_output signal with message."""
        self.append_output.emit(message)
        
    def emit_discord_log(self, message):
        """Emit discord_log signal with message."""
        self.discord_log.emit(message)
        
    def emit_automation_result(self, result):
        """Emit automation_result signal with result."""
        self.automation_result.emit(result)
        
    def register_listener(self, signal_name, callback):
        """
        Register a callback function to be called when a signal is emitted.
        
        Args:
            signal_name (str): Name of the signal to listen for
            callback (callable): Function to call when signal is emitted
        """
        if signal_name in self._listeners:
            self._listeners[signal_name].append(callback)
            signal = getattr(self, signal_name, None)
            if signal and isinstance(signal, pyqtSignal):
                signal.connect(callback)
        else:
            raise ValueError(f"Unknown signal: {signal_name}")
            
    def unregister_listener(self, signal_name, callback):
        """
        Unregister a callback function.
        
        Args:
            signal_name (str): Name of the signal to stop listening for
            callback (callable): Function to unregister
        """
        if signal_name in self._listeners and callback in self._listeners[signal_name]:
            self._listeners[signal_name].remove(callback)
            signal = getattr(self, signal_name, None)
            if signal and isinstance(signal, pyqtSignal):
                signal.disconnect(callback)

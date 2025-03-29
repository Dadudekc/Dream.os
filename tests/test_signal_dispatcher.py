import pytest
import asyncio
from PyQt5.QtCore import QObject, pyqtSlot
from utils.signal_dispatcher import SignalDispatcher

class SignalRecorder(QObject):
    """Helper class to record emitted signals for testing."""
    
    def __init__(self):
        super().__init__()
        self.log_messages = []
        self.prompt_data = []
        self.dreamscape_data = []
        self.discord_events = []
        self.task_events = {
            'started': [],
            'progress': [],
            'completed': [],
            'failed': []
        }
        self.status_updates = []
        
    @pyqtSlot(str)
    def on_log_output(self, message):
        self.log_messages.append(message)
        
    @pyqtSlot(str, dict)
    def on_prompt_executed(self, prompt_name, data):
        self.prompt_data.append((prompt_name, data))
        
    @pyqtSlot(dict)
    def on_dreamscape_generated(self, data):
        self.dreamscape_data.append(data)
        
    @pyqtSlot(str, dict)
    def on_discord_event(self, event_type, data):
        self.discord_events.append((event_type, data))
        
    @pyqtSlot(str)
    def on_task_started(self, task_id):
        self.task_events['started'].append(task_id)
        
    @pyqtSlot(str, int, str)
    def on_task_progress(self, task_id, progress, message):
        self.task_events['progress'].append((task_id, progress, message))
        
    @pyqtSlot(str, dict)
    def on_task_completed(self, task_id, data):
        self.task_events['completed'].append((task_id, data))
        
    @pyqtSlot(str, str)
    def on_task_failed(self, task_id, error):
        self.task_events['failed'].append((task_id, error))
        
    @pyqtSlot(str)
    def on_status_update(self, message):
        self.status_updates.append(message)

@pytest.fixture
def dispatcher():
    """Create a fresh SignalDispatcher instance for each test."""
    return SignalDispatcher()

@pytest.fixture
def recorder():
    """Create a SignalRecorder to capture emitted signals."""
    return SignalRecorder()

def test_log_output_signal(dispatcher, recorder):
    """Test that log_output signal is properly emitted and received."""
    # Connect the signal
    dispatcher.log_output.connect(recorder.on_log_output)
    
    # Emit a test message
    test_message = "Test log message"
    dispatcher.emit_log_output(test_message)
    
    # Check that the message was received
    assert len(recorder.log_messages) == 1
    assert recorder.log_messages[0] == test_message

def test_prompt_executed_signal(dispatcher, recorder):
    """Test that prompt_executed signal is properly emitted and received."""
    # Connect the signal
    dispatcher.prompt_executed.connect(recorder.on_prompt_executed)
    
    # Emit test data
    test_prompt = "test_prompt"
    test_data = {"response": "Test response", "tokens": 150}
    dispatcher.emit_prompt_executed(test_prompt, test_data)
    
    # Check that the data was received
    assert len(recorder.prompt_data) == 1
    assert recorder.prompt_data[0][0] == test_prompt
    assert recorder.prompt_data[0][1] == test_data

def test_dreamscape_generated_signal(dispatcher, recorder):
    """Test that dreamscape_generated signal is properly emitted and received."""
    # Connect the signal
    dispatcher.dreamscape_generated.connect(recorder.on_dreamscape_generated)
    
    # Emit test data
    test_data = {"episodes_created": 3, "output_directory": "/test/path"}
    dispatcher.emit_dreamscape_generated(test_data)
    
    # Check that the data was received
    assert len(recorder.dreamscape_data) == 1
    assert recorder.dreamscape_data[0] == test_data

def test_discord_event_signal(dispatcher, recorder):
    """Test that discord_event signal is properly emitted and received."""
    # Connect the signal
    dispatcher.discord_event.connect(recorder.on_discord_event)
    
    # Emit test data
    test_event = "message_received"
    test_data = {"channel_id": "123456789", "content": "Hello, world!"}
    dispatcher.emit_discord_event(test_event, test_data)
    
    # Check that the data was received
    assert len(recorder.discord_events) == 1
    assert recorder.discord_events[0][0] == test_event
    assert recorder.discord_events[0][1] == test_data

def test_task_signals(dispatcher, recorder):
    """Test that task-related signals are properly emitted and received."""
    # Connect the signals
    dispatcher.task_started.connect(recorder.on_task_started)
    dispatcher.task_progress.connect(recorder.on_task_progress)
    dispatcher.task_completed.connect(recorder.on_task_completed)
    dispatcher.task_failed.connect(recorder.on_task_failed)
    
    # Emit test data for a task lifecycle
    test_task_id = "test_task_1"
    
    # Task started
    dispatcher.emit_task_started(test_task_id)
    
    # Task progress
    dispatcher.emit_task_progress(test_task_id, 25, "Started processing")
    dispatcher.emit_task_progress(test_task_id, 50, "Halfway done")
    dispatcher.emit_task_progress(test_task_id, 75, "Almost complete")
    
    # Task completed
    test_result = {"status": "success", "data": "Some result data"}
    dispatcher.emit_task_completed(test_task_id, test_result)
    
    # A second task that fails
    test_task_id_2 = "test_task_2"
    dispatcher.emit_task_started(test_task_id_2)
    dispatcher.emit_task_progress(test_task_id_2, 25, "Started processing")
    dispatcher.emit_task_failed(test_task_id_2, "Something went wrong")
    
    # Check task started events
    assert len(recorder.task_events['started']) == 2
    assert recorder.task_events['started'][0] == test_task_id
    assert recorder.task_events['started'][1] == test_task_id_2
    
    # Check task progress events
    assert len(recorder.task_events['progress']) == 4
    assert recorder.task_events['progress'][0] == (test_task_id, 25, "Started processing")
    assert recorder.task_events['progress'][1] == (test_task_id, 50, "Halfway done")
    assert recorder.task_events['progress'][2] == (test_task_id, 75, "Almost complete")
    assert recorder.task_events['progress'][3] == (test_task_id_2, 25, "Started processing")
    
    # Check task completed events
    assert len(recorder.task_events['completed']) == 1
    assert recorder.task_events['completed'][0] == (test_task_id, test_result)
    
    # Check task failed events
    assert len(recorder.task_events['failed']) == 1
    assert recorder.task_events['failed'][0] == (test_task_id_2, "Something went wrong")

def test_listener_registration(dispatcher, recorder):
    """Test manual listener registration and unregistration."""
    # Register a listener
    dispatcher.register_listener('log_output', recorder.on_log_output)
    
    # Emit a test message
    test_message = "Test registration message"
    dispatcher.emit_log_output(test_message)
    
    # Check that the message was received
    assert len(recorder.log_messages) == 1
    assert recorder.log_messages[0] == test_message
    
    # Unregister the listener
    dispatcher.unregister_listener('log_output', recorder.on_log_output)
    
    # Emit another message
    dispatcher.emit_log_output("This shouldn't be received")
    
    # Check that no additional messages were received
    assert len(recorder.log_messages) == 1

@pytest.mark.asyncio
async def test_async_task_integration(dispatcher, recorder):
    """Test integration with async tasks."""
    # Connect signals
    dispatcher.task_started.connect(recorder.on_task_started)
    dispatcher.task_progress.connect(recorder.on_task_progress)
    dispatcher.task_completed.connect(recorder.on_task_completed)
    
    # Create an async task that emits signals
    async def test_task():
        task_id = "async_test_task"
        dispatcher.emit_task_started(task_id)
        
        for i in range(1, 4):
            await asyncio.sleep(0.1)
            progress = i * 25
            dispatcher.emit_task_progress(task_id, progress, f"Progress: {progress}%")
            
        await asyncio.sleep(0.1)
        dispatcher.emit_task_completed(task_id, {"result": "Task completed"})
        
        return "Done"
    
    # Run the task
    task = asyncio.create_task(test_task())
    result = await task
    
    # Check the result
    assert result == "Done"
    
    # Check that signals were emitted
    assert len(recorder.task_events['started']) == 1
    assert recorder.task_events['started'][0] == "async_test_task"
    
    assert len(recorder.task_events['progress']) == 3
    assert recorder.task_events['progress'][0][0] == "async_test_task"
    assert recorder.task_events['progress'][0][1] == 25
    assert recorder.task_events['progress'][1][1] == 50
    assert recorder.task_events['progress'][2][1] == 75
    
    assert len(recorder.task_events['completed']) == 1
    assert recorder.task_events['completed'][0][0] == "async_test_task"
    assert recorder.task_events['completed'][0][1] == {"result": "Task completed"}

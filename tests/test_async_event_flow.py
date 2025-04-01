import pytest
import asyncio
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from utils.signal_dispatcher import SignalDispatcher
from qasync import asyncSlot
import time

class MockDreamscapeTab(QObject):
    """Mock DreamscapeGenerationTab for testing async event flows."""
    
    def __init__(self, dispatcher):
        super().__init__()
        self.dispatcher = dispatcher
        self.log_messages = []
        self.completed_tasks = []
        self.received_discord_events = []
        
    def log_output(self, message):
        """Record log messages."""
        self.log_messages.append(message)
        
    def handle_discord_event(self, event_type, event_data):
        """Handler for discord_event signals."""
        self.received_discord_events.append((event_type, event_data))
        self.log_output(f"Received Discord event: {event_type}")
        
        # If this is a generation request, simulate generating content
        if event_type == "generation_request":
            asyncio.create_task(self.generate_dreamscape_async("dream_task"))
    
    @asyncSlot()
    async def generate_dreamscape_async(self, task_id):
        """Simulate async dreamscape generation."""
        try:
            # Notify that we're starting
            self.dispatcher.emit_task_started(task_id)
            self.log_output(f"Starting dreamscape generation task: {task_id}")
            
            # Simulate work with progress updates
            total_steps = 4
            for i in range(total_steps):
                # Do some "work"
                await asyncio.sleep(0.1)
                
                # Report progress
                progress = int((i + 1) / total_steps * 100)
                self.dispatcher.emit_task_progress(
                    task_id, 
                    progress, 
                    f"Generating dreamscape step {i+1}/{total_steps}"
                )
                self.log_output(f"Generation progress: {progress}%")
            
            # Generate result data
            result = {
                "episodes_created": 3,
                "output_directory": "/test/path",
                "timestamp": time.time()
            }
            
            # Mark task as completed
            self.dispatcher.emit_task_completed(task_id, result)
            self.completed_tasks.append((task_id, result))
            self.log_output(f"Completed dreamscape generation: {task_id}")
            
            # Emit dreamscape_generated signal with the result
            self.dispatcher.emit_dreamscape_generated(result)
            
            return result
            
        except Exception as e:
            self.log_output(f"Error in generation task: {str(e)}")
            self.dispatcher.emit_task_failed(task_id, str(e))
            raise e

class MockDiscordTab(QObject):
    """Mock DiscordTab for testing async event flows."""
    
    def __init__(self, dispatcher):
        super().__init__()
        self.dispatcher = dispatcher
        self.log_messages = []
        self.received_dreamscape_content = []
        self.posted_messages = []
        
    def log_output(self, message):
        """Record log messages."""
        self.log_messages.append(message)
        
    def handle_dreamscape_generated(self, data):
        """Handler for dreamscape_generated signals."""
        self.received_dreamscape_content.append(data)
        self.log_output(f"Received dreamscape content: {data.get('episodes_created', 0)} episodes")
        
        # Simulate posting to Discord
        asyncio.create_task(self.post_to_discord_async("post_task", data))
    
    @asyncSlot()
    async def post_to_discord_async(self, task_id, content_data):
        """Simulate async posting to Discord."""
        try:
            # Notify that we're starting
            self.dispatcher.emit_task_started(task_id)
            self.log_output(f"Starting Discord post task: {task_id}")
            
            # Simulate work with progress updates
            await asyncio.sleep(0.1)
            self.dispatcher.emit_task_progress(task_id, 50, "Preparing Discord message")
            self.log_output("Preparing Discord message")
            
            await asyncio.sleep(0.1)
            self.dispatcher.emit_task_progress(task_id, 90, "Sending to Discord")
            self.log_output("Sending to Discord")
            
            # Record the posted message
            message = f"New dreamscape content available: {content_data.get('episodes_created', 0)} episodes"
            self.posted_messages.append(message)
            
            # Simulate Discord API response
            result = {
                "channel_id": "12345",
                "message_id": "67890",
                "content": message,
                "timestamp": time.time()
            }
            
            # Mark task as completed
            self.dispatcher.emit_task_completed(task_id, result)
            self.log_output(f"Posted to Discord: {message}")
            
            # Emit discord_event signal for the post
            self.dispatcher.emit_discord_event("message_posted", result)
            
            return result
            
        except Exception as e:
            self.log_output(f"Error posting to Discord: {str(e)}")
            self.dispatcher.emit_task_failed(task_id, str(e))
            raise e
    
    @asyncSlot()
    async def simulate_discord_request(self):
        """Simulate a request coming from Discord."""
        event_data = {
            "user_id": "user123",
            "channel_id": "channel456",
            "content": "Please generate new dreamscape content!",
            "timestamp": time.time()
        }
        
        self.log_output("Received message from Discord")
        
        # Emit discord_event signal
        self.dispatcher.emit_discord_event("generation_request", event_data)
        self.log_output("Emitted generation request event")
        
        return event_data

@pytest.fixture
def dispatcher():
    """Create a fresh SignalDispatcher instance for each test."""
    return SignalDispatcher()

@pytest.fixture
def dreamscape_tab(dispatcher):
    """Create a MockDreamscapeTab instance."""
    tab = MockDreamscapeTab(dispatcher)
    
    # Connect signals
    dispatcher.discord_event.connect(tab.handle_discord_event)
    
    return tab

@pytest.fixture
def discord_tab(dispatcher):
    """Create a MockDiscordTab instance."""
    tab = MockDiscordTab(dispatcher)
    
    # Connect signals
    dispatcher.dreamscape_generated.connect(tab.handle_dreamscape_generated)
    
    return tab

@pytest.mark.asyncio
async def test_full_event_flow(dispatcher, dreamscape_tab, discord_tab):
    """Test a complete async event flow between components."""
    # Simulate a request from Discord
    await discord_tab.simulate_discord_request()
    
    # Allow time for all async operations to complete
    await asyncio.sleep(1)
    
    # Check Discord tab logs
    assert len(discord_tab.log_messages) >= 4
    assert "Received message from Discord" in discord_tab.log_messages[0]
    assert "Emitted generation request event" in discord_tab.log_messages[1]
    
    # Check Dreamscape tab logs
    assert len(dreamscape_tab.log_messages) >= 6
    assert "Received Discord event: generation_request" in dreamscape_tab.log_messages[0]
    assert "Starting dreamscape generation task" in dreamscape_tab.log_messages[1]
    
    # Verify that dreamscape content was generated
    assert len(dreamscape_tab.completed_tasks) == 1
    assert dreamscape_tab.completed_tasks[0][1]["episodes_created"] == 3
    
    # Verify that Discord tab received the generated content
    assert len(discord_tab.received_dreamscape_content) == 1
    assert discord_tab.received_dreamscape_content[0]["episodes_created"] == 3
    
    # Verify that content was posted to Discord
    assert len(discord_tab.posted_messages) == 1
    assert "New dreamscape content available: 3 episodes" in discord_tab.posted_messages[0]

@pytest.mark.asyncio
async def test_concurrent_tasks(dispatcher, dreamscape_tab, discord_tab):
    """Test multiple concurrent tasks across components."""
    # Start multiple concurrent generation requests
    task1 = asyncio.create_task(discord_tab.simulate_discord_request())
    await asyncio.sleep(0.05)  # Small delay to ensure different task IDs
    task2 = asyncio.create_task(discord_tab.simulate_discord_request())
    await asyncio.sleep(0.05)
    task3 = asyncio.create_task(discord_tab.simulate_discord_request())
    
    # Wait for all tasks to complete
    await asyncio.gather(task1, task2, task3)
    
    # Allow time for all async operations to complete
    await asyncio.sleep(1.5)
    
    # Verify that multiple dreamscape generation tasks completed
    assert len(dreamscape_tab.completed_tasks) == 3
    
    # Verify that Discord tab received all generation results
    assert len(discord_tab.received_dreamscape_content) == 3
    
    # Verify that multiple Discord posts were made
    assert len(discord_tab.posted_messages) == 3

@pytest.mark.asyncio
async def test_error_handling(dispatcher, dreamscape_tab, discord_tab):
    """Test error handling in async event flows."""
    # Patch the dreamscape generation method to raise an exception
    original_method = dreamscape_tab.generate_dreamscape_async
    
    async def generate_with_error(task_id):
        if task_id == "error_task":
            await asyncio.sleep(0.1)
            raise ValueError("Simulated error in dreamscape generation")
        return await original_method(task_id)
    
    dreamscape_tab.generate_dreamscape_async = generate_with_error
    
    # Create a recorder for task failure events
    task_failures = []
    
    @pyqtSlot(str, str)
    def on_task_failed(task_id, error):
        task_failures.append((task_id, error))
    
    dispatcher.task_failed.connect(on_task_failed)
    
    # Generate a task that will fail
    try:
        await dreamscape_tab.generate_dreamscape_async("error_task")
    except ValueError:
        pass  # We expect this to fail
    
    # Allow time for signals to propagate
    await asyncio.sleep(0.2)
    
    # Verify that the error was properly signaled
    assert len(task_failures) == 1
    assert task_failures[0][0] == "error_task"
    assert "Simulated error" in task_failures[0][1]
    
    # Restore the original method
    dreamscape_tab.generate_dreamscape_async = original_method 

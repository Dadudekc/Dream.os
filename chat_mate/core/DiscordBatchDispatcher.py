import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from queue import Queue, Empty
import threading
import time
from .ConfigManager import ConfigManager

class DiscordBatchDispatcher:
    """
    Handles queuing and batching of Discord messages for efficient delivery.
    Manages rate limits and provides feedback on message delivery status.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Discord batch dispatcher.
        
        :param config_manager: The configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.message_queue = Queue()
        self.batch_size = self.config_manager.get('DISCORD_BATCH_SIZE', 10)
        self.rate_limit_delay = self.config_manager.get('DISCORD_RATE_LIMIT_DELAY', 1)
        self.is_running = False
        self.dispatcher_thread = None

    def start(self) -> None:
        """Start the message dispatcher thread."""
        if self.is_running:
            self.logger.warning("Dispatcher already running")
            return

        self.is_running = True
        self.dispatcher_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self.dispatcher_thread.start()
        self.logger.info("Discord batch dispatcher started")

    def stop(self) -> None:
        """Stop the message dispatcher thread."""
        if not self.is_running:
            self.logger.warning("Dispatcher not running")
            return

        self.is_running = False
        if self.dispatcher_thread:
            self.dispatcher_thread.join()
        self.logger.info("Discord batch dispatcher stopped")

    def queue_message(self, channel_id: int, content: str, **kwargs) -> None:
        """
        Queue a message for delivery.
        
        :param channel_id: The Discord channel ID
        :param content: The message content
        :param kwargs: Additional message parameters
        """
        message = {
            'channel_id': channel_id,
            'content': content,
            'timestamp': datetime.now(),
            **kwargs
        }
        self.message_queue.put(message)
        self.logger.debug(f"Queued message for channel {channel_id}")

    def queue_batch(self, channel_id: int, messages: List[str], **kwargs) -> None:
        """
        Queue multiple messages for delivery.
        
        :param channel_id: The Discord channel ID
        :param messages: List of message contents
        :param kwargs: Additional message parameters
        """
        for content in messages:
            self.queue_message(channel_id, content, **kwargs)

    def _dispatch_loop(self) -> None:
        """Main dispatch loop that processes queued messages."""
        batch = []
        last_dispatch = 0

        while self.is_running:
            try:
                # Collect messages for the current batch
                while len(batch) < self.batch_size:
                    try:
                        message = self.message_queue.get(timeout=1)
                        batch.append(message)
                    except Empty:
                        break

                # Process batch if we have messages
                if batch:
                    current_time = time.time()
                    time_since_last = current_time - last_dispatch

                    # Respect rate limit delay
                    if time_since_last >= self.rate_limit_delay:
                        self._process_batch(batch)
                        batch = []
                        last_dispatch = current_time
                    else:
                        time.sleep(self.rate_limit_delay - time_since_last)

            except Exception as e:
                self.logger.error(f"Error in dispatch loop: {str(e)}")
                time.sleep(1)  # Prevent tight error loop

    def _process_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Process a batch of messages.
        
        :param batch: List of message dictionaries
        """
        try:
            # Group messages by channel
            channel_messages = {}
            for message in batch:
                channel_id = message['channel_id']
                if channel_id not in channel_messages:
                    channel_messages[channel_id] = []
                channel_messages[channel_id].append(message)

            # Send messages for each channel
            for channel_id, messages in channel_messages.items():
                self._send_channel_messages(channel_id, messages)

        except Exception as e:
            self.logger.error(f"Error processing batch: {str(e)}")

    def _send_channel_messages(self, channel_id: int, messages: List[Dict[str, Any]]) -> None:
        """
        Send messages to a specific channel.
        
        :param channel_id: The Discord channel ID
        :param messages: List of messages to send
        """
        try:
            # TODO: Implement actual Discord API calls
            # For now, just log the messages
            for message in messages:
                self.logger.info(f"Sending to channel {channel_id}: {message['content']}")
                time.sleep(self.rate_limit_delay)  # Simulate API rate limiting

        except Exception as e:
            self.logger.error(f"Error sending messages to channel {channel_id}: {str(e)}")

    def get_queue_size(self) -> int:
        """
        Get the current size of the message queue.
        
        :return: Number of messages in queue
        """
        return self.message_queue.qsize()

    def clear_queue(self) -> None:
        """Clear all messages from the queue."""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except Empty:
                break
        self.logger.info("Message queue cleared") 
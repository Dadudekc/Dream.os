import asyncio
import logging
import signal
from qasync import QEventLoop
from PyQt5.QtWidgets import QApplication


class QAsyncEventLoopManager:
    """
    Manages the qasync event loop, providing async task handling for PyQt applications.
    Handles lifecycle: initialization, task scheduling, and graceful shutdown.
    """

    def __init__(self, app: QApplication, dispatcher=None, logger=None):
        """
        Args:
            app (QApplication): The main Qt application instance.
            dispatcher (SignalDispatcher, optional): Central signal dispatcher.
            logger (logging.Logger, optional): Logger instance.
        """
        self.app = app
        self.dispatcher = dispatcher
        self.logger = logger or logging.getLogger("QAsyncEventLoopManager")

        # Set up the qasync event loop
        self.loop = QEventLoop(app)
        asyncio.set_event_loop(self.loop)

        # Track running tasks for graceful shutdown
        self.tasks = []

        self.logger.info("QAsyncEventLoopManager initialized.")

    def start(self):
        """Start the event loop."""
        self.logger.info("Starting qasync event loop...")

        # Handle shutdown signals
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

        try:
            with self.loop:
                self.loop.run_forever()
        except KeyboardInterrupt:
            self.logger.warning("KeyboardInterrupt detected, shutting down...")
            self.shutdown()

    def schedule_task(self, coro, task_name=None):
        """
        Schedule a coroutine to run asynchronously.

        Args:
            coro (coroutine): The coroutine to run.
            task_name (str, optional): Name for logging/tracking.
        """
        if not asyncio.iscoroutine(coro):
            raise TypeError("Task must be a coroutine")

        task = asyncio.ensure_future(coro, loop=self.loop)
        self.tasks.append(task)

        task_name = task_name or coro.__name__
        self.logger.info(f"Scheduled async task: {task_name}")

        return task

    def _shutdown_handler(self, *args):
        """Handle system signals for graceful shutdown."""
        self.logger.info("Received shutdown signal.")
        self.shutdown()

    def shutdown(self):
        """Stop the event loop and cancel all running tasks."""
        self.logger.info("Shutting down event loop...")

        # Cancel all running tasks
        try:
            for task in self.tasks:
                if not task.done() and not task.cancelled():
                    self.logger.info(f"Cancelling task: {task}")
                    task.cancel()
        except Exception as e:
            self.logger.error(f"Error cancelling tasks: {e}")

        # Stop the loop
        try:
            # Check if loop is running and stop it
            if self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
                self.logger.info("Called stop on running event loop")
            else:
                self.logger.info("Event loop was not running")
        except Exception as e:
            self.logger.error(f"Error stopping event loop: {e}")

        # Clean up asyncio tasks
        try:
            # Get all remaining tasks
            remaining_tasks = asyncio.all_tasks(self.loop)
            if remaining_tasks:
                self.logger.info(f"Found {len(remaining_tasks)} remaining asyncio tasks to cancel")
                for task in remaining_tasks:
                    if not task.done() and not task.cancelled():
                        task.cancel()
        except Exception as e:
            self.logger.error(f"Error cancelling remaining tasks: {e}")
            
        # Don't close the loop if it's still running
        try:
            if hasattr(self.loop, 'close') and not self.loop.is_running():
                self.loop.close()
                self.logger.info("Event loop closed")
            else:
                self.logger.info("Event loop is still running or already closed, skipping loop.close()")
        except Exception as e:
            self.logger.error(f"Error closing event loop: {e}")
            
        self.logger.info("Event loop shutdown complete")

import queue
import threading
import time
import logging
import traceback
from typing import Callable, Dict, Any, Optional

from social.log_writer import write_json_log

logger = logging.getLogger("TaskQueueManager")

class TaskQueueManager:
    """
    TaskQueueManager: A robust, priority-based task queue with threaded workers.
    This manager supports:
      - Prioritized task scheduling (lower value = higher priority)
      - Delayed execution for rate-limiting or scheduling
      - Configurable retries with exponential backoff
      - Structured logging of task outcomes for feedback and reinforcement learning loops
    """

    def __init__(self, worker_count: int = 4, default_retry: int = 3, base_retry_delay: int = 5):
        """
        :param worker_count: Number of worker threads.
        :param default_retry: Default number of retries per task.
        :param base_retry_delay: Base delay in seconds before retrying (will be used for exponential backoff).
        """
        self.task_queue = queue.PriorityQueue()
        self.worker_count = worker_count
        self.default_retry = default_retry
        self.base_retry_delay = base_retry_delay
        self.workers = []
        self.shutdown_event = threading.Event()

    # ----------------------------------------
    # START / STOP
    # ----------------------------------------
    def start(self):
        """Starts the worker threads."""
        if self.shutdown_event.is_set():
            logger.warning("⚠️ TaskQueueManager is already stopped. Reset shutdown_event to start again.")
            return

        logger.info(f"🚀 Starting TaskQueueManager with {self.worker_count} workers...")
        self.shutdown_event.clear()
        for i in range(self.worker_count):
            thread = threading.Thread(target=self._worker, daemon=True, name=f"Worker-{i+1}")
            thread.start()
            self.workers.append(thread)

    def stop(self):
        """Gracefully stops all workers."""
        logger.info("🛑 Stopping TaskQueueManager...")
        self.shutdown_event.set()  # Signal workers to stop

        # Wait for each worker to finish; timeout after a short period to avoid hanging indefinitely.
        for thread in self.workers:
            thread.join(timeout=3)
        self.workers.clear()
        logger.info("✅ TaskQueueManager stopped.")

    # ----------------------------------------
    # ADD TASK TO QUEUE
    # ----------------------------------------
    def add_task(
        self,
        task_fn: Callable,
        task_data: Optional[Dict[str, Any]] = None,
        priority: int = 10,
        retries: Optional[int] = None,
        delay: int = 0
    ):
        """
        Adds a new task to the queue.

        :param task_fn: Function to execute.
        :param task_data: Optional metadata/context for the task.
        :param priority: Task priority (lower value runs first).
        :param retries: Number of retries available (defaults to default_retry if not provided).
        :param delay: Delay in seconds before task execution.
        """
        task = {
            "function": task_fn,
            "retries": retries if retries is not None else self.default_retry,
            "data": task_data or {},
            "delay": delay
        }
        logger.info(f"📥 Queuing task: {task_data} | Priority: {priority} | Delay: {delay}s")
        # Use current time as a tiebreaker for tasks with equal priority.
        self.task_queue.put((priority, time.time(), task))

    # ----------------------------------------
    # WORKER LOOP
    # ----------------------------------------
    def _worker(self):
        """Worker loop to process tasks from the queue."""
        thread_name = threading.current_thread().name
        logger.info(f"🧰 {thread_name} started.")

        while not self.shutdown_event.is_set():
            try:
                # Wait for a task with a timeout to allow checking the shutdown_event.
                priority, _, task = self.task_queue.get(timeout=1)
                retries = task["retries"]
                task_fn = task["function"]
                task_data = task["data"]
                delay = task["delay"]

                if delay > 0:
                    logger.info(f"⏳ {thread_name}: Delaying task execution by {delay}s for task {task_data}")
                    time.sleep(delay)

                logger.info(f"⚙️ {thread_name}: Executing task: {task_data}")
                try:
                    result = task_fn()
                    logger.info(f"✅ {thread_name}: Task completed: {task_data} -> {result}")

                    write_json_log(
                        platform="TaskQueueManager",
                        status="successful",
                        tags=["task_complete"],
                        ai_output={
                            "task_data": task_data,
                            "result": str(result),
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    )

                except Exception as e:
                    # Log the full traceback for debugging.
                    error_trace = traceback.format_exc()
                    logger.error(f"❌ {thread_name}: Task failed: {task_data}, retries left: {retries}, error: {e}\n{error_trace}")

                    write_json_log(
                        platform="TaskQueueManager",
                        status="failed",
                        tags=["task_failed"],
                        ai_output={
                            "task_data": task_data,
                            "error": str(e),
                            "retries_left": retries,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    )

                    if retries > 0:
                        # Calculate exponential backoff delay.
                        new_delay = delay + (self.base_retry_delay * (2 ** (self.default_retry - retries)))
                        logger.info(f"🔁 {thread_name}: Requeuing task after {new_delay}s | Retries remaining: {retries - 1}")
                        self.add_task(
                            task_fn,
                            task_data=task_data,
                            priority=priority + 1,  # Increase priority value (lower priority) on retry
                            retries=retries - 1,
                            delay=new_delay
                        )
                    else:
                        logger.warning(f"⚠️ {thread_name}: Task permanently failed: {task_data}")

                self.task_queue.task_done()

            except queue.Empty:
                continue

        logger.info(f"🧰 {thread_name} stopping.")

    # ----------------------------------------
    # METRICS + STATUS
    # ----------------------------------------
    def queue_size(self) -> int:
        """Returns the current number of tasks in the queue."""
        return self.task_queue.qsize()

    def status(self) -> Dict[str, Any]:
        """Returns status details of the queue and worker threads."""
        return {
            "running": not self.shutdown_event.is_set(),
            "queue_size": self.queue_size(),
            "workers_active": len(self.workers)
        }

# ----------------------------------------
# Example Usage
# ----------------------------------------
if __name__ == "__main__":
    # Dummy task function for testing
    def sample_task():
        logger.info("🔨 Running sample task...")
        time.sleep(1)
        return "Sample task result"

    # Initialize TaskQueueManager with 3 workers
    manager = TaskQueueManager(worker_count=3)
    manager.start()

    # Add several tasks with various priorities and delays
    manager.add_task(sample_task, task_data={"type": "engagement_reply", "id": 1}, priority=5, delay=2)
    manager.add_task(sample_task, task_data={"type": "proactive_post", "id": 2}, priority=10)
    manager.add_task(sample_task, task_data={"type": "feedback_loop_trigger", "id": 3}, priority=3)

    # Monitor the queue status for 10 seconds
    for _ in range(10):
        logger.info(f"Status: {manager.status()}")
        time.sleep(1)

    manager.stop()

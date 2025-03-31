import time
import threading
import queue
from ....core.openai.OpenAIClient import OpenAIClient
from .setup_logging import setup_logging

# Configure logger with a specific log directory (supports both beta and production)
logger = setup_logging("bot_worker", log_dir="logs/social")

# Configuration constants (can be exposed via config files later)
TASKS_BEFORE_REVALIDATE = 5
LOGIN_RETRY_ATTEMPTS = 3
LOGIN_RETRY_DELAY = 5  # seconds between retry attempts

class BotWorker(threading.Thread):
    """
    A threaded worker that processes tasks using OpenAIClient.
    Handles login sessions, periodic revalidation, and task execution.
    
    This implementation supports:
      - Robust login with retries
      - Graceful handling of task exceptions
      - Periodic session revalidation for long-running tasks
      - Scalability for beta and production environments
    """
    def __init__(self, bot_id, profile_dir, task_queue: queue.Queue, results_queue: queue.Queue, status_callback=None):
        super().__init__()
        self.name = f"Bot-{bot_id}"
        self.profile_dir = profile_dir
        self.task_counter = 0
        self.task_queue = task_queue
        self.results_queue = results_queue
        self.status_callback = status_callback
        self._shutdown = threading.Event()
        self.daemon = True  # Ensures the worker stops when the main program exits

        logger.info(f"[{self.name}] 🚀 Instantiating OpenAIClient (Profile: {self.profile_dir})")
        self.openai_client = OpenAIClient(profile_dir=self.profile_dir, headless=False)
        logger.info(f"[{self.name}] ✅ OpenAI client initialized. Ready to process tasks!")
        self.start()

    def _login_with_retries(self):
        """
        Attempt to login with retry logic.
        Returns True if login succeeds, False otherwise.
        """
        for attempt in range(1, LOGIN_RETRY_ATTEMPTS + 1):
            logger.info(f"[{self.name}] 🔐 Attempting login (Attempt {attempt}/{LOGIN_RETRY_ATTEMPTS})...")
            if self.openai_client.login_openai():
                logger.info(f"[{self.name}] ✅ Login attempt {attempt} successful.")
                return True
            logger.warning(f"[{self.name}] ⚠️ Login attempt {attempt} failed. Retrying in {LOGIN_RETRY_DELAY}s...")
            time.sleep(LOGIN_RETRY_DELAY)
        logger.error(f"[{self.name}] ❌ All login attempts failed.")
        return False

    def run(self):
        """
        Main loop: fetch tasks, process them, update results, and revalidate the session periodically.
        """
        logger.info(f"[{self.name}] ▶️ Worker thread started.")
        while not self._shutdown.is_set():
            try:
                task = self.task_queue.get(timeout=1)
            except queue.Empty:
                continue

            if not task:
                logger.warning(f"[{self.name}] ⚠️ Received empty task; skipping.")
                self.task_queue.task_done()
                continue

            logger.info(f"[{self.name}] 📝 Fetched task #{self.task_counter + 1}: {task}")

            # Ensure we're logged in before processing task
            if not self._login_with_retries():
                logger.error(f"[{self.name}] ❌ Failed to login before task. Skipping task.")
                self.results_queue.put((task, {"error": "Login failed"}))
                self.task_queue.task_done()
                continue

            try:
                success, result = self.process_task(task)
                self.results_queue.put((task, result))

                if self.status_callback:
                    update_type = "progress" if success else "error"
                    self.status_callback(update_type, {
                        "worker": self.name,
                        "task": task,
                        "result": result
                    })

            except Exception as e:
                logger.exception(f"[{self.name}] ❌ Exception during task execution.")
                self.results_queue.put((task, {"error": str(e)}))
                if self.status_callback:
                    self.status_callback("error", {
                        "worker": self.name,
                        "task": task,
                        "error": str(e)
                    })

            finally:
                self.task_queue.task_done()

            self.task_counter += 1
            logger.info(f"[{self.name}] ✅ Task #{self.task_counter} complete. Queue size: {self.task_queue.qsize()}")

            # Revalidate the session after a set number of tasks to ensure long-term stability
            if self.task_counter % TASKS_BEFORE_REVALIDATE == 0:
                self._revalidate_session()

        logger.info(f"[{self.name}] 🛑 Worker thread exiting.")

    def process_task(self, prompt):
        """
        Process a single prompt task using OpenAIClient's process_prompt method.
        Returns a tuple (success: bool, result: dict) with elapsed time.
        """
        logger.info(f"[{self.name}] ➡️ Processing task #{self.task_counter + 1}: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
        start_time = time.time()

        try:
            response = self.openai_client.process_prompt(prompt)
            elapsed_time = time.time() - start_time

            if not response:
                logger.warning(f"[{self.name}] ❌ No response received.")
                return False, {"error": "No response", "elapsed_time": elapsed_time}

            logger.info(f"[{self.name}] ✅ Task completed. Response length: {len(response)} | Time: {elapsed_time:.2f}s")
            return True, {"response": response, "elapsed_time": elapsed_time}

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"[{self.name}] ❌ Error during task: {e} | Time: {elapsed_time:.2f}s")
            return False, {"error": str(e), "elapsed_time": elapsed_time}

    def _revalidate_session(self):
        """
        Periodically refresh the OpenAI session after processing a batch of tasks.
        """
        logger.info(f"[{self.name}] 🔄 Revalidating session after {self.task_counter} tasks.")
        revalidate_start = time.time()

        try:
            # Shutdown current client session
            self.openai_client.shutdown()
        except Exception as e:
            logger.error(f"[{self.name}] ❌ Error during session shutdown: {e}")

        if not self._login_with_retries():
            logger.error(f"[{self.name}] ❌ Session revalidation failed. Shutting down worker.")
            self.shutdown()
        else:
            elapsed_revalidate = time.time() - revalidate_start
            logger.info(f"[{self.name}] ✅ Session revalidated in {elapsed_revalidate:.2f}s.")

    def shutdown(self):
        """
        Gracefully shut down the worker and its OpenAIClient session.
        """
        logger.info(f"[{self.name}] 🛑 Initiating shutdown sequence...")
        self._shutdown.set()
        try:
            if self.openai_client:
                self.openai_client.shutdown()
                logger.info(f"[{self.name}] ✅ OpenAIClient shut down successfully.")
        except Exception as e:
            logger.error(f"[{self.name}] ❌ Error shutting down OpenAIClient: {e}")

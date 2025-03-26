import queue
import threading
import time
from ..bot_worker import BotWorker

class MultibotManager:
    """
    Manages a pool of BotWorker threads to process tasks asynchronously.

    Usage:
        with MultibotManager(scanner, num_workers=4, status_callback=gui_callback) as manager:
            manager.add_task(task)
            manager.wait_for_completion()
            results = manager.get_all_results()
    """

    def __init__(self, scanner=None, num_workers=4, status_callback=None, auto_start=True):
        self.task_queue = queue.Queue()
        self.results_queue = queue.Queue()

        self.scanner = scanner
        self.status_callback = status_callback

        self.num_workers = num_workers
        self.workers = []
        self._lock = threading.Lock()
        self._started = False

        if scanner is not None and hasattr(scanner, 'profile_dir'):
            self.profile_dir = scanner.profile_dir
        else:
            self.profile_dir = "default_profile_dir"

        # Progress metrics
        self.total_tasks = 0
        self.completed_tasks = 0
        self.start_time = None

        if auto_start:
            self.start_workers()

    def start_workers(self):
        """Launch BotWorker threads."""
        with self._lock:
            if self._started:
                print("⚠️ Workers already started.")
                return

            self.workers = [
                BotWorker(
                    task_queue=self.task_queue,
                    results_queue=self.results_queue,
                    status_callback=self._worker_status_update,
                    bot_id=i,
                    profile_dir=self.profile_dir
                )
                for i in range(self.num_workers)
            ]
            self._started = True
            print(f"🚀 {self.num_workers} workers started.")

    def add_task(self, task):
        """Add a task to the queue and update progress counters."""
        if not self._started:
            raise RuntimeError("Workers not started. Call start_workers() first.")

        if not task:
            print("⚠️ Ignored empty task.")
            return

        self.task_queue.put(task)
        self.total_tasks += 1
        print(f"📝 Task added: {task}")

        if not self.start_time:
            self.start_time = time.time()

        self._update_progress()

    def wait_for_completion(self):
        """Block until all tasks are completed."""
        if not self._started:
            raise RuntimeError("Workers not started. Call start_workers() first.")

        print("⏳ Waiting for task completion...")
        self.task_queue.join()
        self._update_progress(force=True)
        print("✅ All tasks processed.")

    def get_all_results(self):
        """Retrieve all task results."""
        results = []
        while not self.results_queue.empty():
            task, result = self.results_queue.get()
            results.append((task, result))
            print(f"📦 Retrieved result for task: {task}")
            # Auto-update progress for consistency
            self.mark_task_complete()

        return results

    def shutdown(self):
        """Shut down all workers."""
        if not self._started:
            print("⚠️ Workers are not running.")
            return

        print("🛑 Shutting down workers...")

        for worker in self.workers:
            worker.shutdown()

        for worker in self.workers:
            worker.join(timeout=5)
            if worker.is_alive():
                print(f"⚠️ Worker {worker.name} did not shut down gracefully.")
            else:
                print(f"✅ Worker {worker.name} shut down cleanly.")

        with self._lock:
            self._started = False

        print("🧹 All workers stopped and cleaned up.")

    def mark_task_complete(self):
        """Thread-safe increment of completed tasks."""
        with self._lock:
            self.completed_tasks += 1
        self._update_progress()

    def _update_progress(self, force=False):
        """Update progress and invoke the callback."""
        if not self.status_callback:
            return

        percent = int((self.completed_tasks / self.total_tasks) * 100) if self.total_tasks else 0
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        status_text = f"{self.completed_tasks}/{self.total_tasks} tasks completed in {elapsed_time:.1f}s"

        self.status_callback(percent, status_text)

    def _worker_status_update(self, update_type, payload=None):
        """Callback for worker updates."""
        if update_type == "progress":
            self.mark_task_complete()

        elif update_type == "log":
            print(f"📜 Worker Log: {payload}")

        # Optional: restart dead workers
        # elif update_type == "error":
        #     self._restart_worker(payload['worker_id'])

    # Optional Dead Worker Recovery
    # def _restart_worker(self, worker_id):
    #     print(f"🔄 Restarting dead worker {worker_id}")
    #     new_worker = BotWorker(
    #         task_queue=self.task_queue,
    #         results_queue=self.results_queue,
    #         status_callback=self._worker_status_update,
    #         bot_id=worker_id,
    #         profile_dir=self.profile_dir
    #     )
    #     self.workers[worker_id] = new_worker

    def __enter__(self):
        self.start_workers()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from core.services.elephant_builder_service import ElephantBuilderService

class TaskQueueService:
    """
    TaskQueueService loads a list of tasks from a JSON file, processes each task,
    and saves the updated queue back to disk. It is designed to work with the
    ElephantBuilderService to automate module generation.
    """

    def __init__(self, path_manager, builder_service: ElephantBuilderService, queue_file_path: Path):
        """
        Initialize TaskQueueService.
        
        :param path_manager: Provides consistent path references.
        :param builder_service: Instance of ElephantBuilderService used to build modules.
        :param queue_file_path: Path to the task queue JSON file.
        """
        self.path_manager = path_manager
        self.builder_service = builder_service
        self.queue_file_path = queue_file_path if isinstance(queue_file_path, Path) else Path(queue_file_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._tasks: List[Dict[str, Any]] = []
        self.load_tasks()

    def load_tasks(self):
        """Load tasks from the JSON queue file. If the file does not exist, initialize an empty list."""
        try:
            if not self.queue_file_path.exists():
                self.logger.warning(f"TaskQueueService: Task queue file not found at {self.queue_file_path}. Creating new one.")
                self._tasks = []
                self.save_tasks()
            else:
                with open(self.queue_file_path, 'r', encoding='utf-8') as f:
                    self._tasks = json.load(f)
                self.logger.info(f"TaskQueueService: Loaded {len(self._tasks)} tasks from {self.queue_file_path}")
        except Exception as e:
            self.logger.error(f"TaskQueueService: Failed to load tasks: {e}", exc_info=True)
            self._tasks = []

    def save_tasks(self):
        """Persist the current task list to the queue file in JSON format."""
        try:
            with open(self.queue_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._tasks, f, indent=4)
            self.logger.info(f"TaskQueueService: Saved {len(self._tasks)} tasks to {self.queue_file_path}")
        except Exception as e:
            self.logger.error(f"TaskQueueService: Failed to save tasks: {e}", exc_info=True)

    def add_task(self, task: Dict[str, Any]):
        """
        Add a new task to the queue and save the updated queue.
        
        :param task: A dictionary representing a task (e.g., build_module task).
        """
        self._tasks.append(task)
        self.save_tasks()
        self.logger.info(f"TaskQueueService: Added new task: {task}")

    def process_queue(self):
        """
        Process all tasks in the queue sequentially.
        
        For each task of type 'build_module', it calls the ElephantBuilderService.
        After processing, successfully handled tasks are removed from the queue.
        """
        if not self._tasks:
            self.logger.info("TaskQueueService: No tasks to process.")
            return

        self.logger.info("TaskQueueService: Beginning processing of tasks.")
        tasks_to_remove = []

        for task in self._tasks:
            try:
                task_type = task.get("task_type")
                if task_type == "build_module":
                    module_name = task.get("module_name")
                    module_goal = task.get("module_goal")
                    self.logger.info(f"TaskQueueService: Processing build_module task for '{module_name}' with goal '{module_goal}'.")
                    
                    # Dispatch task to ElephantBuilderService
                    self.builder_service.build_single_module(module_name, module_goal)
                    tasks_to_remove.append(task)
                else:
                    self.logger.warning(f"TaskQueueService: Encountered unknown task type '{task_type}'. Skipping task.")
            except Exception as e:
                self.logger.error(f"TaskQueueService: Error processing task {task}: {e}", exc_info=True)
                # Optionally decide whether to remove or keep the task for reprocessing.

        # Remove successfully processed tasks from the queue and persist the updated list.
        if tasks_to_remove:
            self._tasks = [t for t in self._tasks if t not in tasks_to_remove]
            self.save_tasks()
            self.logger.info(f"TaskQueueService: Processed {len(tasks_to_remove)} tasks and updated the queue.")

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Return the current list of tasks in the queue."""
        return self._tasks

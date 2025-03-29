# base_agent.py

import time
import threading
import logging

logger = logging.getLogger("BaseAgent")

class BaseAgent:
    def __init__(self, name):
        self.name = name
        self.task_queue = []
        self.running = False

    def receive_task(self, task: dict):
        logger.info(f"[{self.name}] Received task: {task}")
        self.task_queue.append(task)

    def handle_task(self, task: dict):
        """
        Override in derived classes
        """
        raise NotImplementedError(f"{self.name} must implement handle_task()")

    def process_tasks(self):
        while self.task_queue:
            task = self.task_queue.pop(0)
            try:
                self.handle_task(task)
            except Exception as e:
                logger.error(f"[{self.name}] Task processing error: {e}")

    def run(self, tick_rate=1):
        logger.info(f"[{self.name}] Agent is running...")
        self.running = True
        while self.running:
            self.process_tasks()
            time.sleep(tick_rate)

    def stop(self):
        logger.info(f"[{self.name}] Stopping agent...")
        self.running = False

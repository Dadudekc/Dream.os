import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class TaskManager:
    """
    JSON-based Task / To-Do List Manager.
    Manages tasks with support for adding, completing, deleting, and listing.
    """

    def __init__(self, db_file: str = "tasks/task_list.json"):
        self.db_file = db_file
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        self.tasks: List[Dict] = []
        self._load()

    # ---------------------------
    # Private Methods
    # ---------------------------
    def _load(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
            print(f"✅ Loaded {len(self.tasks)} tasks from {self.db_file}")
        else:
            print(f"📂 No existing task list found. Starting fresh.")

    def _save(self):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, indent=4)
        print(f"💾 Task list saved: {self.db_file}")

    # ---------------------------
    # Public Methods
    # ---------------------------
    def add_task(self, description: str, tags: Optional[List[str]] = None, priority: int = 1):
        task = {
            "id": len(self.tasks) + 1,
            "description": description,
            "tags": tags or [],
            "priority": priority,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None
        }
        self.tasks.append(task)
        self._save()
        print(f"📝 Added task: {description}")

    def list_tasks(self, status_filter: Optional[str] = None):
        filtered_tasks = [t for t in self.tasks if not status_filter or t["status"] == status_filter]
        if not filtered_tasks:
            print("🚫 No tasks found.")
            return

        print(f"\n🗂 {len(filtered_tasks)} Task(s) {'(' + status_filter + ')' if status_filter else ''}:")
        for task in filtered_tasks:
            print(f"[{task['id']}] {task['description']} | Status: {task['status']} | Priority: {task['priority']}")
        print()

    def complete_task(self, task_id: int):
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            print(f"❌ Task ID {task_id} not found.")
            return

        if task["status"] == "completed":
            print(f"⚠️ Task ID {task_id} is already completed.")
            return

        task["status"] = "completed"
        task["completed_at"] = datetime.utcnow().isoformat() + "Z"
        self._save()
        print(f"✅ Task ID {task_id} marked as completed.")

    def delete_task(self, task_id: int):
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            print(f"❌ Task ID {task_id} not found.")
            return

        self.tasks.remove(task)
        self._save()
        print(f"🗑 Deleted task ID {task_id}: {task['description']}")

    def clear_completed(self):
        completed_count = len([t for t in self.tasks if t["status"] == "completed"])
        self.tasks = [t for t in self.tasks if t["status"] != "completed"]
        self._save()
        print(f"🧹 Cleared {completed_count} completed task(s).")

    def get_pending_count(self) -> int:
        pending = len([t for t in self.tasks if t["status"] == "pending"])
        print(f"📊 Pending tasks: {pending}")
        return pending

# ------------------------------------
# Example Usage
# ------------------------------------
if __name__ == "__main__":
    manager = TaskManager()

    # Add tasks
    manager.add_task("Finish DriverManager refactor", tags=["coding", "priority"], priority=1)
    manager.add_task("Run daily social post loop", tags=["automation"], priority=2)
    manager.add_task("Review pull requests", tags=["review"], priority=3)

    # List all tasks
    manager.list_tasks()

    # Complete task 1
    manager.complete_task(1)

    # List only pending tasks
    manager.list_tasks(status_filter="pending")

    # Delete task 2
    manager.delete_task(2)

    # Clear all completed tasks
    manager.clear_completed()

    # Final list
    manager.list_tasks()

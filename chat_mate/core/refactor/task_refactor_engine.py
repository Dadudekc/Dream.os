#!/usr/bin/env python3
"""
TaskRefactorEngine Module

This module performs deterministic, anchor-based refactoring based on a structured tasks.json file.
Features:
  - Processes "extract" and "replace" instructions.
  - Creates backups for modified files.
  - Previews diffs before applying changes (dry-run and interactive modes).
  - Optionally runs in dry-run (no actual file changes) or interactive mode (user approval before writing).

Usage:
    python task_refactor_engine.py --tasks path/to/tasks.json [--dry-run] [--interactive] [--backup]
"""

import json
import shutil
from pathlib import Path
import difflib
import logging
import argparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
logger = logging.getLogger("TaskRefactorEngine")


class TaskRefactorEngine:
    def __init__(self, task_file: str, dry_run: bool = False, interactive: bool = False, backup: bool = False):
        self.task_path = Path(task_file)
        if not self.task_path.exists():
            raise FileNotFoundError(f"Task file not found: {self.task_path}")
        self.dry_run = dry_run
        self.interactive = interactive
        self.backup = backup
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> list:
        with open(self.task_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "tasks" not in data:
            raise ValueError("Invalid task file: missing 'tasks' key")
        return data["tasks"]

    def run(self):
        for task in self.tasks:
            file_path = Path(task["file_path"])
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue

            original_code = file_path.read_text(encoding='utf-8')
            updated_code = original_code

            for instr in task.get("instructions", []):
                action = instr.get("type")
                if action == "extract":
                    updated_code = self._handle_extract(updated_code, instr, file_path)
                elif action == "replace":
                    updated_code = self._handle_replace(updated_code, instr)
                else:
                    logger.error(f"Unknown instruction type: {action}")
            self._apply_changes(file_path, original_code, updated_code)

    def _handle_extract(self, code: str, instr: dict, origin_file: Path) -> str:
        start = code.find(instr["anchor_start"])
        end = code.find(instr["anchor_end"])
        if start == -1 or end == -1:
            logger.warning(f"Anchors not found for extract in {origin_file.name}")
            return code

        snippet = code[start:end].strip()
        dest_path = Path(instr["destination"])
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        insert_marker = instr["insert_marker"]
        if not dest_path.exists():
            dest_path.write_text(f"{insert_marker}\n\n", encoding='utf-8')

        dest_code = dest_path.read_text(encoding='utf-8')
        new_dest_code = dest_code.replace(insert_marker, f"{insert_marker}\n\n{snippet}\n")
        self._apply_changes(dest_path, dest_code, new_dest_code, file_label=f"Extract -> {dest_path.name}")

        logger.info(f"[✂️ EXTRACT] → {dest_path.name}")
        # Remove the extracted block from the origin code
        return code[:start].rstrip() + "\n\n" + code[end:].lstrip()

    def _handle_replace(self, code: str, instr: dict) -> str:
        anchor = instr["anchor"]
        if anchor not in code:
            logger.warning(f"Anchor not found for replace: {anchor}")
            return code
        return code.replace(anchor, instr["content"])

    def _apply_changes(self, file_path: Path, original: str, updated: str, file_label: str = None):
        """
        Shows a diff preview and applies changes if not in dry-run mode.
        In interactive mode, asks for confirmation.
        Also makes a backup if enabled.
        """
        file_label = file_label or file_path.name

        if original == updated:
            logger.info(f"[ℹ️ NO CHANGE] {file_label} remains unchanged.")
            return

        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"{file_label} (original)",
            tofile=f"{file_label} (updated)",
        )
        diff_text = "".join(diff)
        logger.info(f"Diff for {file_label}:\n{diff_text}")

        if self.interactive:
            confirm = input(f"Apply changes to {file_label}? [y/N]: ").strip().lower()
            if confirm != "y":
                logger.info(f"Skipping changes for {file_label}.")
                return

        if self.dry_run:
            logger.info(f"[DRY-RUN] Not applying changes to {file_label}.")
        else:
            if self.backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                shutil.copy2(file_path, backup_path)
                logger.info(f"Backup created at: {backup_path}")

            file_path.write_text(updated, encoding='utf-8')
            logger.info(f"[✅ APPLIED] Changes written to {file_label}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TaskRefactorEngine - Run anchor-based file transformations")
    parser.add_argument("--tasks", type=str, required=True, help="Path to the tasks.json file")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing to files")
    parser.add_argument("--interactive", action="store_true", help="Ask for confirmation before each change")
    parser.add_argument("--backup", action="store_true", help="Create a backup of each file before applying changes")
    args = parser.parse_args()

    engine = TaskRefactorEngine(
        task_file=args.tasks,
        dry_run=args.dry_run,
        interactive=args.interactive,
        backup=args.backup,
    )
    engine.run()

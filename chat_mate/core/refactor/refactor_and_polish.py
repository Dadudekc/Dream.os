#!/usr/bin/env python3
"""
Refactor and Polish Module

This module integrates the TaskRefactorEngine with the OpenAIPromptEngine.
It first runs anchor-based refactoring on your codebase using a tasks.json file,
and then (optionally) uses OpenAIPromptEngine to polish the refactored code.
The polishing phase is driven by a Jinja2 template and executed via a custom GPT endpoint.

Usage:
    python refactor_and_polish.py --tasks path/to/tasks.json --polish-template polish_template.j2 [--dry-run] [--interactive] [--backup]
"""

import argparse
import logging
import os

# Import your deterministic refactoring engine
from core.refactor.task_refactor_engine import TaskRefactorEngine

# Import Selenium and your OpenAIPromptEngine
from selenium import webdriver
from core.OpenAIPromptEngine import OpenAIPromptEngine

logger = logging.getLogger("RefactorAndPolish")
logger.setLevel(logging.INFO)

def main():
    parser = argparse.ArgumentParser(description="Integrate TaskRefactorEngine with OpenAIPromptEngine polishing")
    parser.add_argument("--tasks", type=str, required=True, help="Path to the tasks.json file")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run for refactoring (no file changes)")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode for refactoring (ask confirmation)")
    parser.add_argument("--backup", action="store_true", help="Create backups before applying changes")
    parser.add_argument("--polish-template", type=str, help="Jinja2 template for polishing the refactored code")
    parser.add_argument("--target-file", type=str, help="File to polish after refactoring (required if --polish-template is set)")
    args = parser.parse_args()

    # Run the TaskRefactorEngine for deterministic code refactoring
    logger.info("Starting TaskRefactorEngine refactoring...")
    refactor_engine = TaskRefactorEngine(
        task_file=args.tasks,
        dry_run=args.dry_run,
        interactive=args.interactive,
        backup=args.backup,
    )
    refactor_engine.run()
    logger.info("Refactoring complete.")

    # If a polishing template is provided, run the OpenAIPromptEngine to polish the code.
    if args.polish_template:
        if not args.target_file:
            logger.error("--target-file is required when --polish-template is specified.")
            return

        # Set up Selenium driver (customize for your browser/driver as needed)
        logger.info("Launching Selenium driver for AI polishing...")
        driver = webdriver.Chrome()  # Ensure your webdriver is correctly set up in PATH
        try:
            prompt_engine = OpenAIPromptEngine(driver)

            # Read the content of the target refactored file
            target_path = args.target_file
            if not os.path.exists(target_path):
                logger.error(f"Target file for polishing not found: {target_path}")
                return

            with open(target_path, "r", encoding="utf-8") as f:
                code_content = f.read()

            # Prepare a memory state (you can expand this to include additional metadata)
            memory_state = {"code": code_content}

            # Execute the polishing prompt
            logger.info(f"Polishing code in {target_path} using template '{args.polish_template}'...")
            polished_code = prompt_engine.execute(
                template_name=args.polish_template,
                memory_state=memory_state,
                additional_context="Polish and optimize the refactored code.",
                metadata={"file": target_path}
            )

            if polished_code:
                # Optionally, create a backup before polishing
                backup_path = target_path + ".polish.bak"
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(code_content)
                logger.info(f"Backup of original polished file created at {backup_path}")

                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(polished_code)
                logger.info(f"Polished code written to {target_path}")
            else:
                logger.error("Polishing did not return any content.")

        except Exception as e:
            logger.error(f"Error during polishing: {e}")
        finally:
            driver.quit()
            logger.info("Selenium driver closed.")

if __name__ == "__main__":
    main()

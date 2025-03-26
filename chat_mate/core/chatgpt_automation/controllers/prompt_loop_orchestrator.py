import json
import logging
import os
from pathlib import Path
from time import sleep

# Assume our AutomationEngine is already implemented and imported
from core.chatgpt_automation.automation_engine import AutomationEngine

logger = logging.getLogger(__name__)

class PromptLoopOrchestrator:
    """
    Manages context injection into prompts and orchestrates a loop
    that sends combined prompts to ChatGPT and handles the responses.
    
    This layer is part of Full Sync Mode.
    """
    def __init__(self, context_file: str = "chatgpt_project_context.json"):
        """
        Initialize the orchestrator with project context.
        
        Args:
            context_file (str): Path to the exported project context.
        """
        self.context_file = Path(context_file)
        self.context = self._load_context()
        # Instantiate AutomationEngine (or inject an instance if available)
        self.engine = AutomationEngine(use_local_llm=True, model_name="mistral", beta_mode=True)
        logger.info("PromptLoopOrchestrator initialized.")

    def _load_context(self):
        """Load the project context from a JSON file."""
        if self.context_file.exists():
            try:
                with open(self.context_file, "r", encoding="utf-8") as f:
                    context = json.load(f)
                logger.info(f"Loaded project context from {self.context_file}")
                return context
            except Exception as e:
                logger.error(f"Error loading context: {e}")
                return {}
        else:
            logger.warning(f"Context file {self.context_file} does not exist.")
            return {}

    def inject_context(self, user_prompt: str) -> str:
        """
        Injects project context into a user prompt.
        
        Args:
            user_prompt (str): The base prompt/command from the user.
            
        Returns:
            str: The combined prompt with context.
        """
        # For example, append a summary of the project context
        context_summary = f"Project Root: {self.context.get('project_root', 'N/A')}\n" \
                          f"Files Analyzed: {self.context.get('num_files_analyzed', 0)}\n"
        # You can expand this to include specific module summaries or insights
        combined_prompt = f"{user_prompt}\n\nContext:\n{context_summary}\n"
        logger.debug(f"Combined prompt: {combined_prompt[:100]}{'...' if len(combined_prompt) > 100 else ''}")
        return combined_prompt

    def orchestrate_prompt_loop(self, user_prompt: str, iterations: int = 1, delay: float = 2.0):
        """
        Runs a prompt loop: injects context, sends prompt, processes response,
        and can optionally iterate (simulate a feedback loop).
        
        Args:
            user_prompt (str): The initial command/prompt from the user.
            iterations (int): Number of iterations for the loop.
            delay (float): Delay in seconds between iterations.
        """
        current_prompt = self.inject_context(user_prompt)
        for i in range(iterations):
            logger.info(f"Sending prompt (Iteration {i+1}/{iterations})...")
            try:
                response = self.engine.get_chatgpt_response(current_prompt)
                logger.info(f"Response received (Iteration {i+1}): {response[:200]}{'...' if len(response)>200 else ''}")
                # Optionally, update context or current_prompt based on response
                # For now, we simply iterate with the same prompt.
            except Exception as e:
                logger.error(f"Error in prompt loop iteration {i+1}: {e}")
            sleep(delay)

# Example usage:
if __name__ == "__main__":
    # In production, this would be triggered via a GUI button or voice command.
    orchestrator = PromptLoopOrchestrator(context_file="chatgpt_project_context.json")
    user_command = input("Enter your prompt command: ").strip()
    orchestrator.orchestrate_prompt_loop(user_command, iterations=3, delay=3)

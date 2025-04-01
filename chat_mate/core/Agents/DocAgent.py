from typing import Dict, Any
from core.Agents.CursorAgentInterface import CursorAgentInterface

class DocAgent(CursorAgentInterface):
    """Agent for handling documentation generation tasks."""
    
    def run_task(self, prompt_template: str, target_file: str) -> Dict[str, Any]:
        """Run a documentation generation task."""
        self._log_task_start("DocGeneration", target_file)
        
        # Format the prompt
        prompt = self._format_prompt(prompt_template, file=target_file)
        
        # Log the prompt for manual execution
        self.logger.log_debug(f"Documentation generation prompt for {target_file}:\n{prompt}")
        
        # TODO: When Cursor API is available, automate this
        print("\n=== Cursor Documentation Generation Prompt ===\n")
        print(prompt)
        print("\n=== End Prompt ===\n")
        
        # Return pseudo-result
        result = {
            "status": "completed",
            "file": target_file,
            "prompt": prompt,
            "metrics": {
                "doc_coverage": 0.0,  # To be calculated
                "methods_documented": 0,  # To be calculated
                "examples_generated": 0  # To be calculated
            }
        }
        
        self._log_task_complete("DocGeneration", target_file, result)
        return result
        
    def generate_docs(self, target_file: str) -> Dict[str, Any]:
        """Run a standard documentation generation task."""
        prompt_template = """
TASK: Generate comprehensive documentation for the following module.
MODE: DOCUMENTATION MODE

CONSTRAINTS:
- Follow Google-style docstrings
- Include usage examples
- Document all public methods
- Add type hints
- Generate API documentation
- Include error handling examples

INPUT FILE:
{file}

OUTPUT:
1. Module docstring
2. Method docstrings
3. Usage examples
4. API documentation
5. Git commit message
"""
        return self.run_task(prompt_template, target_file) 

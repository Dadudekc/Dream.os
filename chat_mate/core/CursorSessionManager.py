import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

class CursorSessionManager:
    """
    Manages a Cursor IDE session using Selenium WebDriver.
    Handles interactions like executing prompts and retrieving generated code.
    """
    
    VALID_MODES = ["full_sync", "tdd", "async", "repl"]
    
    def __init__(self, config, memory_manager):
        """
        Initialize the Cursor Session Manager.
        
        Args:
            config (dict): Configuration settings
            memory_manager: Memory manager for storing and retrieving context
        """
        self.config = config
        self.memory_manager = memory_manager
        self.execution_mode = config.get("execution_mode", "full_sync")
        
        # Initialize Chrome driver with headless options if specified
        chrome_options = Options()
        if config.get("headless", False):
            chrome_options.add_argument("--headless")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            # Open Cursor IDE URL if provided in config
            cursor_url = config.get("cursor_url", "https://cursor.sh")
            self.driver.get(cursor_url)
            print("[CursorSessionManager] Successfully initialized Chrome WebDriver.")
        except Exception as e:
            print(f"[CursorSessionManager] Failed to initialize Chrome WebDriver: {e}")
            self.driver = None
    
    def switch_mode(self, mode):
        """
        Switch the execution mode.
        
        Args:
            mode (str): The mode to switch to (full_sync, tdd, async, repl)
        """
        if mode in self.VALID_MODES:
            self.execution_mode = mode
        else:
            print("[CursorSessionManager] Invalid mode.")
    
    def generate_prompt(self, task, ltm_context=None, scraper_insights=None):
        """
        Generate a prompt based on the current execution mode.
        
        Args:
            task (str): The task to be executed
            ltm_context (list): Context from long-term memory
            scraper_insights (list): Insights from code scraper
            
        Returns:
            str: The generated prompt
        """
        if ltm_context is None:
            ltm_context = []
        if scraper_insights is None:
            scraper_insights = []
        
        # Base prompt structure
        prompt = f"# TASK: {task}\n\n"
        
        # Add context if available
        if ltm_context:
            prompt += "## CONTEXT\n"
            for context_item in ltm_context:
                prompt += f"{context_item}\n"
            prompt += "\n"
        
        # Add code insights if available
        if scraper_insights:
            prompt += "## CODE INSIGHTS\n"
            for insight in scraper_insights:
                prompt += f"- {insight.get('summary', '')}\n"
                if 'code' in insight:
                    prompt += f"```\n{insight['code']}\n```\n"
            prompt += "\n"
        
        # Mode-specific instructions
        prompt += "## MODE-SPECIFIC INSTRUCTIONS\n"
        
        if self.execution_mode == "full_sync":
            prompt += "- Prioritize rapid development\n"
            prompt += "- Implement comprehensive solution\n"
            prompt += "- Include error handling\n"
        elif self.execution_mode == "tdd":
            prompt += "- Follow Red-Green-Refactor cycle\n"
            prompt += "- Write test cases first\n"
            prompt += "- Focus on test coverage\n"
        elif self.execution_mode == "async":
            prompt += "- Implement asynchronous patterns\n"
            prompt += "- Use async/await when appropriate\n"
            prompt += "- Handle concurrency carefully\n"
        elif self.execution_mode == "repl":
            prompt += "- Generate code that can be executed in a REPL\n"
            prompt += "- Focus on immediate feedback\n"
            prompt += "- Include examples and expected output\n"
        
        return prompt
    
    def execute_prompt(self, prompt):
        """
        Execute a prompt in Cursor IDE and return the generated code.
        
        Args:
            prompt (str): The prompt to execute
            
        Returns:
            str: The generated code or None if execution failed
        """
        if not self.driver:
            print("[CursorSessionManager] WebDriver not initialized.")
            return None
        
        try:
            # Find the prompt input element
            prompt_input = self.driver.find_element(By.CSS_SELECTOR, "textarea.ai-input")
            
            # Clear existing content and enter new prompt
            prompt_input.clear()
            prompt_input.send_keys(prompt)
            prompt_input.send_keys(Keys.CONTROL + Keys.ENTER)
            
            # Wait for the response to be generated
            time.sleep(self.config.get("response_timeout", 10))
            
            # Extract generated code
            code_elements = self.driver.find_elements(By.CSS_SELECTOR, ".generated-code pre")
            generated_code = "\n".join([element.text for element in code_elements])
            
            return generated_code
        except Exception as e:
            print(f"[CursorSessionManager] Failed to execute prompt: {e}")
            return None
    
    def close(self):
        """
        Close the WebDriver session.
        """
        if self.driver:
            self.driver.quit()
            print("[CursorSessionManager] WebDriver session closed.") 

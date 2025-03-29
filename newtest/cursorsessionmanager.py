import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

class CursorSessionManager:
    def __init__(self, config, memory_manager):
        self.execution_mode = config["execution_mode"]
        self.memory_manager = memory_manager
        self.driver = self._start_cursor_session()

    def _start_cursor_session(self):
        # Launch or attach to Cursor IDE (as webapp or local app via webdriver)
        # If web version available, specify the path; otherwise use desktop automation
        options = webdriver.ChromeOptions()
        options.add_argument("--remote-debugging-port=9222")  # DevTools Protocol Port
        driver = webdriver.Chrome(options=options)
        driver.get("http://localhost:3000")  # Example local server port for Cursor; adjust as needed
        time.sleep(3)
        print("[CursorSessionManager] Cursor IDE session started.")
        return driver

    def switch_mode(self, mode):
        if mode not in ["full_sync", "tdd"]:
            print("[CursorSessionManager] Invalid mode.")
            return
        self.execution_mode = mode
        print(f"[CursorSessionManager] Switched to {mode.upper()} mode.")

    def generate_prompt(self, task, ltm_context, scraper_insights):
        prompt = f"# TASK: {task}\n"

        if ltm_context:
            prompt += "\n# Previous Context:\n"
            for doc in ltm_context:
                prompt += f"{doc}\n"

        if scraper_insights:
            prompt += "\n# Scraper Insights:\n"
            for insight in scraper_insights:
                prompt += f"{insight['summary']}\n{insight['code']}\n"

        prompt += "\n# Instructions:\n"
        if self.execution_mode == "tdd":
            prompt += "- Follow Red-Green-Refactor cycle.\n- Start by writing failing tests.\n"
        else:
            prompt += "- Prioritize rapid development. Use existing modules when possible.\n"

        return prompt

    def execute_prompt(self, prompt):
        print(f"\n[CursorSessionManager] Executing prompt in {self.execution_mode.upper()} mode...")

        # Locate Cursor AI prompt interface and input the prompt
        try:
            prompt_input = self.driver.find_element(By.CSS_SELECTOR, "textarea.ai-input")  # Adjust selector!
            prompt_input.clear()
            prompt_input.send_keys(prompt)
            time.sleep(1)
            prompt_input.send_keys(Keys.RETURN)

            # Wait for response generation
            time.sleep(5)  # Wait for Cursor to generate code (optimize with smarter waits)

            # Retrieve the generated code (this may need DevTools API if DOM doesn’t expose it directly)
            generated_code_elements = self.driver.find_elements(By.CSS_SELECTOR, ".generated-code")  # Adjust selector!
            generated_code = "\n".join([element.text for element in generated_code_elements])

            print("[CursorSessionManager] Retrieved AI-generated code successfully.")
            return generated_code

        except Exception as e:
            print(f"[CursorSessionManager] Error during prompt execution: {e}")
            return None
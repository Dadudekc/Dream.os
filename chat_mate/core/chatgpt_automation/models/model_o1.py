"""
Model O1 Handler Plugin

Handles prompt construction and response retrieval for O1 model.
Relies on chatgpt_driver for communication.

✅ Drop this file into the /models directory.
✅ AutomationEngine will auto-load this model.
"""

def process_with_o1(driver, file_content):
    """
    Sends file content to O1 model with a focus on fast reasoning,
    basic modularization, and lightweight optimization.

    Args:
        driver: Selenium WebDriver instance
        file_content: The Python code to refactor (as string)

    Returns:
        The refactored and optimized code returned by ChatGPT O1
    """
    prompt = (
        """
        You are O1, an ultra-lightweight AI designed for quick refactoring and optimization.

        Your mission:
        1. Refactor the provided Python code to enhance clarity and performance.
        2. Maintain simple modular structure while ensuring PEP8 compliance.
        3. Optimize where possible, but prioritize speed over deep reasoning.

        ⚠️ Return ONLY valid Python code. No explanations, comments, or markdown formatting.

        Code to refactor and optimize:


        """ + file_content + """
        """
    )

    print("[O1] Sending prompt to ChatGPT O1...")

    # Inline import to avoid circular dependencies
    from chatgpt_automation.OpenAIClient import get_chatgpt_response

    # Send prompt directly to O1 model endpoint
    response = get_chatgpt_response(driver, prompt, model_url="https://chatgpt.com/?model=o1")

    print("[O1] Received response from ChatGPT O1.")
    return response

def register():
    """
    Registers the O1 model plugin for use in the AutomationEngine.

    Returns:
        dict: {
            "name": Model identifier string,
            "threshold": Line count threshold for this model,
            "handler": The function to invoke for processing,
            "endpoint": Optional model-specific URL (for reference)
        }
    """
    return {
        "name": "O1",                               # Unique model name
        "threshold": 800,                            
        "handler": process_with_o1,
        "endpoint": "https://chatgpt.com/?model=o1"
    }

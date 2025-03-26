"""
Model O3-Mini-High Handler Plugin

Handles prompt construction and response retrieval for O3-Mini-High model.
Relies on chatgpt_driver for communication.

✅ Drop this file into the /models directory.
✅ AutomationEngine will auto-load this model.
"""

def process_with_o3_mini_high(driver, file_content):
    """
    Sends file content to O3-Mini-High model with a focus on higher reasoning
    and optimized modular architecture.

    Args:
        driver: Selenium WebDriver instance
        file_content: The Python code to refactor (as string)

    Returns:
        The refactored and optimized code returned by ChatGPT O3-Mini-High
    """
    prompt = (
        """
        You are O3-Mini-High, an advanced AI focused on delivering highly optimized,
        modular, and scalable Python code.

        Your task:
        1. Refactor and optimize the provided Python code.
        2. Enhance modularity, scalability, and performance.
        3. Ensure the code follows PEP8 standards and clean architecture principles.
        4. Remove any redundant or unnecessary logic, compress where possible without sacrificing clarity.

        ⚠️ Important: Return ONLY valid Python code without explanations, comments, or markdown.

        Code to refactor and optimize:


        """ + file_content + """
        """
    )

    print("[O3-Mini-High] Sending prompt to ChatGPT O3-Mini-High...")

    # Inline import to avoid circular dependencies
    from chatgpt_automation.OpenAIClient import get_chatgpt_response

    # Send prompt directly to O3-Mini-High model endpoint
    response = get_chatgpt_response(driver, prompt, model_url="https://chatgpt.com/?model=o3-mini-high")

    print("[O3-Mini-High] Received response from ChatGPT O3-Mini-High.")
    return response

def register():
    """
    Registers the O3-Mini-High model plugin for use in the AutomationEngine.

    Returns:
        dict: {
            "name": Model identifier string,
            "threshold": Line count threshold for this model,
            "handler": The function to invoke for processing,
            "endpoint": Optional model-specific URL (for reference)
        }
    """
    return {
        "name": "O3-Mini-High",                     # Unique model name
        "threshold": 500,                           # Example: Use this for files >= 300 lines
        "handler": process_with_o3_mini_high,
        "endpoint": "https://chatgpt.com/?model=o3-mini-high"
    }

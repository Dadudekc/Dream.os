"""
Model GPT-4o Mini Handler Plugin

Handles prompt construction and response retrieval for GPT-4o Mini model.
Relies on chatgpt_driver for communication.

✅ Drop this file into the /models directory.
✅ AutomationEngine will auto-load this model.
"""

def process_with_gpt4o_mini(driver, file_content):
    """
    Sends file content to GPT-4o Mini model with a focus on fast processing,
    lightweight reasoning, and efficient modular optimization.

    Args:
        driver: Selenium WebDriver instance
        file_content: The Python code to refactor (as string)

    Returns:
        The refactored and optimized code returned by ChatGPT GPT-4o Mini
    """
    prompt = (
        """
        You are GPT-4o Mini, a high-speed AI designed for efficient and effective
        code refactoring.

        Your tasks:
        1. Refactor the following Python code for clarity and performance.
        2. Optimize for lightweight, modular design while ensuring PEP8 compliance.
        3. Eliminate redundant logic and improve readability.

        ⚠️ Return ONLY valid Python code without explanations, comments, or markdown formatting.

        Code to refactor and optimize:


        """ + file_content + """
        """
    )

    print("[GPT-4o Mini] Sending prompt to ChatGPT GPT-4o Mini...")

    # Inline import to avoid circular dependencies
    from chatgpt_automation.OpenAIClient import get_chatgpt_response

    # Send prompt directly to GPT-4o Mini model endpoint
    response = get_chatgpt_response(driver, prompt, model_url="https://chatgpt.com/?model=gpt-4o-mini")

    print("[GPT-4o Mini] Received response from ChatGPT GPT-4o Mini.")
    return response

def register():
    """
    Registers the GPT-4o Mini model plugin for use in the AutomationEngine.

    Returns:
        dict: {
            "name": Model identifier string,
            "threshold": Line count threshold for this model,
            "handler": The function to invoke for processing,
            "endpoint": Optional model-specific URL (for reference)
        }
    """
    return {
        "name": "GPT-4o Mini",                    # Unique model name
        "threshold": 100,                         # Files >= 100 lines (adjust as needed)
        "handler": process_with_gpt4o_mini,
        "endpoint": "https://chatgpt.com/?model=gpt-4o-mini"
    }

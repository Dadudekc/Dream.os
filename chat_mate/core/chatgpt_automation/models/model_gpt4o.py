"""
Model GPT-4o Handler Plugin

Handles prompt construction and response retrieval for GPT-4o model.
Relies on chatgpt_driver for communication.

✅ Drop this file into the /models directory.
✅ AutomationEngine will auto-load this model.
"""

def process_with_gpt4o(driver, file_content):
    """
    Sends file content to GPT-4o model with focus on advanced reasoning,
    best-practice architecture, and clean code optimization.

    Args:
        driver: Selenium WebDriver instance
        file_content: The Python code to refactor (as string)

    Returns:
        The refactored and optimized code returned by ChatGPT GPT-4o
    """
    prompt = (
        """
        You are GPT-4o, an advanced AI specialized in:
        - Deep code reasoning and optimization.
        - Clean architecture and modular design.
        - Scalability, readability, and performance.

        Your task:
        1. Refactor the following Python code.
        2. Eliminate redundancies and simplify logic where possible.
        3. Ensure PEP8 compliance and best practices.
        4. Preserve functionality but improve efficiency and scalability.

        ⚠️ ONLY return clean, executable Python code. No commentary, no markdown.

        Code to refactor and optimize:


        """ + file_content + """
        """
    )

    print("[GPT-4o] Sending prompt to ChatGPT GPT-4o...")

    # Inline import to avoid circular dependencies
    from chatgpt_automation.OpenAIClient import get_chatgpt_response

    # Send prompt directly to GPT-4o model endpoint
    response = get_chatgpt_response(driver, prompt, model_url="https://chatgpt.com/?model=gpt-4o")

    print("[GPT-4o] Received response from ChatGPT GPT-4o.")
    return response

def register():
    """
    Registers the GPT-4o model plugin for use in the AutomationEngine.

    Returns:
        dict: {
            "name": Model identifier string,
            "threshold": Line count threshold for this model,
            "handler": The function to invoke for processing,
            "endpoint": Optional model-specific URL (for reference)
        }
    """
    return {
        "name": "GPT-4o",             # Unique model name (must match select_model logic)
        "threshold": 200,             # Use GPT-4o for files >= 500 lines (or whatever you want)
        "handler": process_with_gpt4o,
        "endpoint": "https://chatgpt.com/?model=gpt-4o"  # Optional, for future use
    }

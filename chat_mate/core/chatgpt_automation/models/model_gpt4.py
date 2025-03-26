"""
Model GPT-4 Handler Plugin

Handles prompt construction and response retrieval for GPT-4 model.
Relies on chatgpt_driver for communication.

✅ Drop this file into the /models directory.
✅ AutomationEngine will auto-load this model.
"""

def process_with_gpt4(driver, file_content):
    """
    Sends file content to GPT-4 model with a focus on advanced reasoning,
    precision refactoring, and scalable architecture.

    Args:
        driver: Selenium WebDriver instance
        file_content: The Python code to refactor (as string)

    Returns:
        The refactored and optimized code returned by ChatGPT GPT-4
    """
    prompt = (
        """
        You are GPT-4, a highly capable AI model focused on advanced code refactoring.

        Your objectives:
        1. Refactor and optimize the provided Python code.
        2. Prioritize modularity, scalability, and clean architecture.
        3. Eliminate redundancy, improve readability, and ensure maintainability.
        4. Apply PEP8 coding standards without compromising clarity.

        ⚠️ Return ONLY valid Python code. No explanations or markdown formatting.

        Code to refactor and optimize:


        """ + file_content + """
        """
    )

    print("[GPT-4] Sending prompt to ChatGPT GPT-4...")

    # Inline import to avoid circular dependencies
    from chatgpt_automation.OpenAIClient import get_chatgpt_response

    # Send prompt directly to GPT-4 model endpoint
    response = get_chatgpt_response(driver, prompt, model_url="https://chatgpt.com/?model=gpt-4")

    print("[GPT-4] Received response from ChatGPT GPT-4.")
    return response

def register():
    """
    Registers the GPT-4 model plugin for use in the AutomationEngine.

    Returns:
        dict: {
            "name": Model identifier string,
            "threshold": Line count threshold for this model,
            "handler": The function to invoke for processing,
            "endpoint": Optional model-specific URL (for reference)
        }
    """
    return {
        "name": "GPT-4",                        # Unique model name
        "threshold": 50,                       # Use GPT-4 for files >= 600 lines (adjustable)5
        "handler": process_with_gpt4,
        "endpoint": "https://chatgpt.com/?model=gpt-4"
    }

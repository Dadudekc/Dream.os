"""
Model GPT-4.5 Handler Plugin

Handles prompt construction and response retrieval for GPT-4.5 model.
Relies on chatgpt_driver for communication.

✅ Drop this file into the /models directory.
✅ AutomationEngine will auto-load this model.
"""

def process_with_gpt4_5(driver, file_content):
    """
    Sends file content to GPT-4.5 model with emphasis on precision refactoring,
    optimization, and large-scale code architecture.

    Args:
        driver: Selenium WebDriver instance
        file_content: The Python code to refactor (as string)

    Returns:
        The refactored and optimized code returned by ChatGPT GPT-4.5
    """
    prompt = (
        """
        You are GPT-4.5, a cutting-edge AI engineered for large-scale,
        highly optimized code refactoring and architecture design.

        Your tasks:
        1. Refactor the provided Python code to follow enterprise-grade clean architecture principles.
        2. Eliminate all redundant logic, ensuring concise and scalable code.
        3. Prioritize modularity, maintainability, and performance.
        4. Ensure PEP8 compliance and readability without compromising complexity.

        ⚠️ Return ONLY clean Python code. No explanations, comments, or markdown formatting.

        Code to refactor and optimize:


        """ + file_content + """
        """
    )

    print("[GPT-4.5] Sending prompt to ChatGPT GPT-4.5...")

    # Inline import to avoid circular dependencies
    from chatgpt_automation.OpenAIClient import get_chatgpt_response

    # Send prompt directly to GPT-4.5 model endpoint
    response = get_chatgpt_response(driver, prompt, model_url="https://chatgpt.com/?model=gpt-4-5")

    print("[GPT-4.5] Received response from ChatGPT GPT-4.5.")
    return response

def register():
    """
    Registers the GPT-4.5 model plugin for use in the AutomationEngine.

    Returns:
        dict: {
            "name": Model identifier string,
            "threshold": Line count threshold for this model,
            "handler": The function to invoke for processing,
            "endpoint": Optional model-specific URL (for reference)
        }
    """
    return {
        "name": "GPT-4.5",                       # Unique model name
        "threshold": 750,                        # Use GPT-4.5 for large files (adjust as needed)
        "handler": process_with_gpt4_5,
        "endpoint": "https://chatgpt.com/?model=gpt-4-5"
    }

"""
Model Plugin Template

- Each plugin MUST implement:
    1. process_with_<model_name>(driver, file_content)
    2. register() returning: { "name", "threshold", "handler", "endpoint" }

✅ Drop this file into the /models directory.
✅ AutomationEngine auto-loads this model.
"""

import requests

# Example Process Function
def process_with_template(driver, file_content):
    """
    Process the file content using this model's strategy.

    Args:
        driver: The Selenium WebDriver instance.
        file_content: The raw string content of the Python file.

    Returns:
        str: The refactored or processed code as a string.
    """
    prompt = (
        f"Refactor this Python file according to best practices and efficiency:\n\n"
        f"{file_content}"
    )

    # You may import get_chatgpt_response inline to avoid circular imports
    from chatgpt_automation.OpenAIClient import get_chatgpt_response

    # Send the prompt to ChatGPT (or any LLM you are using)
    response = get_chatgpt_response(driver, prompt)

    # --- Send the response to a designated endpoint ---
    # The endpoint URL is defined in the register() output (see below)
    endpoint = register().get("endpoint")
    if endpoint:
        try:
            payload = {"response": response}
            r = requests.post(endpoint, json=payload)
            r.raise_for_status()
            print(f"[Template-Model] Successfully sent response to endpoint: {endpoint}")
        except Exception as e:
            print(f"[Template-Model] Failed to send response to endpoint {endpoint}: {e}")
    else:
        print("[Template-Model] No endpoint configured; skipping POST request.")

    return response

# Required register() function for discovery by AutomationEngine
def register():
    """
    Register this model in the AutomationEngine's model registry.

    Returns:
        dict: {
            "name": (str) model name,
            "threshold": (int) minimum line count for this model,
            "handler": (callable) function to process the file,
            "endpoint": (str) URL where the processed response will be sent.
        }
    """
    return {
        "name": "Template-Model",              # Unique model name (must be string)
        "threshold": 100,                      # Example: 100 line minimum
        "handler": process_with_template,      # Function to process the file
        "endpoint": "https://chatgpt.com/?model=template-model"  # Endpoint to send response
    }

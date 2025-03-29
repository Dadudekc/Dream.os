import requests

"""
Model O3-Mini Handler Plugin

Handles prompt construction and response retrieval for O3-mini model.
Relies on chatgpt_driver for communication.

✅ Drop this file into the /models directory.
✅ AutomationEngine will auto-load this model.
"""

def process_with_o3mini(driver, file_content):
    """
    Sends file content to the O3-mini model for code optimization.
    After retrieving the response from ChatGPT, it sends the result to the
    designated endpoint: https://chatgpt.com/?model=o3-mini

    Args:
        driver: Selenium WebDriver instance.
        file_content: The Python code to refactor (as string).

    Returns:
        The refactored and optimized code returned by ChatGPT O3-mini.
    """
    prompt = (
        """
        You are O3-mini, an advanced AI engineered for high-performance code optimization.

        Your task:
        - Refactor and optimize the following Python code.
        - Maximize efficiency, modularity, and readability.
        - Improve scalability and follow clean architecture best practices.
        - Ensure no redundant logic, compress where possible without losing clarity.
        - Return ONLY valid Python code without any extra commentary or explanations.

        Code to refactor and optimize:
        
        
        """ + file_content + """
        """
    )

    print("[O3-mini] Sending prompt to ChatGPT O3-mini...")

    # Inline import to avoid circular dependency issues
    from chatgpt_automation.OpenAIClient import get_chatgpt_response
    response = get_chatgpt_response(driver, prompt)

    print("[O3-mini] Received response from ChatGPT O3-mini.")

    # Send the response to the designated endpoint.
    endpoint = "https://chatgpt.com/?model=o3-mini"
    try:
        payload = {"response": response}
        r = requests.post(endpoint, json=payload)
        r.raise_for_status()
        print(f"[O3-mini] Successfully sent response to endpoint: {endpoint}")
    except Exception as e:
        print(f"[O3-mini] Failed to send response to endpoint {endpoint}: {e}")

    return response

def register():
    """
    Registers the O3-mini model plugin for use in the AutomationEngine.

    Returns:
        dict: {
            "name": Model identifier string,
            "threshold": Line count threshold for this model,
            "handler": The function to invoke for processing,
            "endpoint": The endpoint URL for this model
        }
    """
    return {
        "name": "O3-mini",          # Unique model name (must match select_model logic)
        "threshold": 400,           # Use this model when files are >= 200 lines
        "handler": process_with_o3mini,
        "endpoint": "https://chatgpt.com/?model=o3-mini"
    }

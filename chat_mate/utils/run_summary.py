import os
import json
from datetime import datetime


def generate_full_run_json(chat_title: str,
                           chat_link: str,
                           chat_responses: list,
                           run_metadata: dict,
                           output_dir: str) -> None:
    """
    Generates a `full_run.json` summary for a chat prompt cycle execution.

    Args:
        chat_title (str): The title of the chat.
        chat_link (str): URL link to the chat.
        chat_responses (list): A list of responses with metadata for each prompt.
        run_metadata (dict): Metadata about this run (model, timestamps, etc.).
        output_dir (str): Directory to save the run summary.
    """
    if not chat_title:
        raise ValueError("Chat title cannot be empty.")

    # Prepare the summary data structure
    summary_data = {
        "chat_title": chat_title,
        "chat_link": chat_link,
        "execution_timestamp": datetime.now().isoformat(),
        "run_metadata": run_metadata,
        "responses": chat_responses
    }

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Build the full path to the JSON file
    sanitized_title = sanitize_filename(chat_title)
    output_file = os.path.join(output_dir, f"{sanitized_title}_full_run.json")

    # Write the JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Full run JSON saved: {output_file}")
    except Exception as e:
        print(f"❌ Failed to write full_run.json for chat '{chat_title}': {e}")


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes filenames by removing/replacing problematic characters.

    Args:
        filename (str): The raw filename string.

    Returns:
        str: A sanitized filename string safe for filesystem usage.
    """
    import re
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", filename)
    return sanitized.strip().replace(" ", "_")[:50]


# Optional standalone test run
if __name__ == "__main__":
    # Quick functional test
    chat_title = "Test Chat Example"
    chat_link = "https://chat.openai.com/c/123456"
    chat_responses = [
        {
            "prompt_name": "dreamscape",
            "prompt_text": "Generate the next Dreamscape episode.",
            "response": "Episode 1: The Awakening...",
            "timestamp": datetime.now().isoformat(),
            "ai_observations": {
                "victor_tactics_used": ["Pattern recognition"],
                "adaptive_executions": ["Refined pipeline sequence"]
            }
        }
    ]
    run_metadata = {
        "timestamp": datetime.now().isoformat(),
        "model": "gpt-4o",
        "chat_count": 1,
        "execution_time": "5.23s",
        "bottlenecks": []
    }
    output_dir = "./test_outputs"

    generate_full_run_json(chat_title, chat_link, chat_responses, run_metadata, output_dir)

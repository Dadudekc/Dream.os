# main.py

import time
from AgentDispatcher import AgentDispatcher
import sys
import os

# Append the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from chat_mate_config import Config


from chat_mate_config import Config

if __name__ == "__main__":
    config = Config("config.json")
    dispatcher = AgentDispatcher(config)

    try:
        dispatcher.start()

        # Sample tasks
        dispatcher.add_task({"action": "scrape_chats"})
        time.sleep(3)

        # After scraping, manually queue a prompt execution (example)
        sample_chat = {"title": "Test Chat", "link": "https://chat.openai.com/c/xyz123"}
        dispatcher.add_task({
            "action": "execute_prompts",
            "chat": sample_chat,
            "prompts": ["dreamscape", "workflow_audit"]
        })

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        dispatcher.stop()

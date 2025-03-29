import os
import json
from jinja2 import Template

# Load your master prompt registry
PROMPTS_FILE = "chat_mate/prompts.json"
TEMPLATE_DIR = "chat_mate/templates/"

def generate_templates():
    if not os.path.exists(TEMPLATE_DIR):
        os.makedirs(TEMPLATE_DIR)

    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    for key, data in prompts.items():
        raw_prompt = data.get("prompt", "")
        if not raw_prompt:
            continue

        # Convert {CURRENT_MEMORY_STATE} to {{ CURRENT_MEMORY_STATE }}
        converted_prompt = raw_prompt.replace("{CURRENT_MEMORY_STATE}", "{{ CURRENT_MEMORY_STATE }}")

        template_path = os.path.join(TEMPLATE_DIR, f"{key}_prompt.j2")
        with open(template_path, "w", encoding="utf-8") as template_file:
            template_file.write(converted_prompt)

        print(f"✅ Template generated: {template_path}")

if __name__ == "__main__":
    generate_templates()

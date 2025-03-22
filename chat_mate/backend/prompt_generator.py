def generate_initial_prompt():
    # Define the base prompt
    base_prompt = "You are ChatGPT, a large language model trained by OpenAI."
    return base_prompt

def generate_prompt(conversation_history):
    # Build the prompt based on conversation history
    updated_prompt = generate_initial_prompt()
    for entry in conversation_history:
        updated_prompt += f"\n{entry}"
    return updated_prompt 
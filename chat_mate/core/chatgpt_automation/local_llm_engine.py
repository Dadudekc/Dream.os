import requests

class LocalLLMEngine:
    def __init__(self, model='mistral', base_url='http://localhost:11434'):
        self.model = model
        self.base_url = base_url

    def set_model(self, model_name):
        """Switch to a different local model on-the-fly."""
        self.model = model_name
        print(f"✅ Switched to local model: {self.model}")

    def get_response(self, prompt, stream=False):
        """Send prompt to the local LLM and get a response."""
        endpoint = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }

        try:
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

            return data.get('response', '').strip()

        except Exception as e:
            print(f"❌ LocalLLMEngine error: {e}")
            return None

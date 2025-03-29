# huggingface_backend.py

class HuggingFaceBackend:
    def __init__(self, model_name: str = "gpt2"):
        self.model_name = model_name
        self.pipeline = None

    def load_model(self):
        from transformers import pipeline
        self.pipeline = pipeline("text-generation", model=self.model_name)

    def generate(self, prompt: str, max_length: int = 100):
        if self.pipeline is None:
            self.load_model()
        return self.pipeline(prompt, max_length=max_length)[0]["generated_text"]

import subprocess
import json
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class LocalEmbeddingsGeneratorAgent:
    """
    Generates embeddings for document chunks using a local LLM via Ollama.
    """

    def __init__(self, model: str = "mistral", host: str = "127.0.0.1:11434"):
        self.model = model
        self.host = host  # In case you spin up Ollama on a different port
        logging.info(f"Initialized Local Embeddings Generator with model: {self.model}")

    def generate_embeddings(self, documents: List[Dict[str, str]]) -> List[Dict[str, any]]:
        """
        Process preprocessed chunks and generate embeddings using the local LLM.

        Args:
            documents: List of dictionaries with 'file_name', 'chunk_index', 'content'

        Returns:
            List of embeddings with metadata
        """
        embeddings_output = []

        for idx, doc in enumerate(documents):
            chunk_text = doc['content']
            logging.info(f"Processing chunk {idx + 1}/{len(documents)}")

            try:
                embedding = self._generate_embedding_from_ollama(chunk_text)

                embeddings_output.append({
                    "file_name": doc['file_name'],
                    "chunk_index": doc['chunk_index'],
                    "embedding": embedding,
                    "metadata": doc.get('metadata', {})
                })

            except Exception as e:
                logging.error(f"Failed to generate embedding for chunk {idx}: {e}")

        logging.info(f"Generated embeddings for {len(embeddings_output)} chunks.")
        return embeddings_output

    def _generate_embedding_from_ollama(self, text: str) -> List[float]:
        """
        Sends a prompt to Ollama's local model and retrieves the embedding.

        Args:
            text: The chunk of text to embed.

        Returns:
            The embedding vector as a list of floats.
        """
        prompt = f"""
        Convert the following text into a JSON array of numerical vector embeddings (float values).
        Keep the vector length consistent and suitable for semantic search embeddings.

        Text:
        \"\"\"
        {text}
        \"\"\"
        Return only the JSON array.
        """

        # Run the Ollama model with the given prompt
        cmd = [
            "ollama",
            "run",
            self.model,
            prompt,
            "--format", "json"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout.strip()

            # Parse JSON array from the output
            embedding = json.loads(output)

            # Validate embedding format (must be list of floats)
            if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
                raise ValueError(f"Invalid embedding format: {embedding}")

            return embedding

        except subprocess.CalledProcessError as e:
            logging.error(f"Ollama run failed: {e.stderr}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from Ollama output: {output}")
            raise


import re
from typing import List, Dict

class PreprocessorAgent:
    """
    Preprocesses ingested documents for embedding, parsing, or analysis.
    Cleans, normalizes, and chunks raw text with overlap.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def preprocess_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Full preprocessing pipeline for a list of raw documents.

        Args:
            documents: List of dictionaries with 'file_name' and 'content'

        Returns:
            List of cleaned and chunked document sections with metadata
        """
        preprocessed_docs = []
        for doc in documents:
            file_name = doc.get("file_name")
            raw_text = doc.get("content")

            if not raw_text:
                continue  # Skip empty content

            cleaned_text = self.clean_text(raw_text)
            chunks = self.chunk_text(cleaned_text)

            for idx, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue  # Skip empty chunks
                preprocessed_docs.append({
                    "file_name": file_name,
                    "chunk_index": idx,
                    "content": chunk,
                    "metadata": {
                        "chunk_size": len(chunk.split()),
                        "total_chunks": len(chunks)
                    }
                })

        return preprocessed_docs

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean raw text by removing unwanted characters, multiple spaces, etc.

        Args:
            text: Raw text string.

        Returns:
            Cleaned string.
        """
        if not text:
            return ""

        text = re.sub(r'\s+', ' ', text)  # Collapse multiple whitespaces
        text = text.replace('\x00', '')   # Remove null bytes
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII chars (optional)
        return text.strip()

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into segments with overlap for embeddings or analysis.

        Args:
            text: The cleaned text string

        Returns:
            List of text chunks
        """
        if not text:
            return []

        words = text.split()
        chunks = []
        start = 0
        total_words = len(words)

        while start < total_words:
            end = min(start + self.chunk_size, total_words)
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            # Move start forward with overlap
            start += self.chunk_size - self.chunk_overlap

        return chunks

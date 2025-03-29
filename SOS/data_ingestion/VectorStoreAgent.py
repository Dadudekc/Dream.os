import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class VectorStoreAgent:
    """
    Manages vector storage, retrieval, and similarity search.
    Default backend: ChromaDB (local setup).
    """

    def __init__(self, collection_name: str = "default_collection", persist_directory: str = "./chroma_storage"):
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        logging.info(f"Initializing VectorStoreAgent for collection: {self.collection_name}")

        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.persist_directory
        ))

        self.collection = self._get_or_create_collection(self.collection_name)

    def _get_or_create_collection(self, name: str):
        """
        Creates or retrieves a collection in ChromaDB.
        """
        try:
            return self.client.get_or_create_collection(name=name)
        except Exception as e:
            logging.error(f"Failed to create/retrieve collection {name}: {e}")
            raise

    def add_embeddings(self, embeddings: List[Dict[str, any]]) -> None:
        """
        Adds a batch of embeddings to the collection.

        Args:
            embeddings: List of dicts with 'file_name', 'chunk_index', 'embedding', 'metadata'
        """
        if not embeddings:
            logging.warning("No embeddings provided to add.")
            return

        ids = []
        vectors = []
        metadatas = []
        documents = []

        for entry in embeddings:
            uid = f"{entry['file_name']}_chunk_{entry['chunk_index']}"
            ids.append(uid)
            vectors.append(entry['embedding'])
            metadatas.append({
                "file_name": entry['file_name'],
                "chunk_index": entry['chunk_index'],
                **entry.get('metadata', {})
            })
            documents.append(entry.get('content', ''))  # Optional raw text storage

        try:
            self.collection.add(
                ids=ids,
                embeddings=vectors,
                metadatas=metadatas,
                documents=documents
            )
            logging.info(f"Successfully added {len(ids)} embeddings to collection: {self.collection_name}")

        except Exception as e:
            logging.error(f"Failed to add embeddings: {e}")

    def query_similar(self, query_embedding: List[float], n_results: int = 5) -> List[Dict]:
        """
        Queries the vector store for similar embeddings.

        Args:
            query_embedding: Vector embedding to search against
            n_results: Number of closest matches to return

        Returns:
            List of matching records with metadata
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            logging.info(f"Query returned {len(results['ids'][0])} results.")
            return results

        except Exception as e:
            logging.error(f"Similarity query failed: {e}")
            return []

    def delete_embedding(self, id: str) -> None:
        """
        Deletes an embedding from the collection by its unique ID.
        """
        try:
            self.collection.delete(ids=[id])
            logging.info(f"Deleted embedding with id: {id}")
        except Exception as e:
            logging.error(f"Failed to delete embedding {id}: {e}")

    def persist(self):
        """
        Explicitly persists the database to disk.
        """
        try:
            self.client.persist()
            logging.info("Persisted vector store to disk.")
        except Exception as e:
            logging.error(f"Persist operation failed: {e}")


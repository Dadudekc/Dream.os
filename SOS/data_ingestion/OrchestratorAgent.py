import os
import shutil
import time
import logging

from IngestManager import IngestManager
from PreprocessorAgent import PreprocessorAgent
from LocalEmbeddingsGeneratorAgent import LocalEmbeddingsGeneratorAgent
from VectorStoreAgent import VectorStoreAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class OrchestratorAgent:
    """
    Orchestrates the complete SOS ingestion, preprocessing, embedding, and vector storage pipeline.
    Supports batch and real-time execution.
    """

    def __init__(self,
                 folder_to_watch: str = "./data/uploads",
                 embedding_model: str = "mistral",
                 vector_collection: str = "sos_collection"):

        logging.info("Initializing OrchestratorAgent...")

        # Initialize all core agents
        self.queue = []
        self.ingest_agent = IngestManager(folder_path=folder_to_watch, queue=self.queue)
        self.preprocessor_agent = PreprocessorAgent(chunk_size=500, chunk_overlap=50)
        self.embedding_agent = LocalEmbeddingsGeneratorAgent(model=embedding_model)
        self.vector_store_agent = VectorStoreAgent(collection_name=vector_collection)

        # Directories for archiving and processed files
        self.archive_folder = "D:/overnight_scripts/SOS/data/archive"
        self.processed_folder = "D:/overnight_scripts/SOS/data/processed"

        os.makedirs(self.archive_folder, exist_ok=True)
        os.makedirs(self.processed_folder, exist_ok=True)

        self.poll_interval = 5  # seconds between checking the queue in real-time mode

    # -------------------------
    # BATCH PIPELINE
    # -------------------------
    def run_batch_pipeline(self):
        """
        Runs the complete batch ingestion, processing, embedding, and storage pipeline.
        """
        logging.info("Starting batch pipeline...")

        # Step 1: Batch ingest files
        documents = self.ingest_agent.ingest()
        if not documents:
            logging.warning("No documents found for batch processing.")
            return

        # Step 2: Process each document
        preprocessed_chunks = []
        for doc in documents:
            file_name = doc.get("file_name")
            raw_text = doc.get("content")

            # Clean and chunk
            cleaned_text = self.preprocessor_agent.clean_text(raw_text)
            chunks = self.preprocessor_agent.chunk_text(cleaned_text)

            # Save cleaned version
            self._save_cleaned_file(file_name, cleaned_text)

            # Archive original file
            original_file_path = os.path.join(self.ingest_agent.folder_path, file_name)
            self._archive_file(original_file_path)

            # Add chunks for embedding
            for idx, chunk in enumerate(chunks):
                preprocessed_chunks.append({
                    "file_name": file_name,
                    "chunk_index": idx,
                    "content": chunk
                })

        # Step 3: Generate embeddings
        embeddings = self.embedding_agent.generate_embeddings(preprocessed_chunks)

        # Step 4: Store embeddings in vector DB
        self.vector_store_agent.add_embeddings(embeddings)

        # Step 5: Persist storage
        self.vector_store_agent.persist()

        logging.info("Batch pipeline completed successfully.")

    # -------------------------
    # REAL-TIME PIPELINE
    # -------------------------
    def run_realtime_pipeline(self):
        """
        Starts real-time file monitoring and processing pipeline.
        Watches the queue for new files and processes them as they arrive.
        """
        logging.info("Starting real-time ingestion and processing pipeline...")

        # Start watching folder for real-time ingestion
        self.ingest_agent.start_watcher()

        try:
            while True:
                if self.queue:
                    # Pop a new file and process
                    new_file_path = self.queue.pop(0)
                    logging.info(f"Processing new file from queue: {new_file_path}")

                    # Manual processing (simulate batch with single file)
                    documents = self.ingest_agent._process_files([new_file_path])
                    if not documents:
                        continue

                    preprocessed_chunks = []
                    for doc in documents:
                        file_name = doc.get("file_name")
                        raw_text = doc.get("content")

                        # Clean and chunk
                        cleaned_text = self.preprocessor_agent.clean_text(raw_text)
                        chunks = self.preprocessor_agent.chunk_text(cleaned_text)

                        # Save cleaned version
                        self._save_cleaned_file(file_name, cleaned_text)

                        # Archive original file
                        self._archive_file(new_file_path)

                        # Add chunks for embedding
                        for idx, chunk in enumerate(chunks):
                            preprocessed_chunks.append({
                                "file_name": file_name,
                                "chunk_index": idx,
                                "content": chunk
                            })

                    # Step 3: Generate embeddings
                    embeddings = self.embedding_agent.generate_embeddings(preprocessed_chunks)

                    # Step 4: Store embeddings in vector DB
                    self.vector_store_agent.add_embeddings(embeddings)

                    # Step 5: Persist storage
                    self.vector_store_agent.persist()

                    logging.info(f"Real-time processing complete for: {new_file_path}")

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logging.info("Real-time pipeline interrupted. Shutting down...")

    # -------------------------
    # HELPER FUNCTIONS
    # -------------------------
    def _archive_file(self, file_path: str):
        """
        Moves the original file to the archive folder.
        """
        try:
            filename = os.path.basename(file_path)
            destination = os.path.join(self.archive_folder, filename)
            shutil.move(file_path, destination)
            logging.info(f"Archived file to: {destination}")
        except Exception as e:
            logging.error(f"Failed to archive file {file_path}: {e}")

    def _save_cleaned_file(self, file_name: str, cleaned_text: str):
        """
        Saves the cleaned text to the processed folder.
        """
        try:
            processed_file_path = os.path.join(self.processed_folder, file_name)
            with open(processed_file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            logging.info(f"Saved cleaned file to: {processed_file_path}")
        except Exception as e:
            logging.error(f"Failed to save cleaned file {file_name}: {e}")

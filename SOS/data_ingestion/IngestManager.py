import os
import glob
import re
import logging
import json
from typing import List, Dict, Callable
from pypdf import PdfReader
import markdown
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class IngestManager(FileSystemEventHandler):
    """
    Unified Ingest Manager and File System Watcher.
    Supports batch ingestion and real-time ingestion.
    Handles TXT, MD, PDF, and JSON formats.
    """

    SUPPORTED_FORMATS = ['*.txt', '*.md', '*.pdf', '*.json']
    SUPPORTED_EXTENSIONS = ['.txt', '.md', '.pdf', '.json']

    def __init__(self, folder_path: str, queue: List[str] = None):
        self.folder_path = folder_path
        self.queue = queue if queue is not None else []
        self.documents: List[Dict[str, str]] = []

    # -------------------------------
    # Batch Ingestion Process
    # -------------------------------

    def ingest(self) -> List[Dict[str, str]]:
        """
        Run the full ingestion pipeline for batch processing.
        Returns a list of documents with file_name and content.
        """
        files = self._load_files()
        if not files:
            logging.warning("No files found in the provided folder.")
            return []

        self.documents = self._process_files(files)
        logging.info(f"Ingested {len(self.documents)} documents successfully.")
        return self.documents

    def _load_files(self) -> List[str]:
        """
        Scans the target folder for supported files.
        Returns a list of file paths.
        """
        all_files = []
        for pattern in self.SUPPORTED_FORMATS:
            matched_files = glob.glob(os.path.join(self.folder_path, pattern))
            all_files.extend(matched_files)

        logging.info(f"Found {len(all_files)} files in {self.folder_path}.")
        return all_files

    def _process_files(self, files: List[str]) -> List[Dict[str, str]]:
        """
        Processes a list of files and returns structured document objects.
        """
        docs = []
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            handler = self._get_handler(ext)

            if handler:
                try:
                    raw_text = handler(file_path)
                    clean_text = self._clean_text(raw_text)
                    doc = {
                        "file_name": os.path.basename(file_path),
                        "content": clean_text
                    }
                    docs.append(doc)
                    logging.info(f"Processed file: {file_path}")
                except Exception as e:
                    logging.error(f"Failed to process {file_path}: {e}")
            else:
                logging.warning(f"Unsupported file type: {file_path}")

        return docs

    # -------------------------------
    # Real-Time File Monitoring
    # -------------------------------

    def start_watcher(self):
        """
        Starts monitoring the folder for real-time file ingestion.
        """
        observer = Observer()
        observer.schedule(self, path=self.folder_path, recursive=False)
        observer.start()
        logging.info(f"Started watching folder: {self.folder_path}")

    def on_created(self, event):
        """
        Handler triggered when a new file is created in the watched folder.
        """
        if event.is_directory:
            return
        file_path = event.src_path
        ext = os.path.splitext(file_path)[1].lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            logging.warning(f"Unsupported file type detected: {file_path}")
            return

        logging.info(f"New file detected: {file_path}")
        self.queue.append(file_path)  # Push to queue for Normalization/Processing

    # -------------------------------
    # Handlers for File Formats
    # -------------------------------

    def _get_handler(self, extension: str) -> Callable[[str], str]:
        """
        Returns the appropriate handler function for the given file extension.
        """
        return {
            '.txt': self._read_txt,
            '.md': self._read_md,
            '.pdf': self._read_pdf,
            '.json': self._read_json
        }.get(extension)

    @staticmethod
    def _read_txt(file_path: str) -> str:
        """Reads and returns the content of a TXT file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def _read_md(file_path: str) -> str:
        """Reads and converts Markdown to plain text."""
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        # Convert Markdown to HTML, then strip tags for plain text
        raw_text = markdown.markdown(md_content)
        clean_text = re.sub('<[^<]+?>', '', raw_text)
        return clean_text

    @staticmethod
    def _read_pdf(file_path: str) -> str:
        """Extracts and returns text from a PDF file."""
        reader = PdfReader(file_path)
        text = []
        for page_number, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
            else:
                logging.warning(f"No text found on page {page_number} in {file_path}")
        return "\n".join(text)

    @staticmethod
    def _read_json(file_path: str) -> str:
        """Reads and returns JSON data as a formatted string."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Convert JSON to a flat string representation (or customize as needed)
        return json.dumps(data, indent=2)

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Cleans the text by collapsing extra whitespace and stripping leading/trailing spaces.
        """
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

# -------------------------------
# Example Usage
# -------------------------------
if __name__ == "__main__":
    queue = []
    folder_to_watch = "./data/uploads"

    ingest_manager = IngestManager(folder_path=folder_to_watch, queue=queue)

    # Batch Ingest
    batch_documents = ingest_manager.ingest()

    # Start Real-Time Watcher
    ingest_manager.start_watcher()

    # Monitor the queue (example loop - replace with queue processing logic)
    try:
        while True:
            if queue:
                new_file = queue.pop(0)
                logging.info(f"Processing queued file: {new_file}")
                ingest_manager._process_files([new_file])
    except KeyboardInterrupt:
        logging.info("Shutting down ingestion system.")

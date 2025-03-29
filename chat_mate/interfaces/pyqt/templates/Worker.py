import os
import time
from PyQt5 import QtCore
from ..setup_logging import setup_logging

logger = setup_logging("worker_thread", log_dir=os.path.join(os.getcwd(), "logs", "social"))

class Worker(QtCore.QThread):
    # Emitting: file_path, status message, updated_content, row index
    result_signal = QtCore.pyqtSignal(str, str, str, int)

    def __init__(self, file_path, engine, manual_model=None, row_index=None):
        super().__init__()
        self.file_path = file_path
        self.engine = engine
        self.manual_model = manual_model
        self.row_index = row_index

    def run(self):
        logger.info(f"🚀 Processing: {self.file_path}")
        try:
            output_file = self.engine.process_file(self.file_path, manual_model=self.manual_model)
            if output_file:
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        updated_content = f.read()
                    status = f"✅ Processed: {self.file_path}"
                    logger.info(status)
                    self.result_signal.emit(self.file_path, status, updated_content, self.row_index)
                except Exception as e:
                    status = f"⚠️ Processed but failed to read output: {e}"
                    logger.error(status)
                    self.result_signal.emit(self.file_path, status, "", self.row_index)
            else:
                status = f"⚠️ Processing failed: {self.file_path}"
                logger.warning(status)
                self.result_signal.emit(self.file_path, status, "", self.row_index)
        except Exception as e:
            status = f"❌ Error processing {self.file_path}: {e}"
            logger.error(status)
            self.result_signal.emit(self.file_path, status, "", self.row_index)

import os
import json
import threading
from datetime import datetime
import logging
from utils.reinforcement_trainer import process_feedback  # Step 2 will cover this

logger = logging.getLogger("ai_output_logger")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# Module-level lock for thread-safe file access
write_lock = threading.Lock()

def log_ai_output(context, input_prompt, ai_output, tags=None, result=None, log_dir="ai_logs", enable_reinforcement=True):
    """
    Log AI output to a structured JSONL file and trigger reinforcement training if enabled.
    
    :param context: String indicating which system or module generated the output.
    :param input_prompt: The prompt used to generate the output.
    :param ai_output: The AI's generated output.
    :param tags: Optional list of tags for categorizing this log entry.
    :param result: Optional result (e.g., "executed", "failed") for additional context.
    :param log_dir: Directory to store the log files.
    :param enable_reinforcement: If True, triggers post-processing reinforcement logic.
    """
    os.makedirs(log_dir, exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "context": context,
        "input_prompt": input_prompt,
        "ai_output": ai_output,
        "tags": tags or [],
        "result": result
    }

    file_name = os.path.join(log_dir, f"ai_output_log_{datetime.utcnow().strftime('%Y%m%d')}.jsonl")
    
    with write_lock:
        try:
            with open(file_name, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            logger.info(f"Logged AI output from '{context}' to {file_name}")

            # Trigger reinforcement processing
            if enable_reinforcement:
                process_feedback(log_entry)

        except Exception as e:
            logger.error(f"Failed to log AI output: {e}")

import os
import json
import logging
from datetime import datetime
from core.AletheiaPromptManager import AletheiaPromptManager

logger = logging.getLogger("prompt_tuner")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def load_reinforcement_feedback(log_file):
    """Load reinforcement training logs from a JSONL file."""
    feedback = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    feedback.append(json.loads(line))
                except Exception as e:
                    logger.error(f"Error parsing log line: {e}")
    else:
        logger.info(f"No reinforcement log file found at {log_file}.")
    return feedback

def analyze_feedback(feedback, prompt_type):
    """
    Analyze feedback for a given prompt type.
    Returns a dictionary with total entries and a calculated failure rate.
    For example, count the number of "failed" results.
    """
    total = len(feedback)
    failures = sum(1 for entry in feedback 
                   if prompt_type.lower() in " ".join(entry.get("tags", [])).lower() 
                   and "failed" in (entry.get("result") or "").lower())
    
    failure_rate = failures / total if total > 0 else 0.0
    logger.info(f"Analyzed {total} feedback entries for prompt '{prompt_type}'. Failure rate: {failure_rate:.2f}")
    return {"failure_rate": failure_rate, "total": total}

def tune_prompt(prompt_manager, prompt_type, feedback, threshold=0.3):
    """
    Automatically adjust the prompt if its failure rate exceeds the threshold.
    For this example, we simply append a note advising a rephrase.
    """
    analysis = analyze_feedback(feedback, prompt_type)
    failure_rate = analysis["failure_rate"]

    current_prompt = prompt_manager.get_prompt(prompt_type)
    if failure_rate > threshold:
        tuned_prompt = current_prompt.strip() + " [ADJUSTED: Consider rephrasing for clearer, more effective responses.]"
        prompt_manager.add_prompt(prompt_type, tuned_prompt)
        logger.info(f"Prompt '{prompt_type}' tuned due to high failure rate ({failure_rate:.2f}).")
        return tuned_prompt
    else:
        logger.info(f"Prompt '{prompt_type}' does not require tuning (failure rate {failure_rate:.2f}).")
        return current_prompt

if __name__ == "__main__":
    # Example usage
    today_log = os.path.join("ai_logs", f"ai_output_log_{datetime.utcnow().strftime('%Y%m%d')}.jsonl")
    feedback = load_reinforcement_feedback(today_log)
    prompt_manager = AletheiaPromptManager()  # Loads prompts from prompts.json
    tuned = tune_prompt(prompt_manager, "devlog", feedback)
    print("Tuned Prompt:", tuned)

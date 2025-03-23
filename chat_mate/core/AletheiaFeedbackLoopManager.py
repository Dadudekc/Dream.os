import json
import os
import logging
from datetime import datetime
from core.AIOutputLogAnalyzer import AIOutputLogAnalyzer # Your class
from social.social_config import social_config   # Singleton config w/ rate limits
from social.log_writer import write_json_log     # Logger

logger = logging.getLogger(__name__)

class AletheiaFeedbackLoopManager:
    """
    FULL SYNC Feedback Loop Manager:
    - Reviews log summaries.
    - Detects failure clusters and reinforces actions.
    - Adjusts system configurations (rate limits, retries, etc).
    """

    def __init__(self, log_dir="social/logs/json_logs", verbose=True):
        self.analyzer = AIOutputLogAnalyzer(log_dir=log_dir, verbose=verbose)
        logger.info("Aletheia Feedback Loop Manager initialized.")

    def generate_feedback_loops(self):
        """
        Analyze logs ➜ generate feedback ➜ trigger adaptive loops.
        """
        logger.info(" Running feedback loop analysis...")

        # Get raw summary
        summary = self.analyzer.summarize()

        # Evaluate results
        success_rate = self._calculate_success_rate(summary)
        top_failed_tags = self._get_top_tags(summary, result_type="failed")
        recommendations = []

        # If failure rate too high, suggest action
        if success_rate < 0.75:
            recommendations.append("🚨 High failure rate detected. Consider reducing post frequency or adjusting content.")

        # Tag-specific feedback loops
        for tag, count in top_failed_tags:
            if count > 3:  # Threshold, tweak as needed
                recommendations.append(f"⚠️ Repeated failures on '{tag}' tag. Review related platform workflows.")

        # If specific platforms fail frequently, adjust their cooldowns
        self._auto_adjust_rate_limits(top_failed_tags)

        # Feedback loop log
        feedback_loop_payload = {
            "new_feedback_loops": recommendations,
            "optimized_processes": ["Rate limit adjustments", "Failure pattern detection"]
        }

        # Log feedback
        write_json_log(
            platform="aletheia",
            result="successful",
            tags=["feedback_loop"],
            ai_output=json.dumps(feedback_loop_payload, indent=2),
            event_type="system"
        )

        logger.info(" Feedback loop executed.")
        return feedback_loop_payload

    def _calculate_success_rate(self, summary):
        total = summary.get("total_entries", 1)
        successful = summary.get("successful", 0)
        success_rate = successful / total
        logger.info(f" Success Rate: {success_rate:.2%}")
        return success_rate

    def _get_top_tags(self, summary, result_type="failed", top_n=5):
        """
        Returns top tags from failed (or any) logs.
        """
        tag_counter = summary.get("tag_distribution", {})
        sorted_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)
        logger.info(f"️  Top tags by {result_type}: {sorted_tags[:top_n]}")
        return sorted_tags[:top_n]

    def _auto_adjust_rate_limits(self, top_failed_tags):
        """
        Example: If too many failures on 'linkedin_post', back off.
        """
        for tag, count in top_failed_tags:
            if "linkedin" in tag:
                platform = "linkedin"
                action = "post"

                # Increase cooldown dynamically (example)
                current_cooldown = social_config.rate_limits[platform][action]["cooldown"]
                new_cooldown = min(current_cooldown * 1.5, 3600)

                social_config.rate_limits[platform][action]["cooldown"] = new_cooldown
                logger.warning(f" Increased cooldown for {platform}:{action}  {new_cooldown} sec")

    # Optional Export for Dashboard or Discord
    def export_feedback_report(self, output_file="feedback_report.json"):
        loops = self.generate_feedback_loops()

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(loops, f, indent=4)
            logger.info(f" Feedback report exported to {output_file}")
        except Exception as e:
            logger.error(f" Failed to export feedback report: {e}")

    def process_feedback(self, feedback):
        logger.info(f"Processing feedback: {feedback}")


# ---------------------------
# Example Usage
# ---------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    feedback_manager = AletheiaFeedbackLoopManager(
        log_dir="social/logs/json_logs",
        verbose=True
    )

    feedback_loops = feedback_manager.generate_feedback_loops()
    print(json.dumps(feedback_loops, indent=4))

    # Optional: export full feedback report
    feedback_manager.export_feedback_report(output_file="feedback_report.json")

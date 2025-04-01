import time
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure module logger
logger = logging.getLogger("PromptEngine")
logger.setLevel(logging.INFO)


###############################################################################
# Lower-level PromptEngine (Selenium-based)
###############################################################################
class PromptEngine:
    """
    Handles direct interaction with the ChatGPT interface via Selenium:
      - Sends prompt using either DOM injection or simulated typing.
      - Polls for and fetches AI responses.
      - Waits for a response to remain stable for a specified period.
      - Logs metrics and optionally triggers reinforcement feedback.
    """

    def __init__(self,
                 driver: Any,
                 timeout: int = 180,
                 stable_period: int = 10,
                 poll_interval: int = 5,
                 reinforcement_engine: Optional[Any] = None,
                 simulate_typing: bool = False,
                 typing_delay: float = 0.02):
        """
        :param driver: Selenium driver instance.
        :param timeout: Maximum time to wait for a response.
        :param stable_period: Seconds that the response must remain unchanged.
        :param poll_interval: Seconds between polls.
        :param reinforcement_engine: Optional engine for processing feedback.
        :param simulate_typing: If True, types character-by-character.
        :param typing_delay: Delay between keystrokes.
        """
        self.driver = driver
        self.timeout = timeout
        self.stable_period = stable_period
        self.poll_interval = poll_interval
        self.reinforcement_engine = reinforcement_engine
        self.simulate_typing = simulate_typing
        self.typing_delay = typing_delay

    def send_prompt(self, prompt: str) -> bool:
        """
        Send the prompt to the ChatGPT input box.
        Uses simulated typing if enabled; otherwise injects text via the DOM.
        Returns True if successful.
        """
        try:
            wait = WebDriverWait(self.driver, 15)
            input_box = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']")
                )
            )
            input_box.click()
            if self.simulate_typing:
                logger.info(f"Simulating typing for prompt ({len(prompt)} chars)...")
                for char in prompt:
                    input_box.send_keys(char)
                    time.sleep(self.typing_delay)
            else:
                # DOM injection method for speed.
                self.driver.execute_script("arguments[0].innerText = arguments[1];",
                                             input_box, prompt)
                self.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_box)
            input_box.send_keys(Keys.RETURN)
            logger.info("Prompt sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send prompt: {e}")
            return False

    def fetch_response(self) -> str:
        """
        Retrieves the latest ChatGPT response text from the page.
        Returns the text of the last message if available.
        """
        try:
            messages = self.driver.find_elements(By.CSS_SELECTOR, ".markdown.prose.w-full.break-words")
            if messages:
                response = messages[-1].text.strip()
                logger.debug(f"Fetched response ({len(response)} chars)")
                return response
            return ""
        except Exception as e:
            logger.error(f"Error fetching response: {e}")
            return ""

    def wait_for_stable_response(self) -> str:
        """
        Wait until the ChatGPT response remains unchanged for the specified
        stable period or until timeout is reached.
        Logs response metrics and returns the cleaned final response.
        """
        logger.info("⏳ Waiting for stable AI response...")
        start_time = time.time()
        last_response = ""
        stable_start = None

        while (time.time() - start_time) < self.timeout:
            time.sleep(self.poll_interval)
            current_response = self.fetch_response()
            if current_response != last_response:
                logger.info("AI response updated; resetting stability timer.")
                last_response = current_response
                stable_start = time.time()
            elif stable_start and (time.time() - stable_start) >= self.stable_period:
                response_time = round(time.time() - start_time, 2)
                logger.info(f" Stable AI response achieved in {response_time}s.")
                self.log_ai_response(last_response, response_time=response_time)
                return self.clean_response(last_response)
        logger.warning("️ AI response stabilization timeout. Returning last available response.")
        self.log_ai_response(last_response, timeout_reached=True)
        return self.clean_response(last_response)

    def log_ai_response(self, response: str, response_time: Optional[float] = None, timeout_reached: bool = False) -> None:
        """
        Log metrics about the AI response. Optionally, analyze the response via
        the reinforcement engine.
        """
        ai_observations = {
            "response_length": len(response),
            "tokens_used": len(response.split()),
            "timeout_occurred": timeout_reached,
            "hallucination_detected": "AI hallucination" in response,
            "execution_timestamp": datetime.now().isoformat(),
        }
        if response_time:
            ai_observations["response_time"] = response_time

        logger.info(f" AI Response Metrics:\n{json.dumps(ai_observations, indent=2)}")

        if self.reinforcement_engine:
            try:
                feedback_score = self.reinforcement_engine.analyze_response("N/A", response)
                logger.info(f" Reinforcement score: {feedback_score}")
            except Exception as e:
                logger.error(f"Error in reinforcement engine processing: {e}")

    @staticmethod
    def clean_response(response: str) -> str:
        """
        Clean and normalize the AI response text.
        """
        return response.strip()


###############################################################################
# Higher-level PromptEngine
###############################################################################
class PromptExecutionError(Exception):
    """Raised when prompt execution fails."""


class PromptEngine:
    """
    Centralized prompt execution engine that:
      - Retrieves and optionally optimizes a prompt template.
      - Executes the prompt via a lower-level PromptEngine with automatic retry and exponential backoff.
      - Analyzes the response and records feedback.
      - Maintains performance statistics.
    """

    def __init__(
        self,
        prompt_manager: Any,
        driver_manager: Any,
        max_retries: int = 3,
        feedback_threshold: float = 0.7
    ):
        """
        :param prompt_manager: Manager for prompt templates and generation.
        :param driver_manager: Manager that wraps the Selenium driver and low-level prompt execution.
        :param max_retries: Maximum number of retry attempts.
        :param feedback_threshold: Minimum feedback score threshold for prompt optimization.
        """
        self.prompt_manager = prompt_manager
        self.driver_manager = driver_manager  # Expected to expose methods like send_prompt, update_settings, etc.
        self.max_retries = max_retries
        self.feedback_threshold = feedback_threshold
        self._lock = threading.Lock()
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        self.logger = logger

        # Load configuration settings from a central config (or defaults)
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration settings (using a hypothetical config module)."""
        # For this example, we use hardcoded defaults.
        self.config = {
            "temperature": 0.7,
            "max_tokens": 2000,
            "retry_delay": 1.0,
            "optimization_enabled": True,
            "min_samples": 100,
            "learning_rate": 0.01
        }

    def execute_prompt(
        self,
        prompt_type: str,
        chat_title: str,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt with automatic optimization, retry, and feedback integration.

        Returns a dictionary containing the AI response and execution metadata.
        """
        execution_id = f"{chat_title}_{datetime.now(timezone.utc).isoformat()}"
        context = context or {}
        metadata = metadata or {}
        tags = tags or []

        try:
            # Retrieve (and optionally optimize) the prompt template.
            prompt, prompt_metadata = self._get_optimized_prompt(prompt_type, context)

            # Execute the prompt with automatic retry/backoff.
            response, execution_metadata = self._execute_with_retry(prompt, prompt_type, execution_id)

            # (Here you might save the response to disk or a database via your file_manager)

            # Analyze the response.
            analysis = self._analyze_response(response, prompt_type)

            # Record feedback (using a hypothetical feedback module).
            self._record_feedback(
                prompt_type=prompt_type,
                input_prompt=prompt,
                output=response,
                result="success",
                analysis=analysis,
                metadata={**metadata, "execution_id": execution_id,
                          "prompt_metadata": prompt_metadata,
                          "execution_metadata": execution_metadata},
                tags=tags
            )

            # Update execution statistics.
            self._update_stats(prompt_type, True, execution_metadata)

            return {
                "success": True,
                "response": response,
                "analysis": analysis,
                "execution_id": execution_id,
                "metadata": {
                    "prompt_metadata": prompt_metadata,
                    "execution_metadata": execution_metadata
                }
            }

        except Exception as e:
            error_msg = f"Prompt execution failed: {str(e)}"
            self.logger.error(error_msg)

            # Record failure feedback.
            self._record_feedback(
                prompt_type=prompt_type,
                input_prompt=locals().get("prompt", ""),
                output="",
                result="failure",
                analysis={"error": str(e)},
                metadata={**metadata, "execution_id": execution_id, "error": str(e)},
                tags=tags + ["error"]
            )
            self._update_stats(prompt_type, False, {"error": str(e)})
            raise PromptExecutionError(error_msg)

    def _get_optimized_prompt(
        self,
        prompt_type: str,
        context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Retrieve and optionally optimize the prompt template.
        """
        base_prompt = self.prompt_manager.get_prompt(prompt_type)

        if not self.config["optimization_enabled"]:
            return base_prompt, {"optimized": False}

        # Retrieve recent feedback for this prompt type (using a hypothetical feedback module)
        recent_feedback = []  # feedback.get_feedback(...)

        if len(recent_feedback) < self.config["min_samples"]:
            return base_prompt, {"optimized": False, "reason": "insufficient_samples"}

        # Analyze feedback patterns.
        feedback_analysis = {}  # feedback.analyze_feedback(...)

        # Apply optimization.
        optimized_prompt = self._optimize_prompt(base_prompt, feedback_analysis, context)
        return optimized_prompt, {"optimized": True, "feedback_stats": feedback_analysis.get(prompt_type, {})}

    def _optimize_prompt(
        self,
        base_prompt: str,
        feedback_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Apply optimization to the prompt based on feedback.
        """
        # Extract sample performance metrics.
        performance = feedback_analysis.get("context_performance", {})
        avg_score = performance.get("avg_score", 0.0)
        success_rate = performance.get("success_rate", 0.0)

        # Adjust temperature setting based on success rate.
        temperature = self.config["temperature"]
        if success_rate < 0.5:
            temperature *= 0.8
        elif avg_score > 0.8:
            temperature *= 1.2

        # Update driver settings (if applicable).
        self.driver_manager.update_settings({"temperature": temperature})

        # Enhance prompt with context-specific instructions.
        enhanced_prompt = self._enhance_prompt(base_prompt, context)
        return enhanced_prompt

    def _enhance_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Enhance the base prompt using the execution context.
        """
        if context.get("require_precision"):
            prompt = f"[Precision Required] {prompt}"
        if context.get("creative_mode"):
            prompt = f"[Creative Mode] {prompt}"

        # Append any learned improvements (hypothetical).
        improvements = ""  # self._get_learned_improvements()
        if improvements:
            prompt = f"{prompt}\n\nAdditional Guidelines:\n{improvements}"

        return prompt

    def _execute_with_retry(
        self,
        prompt: str,
        prompt_type: str,
        execution_id: str
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Execute the prompt with automatic retries and exponential backoff.
        """
        metadata = {"attempts": 0, "start_time": datetime.now(timezone.utc).isoformat()}
        for attempt in range(self.max_retries):
            try:
                metadata["attempts"] += 1
                # Send prompt using the lower-level PromptEngine.
                if not self.driver_manager.send_prompt(prompt, max_tokens=self.config["max_tokens"]):
                    raise Exception("Prompt sending failed.")
                # Wait for a stable response.
                response = self.driver_manager.wait_for_stable_response()
                metadata["end_time"] = datetime.now(timezone.utc).isoformat()
                return response, metadata
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                self.logger.info(f"Retrying prompt execution (attempt {attempt+1}) due to error: {e}")
                delay = self.config["retry_delay"] * (2 ** attempt)
                time.sleep(delay)

    def _analyze_response(self, response: Any, prompt_type: str) -> Dict[str, Any]:
        """
        Analyze the response quality and extract metrics.
        """
        analysis = {
            "length": len(str(response)),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if prompt_type == "creative":
            analysis["creativity_score"] = self._assess_creativity(response)
        elif prompt_type == "technical":
            analysis["technical_accuracy"] = self._assess_technical_accuracy(response)
        return analysis

    def _assess_creativity(self, response: str) -> float:
        """Placeholder for creativity assessment."""
        return 0.8

    def _assess_technical_accuracy(self, response: str) -> float:
        """Placeholder for technical accuracy assessment."""
        return 0.9

    def _record_feedback(
        self,
        prompt_type: str,
        input_prompt: str,
        output: Any,
        result: str,
        analysis: Dict[str, Any],
        metadata: Dict[str, Any],
        tags: List[str]
    ) -> None:
        """Record feedback for the prompt execution (using a hypothetical feedback module)."""
        score = self._calculate_feedback_score(result, analysis)
        # feedback.add_feedback(...)  # Implement feedback recording as needed.
        self.logger.info(f"Feedback recorded with score: {score}")

    def _calculate_feedback_score(self, result: str, analysis: Dict[str, Any]) -> float:
        if result == "failure":
            return -1.0
        base_score = 0.5
        if "creativity_score" in analysis:
            base_score += analysis["creativity_score"] * 0.3
        if "technical_accuracy" in analysis:
            base_score += analysis["technical_accuracy"] * 0.3
        return min(max(base_score, -1.0), 1.0)

    def _update_stats(self, prompt_type: str, success: bool, metadata: Dict[str, Any]) -> None:
        """Update execution statistics."""
        with self._lock:
            if prompt_type not in self.execution_stats:
                self.execution_stats[prompt_type] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "last_execution": None,
                    "error_counts": {}
                }
            stats = self.execution_stats[prompt_type]
            stats["total_executions"] += 1
            if success:
                stats["successful_executions"] += 1
            else:
                stats["failed_executions"] += 1
                error_type = metadata.get("error", "unknown_error")
                stats["error_counts"][error_type] = stats["error_counts"].get(error_type, 0) + 1
            stats["last_execution"] = datetime.now(timezone.utc).isoformat()

    def get_stats(self, prompt_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Return execution statistics.
        """
        with self._lock:
            if prompt_type:
                return self.execution_stats.get(prompt_type, {})
            return self.execution_stats.copy()

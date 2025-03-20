import subprocess
import json
import logging
from textblob import TextBlob
from datetime import datetime

# FIXED IMPORT: Use the full path from the project root
from social.log_writer import write_json_log, log_error

logger = logging.getLogger("SentimentAnalyzer")


class SentimentAnalyzer:
    """
    SentimentAnalyzer:
    Classifies sentiment using Ollama + DeepSeek with fallback.
    Supports confidence scoring and structured JSON output.
    """

    def __init__(self, ollama_model="deepseek-r1:latest", fallback_to_textblob=True, neutral_threshold=0.1):
        self.ollama_model = ollama_model
        self.fallback_to_textblob = fallback_to_textblob
        self.neutral_threshold = neutral_threshold  # Controls neutral threshold for TextBlob fallback
        logger.info(f"🧠 SentimentAnalyzer initialized (model: {self.ollama_model})")

    def analyze(self, text: str, platform: str = "sentiment", log_file: str = "sentiment_analysis.jsonl") -> dict:
        """
        Analyze sentiment for provided text.
        Returns:
            dict: { sentiment: 'positive' | 'neutral' | 'negative', confidence: float, model: str }
        """
        try:
            prompt = self._build_prompt(text)
            logger.info(f"📝 Sending sentiment prompt to Ollama ({self.ollama_model})")

            response = self._run_ollama_command(prompt)
            parsed_result = self._parse_response(response)

            logger.info(f"🎯 Sentiment detected: {parsed_result}")

            # Log structured output
            write_json_log(
                platform=platform,
                result="successful",
                tags=["sentiment", parsed_result["sentiment"]],
                ai_output={
                    "input_text": text,
                    "sentiment": parsed_result["sentiment"],
                    "confidence": parsed_result["confidence"],
                    "model": self.ollama_model,
                    "timestamp": datetime.utcnow().isoformat()
                },
                event_type="sentiment",
                log_file=log_file
            )

            return parsed_result

        except Exception as e:
            logger.error(f"❌ SentimentAnalyzer failed: {e}")
            log_error(
                platform=platform,
                error_msg=f"SentimentAnalyzer failure: {str(e)}",
                tags=["sentiment", "error"]
            )

            if self.fallback_to_textblob:
                logger.warning("⚠️ Falling back to TextBlob sentiment analysis...")
                fallback_result = self._fallback_textblob(text)

                write_json_log(
                    platform=platform,
                    result="partial",
                    tags=["sentiment", "fallback", fallback_result["sentiment"]],
                    ai_output={
                        "input_text": text,
                        "sentiment": fallback_result["sentiment"],
                        "confidence": fallback_result["confidence"],
                        "fallback": "TextBlob",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    event_type="sentiment",
                    log_file=log_file
                )
                return fallback_result

            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "model": "none"
            }

    def _build_prompt(self, text: str) -> str:
        """
        Build a prompt for Ollama to classify sentiment and return JSON.
        """
        return (
            "You are a sentiment analysis AI. Analyze the following text.\n"
            "Return JSON format like this: {\"sentiment\": \"positive\", \"confidence\": 0.85}\n\n"
            f"Text: \"{text}\"\n\n"
            "Respond ONLY with valid JSON."
        )

    def _run_ollama_command(self, prompt: str) -> str:
        """
        Execute Ollama CLI command and return the output.
        """
        process = subprocess.Popen(
            ["ollama", "run", self.ollama_model, prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise Exception(f"Ollama failed with error: {stderr.decode().strip()}")

        return stdout.decode().strip()

    def _parse_response(self, response: str) -> dict:
        """
        Parse JSON response from Ollama into {sentiment, confidence}.
        """
        try:
            logger.debug(f"🧾 Raw Ollama response: {response}")
            parsed = json.loads(response)

            sentiment = parsed.get("sentiment", "").lower()
            confidence = float(parsed.get("confidence", 0.0))

            if sentiment not in ["positive", "neutral", "negative"]:
                logger.warning(f"⚠️ Unexpected sentiment label: {sentiment}")
                sentiment = "neutral"

            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "model": self.ollama_model
            }

        except json.JSONDecodeError:
            logger.warning("⚠️ JSON parsing failed. Falling back to string parsing.")
            cleaned = response.lower().strip()

            if "positive" in cleaned:
                sentiment = "positive"
            elif "neutral" in cleaned:
                sentiment = "neutral"
            elif "negative" in cleaned:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            return {
                "sentiment": sentiment,
                "confidence": 0.5,
                "model": self.ollama_model
            }

    def _fallback_textblob(self, text: str) -> dict:
        """
        Fallback sentiment analysis using TextBlob.
        """
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        logger.debug(f"🔍 TextBlob polarity: {polarity}")

        if polarity > self.neutral_threshold:
            sentiment = "positive"
        elif polarity < -self.neutral_threshold:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        confidence = round(abs(polarity), 2)

        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "model": "TextBlob"
        }


# ----------------------------------------
# Example Usage
# ----------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    analyzer = SentimentAnalyzer(ollama_model="deepseek-r1:latest")

    test_texts = [
        "This platform is fantastic! The new update rocks.",
        "It's okay. Nothing special.",
        "I'm really disappointed with the performance lately."
    ]

    for text in test_texts:
        result = analyzer.analyze(text, platform="test_run")
        print(f"Text: {text}\nSentiment: {result['sentiment']} | Confidence: {result['confidence']}\n")

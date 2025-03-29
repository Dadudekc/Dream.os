import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class NarrativeAnalytics:
    """
    A simple narrative analytics engine placeholder.
    Provides basic summarization, sentiment analysis, and keyword extraction.
    """

    def __init__(self):
        logger.info("NarrativeAnalytics initialized.")

    def analyze(self, text: str) -> Dict[str, str]:
        """
        Analyze the given text and return a summary of findings.

        Args:
            text (str): Input text for analysis

        Returns:
            Dict[str, str]: Dictionary containing summary, sentiment, and keywords
        """
        logger.info("Starting narrative analysis...")

        summary = self._summarize(text)
        sentiment = self._analyze_sentiment(text)
        keywords = self._extract_keywords(text)

        analysis_result = {
            "summary": summary,
            "sentiment": sentiment,
            "keywords": keywords
        }

        logger.info("Narrative analysis completed.")
        return analysis_result

    def _summarize(self, text: str) -> str:
        """
        Generate a placeholder summary of the input text.

        Args:
            text (str): Input text

        Returns:
            str: Summary text
        """
        logger.debug("Generating summary...")
        if not text:
            return "No content provided."
        return f"Summary: {text[:75]}..." if len(text) > 75 else text

    def _analyze_sentiment(self, text: str) -> str:
        """
        Perform a basic sentiment analysis.

        Args:
            text (str): Input text

        Returns:
            str: Sentiment (positive, neutral, negative)
        """
        logger.debug("Analyzing sentiment...")
        if not text:
            return "neutral"

        lowered = text.lower()
        if any(word in lowered for word in ["good", "great", "excellent", "positive"]):
            return "positive"
        elif any(word in lowered for word in ["bad", "poor", "negative", "fail"]):
            return "negative"
        else:
            return "neutral"

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract basic keywords from the input text.

        Args:
            text (str): Input text

        Returns:
            List[str]: List of keywords
        """
        logger.debug("Extracting keywords...")
        if not text:
            return []

        words = text.split()
        keywords = [word.strip('.,!?') for word in words if len(word) > 4]
        return list(set(keywords))

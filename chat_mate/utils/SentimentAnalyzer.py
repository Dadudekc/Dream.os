#!/usr/bin/env python3
"""
SentimentAnalyzer: Scalable sentiment analysis for social media content.
This module uses NLTK’s VADER when available and supports a custom lexicon.
"""

import re
import logging
import os
import json
import datetime
import statistics
from collections import Counter
from typing import Dict, Any, List, Union, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

# Local imports
from utils.path_manager import PathManager
from .nltk_init import ensure_nltk_data  # This function should return True if required NLTK data is present

# Try to import NLTK and its VADER analyzer
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Configure module-level logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class SentimentAnalyzer:
    """
    Analyzes sentiment in text content, optimized for social media posts and comments.
    Supports both individual and batch processing.
    """
    # Predefined custom keyword sets for when NLTK is not used or to augment the lexicon
    POSITIVE_KEYWORDS = {
        'love', 'great', 'awesome', 'excellent', 'good', 'amazing', 'fantastic',
        'wonderful', 'helpful', 'impressive', 'happy', 'thanks', 'thank you',
        'brilliant', 'perfect', 'best', 'excited', 'appreciate', 'enjoy', 'nice', 
        'quality', 'worth', 'favorite', 'loved', 'positive', 'recommended', 'satisfied',
        'super', 'support', 'valuable', 'win', 'yes'
    }
    
    NEGATIVE_KEYWORDS = {
        'bad', 'terrible', 'awful', 'horrible', 'disappointing', 'poor', 'worst',
        'hate', 'useless', 'not working', 'problem', 'issue', 'bug', 'fix', 'error',
        'wrong', 'fail', 'broken', 'waste', 'difficult', 'slow', 'confusing', 
        'expensive', 'painful', 'frustrating', 'annoying', 'impossible', 'sucks',
        'complaint', 'crash', 'glitch', 'refund', 'cancel', 'negative', 'unhappy'
    }
    
    # Emoticon mappings (could be expanded)
    EMOTICONS = {
        'positive': [':)', ':-)', ':D', ':-D', ';)', ';-)', '(:', '(-:', '=)', '(='],
        'negative': [':(', ':-(', ':c', ':C', ':-<', ':/', ':-/', ':\\', ':-\\', ':<', '>:(']
    }
    
    def __init__(self, custom_lexicon: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.sia: Optional[SentimentIntensityAnalyzer] = None

        # Initialize NLTK resources (if available)
        if NLTK_AVAILABLE and ensure_nltk_data():
            try:
                # Check if vader_lexicon is already present; if not, download it once
                try:
                    nltk.data.find('sentiment/vader_lexicon')
                except LookupError:
                    logger.info("vader_lexicon not found; downloading...")
                    nltk.download('vader_lexicon', quiet=True)
                self.sia = SentimentIntensityAnalyzer()
                logger.info("Sentiment analyzer initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing SentimentIntensityAnalyzer: {e}")
                self.sia = None
        else:
            logger.warning("NLTK is not available or NLTK data is missing; fallback to custom analysis")
            self.sia = None

        # If a custom lexicon is provided (or exists by default), load it
        if custom_lexicon:
            self.load_lexicon(custom_lexicon)
        else:
            # Attempt to load default custom lexicon from a known path
            default_lexicon_path = os.path.join(PathManager.get_path('utils'), 'lexicons', 'custom_lexicon.json')
            if os.path.exists(default_lexicon_path):
                self.load_lexicon(default_lexicon_path)
    
    def load_lexicon(self, lexicon_path: str) -> bool:
        """Load a custom lexicon (JSON file) to augment the NLTK VADER lexicon."""
        try:
            if os.path.exists(lexicon_path):
                with open(lexicon_path, 'r', encoding='utf-8') as f:
                    lexicon = json.load(f)
                if self.sia:
                    self.sia.lexicon.update(lexicon)
                    self.logger.info(f"Loaded custom lexicon with {len(lexicon)} entries")
                else:
                    self.logger.warning("Sentiment analyzer is not initialized; cannot update lexicon")
                return True
            else:
                self.logger.warning(f"Lexicon file not found: {lexicon_path}")
                return False
        except Exception as e:
            self.logger.error(f"Error loading lexicon: {e}")
            return False
    
    def analyze(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze the sentiment of a given text.
        
        Returns:
            Dictionary with sentiment scores or None on failure.
        """
        if not self.sia:
            logger.warning("Sentiment analysis requested but analyzer not initialized")
            return None
        try:
            return self.sia.polarity_scores(text)
        except Exception as e:
            logger.error(f"Error during sentiment analysis: {e}")
            return None
    
    def analyze_batch(self, texts: List[Union[str, Dict[str, str]]]) -> Dict[str, Any]:
        """Analyze sentiment for a batch of texts and return aggregated scores."""
        if not texts:
            return {
                "compound": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "sentiment": "neutral",
                "items": []
            }
        
        results = []
        compounds = []
        positives = []
        negatives = []
        neutrals = []
        sentiment_labels = []
        
        for text in texts:
            # Allow text to be either a string or a dict with a 'text' key
            text_content = text['text'] if isinstance(text, dict) and 'text' in text else text if isinstance(text, str) else ""
            if not text_content:
                continue
            result = self.analyze(text_content)
            if result:
                results.append(result)
                compounds.append(result.get('compound', 0))
                positives.append(result.get('positive', 0))
                negatives.append(result.get('negative', 0))
                neutrals.append(result.get('neutral', 0))
                # Derive sentiment label from compound score
                if result.get('compound', 0) >= 0.05:
                    sentiment_labels.append("positive")
                elif result.get('compound', 0) <= -0.05:
                    sentiment_labels.append("negative")
                else:
                    sentiment_labels.append("neutral")
        
        if results:
            avg_compound = statistics.mean(compounds)
            avg_positive = statistics.mean(positives)
            avg_negative = statistics.mean(negatives)
            avg_neutral = statistics.mean(neutrals)
            common_sentiment = Counter(sentiment_labels).most_common(1)[0][0]
            return {
                "compound": avg_compound,
                "positive": avg_positive,
                "negative": avg_negative,
                "neutral": avg_neutral,
                "sentiment": common_sentiment,
                "items": results
            }
        else:
            return {
                "compound": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "sentiment": "neutral",
                "items": []
            }
    
    def analyze_with_context(self, text: str, context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Analyze sentiment with additional context consideration."""
        basic_sentiment = self.analyze(text)
        if not basic_sentiment:
            return None
        if not context:
            return basic_sentiment
        
        context_sentiment = self.analyze(context)
        adjusted_compound = basic_sentiment['compound'] * 0.7 + (context_sentiment['compound'] if context_sentiment else 0) * 0.3
        result = {
            "compound": adjusted_compound,
            "positive": basic_sentiment['positive'],
            "negative": basic_sentiment['negative'],
            "neutral": basic_sentiment['neutral'],
            "context_influence": context_sentiment['compound'] if context_sentiment else 0
        }
        if adjusted_compound >= 0.05:
            result['sentiment'] = 'positive'
        elif adjusted_compound <= -0.05:
            result['sentiment'] = 'negative'
        else:
            result['sentiment'] = 'neutral'
        return result
    
    def analyze_trend(self, texts_with_timestamps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment trend over time."""
        if not texts_with_timestamps:
            return {"trend": "stable", "data": []}
        # Sort entries by timestamp
        sorted_entries = sorted(texts_with_timestamps, key=lambda x: x.get('timestamp', ''))
        results = []
        compounds = []
        for item in sorted_entries:
            text = item.get('text', '')
            timestamp = item.get('timestamp', '')
            sentiment = self.analyze(text)
            if sentiment:
                compounds.append(sentiment['compound'])
                results.append({
                    "timestamp": timestamp,
                    "compound": sentiment['compound'],
                    "sentiment": sentiment.get('sentiment', 'neutral')
                })
        if len(compounds) >= 2:
            half = len(compounds) // 2
            first_avg = statistics.mean(compounds[:half])
            second_avg = statistics.mean(compounds[half:])
            diff = second_avg - first_avg
            if diff > 0.1:
                trend = "improving"
            elif diff < -0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
            diff = 0
        return {
            "trend": trend,
            "data": results,
            "start_compound": compounds[0] if compounds else 0,
            "end_compound": compounds[-1] if compounds else 0,
            "change": diff
        }
    
    def get_keyword_sentiment(self, texts: List[Union[str, Dict[str, str]]], keywords: List[str]) -> Dict[str, Any]:
        """Analyze sentiment specifically around mentions of keywords."""
        if not texts or not keywords:
            return {}
        results = {}
        for keyword in keywords:
            keyword_lower = keyword.lower()
            relevant_texts = []
            for text in texts:
                text_content = text['text'] if isinstance(text, dict) and 'text' in text else text if isinstance(text, str) else ""
                if keyword_lower in text_content.lower():
                    relevant_texts.append(text_content)
            if relevant_texts:
                sentiment = self.analyze_batch(relevant_texts)
                results[keyword] = {
                    "compound": sentiment['compound'],
                    "sentiment": sentiment['sentiment'],
                    "mentions": len(relevant_texts)
                }
        return results
    
    def analyze_feedback_trends(self, 
                                texts: List[str], 
                                timestamps: Optional[List[str]] = None,
                                save_visualization: bool = False,
                                output_path: str = 'sentiment_trends.png') -> Dict[str, Any]:
        """
        Analyze sentiment trends over time or across a corpus.
        """
        if not texts:
            return {
                "average_sentiment": 0.0,
                "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
                "trend": "stable",
                "confidence": 0.0
            }
        results = self.analyze_batch(texts)
        compound_scores = [r["compound"] for r in results["items"]]
        avg_sentiment = statistics.mean(compound_scores) if compound_scores else 0.0
        sentiment_counts = Counter([r.get("sentiment", "neutral") for r in results["items"]])
        
        trend_data = {}
        if timestamps and len(timestamps) == len(texts):
            time_data = sorted(zip(timestamps, compound_scores))
            times = [t[0] for t in time_data]
            scores = [t[1] for t in time_data]
            if len(scores) >= 2:
                first_avg = statistics.mean(scores[:len(scores)//2])
                second_avg = statistics.mean(scores[len(scores)//2:])
                trend_direction = second_avg - first_avg
                if trend_direction > 0.1:
                    trend = "improving"
                elif trend_direction < -0.1:
                    trend = "deteriorating"
                else:
                    trend = "stable"
                trend_strength = min(abs(trend_direction) * 5, 1.0)
            else:
                trend = "insufficient data"
                trend_strength = 0.0
            trend_data = {
                "direction": trend,
                "strength": trend_strength,
                "time_series": dict(zip(times, scores))
            }
            if save_visualization:
                self._generate_trend_visualization(times, scores, output_path)
        
        return {
            "average_sentiment": avg_sentiment,
            "sentiment_distribution": dict(sentiment_counts),
            "trend": trend_data.get("direction", "stable"),
            "trend_strength": trend_data.get("strength", 0.0),
            "time_series": trend_data.get("time_series", {})
        }
    
    def _generate_trend_visualization(self, times: List[str], scores: List[float], output_path: str) -> None:
        """Generate a chart for sentiment trends over time."""
        try:
            plt.figure(figsize=(12, 6))
            x = range(len(times))
            plt.plot(x, scores, 'o-', alpha=0.5, label='Sentiment scores')
            # Trend line
            z = np.polyfit(x, scores, 1)
            p = np.poly1d(z)
            plt.plot(x, p(x), 'r--', linewidth=2, label=f'Trend (slope: {z[0]:.4f})')
            plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
            plt.axhspan(0.05, 1.0, alpha=0.1, color='green', label='Positive zone')
            plt.axhspan(-1.0, -0.05, alpha=0.1, color='red', label='Negative zone')
            plt.title('Sentiment Trend Analysis')
            plt.xlabel('Time')
            plt.ylabel('Sentiment Score (-1 to 1)')
            if len(times) > 10:
                tick_indices = np.linspace(0, len(times)-1, 10, dtype=int)
                plt.xticks(tick_indices, [times[i] for i in tick_indices], rotation=45)
            else:
                plt.xticks(x, times, rotation=45)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            logger.info(f"Sentiment trend visualization saved to {output_path}")
        except Exception as e:
            logger.error(f"Error generating sentiment visualization: {e}")
    
    def extract_topics(self, texts: List[str], top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Extract the top N most frequent topics (words) from the given texts.
        """
        all_text = ' '.join(texts).lower()
        # Remove URLs, mentions, and punctuation
        all_text = re.sub(r'https?://\S+', '', all_text)
        all_text = re.sub(r'@\w+', '', all_text)
        all_text = re.sub(r'[^\w\s]', '', all_text)
        words = all_text.split()
        # Simple stopwords list
        stopwords = {
            'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to', 'by',
            'from', 'in', 'of', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'mine', 'yours', 'hers', 'ours', 'what', 'which', 'who', 'whom',
            'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        }
        word_counts = Counter([word for word in words if word not in stopwords and len(word) > 2])
        return word_counts.most_common(top_n)
    
    def add_custom_keywords(self, positive_words: Optional[List[str]] = None, negative_words: Optional[List[str]] = None) -> None:
        """Add additional custom keywords to the analyzer's keyword sets."""
        if positive_words:
            self.POSITIVE_KEYWORDS.update(set(positive_words))
        if negative_words:
            self.NEGATIVE_KEYWORDS.update(set(negative_words))
        logger.info(f"Added {len(positive_words or [])} positive and {len(negative_words or [])} negative custom keywords")
    
    def load_custom_lexicon(self, lexicon_file: str) -> bool:
        """
        Load a custom sentiment lexicon from a JSON file.
        The file should contain a dictionary of {"word": score, ...}.
        """
        if not os.path.exists(lexicon_file):
            logger.error(f"Lexicon file not found: {lexicon_file}")
            return False
        try:
            with open(lexicon_file, 'r', encoding='utf-8') as f:
                lexicon = json.load(f)
            if not isinstance(lexicon, dict):
                logger.error("Lexicon file must contain a dictionary")
                return False
            for word, score in lexicon.items():
                if isinstance(score, (int, float)) and -1.0 <= score <= 1.0:
                    self.sia.lexicon[word] = float(score)
            logger.info(f"Loaded custom lexicon with {len(self.sia.lexicon)} total entries")
            return True
        except Exception as e:
            logger.error(f"Error loading lexicon file: {e}")
            return False

# Example usage for testing
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    
    # Test texts for individual analysis
    test_texts = [
        "I love this product! It's amazing and works perfectly.",
        "This is the worst experience ever. Everything is broken.",
        "The product works as expected. Nothing special.",
        "I'm having some issues with setup, but support is helpful.",
        "😊 Great community, very helpful people here!"
    ]
    
    for text in test_texts:
        result = analyzer.analyze(text)
        if result:
            print(f"\nText: {text}")
            print(f"Sentiment: {result.get('sentiment', 'N/A')} (score: {result.get('compound', 0):.2f})")
            print(f"Details: pos={result.get('positive', 0):.2f}, neg={result.get('negative', 0):.2f}, neu={result.get('neutral', 0):.2f}")
    
    # Test batch analysis
    batch_results = analyzer.analyze_batch(test_texts)
    if batch_results["items"]:
        avg_sentiment = statistics.mean([r["compound"] for r in batch_results["items"]])
        print(f"\nAverage sentiment for batch: {avg_sentiment:.2f}")
    
    # Test topic extraction
    topics = analyzer.extract_topics(test_texts)
    print("\nExtracted Topics:")
    for topic, count in topics:
        print(f"{topic}: {count}")

import re
import logging
import os
import json
from typing import Dict, Any, List, Union, Optional, Tuple
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import statistics
from core.PathManager import PathManager
from nltk.sentiment import SentimentIntensityAnalyzer
from .nltk_init import ensure_nltk_data

try:
    # Try to import nltk for more advanced NLP
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    NLTK_AVAILABLE = True
    # Download required NLTK data if not already downloaded
    try:
        nltk.data.find('vader_lexicon')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
except ImportError:
    NLTK_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class SentimentAnalyzer:
    """
    Analyzes sentiment in text content, optimized for social media posts and comments
    Provides both individual and batch processing capabilities
    """
    
    # Custom keyword dictionaries for when NLTK is not available
    POSITIVE_KEYWORDS = {
        'love', 'great', 'awesome', 'excellent', 'good', 'amazing', 'fantastic',
        'wonderful', 'helpful', 'impressive', 'happy', 'thanks', 'thank you',
        'brilliant', 'perfect', 'best', 'excited', 'appreciate', 'enjoy', 'excited',
        'nice', 'quality', 'worth', 'favorite', 'impressive', 'loved', 'positive',
        'recommended', 'satisfied', 'super', 'support', 'valuable', 'win', 'yes'
    }
    
    NEGATIVE_KEYWORDS = {
        'bad', 'terrible', 'awful', 'horrible', 'disappointing', 'poor', 'worst',
        'hate', 'useless', 'not working', 'problem', 'issue', 'bug', 'fix', 'error',
        'wrong', 'fail', 'broken', 'waste', 'difficult', 'slow', 'confusing', 
        'expensive', 'painful', 'frustrating', 'annoying', 'impossible', 'sucks',
        'complaint', 'crash', 'glitch', 'refund', 'cancel', 'negative', 'unhappy'
    }
    
    # Emoticons and emoji mappings
    EMOTICONS = {
        'positive': [':)', ':-)', ':D', ':-D', ';)', ';-)', '(:', '(-:', '=)', '(='],
        'negative': [':(', ':-(', ':(', ':-c', ':c', ':-<', ':/', ':-/', ':\\', ':-\\', ':<', '>:(']
    }
    
    def __init__(self, custom_lexicon=None):
        self.logger = logging.getLogger(__name__)
        
        # Initialize NLTK resources if not already downloaded
        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            nltk.download('vader_lexicon')
            
        # Initialize the sentiment analyzer
        self.sia = None
        self._initialize()
        
        # Load custom lexicon if provided
        if custom_lexicon:
            self.load_lexicon(custom_lexicon)
        else:
            # Try to load default custom lexicon if it exists
            lexicon_path = os.path.join(PathManager.get_path('utils'), 'lexicons', 'custom_lexicon.json')
            if os.path.exists(lexicon_path):
                self.load_lexicon(lexicon_path)
    
    def _initialize(self):
        """Initialize the sentiment analyzer with proper error handling"""
        try:
            if ensure_nltk_data():
                self.sia = SentimentIntensityAnalyzer()
                logging.info("Sentiment analyzer initialized successfully")
            else:
                logging.warning("Failed to initialize sentiment analyzer - NLTK data not available")
        except Exception as e:
            logging.error(f"Error initializing sentiment analyzer: {str(e)}")
            self.sia = None
    
    def load_lexicon(self, lexicon_path):
        """Load a custom lexicon to enhance sentiment analysis"""
        try:
            if os.path.exists(lexicon_path):
                with open(lexicon_path, 'r') as f:
                    lexicon = json.load(f)
                    
                # Update the lexicon
                self.sia.lexicon.update(lexicon)
                self.logger.info(f"Loaded custom lexicon with {len(lexicon)} entries")
                return True
            else:
                self.logger.warning(f"Lexicon file not found: {lexicon_path}")
                return False
        except Exception as e:
            self.logger.error(f"Error loading lexicon: {e}")
            return False
    
    def analyze(self, text):
        """
        Analyze the sentiment of the given text.
        Returns a dictionary with sentiment scores or None if analysis fails.
        """
        if not self.sia:
            logging.warning("Sentiment analysis requested but analyzer not initialized")
            return None
            
        try:
            return self.sia.polarity_scores(text)
        except Exception as e:
            logging.error(f"Error during sentiment analysis: {str(e)}")
            return None
    
    def analyze_batch(self, texts):
        """Analyze sentiment for a batch of texts"""
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
        sentiments = []
        
        for text in texts:
            if isinstance(text, dict) and 'text' in text:
                text_content = text['text']
            elif isinstance(text, str):
                text_content = text
            else:
                continue
                
            result = self.analyze(text_content)
            results.append(result)
            
            compounds.append(result['compound'])
            positives.append(result['positive'])
            negatives.append(result['negative'])
            neutrals.append(result['neutral'])
            sentiments.append(result['sentiment'])
        
        # Calculate aggregate scores
        if compounds:
            avg_compound = statistics.mean(compounds)
            avg_positive = statistics.mean(positives)
            avg_negative = statistics.mean(negatives)
            avg_neutral = statistics.mean(neutrals)
            
            # Get most common sentiment
            sentiment_counts = Counter(sentiments)
            most_common_sentiment = sentiment_counts.most_common(1)[0][0]
            
            return {
                "compound": avg_compound,
                "positive": avg_positive,
                "negative": avg_negative,
                "neutral": avg_neutral,
                "sentiment": most_common_sentiment,
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
    
    def analyze_with_context(self, text, context=None):
        """Analyze sentiment with additional context consideration"""
        # Basic sentiment analysis
        basic_sentiment = self.analyze(text)
        
        if not context:
            return basic_sentiment
        
        # Consider context for adjusting sentiment
        context_sentiment = self.analyze(context)
        
        # Adjust compound score based on context (weight: 70% text, 30% context)
        adjusted_compound = basic_sentiment['compound'] * 0.7 + context_sentiment['compound'] * 0.3
        
        # Update scores
        result = {
            "compound": adjusted_compound,
            "positive": basic_sentiment['positive'],
            "negative": basic_sentiment['negative'],
            "neutral": basic_sentiment['neutral'],
            "context_influence": context_sentiment['compound']
        }
        
        # Set sentiment label based on adjusted compound
        if adjusted_compound >= 0.05:
            result['sentiment'] = 'positive'
        elif adjusted_compound <= -0.05:
            result['sentiment'] = 'negative'
        else:
            result['sentiment'] = 'neutral'
            
        return result
    
    def analyze_trend(self, texts_with_timestamps):
        """Analyze sentiment trend over time"""
        if not texts_with_timestamps:
            return {"trend": "stable", "data": []}
        
        # Sort by timestamp
        sorted_texts = sorted(texts_with_timestamps, key=lambda x: x.get('timestamp', ''))
        
        # Analyze each text
        results = []
        compounds = []
        
        for item in sorted_texts:
            text = item.get('text', '')
            timestamp = item.get('timestamp', '')
            
            sentiment = self.analyze(text)
            compounds.append(sentiment['compound'])
            
            results.append({
                "timestamp": timestamp,
                "compound": sentiment['compound'],
                "sentiment": sentiment['sentiment']
            })
        
        # Calculate trend
        if len(compounds) >= 2:
            first_half = compounds[:len(compounds)//2]
            second_half = compounds[len(compounds)//2:]
            
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            
            diff = second_avg - first_avg
            
            if diff > 0.1:
                trend = "improving"
            elif diff < -0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "data": results,
            "start_compound": compounds[0] if compounds else 0,
            "end_compound": compounds[-1] if compounds else 0,
            "change": compounds[-1] - compounds[0] if compounds else 0
        }
    
    def get_keyword_sentiment(self, texts, keywords):
        """Analyze sentiment specifically around mentions of keywords"""
        if not texts or not keywords:
            return {}
        
        results = {}
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            relevant_texts = []
            
            for text in texts:
                if isinstance(text, dict) and 'text' in text:
                    text_content = text['text']
                elif isinstance(text, str):
                    text_content = text
                else:
                    continue
                    
                if keyword_lower in text_content.lower():
                    relevant_texts.append(text_content)
            
            if relevant_texts:
                # Get the sentiment for texts containing this keyword
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
        
        Args:
            texts: List of text content to analyze
            timestamps: Optional list of timestamp strings (must be same length as texts)
            save_visualization: Whether to save a visualization of the trends
            output_path: Path to save the visualization if enabled
            
        Returns:
            Dict with trend analysis results
        """
        if not texts:
            return {
                "average_sentiment": 0.0,
                "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
                "trend": "stable",
                "confidence": 0.0
            }
        
        # Analyze all texts
        results = self.analyze_batch(texts)
        
        # Calculate overall sentiment statistics
        compound_scores = [r["compound"] for r in results["items"]]
        avg_sentiment = sum(compound_scores) / len(compound_scores)
        
        # Count sentiment categories
        sentiment_counts = Counter([r["sentiment"] for r in results["items"]])
        
        # Analyze trend if timestamps are provided
        trend_data = {}
        if timestamps and len(timestamps) == len(texts):
            # Create time-ordered data
            time_data = sorted(zip(timestamps, compound_scores))
            times = [t[0] for t in time_data]
            scores = [t[1] for t in time_data]
            
            # Simple trend detection
            if len(scores) >= 2:
                first_half = scores[:len(scores)//2]
                second_half = scores[len(scores)//2:]
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)
                
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
            
            # Generate visualization if requested
            if save_visualization:
                self._generate_trend_visualization(times, scores, output_path)
        
        return {
            "average_sentiment": avg_sentiment,
            "sentiment_distribution": dict(sentiment_counts),
            "trend": trend_data.get("direction", "stable"),
            "trend_strength": trend_data.get("strength", 0.0),
            "time_series": trend_data.get("time_series", {})
        }
    
    def _generate_trend_visualization(self, 
                                     times: List[str], 
                                     scores: List[float],
                                     output_path: str) -> None:
        """Generate a visualization of sentiment trends over time."""
        try:
            plt.figure(figsize=(12, 6))
            
            # Convert to numeric x-values
            x = range(len(times))
            
            # Plot raw sentiment scores
            plt.plot(x, scores, 'o-', alpha=0.5, label='Sentiment scores')
            
            # Add trend line
            z = np.polyfit(x, scores, 1)
            p = np.poly1d(z)
            plt.plot(x, p(x), 'r--', linewidth=2, label=f'Trend (slope: {z[0]:.4f})')
            
            # Add horizontal line at neutral sentiment
            plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
            
            # Add colored regions for sentiment zones
            plt.axhspan(0.05, 1.0, alpha=0.1, color='green', label='Positive zone')
            plt.axhspan(-0.05, 0.05, alpha=0.1, color='gray', label='Neutral zone')
            plt.axhspan(-1.0, -0.05, alpha=0.1, color='red', label='Negative zone')
            
            # Set up chart
            plt.title('Sentiment Trend Analysis')
            plt.ylabel('Sentiment Score (-1 to 1)')
            plt.xlabel('Time')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Add x-tick labels (limit to avoid overcrowding)
            if len(times) > 10:
                tick_indices = np.linspace(0, len(times)-1, 10, dtype=int)
                plt.xticks(tick_indices, [times[i] for i in tick_indices], rotation=45)
            else:
                plt.xticks(x, times, rotation=45)
            
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f" Sentiment trend visualization saved to {output_path}")
        except Exception as e:
            logger.error(f" Error generating sentiment visualization: {e}")
    
    def extract_topics(self, texts: List[str], top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Extract common topics/keywords from a collection of texts.
        Simple implementation based on word frequency.
        
        Args:
            texts: List of text content
            top_n: Number of top topics to return
            
        Returns:
            List of (topic, count) tuples
        """
        # Combine all texts
        all_text = ' '.join(texts).lower()
        
        # Simple stopwords list
        stopwords = {
            'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to', 'by',
            'from', 'in', 'of', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'mine', 'yours', 'hers', 'ours', 'theirs', 'what', 'which', 'who', 'whom',
            'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        }
        
        # Remove URLs, mentions, and punctuation
        all_text = re.sub(r'https?://\S+', '', all_text)
        all_text = re.sub(r'@\w+', '', all_text)
        all_text = re.sub(r'[^\w\s]', '', all_text)
        
        # Tokenize
        words = all_text.split()
        
        # Remove stopwords and count frequencies
        word_counts = Counter([word for word in words if word not in stopwords and len(word) > 2])
        
        # Return top N words
        return word_counts.most_common(top_n)
    
    def add_custom_keywords(self, positive_words: List[str] = None, negative_words: List[str] = None) -> None:
        """
        Add custom keywords to the sentiment lexicons.
        
        Args:
            positive_words: List of positive sentiment words to add
            negative_words: List of negative sentiment words to add
        """
        if positive_words:
            self.POSITIVE_KEYWORDS.update(set(positive_words))
        
        if negative_words:
            self.NEGATIVE_KEYWORDS.update(set(negative_words))
        
        logger.info(f" Added {len(positive_words or [])} positive and {len(negative_words or [])} negative custom keywords")
    
    def load_custom_lexicon(self, lexicon_file: str) -> bool:
        """
        Load a custom sentiment lexicon from a JSON file.
        Format should be {"word": score, ...} where score is between -1.0 and 1.0.
        
        Args:
            lexicon_file: Path to JSON lexicon file
            
        Returns:
            Success status
        """
        if not os.path.exists(lexicon_file):
            logger.error(f" Lexicon file not found: {lexicon_file}")
            return False
        
        try:
            with open(lexicon_file, 'r', encoding='utf-8') as f:
                lexicon = json.load(f)
            
            if not isinstance(lexicon, dict):
                logger.error(" Lexicon file must contain a dictionary")
                return False
                
            # Validate and add entries
            for word, score in lexicon.items():
                if isinstance(score, (int, float)) and -1.0 <= score <= 1.0:
                    self.sia.lexicon[word] = float(score)
            
            logger.info(f" Loaded {len(self.sia.lexicon)} entries from custom lexicon")
            return True
        except Exception as e:
            logger.error(f" Error loading lexicon file: {e}")
            return False

# Example usage
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    
    # Test with various text examples
    test_texts = [
        "I love this product! It's amazing and works perfectly.",
        "This is the worst experience ever. Everything is broken.",
        "The product works as expected. Nothing special.",
        "I'm having some issues with setup, but support is helpful.",
        "😊 Great community, very helpful people here!"
    ]
    
    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\nText: {text}")
        print(f"Sentiment: {result['sentiment']} (score: {result['compound']:.2f}, confidence: {result['confidence']:.2f})")
        print(f"Details: pos={result['positive']:.2f}, neg={result['negative']:.2f}, neu={result['neutral']:.2f}")
    
    # Test batch analysis
    print("\nBatch Analysis Results:")
    batch_results = analyzer.analyze_batch(test_texts)
    avg_sentiment = sum(r["compound"] for r in batch_results["items"]) / len(batch_results["items"])
    print(f"Average sentiment: {avg_sentiment:.2f}")
    
    # Test topic extraction
    topics = analyzer.extract_topics(test_texts)
    print("\nExtracted Topics:")
    for topic, count in topics:
        print(f"{topic}: {count}")

import os
import json
import logging
import time
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.social.AIChatAgent import AIChatAgent

class AIStrategy:
    """
    Enhanced AI strategy for community management and content generation.
    Handles all AI-related tasks including:
    - Content generation
    - Comment responses
    - Engagement prompts
    - Sentiment analysis
    - Content optimization
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ai_agent = AIChatAgent()
        self.data_dir = os.getenv("DATA_DIR", "./data")
        self.response_templates_file = os.path.join(self.data_dir, "ai_response_templates.json")
        self.response_history_file = os.path.join(self.data_dir, "ai_response_history.json")
        
        # Load templates and history
        self.response_templates = self._load_templates()
        self.response_history = self._load_history()

    async def generate_comment_response(self, comment_text: str, context: Dict[str, Any]) -> str:
        """
        Generate an AI response to a comment with context awareness.
        
        Args:
            comment_text: The comment to respond to
            context: Additional context (post type, user history, etc.)
        """
        try:
            # Build prompt with context
            prompt = self._build_response_prompt(comment_text, context)
            
            # Get AI response
            response = await self.ai_agent.ask(prompt)
            
            # Track response
            self._track_response("comment", comment_text, response, context)
            
            return response
        except Exception as e:
            self.logger.error(f"Error generating comment response: {e}")
            return self._get_fallback_response("comment")

    async def generate_engagement_prompt(self, metrics: Dict[str, Any], recent_content: List[Dict[str, Any]]) -> str:
        """Generate an engaging prompt based on metrics and recent content."""
        try:
            # Build context-aware prompt
            content_summary = self._summarize_recent_content(recent_content)
            prompt = f"""
            Based on the following metrics and content:
            - Engagement rate: {metrics.get('engagement_rate', 0)}
            - Active members: {metrics.get('active_members', 0)}
            - Recent content: {content_summary}
            
            Generate an engaging question or discussion prompt that will:
            1. Encourage meaningful discussion
            2. Relate to recent content
            3. Be specific enough to get detailed responses
            4. Feel natural and conversational
            """
            
            response = await self.ai_agent.ask(prompt)
            self._track_response("engagement", prompt, response, metrics)
            
            return response
        except Exception as e:
            self.logger.error(f"Error generating engagement prompt: {e}")
            return self._get_fallback_response("engagement")

    async def optimize_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize content for better engagement."""
        try:
            # Build optimization prompt
            prompt = f"""
            Optimize the following content for maximum engagement:
            Title: {content.get('title', '')}
            Description: {content.get('description', '')}
            Tags: {', '.join(content.get('tags', []))}
            
            Provide optimized version maintaining the same meaning but improving:
            1. Title catchiness
            2. Description clarity
            3. SEO effectiveness
            4. Call-to-action strength
            """
            
            response = await self.ai_agent.ask(prompt)
            
            # Parse optimized content
            try:
                optimized = json.loads(response)
            except:
                # Fallback to basic parsing if JSON fails
                lines = response.split('\n')
                optimized = {
                    'title': lines[0].replace('Title:', '').strip(),
                    'description': '\n'.join(lines[1:-1]).strip(),
                    'tags': content.get('tags', [])
                }
            
            self._track_response("optimization", str(content), str(optimized), {})
            return optimized
            
        except Exception as e:
            self.logger.error(f"Error optimizing content: {e}")
            return content

    def analyze_sentiment(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced sentiment analysis with context awareness."""
        try:
            # Get base sentiment
            sentiment_score = self.ai_agent.analyze_sentiment(text)
            
            # Enhance with context if available
            if context:
                # Adjust score based on context
                if context.get('is_regular_commenter', False):
                    sentiment_score *= 1.1  # Give more weight to regular commenters
                if context.get('is_first_time', False):
                    sentiment_score *= 0.9  # Be more conservative with new users
            
            return {
                "score": sentiment_score,
                "label": self._get_sentiment_label(sentiment_score),
                "confidence": min(abs(sentiment_score) * 2, 1.0),
                "context_adjusted": bool(context)
            }
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return {"score": 0, "label": "neutral", "confidence": 0, "context_adjusted": False}

    def _build_response_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """Build a context-aware prompt for AI responses."""
        template = self._get_response_template(context.get('type', 'general'))
        
        prompt = template.format(
            text=text,
            user_type=context.get('user_type', 'general'),
            content_type=context.get('content_type', 'general'),
            platform=context.get('platform', 'unknown')
        )
        
        return prompt

    def _get_response_template(self, response_type: str) -> str:
        """Get appropriate response template."""
        return self.response_templates.get(response_type, self.response_templates['general'])

    def _get_fallback_response(self, response_type: str) -> str:
        """Get fallback response when AI fails."""
        fallbacks = {
            "comment": "Thank you for your comment! We appreciate your feedback.",
            "engagement": "What are your thoughts on this? We'd love to hear from you!",
            "general": "Thanks for being part of our community!"
        }
        return fallbacks.get(response_type, fallbacks["general"])

    def _summarize_recent_content(self, content: List[Dict[str, Any]]) -> str:
        """Summarize recent content for context."""
        if not content:
            return "No recent content"
        
        summary = []
        for item in content[:3]:  # Last 3 items
            summary.append(f"- {item.get('title', 'Untitled')}")
        
        return "\n".join(summary)

    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to human-readable label."""
        if score > 0.5:
            return "very_positive"
        elif score > 0:
            return "positive"
        elif score == 0:
            return "neutral"
        elif score > -0.5:
            return "negative"
        else:
            return "very_negative"

    def _load_templates(self) -> Dict[str, str]:
        """Load response templates from file."""
        default_templates = {
            "general": "Generate a friendly and engaging response to: {text}",
            "question": "Answer this question helpfully and accurately: {text}",
            "feedback": "Generate a thoughtful response to this feedback: {text}",
            "complaint": "Generate an empathetic and solution-focused response to this concern: {text}"
        }
        
        try:
            if os.path.exists(self.response_templates_file):
                with open(self.response_templates_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
        
        return default_templates

    def _load_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load response history from file."""
        try:
            if os.path.exists(self.response_history_file):
                with open(self.response_history_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading history: {e}")
        
        return {"responses": []}

    def _track_response(self, response_type: str, input_text: str, output_text: str, context: Dict[str, Any]):
        """Track AI response for analysis and improvement."""
        try:
            self.response_history["responses"].append({
                "type": response_type,
                "input": input_text,
                "output": output_text,
                "context": context,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 1000 responses
            if len(self.response_history["responses"]) > 1000:
                self.response_history["responses"] = self.response_history["responses"][-1000:]
            
            # Save to file
            with open(self.response_history_file, 'w') as f:
                json.dump(self.response_history, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error tracking response: {e}")

    def get_response_analytics(self) -> Dict[str, Any]:
        """Get analytics about AI responses."""
        try:
            analytics = {
                "total_responses": len(self.response_history["responses"]),
                "response_types": {},
                "average_length": 0,
                "response_times": []
            }
            
            for response in self.response_history["responses"]:
                # Track response types
                r_type = response["type"]
                if r_type not in analytics["response_types"]:
                    analytics["response_types"][r_type] = 0
                analytics["response_types"][r_type] += 1
                
                # Track length
                analytics["average_length"] += len(response["output"])
                
                # Track time if available
                if "timestamp" in response:
                    analytics["response_times"].append(response["timestamp"])
            
            if analytics["total_responses"] > 0:
                analytics["average_length"] /= analytics["total_responses"]
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error generating response analytics: {e}")
            return {} 

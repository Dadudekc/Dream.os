import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
from config.ConfigManager import ConfigManager

class ReinforcementEvaluator:
    """
    Evaluates responses and provides reinforcement feedback.
    Manages memory data and generates insights for prompt tuning.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the reinforcement evaluator.
        
        :param config_manager: The configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.memory_file = self.config_manager.get('MEMORY_FILE', 'memory_data.json')
        self.memory_data = self._load_memory_data()
        self.min_score_threshold = self.config_manager.get('MIN_SCORE_THRESHOLD', 0.6)

    def _load_memory_data(self) -> Dict[str, Any]:
        """Load memory data from file or create default structure."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            else:
                return self._create_default_memory()
        except Exception as e:
            self.logger.error(f"Error loading memory data: {e}")
            return self._create_default_memory()

    def _create_default_memory(self) -> Dict[str, Any]:
        """Create and return default memory data structure."""
        default_memory = {
            'responses': [],
            'feedback': [],
            'scores': [],
            'last_updated': datetime.now().isoformat(),
            'prompt_performance': {},
            'rate_limit_adjustments': []
        }
        self._save_memory_data(default_memory)
        return default_memory

    def _save_memory_data(self, data: Dict[str, Any]) -> None:
        """Save memory data to file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving memory data: {e}")

    def evaluate_response(self, response: str, prompt_text: str) -> Dict[str, Any]:
        """
        Evaluate a response and generate feedback.
        
        :param response: The response to evaluate
        :param prompt_text: The prompt that generated the response
        :return: Dictionary containing evaluation results
        """
        try:
            # Calculate basic metrics
            length = len(response)
            word_count = len(response.split())
            score = self._calculate_score(response, prompt_text)
            
            evaluation = {
                'timestamp': datetime.now().isoformat(),
                'prompt': prompt_text,
                'response': response,
                'metrics': {
                    'length': length,
                    'word_count': word_count,
                    'score': score
                },
                'feedback': self._generate_feedback(score, response)
            }
            
            # Update memory data
            self.memory_data['responses'].append(evaluation)
            self.memory_data['scores'].append(score)
            self.memory_data['last_updated'] = datetime.now().isoformat()
            
            # Update prompt performance
            self._update_prompt_performance(prompt_text, score)
            
            # Save updated memory data
            self._save_memory_data(self.memory_data)
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Error evaluating response: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _calculate_score(self, response: str, prompt_text: str) -> float:
        """
        Calculate a score for the response.
        
        :param response: The response to score
        :param prompt_text: The prompt that generated the response
        :return: Score between 0 and 1
        """
        # TODO: Implement more sophisticated scoring
        # For now, use a simple length-based score
        min_length = 50
        max_length = 1000
        length = len(response)
        
        if length < min_length:
            return 0.3
        elif length > max_length:
            return 0.7
        else:
            return 0.5 + (length - min_length) / (max_length - min_length) * 0.5

    def _generate_feedback(self, score: float, response: str) -> List[str]:
        """
        Generate feedback based on score and response.
        
        :param score: The calculated score
        :param response: The response to provide feedback for
        :return: List of feedback messages
        """
        feedback = []
        
        if score < self.min_score_threshold:
            feedback.append("Response quality below threshold")
            if len(response.split()) < 50:
                feedback.append("Response is too short")
            elif len(response.split()) > 1000:
                feedback.append("Response is too long")
        else:
            feedback.append("Response meets quality standards")
            
        return feedback

    def _update_prompt_performance(self, prompt_text: str, score: float) -> None:
        """
        Update performance metrics for a prompt.
        
        :param prompt_text: The prompt text
        :param score: The score for the response
        """
        if prompt_text not in self.memory_data['prompt_performance']:
            self.memory_data['prompt_performance'][prompt_text] = {
                'scores': [],
                'average_score': 0.0,
                'total_responses': 0
            }
            
        performance = self.memory_data['prompt_performance'][prompt_text]
        performance['scores'].append(score)
        performance['total_responses'] += 1
        performance['average_score'] = sum(performance['scores']) / performance['total_responses']

    def get_prompt_insights(self, prompt_text: str) -> Dict[str, Any]:
        """
        Get insights for a specific prompt.
        
        :param prompt_text: The prompt to get insights for
        :return: Dictionary containing prompt insights
        """
        if prompt_text not in self.memory_data['prompt_performance']:
            return {
                'error': 'No performance data available for this prompt',
                'prompt': prompt_text
            }
            
        performance = self.memory_data['prompt_performance'][prompt_text]
        return {
            'prompt': prompt_text,
            'total_responses': performance['total_responses'],
            'average_score': performance['average_score'],
            'score_trend': self._calculate_score_trend(performance['scores'])
        }

    def _calculate_score_trend(self, scores: List[float]) -> str:
        """
        Calculate the trend of scores.
        
        :param scores: List of scores
        :return: Trend description
        """
        if len(scores) < 2:
            return "Insufficient data"
            
        recent_scores = scores[-5:] if len(scores) > 5 else scores
        avg_recent = sum(recent_scores) / len(recent_scores)
        avg_older = sum(scores[:-len(recent_scores)]) / (len(scores) - len(recent_scores))
        
        if avg_recent > avg_older:
            return "Improving"
        elif avg_recent < avg_older:
            return "Declining"
        else:
            return "Stable"

    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the memory data.
        
        :return: Dictionary containing memory summary
        """
        return {
            'total_responses': len(self.memory_data['responses']),
            'average_score': sum(self.memory_data['scores']) / len(self.memory_data['scores']) if self.memory_data['scores'] else 0,
            'last_updated': self.memory_data['last_updated'],
            'prompt_count': len(self.memory_data['prompt_performance'])
        }

    def clear_memory(self) -> None:
        """Clear all memory data and reset to defaults."""
        self.memory_data = self._create_default_memory()
        self._save_memory_data(self.memory_data)
        self.logger.info("Memory data cleared and reset to defaults") 
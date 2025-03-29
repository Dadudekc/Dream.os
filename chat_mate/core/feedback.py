from typing import Optional, Dict, List, Any
from core.UnifiedFeedbackMemory import UnifiedFeedbackMemory, FeedbackEntry

class FeedbackSingleton:
    """
    Singleton class that provides global access to the UnifiedFeedbackMemory.
    Ensures only one instance of the feedback memory exists.
    """
    _instance: Optional['FeedbackSingleton'] = None
    _feedback_memory: Optional[UnifiedFeedbackMemory] = None

    def __new__(cls) -> 'FeedbackSingleton':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._feedback_memory = UnifiedFeedbackMemory()
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'FeedbackSingleton':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = FeedbackSingleton()
        return cls._instance

    def add_feedback(
        self,
        context: str,
        input_prompt: str,
        output: str,
        result: str,
        feedback_type: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """Add a new feedback entry."""
        self._feedback_memory.add_feedback(
            context=context,
            input_prompt=input_prompt,
            output=output,
            result=result,
            feedback_type=feedback_type,
            score=score,
            metadata=metadata,
            tags=tags
        )

    def get_feedback(
        self,
        context: Optional[str] = None,
        min_score: Optional[float] = None,
        feedback_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[FeedbackEntry]:
        """Get feedback entries with filtering."""
        return self._feedback_memory.get_feedback(
            context=context,
            min_score=min_score,
            feedback_type=feedback_type,
            tags=tags,
            limit=limit
        )

    def get_context_stats(self, context: str) -> Dict[str, Any]:
        """Get statistics for a context."""
        return self._feedback_memory.get_context_stats(context)

    def analyze_feedback(
        self,
        context: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze feedback patterns."""
        return self._feedback_memory.analyze_feedback(
            context=context,
            timeframe=timeframe
        )

# Global feedback instance
feedback = FeedbackSingleton.get_instance() 
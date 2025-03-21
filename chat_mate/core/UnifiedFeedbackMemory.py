import os
import json
import threading
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict

from core.FileManager import FileManager
from core.PathManager import PathManager
from core.UnifiedLoggingAgent import UnifiedLoggingAgent
from core.config import config

class FeedbackEntry:
    """Structured feedback entry for reinforcement learning."""
    def __init__(
        self,
        context: str,
        input_prompt: str,
        output: str,
        result: str,
        feedback_type: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        self.timestamp = datetime.now(UTC).isoformat()
        self.context = context
        self.input_prompt = input_prompt
        self.output = output
        self.result = result
        self.feedback_type = feedback_type
        self.score = score
        self.metadata = metadata or {}
        self.tags = tags or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            "timestamp": self.timestamp,
            "context": self.context,
            "input_prompt": self.input_prompt,
            "output": self.output,
            "result": self.result,
            "feedback_type": self.feedback_type,
            "score": self.score,
            "metadata": self.metadata,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackEntry':
        """Create entry from dictionary."""
        entry = cls(
            context=data["context"],
            input_prompt=data["input_prompt"],
            output=data["output"],
            result=data["result"],
            feedback_type=data["feedback_type"],
            score=data["score"],
            metadata=data.get("metadata", {}),
            tags=data.get("tags", [])
        )
        entry.timestamp = data["timestamp"]
        return entry

class UnifiedFeedbackMemory:
    """
    Centralized reinforcement learning memory system.
    Features:
    - Thread-safe operations
    - Memory segmentation by context
    - Real-time feedback processing
    - Automatic memory pruning
    - Score-based filtering
    - Context-aware learning
    """

    def __init__(self):
        """Initialize the UnifiedFeedbackMemory system."""
        self.file_manager = FileManager()
        self.logger = UnifiedLoggingAgent()
        self._lock = threading.Lock()
        
        # Memory segments
        self.memory: Dict[str, List[FeedbackEntry]] = defaultdict(list)
        self.context_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Load configuration
        self.max_entries = config.get("ai.memory.max_entries", 10000)
        self.min_score_threshold = config.get("ai.memory.min_score", -0.5)
        self.prune_threshold = config.get("ai.memory.prune_threshold", 0.8)
        
        # Load existing memory
        self.load()

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
        """
        Add a new feedback entry to memory.
        
        Args:
            context: The context/domain of the feedback
            input_prompt: Original input prompt
            output: AI's output
            result: Outcome (success/failure/partial)
            feedback_type: Type of feedback (user/automated/metric)
            score: Numerical score (-1.0 to 1.0)
            metadata: Additional structured data
            tags: Categorization tags
        """
        entry = FeedbackEntry(
            context=context,
            input_prompt=input_prompt,
            output=output,
            result=result,
            feedback_type=feedback_type,
            score=score,
            metadata=metadata,
            tags=tags
        )
        
        with self._lock:
            self.memory[context].append(entry)
            self._update_stats(context, entry)
            
            # Prune if necessary
            if len(self.memory[context]) > self.max_entries:
                self._prune_memory(context)
            
            # Save to disk
            self.save()
            
            # Log the feedback
            self.logger.log_system_event(
                event_type="feedback_added",
                message=f"Added {feedback_type} feedback for context: {context}",
                metadata={
                    "context": context,
                    "score": score,
                    "result": result,
                    "tags": tags
                }
            )

    def get_feedback(
        self,
        context: Optional[str] = None,
        min_score: Optional[float] = None,
        feedback_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[FeedbackEntry]:
        """
        Retrieve feedback entries with optional filtering.
        
        Args:
            context: Filter by specific context
            min_score: Minimum score threshold
            feedback_type: Filter by feedback type
            tags: Filter by tags (all must match)
            limit: Maximum number of entries to return
            
        Returns:
            List of matching feedback entries
        """
        with self._lock:
            entries = []
            contexts = [context] if context else self.memory.keys()
            
            for ctx in contexts:
                for entry in self.memory[ctx]:
                    if min_score is not None and entry.score < min_score:
                        continue
                    if feedback_type and entry.feedback_type != feedback_type:
                        continue
                    if tags and not all(tag in entry.tags for tag in tags):
                        continue
                    entries.append(entry)
            
            entries.sort(key=lambda x: x.timestamp, reverse=True)
            return entries[:limit] if limit else entries

    def get_context_stats(self, context: str) -> Dict[str, Any]:
        """Get statistics for a specific context."""
        return self.context_stats.get(context, {})

    def _update_stats(self, context: str, entry: FeedbackEntry) -> None:
        """Update statistics for a context."""
        stats = self.context_stats[context]
        stats["total_entries"] = stats.get("total_entries", 0) + 1
        stats["total_score"] = stats.get("total_score", 0) + entry.score
        stats["avg_score"] = stats["total_score"] / stats["total_entries"]
        
        # Track success rates
        results = stats.get("results", defaultdict(int))
        results[entry.result] += 1
        stats["results"] = dict(results)
        
        # Track feedback types
        feedback_types = stats.get("feedback_types", defaultdict(int))
        feedback_types[entry.feedback_type] += 1
        stats["feedback_types"] = dict(feedback_types)
        
        # Update tag frequencies
        tag_freq = stats.get("tag_frequencies", defaultdict(int))
        for tag in entry.tags:
            tag_freq[tag] += 1
        stats["tag_frequencies"] = dict(tag_freq)

    def _prune_memory(self, context: str) -> None:
        """
        Prune memory for a context using various strategies:
        1. Remove entries below score threshold
        2. Remove oldest entries while keeping high-scoring ones
        """
        entries = self.memory[context]
        
        # First pass: remove low-scoring entries
        entries = [e for e in entries if e.score >= self.min_score_threshold]
        
        # Second pass: if still too many, remove oldest while preserving high scores
        if len(entries) > self.max_entries:
            # Sort by score and timestamp
            entries.sort(key=lambda x: (x.score, x.timestamp), reverse=True)
            # Keep top percentage based on prune_threshold
            keep_count = int(self.max_entries * self.prune_threshold)
            entries = entries[:keep_count]
        
        self.memory[context] = entries
        self.logger.log_system_event(
            event_type="memory_pruned",
            message=f"Pruned memory for context: {context}",
            metadata={"remaining_entries": len(entries)}
        )

    def load(self) -> None:
        """Load memory from storage."""
        try:
            data = self.file_manager.load_file(
                filepath=os.path.join(PathManager.get_path("memory"), "unified_feedback.json"),
                file_type="json"
            ) or {"memory": {}, "stats": {}}
            
            # Convert dictionary data to FeedbackEntry objects
            self.memory = {
                context: [FeedbackEntry.from_dict(entry) for entry in entries]
                for context, entries in data["memory"].items()
            }
            self.context_stats = data["stats"]
            
            self.logger.log_system_event(
                event_type="memory_loaded",
                message="Loaded feedback memory",
                metadata={"context_count": len(self.memory)}
            )
        except Exception as e:
            self.logger.log_system_event(
                event_type="memory_error",
                message=f"Error loading feedback memory: {str(e)}",
                level="error"
            )
            # Initialize empty if load fails
            self.memory = defaultdict(list)
            self.context_stats = defaultdict(dict)

    def save(self) -> None:
        """Save memory to storage."""
        try:
            data = {
                "memory": {
                    context: [entry.to_dict() for entry in entries]
                    for context, entries in self.memory.items()
                },
                "stats": self.context_stats
            }
            
            self.file_manager.save_memory_state(
                content=data,
                memory_type="feedback"
            )
            
            self.logger.log_system_event(
                event_type="memory_saved",
                message="Saved feedback memory",
                metadata={"context_count": len(self.memory)}
            )
        except Exception as e:
            self.logger.log_system_event(
                event_type="memory_error",
                message=f"Error saving feedback memory: {str(e)}",
                level="error"
            )

    def analyze_feedback(
        self,
        context: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze feedback patterns and generate insights.
        
        Args:
            context: Optional context to analyze
            timeframe: Optional timeframe (e.g., "24h", "7d", "30d")
            
        Returns:
            Dictionary of analysis results
        """
        with self._lock:
            contexts = [context] if context else self.memory.keys()
            analysis = {
                "total_entries": 0,
                "avg_score": 0.0,
                "success_rate": 0.0,
                "feedback_distribution": defaultdict(int),
                "top_tags": [],
                "context_performance": {}
            }
            
            total_score = 0
            success_count = 0
            
            for ctx in contexts:
                entries = self.memory[ctx]
                if not entries:
                    continue
                
                # Filter by timeframe if specified
                if timeframe:
                    entries = self._filter_by_timeframe(entries, timeframe)
                
                ctx_stats = {
                    "entries": len(entries),
                    "avg_score": sum(e.score for e in entries) / len(entries),
                    "success_rate": len([e for e in entries if e.result == "success"]) / len(entries)
                }
                
                analysis["context_performance"][ctx] = ctx_stats
                analysis["total_entries"] += ctx_stats["entries"]
                total_score += sum(e.score for e in entries)
                success_count += len([e for e in entries if e.result == "success"])
                
                # Update feedback distribution
                for entry in entries:
                    analysis["feedback_distribution"][entry.feedback_type] += 1
                    
                # Collect tag frequencies
                tag_freq = defaultdict(int)
                for entry in entries:
                    for tag in entry.tags:
                        tag_freq[tag] += 1
                        
                # Update top tags
                ctx_top_tags = sorted(
                    tag_freq.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                analysis["top_tags"].extend(ctx_top_tags)
            
            # Calculate overall metrics
            if analysis["total_entries"] > 0:
                analysis["avg_score"] = total_score / analysis["total_entries"]
                analysis["success_rate"] = success_count / analysis["total_entries"]
            
            # Convert defaultdict to regular dict
            analysis["feedback_distribution"] = dict(analysis["feedback_distribution"])
            
            # Sort and limit top tags
            analysis["top_tags"] = sorted(
                analysis["top_tags"],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return analysis

    def _filter_by_timeframe(
        self,
        entries: List[FeedbackEntry],
        timeframe: str
    ) -> List[FeedbackEntry]:
        """Filter entries by timeframe."""
        now = datetime.now(UTC)
        if timeframe == "24h":
            delta = timedelta(hours=24)
        elif timeframe == "7d":
            delta = timedelta(days=7)
        elif timeframe == "30d":
            delta = timedelta(days=30)
        else:
            return entries
            
        cutoff = now - delta
        return [
            entry for entry in entries
            if datetime.fromisoformat(entry.timestamp) >= cutoff
        ] 
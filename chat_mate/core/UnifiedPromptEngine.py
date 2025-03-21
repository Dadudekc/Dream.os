import threading
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC

from core.FileManager import FileManager
from core.feedback import feedback
from core.config import config
from core.UnifiedLoggingAgent import UnifiedLoggingAgent
from core.PathManager import PathManager

class PromptExecutionError(Exception):
    """Raised when prompt execution fails."""
    pass

class UnifiedPromptEngine:
    """
    Centralized prompt execution engine with embedded reinforcement learning.
    Features:
    - Unified prompt handling
    - Automatic prompt optimization
    - Real-time feedback integration
    - Context-aware execution
    - Automatic retry with backoff
    - Performance monitoring
    """

    def __init__(
        self,
        prompt_manager: Any,
        driver_manager: Any,
        max_retries: int = 3,
        feedback_threshold: float = 0.7
    ):
        """
        Initialize the UnifiedPromptEngine.
        
        Args:
            prompt_manager: Manager for prompt templates and generation
            driver_manager: Manager for AI model interaction
            max_retries: Maximum number of retry attempts
            feedback_threshold: Minimum feedback score for prompt optimization
        """
        self.prompt_manager = prompt_manager
        self.driver_manager = driver_manager
        self.file_manager = FileManager()
        self.logger = UnifiedLoggingAgent()
        
        # Configuration
        self.max_retries = max_retries
        self.feedback_threshold = feedback_threshold
        self._lock = threading.Lock()
        
        # Performance tracking
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        
        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration settings."""
        self.config = {
            "temperature": config.get("ai.temperature", 0.7),
            "max_tokens": config.get("ai.max_tokens", 2000),
            "retry_delay": config.get("ai.retry_delay", 1.0),
            "optimization_enabled": config.get("ai.reinforcement.enabled", True),
            "min_samples": config.get("ai.reinforcement.min_samples", 100),
            "learning_rate": config.get("ai.reinforcement.learning_rate", 0.01)
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
        Execute a prompt with automatic optimization and feedback integration.
        
        Args:
            prompt_type: Type of prompt to execute
            chat_title: Title/identifier for the chat session
            context: Additional context for prompt generation
            metadata: Additional metadata for feedback
            tags: Tags for categorizing the execution
            
        Returns:
            Dictionary containing response and execution metadata
        """
        execution_id = f"{chat_title}_{datetime.now(UTC).isoformat()}"
        context = context or {}
        metadata = metadata or {}
        tags = tags or []
        
        try:
            # Get optimized prompt
            prompt, prompt_metadata = self._get_optimized_prompt(
                prompt_type,
                context
            )
            
            # Execute with retry
            response, execution_metadata = self._execute_with_retry(
                prompt,
                prompt_type,
                execution_id
            )
            
            # Save response
            saved_path = self.file_manager.save_response(
                content=response,
                prompt_type=prompt_type,
                chat_title=chat_title
            )
            
            # Process and analyze response
            analysis = self._analyze_response(response, prompt_type)
            
            # Record feedback
            self._record_feedback(
                prompt_type=prompt_type,
                input_prompt=prompt,
                output=response,
                result="success",
                analysis=analysis,
                metadata={
                    **metadata,
                    "execution_id": execution_id,
                    "prompt_metadata": prompt_metadata,
                    "execution_metadata": execution_metadata
                },
                tags=tags
            )
            
            # Update execution stats
            self._update_stats(prompt_type, True, execution_metadata)
            
            return {
                "success": True,
                "response": response,
                "analysis": analysis,
                "saved_path": saved_path,
                "execution_id": execution_id,
                "metadata": {
                    "prompt_metadata": prompt_metadata,
                    "execution_metadata": execution_metadata
                }
            }
            
        except Exception as e:
            error_msg = f"Prompt execution failed: {str(e)}"
            self.logger.log_system_event(
                event_type="prompt_error",
                message=error_msg,
                level="error",
                metadata={
                    "prompt_type": prompt_type,
                    "chat_title": chat_title,
                    "execution_id": execution_id
                }
            )
            
            # Record failure feedback
            self._record_feedback(
                prompt_type=prompt_type,
                input_prompt=prompt if 'prompt' in locals() else "",
                output="",
                result="failure",
                analysis={"error": str(e)},
                metadata={
                    **metadata,
                    "execution_id": execution_id,
                    "error": str(e)
                },
                tags=tags + ["error"]
            )
            
            # Update execution stats
            self._update_stats(prompt_type, False, {"error": str(e)})
            
            raise PromptExecutionError(error_msg)

    def _get_optimized_prompt(
        self,
        prompt_type: str,
        context: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Get an optimized prompt based on feedback history.
        
        Args:
            prompt_type: Type of prompt to optimize
            context: Context for prompt generation
            
        Returns:
            Tuple of (optimized prompt, metadata)
        """
        base_prompt = self.prompt_manager.get_prompt(prompt_type)
        
        if not self.config["optimization_enabled"]:
            return base_prompt, {"optimized": False}
            
        # Get recent feedback for this prompt type
        recent_feedback = feedback.get_feedback(
            context=prompt_type,
            min_score=self.feedback_threshold,
            limit=self.config["min_samples"]
        )
        
        if len(recent_feedback) < self.config["min_samples"]:
            return base_prompt, {
                "optimized": False,
                "reason": "insufficient_samples"
            }
            
        # Analyze feedback patterns
        feedback_analysis = feedback.analyze_feedback(
            context=prompt_type,
            timeframe="7d"
        )
        
        # Apply optimization based on feedback
        optimized_prompt = self._optimize_prompt(
            base_prompt,
            feedback_analysis,
            context
        )
        
        return optimized_prompt, {
            "optimized": True,
            "feedback_stats": feedback_analysis["context_performance"].get(prompt_type, {})
        }

    def _optimize_prompt(
        self,
        base_prompt: str,
        feedback_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Optimize prompt based on feedback analysis.
        
        Args:
            base_prompt: Original prompt template
            feedback_analysis: Analysis of feedback patterns
            context: Current execution context
            
        Returns:
            Optimized prompt
        """
        # Extract performance metrics
        performance = feedback_analysis["context_performance"]
        avg_score = performance.get("avg_score", 0.0)
        success_rate = performance.get("success_rate", 0.0)
        
        # Apply adaptive optimization
        temperature = self.config["temperature"]
        if success_rate < 0.5:
            temperature *= 0.8  # Reduce creativity for low success rate
        elif avg_score > 0.8:
            temperature *= 1.2  # Increase creativity for high scores
            
        # Update driver settings
        self.driver_manager.update_settings({
            "temperature": temperature
        })
        
        # Enhance prompt based on context
        enhanced_prompt = self._enhance_prompt(base_prompt, context)
        
        return enhanced_prompt

    def _enhance_prompt(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Enhance prompt with context-specific improvements.
        
        Args:
            prompt: Base prompt
            context: Current context
            
        Returns:
            Enhanced prompt
        """
        # Add context-specific instructions
        if context.get("require_precision"):
            prompt = f"[Precision Required] {prompt}"
        if context.get("creative_mode"):
            prompt = f"[Creative Mode] {prompt}"
            
        # Add any learned improvements
        improvements = self._get_learned_improvements()
        if improvements:
            prompt = f"{prompt}\n\nAdditional Guidelines:\n{improvements}"
            
        return prompt

    def _get_learned_improvements(self) -> str:
        """Get learned improvements from feedback analysis."""
        improvements = []
        
        # Analyze successful patterns
        success_patterns = feedback.get_feedback(
            min_score=0.9,
            result="success",
            limit=50
        )
        
        if success_patterns:
            # Extract common elements from successful prompts
            common_tags = set.intersection(
                *[set(entry.tags) for entry in success_patterns]
            )
            if common_tags:
                improvements.append(
                    f"- Consider these aspects: {', '.join(common_tags)}"
                )
            
        return "\n".join(improvements)

    def _execute_with_retry(
        self,
        prompt: str,
        prompt_type: str,
        execution_id: str
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Execute prompt with automatic retry on failure.
        
        Args:
            prompt: Prompt to execute
            prompt_type: Type of prompt
            execution_id: Unique execution identifier
            
        Returns:
            Tuple of (response, execution metadata)
        """
        metadata = {
            "attempts": 0,
            "start_time": datetime.now(UTC).isoformat()
        }
        
        for attempt in range(self.max_retries):
            try:
                metadata["attempts"] += 1
                
                # Execute prompt
                response = self.driver_manager.send_prompt(
                    prompt,
                    max_tokens=self.config["max_tokens"]
                )
                
                metadata["end_time"] = datetime.now(UTC).isoformat()
                return response, metadata
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                    
                # Log retry attempt
                self.logger.log_system_event(
                    event_type="prompt_retry",
                    message=f"Retrying prompt execution: {str(e)}",
                    metadata={
                        "prompt_type": prompt_type,
                        "execution_id": execution_id,
                        "attempt": attempt + 1
                    }
                )
                
                # Exponential backoff
                delay = self.config["retry_delay"] * (2 ** attempt)
                threading.Event().wait(delay)

    def _analyze_response(
        self,
        response: Any,
        prompt_type: str
    ) -> Dict[str, Any]:
        """
        Analyze response quality and extract metrics.
        
        Args:
            response: Response to analyze
            prompt_type: Type of prompt
            
        Returns:
            Analysis results
        """
        analysis = {
            "length": len(str(response)),
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Add prompt-specific analysis
        if prompt_type == "creative":
            analysis["creativity_score"] = self._assess_creativity(response)
        elif prompt_type == "technical":
            analysis["technical_accuracy"] = self._assess_technical_accuracy(response)
            
        return analysis

    def _assess_creativity(self, response: str) -> float:
        """Assess creativity of a response."""
        # Implement creativity assessment logic
        return 0.8  # Placeholder

    def _assess_technical_accuracy(self, response: str) -> float:
        """Assess technical accuracy of a response."""
        # Implement technical accuracy assessment logic
        return 0.9  # Placeholder

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
        """Record execution feedback."""
        # Calculate score based on analysis
        score = self._calculate_feedback_score(result, analysis)
        
        # Record feedback
        feedback.add_feedback(
            context=prompt_type,
            input_prompt=input_prompt,
            output=str(output),
            result=result,
            feedback_type="automated",
            score=score,
            metadata={
                **metadata,
                "analysis": analysis
            },
            tags=tags
        )

    def _calculate_feedback_score(
        self,
        result: str,
        analysis: Dict[str, Any]
    ) -> float:
        """Calculate feedback score based on result and analysis."""
        if result == "failure":
            return -1.0
            
        base_score = 0.5
        
        # Adjust score based on analysis
        if "creativity_score" in analysis:
            base_score += analysis["creativity_score"] * 0.3
        if "technical_accuracy" in analysis:
            base_score += analysis["technical_accuracy"] * 0.3
            
        return min(max(base_score, -1.0), 1.0)

    def _update_stats(
        self,
        prompt_type: str,
        success: bool,
        metadata: Dict[str, Any]
    ) -> None:
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
                stats["error_counts"][error_type] = \
                    stats["error_counts"].get(error_type, 0) + 1
                
            stats["last_execution"] = datetime.now(UTC).isoformat()

    def get_stats(
        self,
        prompt_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            prompt_type: Optional prompt type to filter stats
            
        Returns:
            Dictionary of execution statistics
        """
        with self._lock:
            if prompt_type:
                return self.execution_stats.get(prompt_type, {})
            return self.execution_stats.copy() 
import time
import logging
import threading
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum, auto

from core.UnifiedLoggingAgent import UnifiedLoggingAgent
from core.memory import MemoryManager
from core.ThreadPoolManager import ThreadPoolManager, TaskPriority

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Status of prompt execution."""
    SUCCESS = auto()
    RETRY = auto()
    FAILED = auto()
    TIMEOUT = auto()

class ResilientPromptExecutor:
    """
    Enhanced prompt executor with automatic retries and error recovery.
    Features:
    - Automatic retries with exponential backoff
    - Error categorization and handling
    - Execution history tracking
    - Performance monitoring
    - Health checks
    """

    def __init__(
        self,
        prompt_service: Any,
        memory_manager: Optional[MemoryManager] = None,
        thread_pool: Optional[ThreadPoolManager] = None,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 30.0,
        timeout: float = 60.0
    ):
        """
        Initialize the ResilientPromptExecutor.
        
        Args:
            prompt_service: Service for executing prompts
            memory_manager: Optional MemoryManager instance
            thread_pool: Optional ThreadPoolManager instance
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff
            max_delay: Maximum delay between retries
            timeout: Default timeout for prompt execution
        """
        self.prompt_service = prompt_service
        self.memory_manager = memory_manager or MemoryManager()
        self.thread_pool = thread_pool or ThreadPoolManager()
        self.logger = UnifiedLoggingAgent()
        
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        
        self._lock = threading.Lock()
        self.execution_history: List[Dict[str, Any]] = []
        
        # Error categorization
        self.error_categories = {
            "timeout": ["TimeoutError", "DeadlineExceeded"],
            "connection": ["ConnectionError", "NetworkError"],
            "service": ["ServiceUnavailable", "InternalError"],
            "validation": ["ValidationError", "InvalidInput"]
        }

    def execute_with_retry(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> Tuple[Optional[str], ExecutionStatus]:
        """
        Execute a prompt with automatic retries.
        
        Args:
            prompt: The prompt to execute
            context: Optional context data
            timeout: Optional custom timeout
            priority: Task priority level
            
        Returns:
            Tuple of (response, status)
        """
        start_time = datetime.now()
        timeout = timeout or self.timeout
        attempt = 0
        last_error = None
        
        while attempt <= self.max_retries:
            try:
                # Check if we've exceeded total timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    self._log_execution_result(prompt, None, ExecutionStatus.TIMEOUT, elapsed, attempt)
                    return None, ExecutionStatus.TIMEOUT
                
                # Submit task to thread pool
                future = self.thread_pool.submit_task(
                    func=self._execute_prompt,
                    prompt=prompt,
                    context=context,
                    timeout=timeout - elapsed,
                    priority=priority,
                    task_id=f"prompt_exec_{datetime.now().timestamp()}"
                )
                
                # Wait for result
                response = future.result(timeout=timeout - elapsed)
                
                # Cache successful response
                if response:
                    self._cache_response(prompt, response, context)
                
                self._log_execution_result(prompt, response, ExecutionStatus.SUCCESS, elapsed, attempt)
                return response, ExecutionStatus.SUCCESS
                
            except Exception as e:
                last_error = e
                attempt += 1
                
                if attempt > self.max_retries:
                    break
                
                # Calculate retry delay with exponential backoff
                delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                
                self.logger.log_system_event(
                    event_type="prompt_retry",
                    message=f"Retrying prompt execution (attempt {attempt}/{self.max_retries})",
                    metadata={
                        "error": str(e),
                        "error_type": self._categorize_error(e),
                        "delay": delay,
                        "attempt": attempt
                    }
                )
                
                time.sleep(delay)
        
        # All retries failed
        elapsed = (datetime.now() - start_time).total_seconds()
        self._log_execution_result(prompt, None, ExecutionStatus.FAILED, elapsed, attempt, last_error)
        return None, ExecutionStatus.FAILED

    def _execute_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Optional[str]:
        """Execute a single prompt attempt."""
        try:
            # Check cache first
            cached_response = self._get_cached_response(prompt, context)
            if cached_response:
                return cached_response
            
            # Execute prompt
            return self.prompt_service.execute(prompt, timeout=timeout)
            
        except Exception as e:
            self.logger.log_system_event(
                event_type="prompt_error",
                message=f"Error executing prompt: {str(e)}",
                level="error",
                metadata={
                    "error_type": self._categorize_error(e),
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt
                }
            )
            raise

    def _categorize_error(self, error: Exception) -> str:
        """Categorize an error based on its type."""
        error_type = error.__class__.__name__
        for category, error_types in self.error_categories.items():
            if error_type in error_types:
                return category
        return "unknown"

    def _cache_response(
        self,
        prompt: str,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Cache a successful response."""
        if self.memory_manager:
            cache_key = self._get_cache_key(prompt, context)
            self.memory_manager.set(
                key=cache_key,
                data={
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "context": context
                },
                segment="prompt_responses"
            )

    def _get_cached_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Try to get a cached response."""
        if self.memory_manager:
            cache_key = self._get_cache_key(prompt, context)
            cached = self.memory_manager.get(cache_key, segment="prompt_responses")
            if cached:
                # Check if cache is still valid (e.g., not too old)
                timestamp = datetime.fromisoformat(cached["timestamp"])
                if datetime.now() - timestamp < timedelta(hours=1):  # Cache TTL
                    return cached["response"]
        return None

    def _get_cache_key(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for a prompt and context."""
        import hashlib
        key_parts = [prompt]
        if context:
            key_parts.extend(f"{k}:{v}" for k, v in sorted(context.items()))
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()

    def _log_execution_result(
        self,
        prompt: str,
        response: Optional[str],
        status: ExecutionStatus,
        elapsed: float,
        attempts: int,
        error: Optional[Exception] = None
    ) -> None:
        """Log execution result and update history."""
        result = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "status": status.name,
            "elapsed_seconds": elapsed,
            "attempts": attempts
        }
        
        if error:
            result["error"] = {
                "type": error.__class__.__name__,
                "message": str(error),
                "category": self._categorize_error(error)
            }
        
        if response:
            result["response_length"] = len(response)
        
        with self._lock:
            self.execution_history.append(result)
            # Keep only last 1000 executions
            if len(self.execution_history) > 1000:
                self.execution_history = self.execution_history[-1000:]
        
        self.logger.log_system_event(
            event_type="prompt_execution",
            message=f"Prompt execution completed with status {status.name}",
            metadata=result
        )

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        with self._lock:
            total = len(self.execution_history)
            if not total:
                return {"total_executions": 0}
            
            successes = sum(1 for r in self.execution_history if r["status"] == "SUCCESS")
            failures = sum(1 for r in self.execution_history if r["status"] == "FAILED")
            retries = sum(1 for r in self.execution_history if r["attempts"] > 1)
            
            avg_elapsed = sum(r["elapsed_seconds"] for r in self.execution_history) / total
            
            error_counts = {}
            for result in self.execution_history:
                if "error" in result:
                    category = result["error"]["category"]
                    error_counts[category] = error_counts.get(category, 0) + 1
            
            return {
                "total_executions": total,
                "success_rate": successes / total * 100,
                "failure_rate": failures / total * 100,
                "retry_rate": retries / total * 100,
                "avg_execution_time": avg_elapsed,
                "error_distribution": error_counts
            }

    def clear_history(self) -> None:
        """Clear execution history."""
        with self._lock:
            self.execution_history.clear()
            self.logger.log_system_event(
                event_type="history_cleared",
                message="Execution history cleared"
            ) 

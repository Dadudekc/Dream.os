import threading
import queue
import time
from typing import Callable, Any, Dict
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class DispatcherMetrics:
    """Metrics for the AsyncDispatcher."""
    total_dispatches: int = 0
    successful_dispatches: int = 0
    failed_dispatches: int = 0
    queue_full_count: int = 0
    processing_times: Dict[str, float] = field(default_factory=lambda: defaultdict(list))
    
class AsyncDispatcher:
    """Handles asynchronous dispatch of logging operations."""
    
    def __init__(self, max_queue_size: int = 1000):
        self.log_queue = queue.Queue(maxsize=max_queue_size)
        self.is_running = False
        self.worker_thread = None
        self.metrics = DispatcherMetrics()
        self._start_worker()
        
    def _start_worker(self) -> None:
        """Start the worker thread for processing log queue."""
        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="AsyncLogger-Worker"
        )
        self.worker_thread.start()
        
    def _process_queue(self) -> None:
        """Process items from the queue."""
        while self.is_running:
            try:
                # Get item from queue with timeout to allow graceful shutdown
                item = self.log_queue.get(timeout=1.0)
                if item is None:  # Shutdown signal
                    break
                    
                callback, args, kwargs = item
                start_time = time.time()
                
                try:
                    callback(*args, **kwargs)
                    self.metrics.successful_dispatches += 1
                except Exception as e:
                    self.metrics.failed_dispatches += 1
                    print(f"Error in AsyncDispatcher: {str(e)}")
                finally:
                    processing_time = time.time() - start_time
                    self.metrics.processing_times[callback.__name__].append(processing_time)
                    
                self.log_queue.task_done()
                
            except queue.Empty:
                continue
                
    def dispatch(self, callback: Callable, *args: Any, **kwargs: Any) -> None:
        """Dispatch a logging operation asynchronously."""
        self.metrics.total_dispatches += 1
        try:
            self.log_queue.put((callback, args, kwargs), timeout=1.0)
        except queue.Full:
            self.metrics.queue_full_count += 1
            # If queue is full, log synchronously as fallback
            callback(*args, **kwargs)
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "total_dispatches": self.metrics.total_dispatches,
            "successful_dispatches": self.metrics.successful_dispatches,
            "failed_dispatches": self.metrics.failed_dispatches,
            "queue_full_count": self.metrics.queue_full_count,
            "average_processing_times": {
                name: sum(times) / len(times) if times else 0
                for name, times in self.metrics.processing_times.items()
            }
        }
            
    def shutdown(self) -> None:
        """Gracefully shutdown the dispatcher."""
        self.is_running = False
        if self.worker_thread:
            self.log_queue.put(None)  # Signal worker to stop
            self.worker_thread.join(timeout=5.0) 

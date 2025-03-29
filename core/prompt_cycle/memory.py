import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from threading import Lock
from core.PathManager import PathManager

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manages memory for the prompt cycle system.
    Handles storing, retrieving, and updating insights from interactions.
    """
    
    def __init__(self, system_state=None):
        """
        Initialize the memory manager.
        
        Args:
            system_state: Optional reference to the system state
        """
        self.system_state = system_state
        self.lock = Lock()
        
        # Use PathManager for file paths
        self.memory_file = PathManager.get_path('memory', 'unified_feedback.json')
        
        # Initialize memory storage
        self.insights = {
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "insights": []
        }
        
        # Load existing insights if available
        self._load_memory()
    
    def _load_memory(self) -> None:
        """Load memory from file."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.insights = data
                    logger.info(f"Loaded memory from {self.memory_file}")
            else:
                logger.info("No memory file found. Starting with empty memory.")
        except Exception as e:
            logger.error(f"Failed to load file {self.memory_file}: {e}")
    
    def _save_memory(self) -> None:
        """Save memory to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.insights, f, indent=2)
                logger.info(f"Saved memory to {self.memory_file}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def store_insights(self, insights: str, category: str, source: str, timestamp: str = None) -> None:
        """
        Store new insights in memory.
        
        Args:
            insights: The insight text
            category: Category of the insight (e.g., 'prompt_cycle', 'audit')
            source: Source of the insight (e.g., 'user', 'system')
            timestamp: Optional timestamp (default: current time)
        """
        with self.lock:
            if not timestamp:
                timestamp = datetime.now().isoformat()
                
            insight_entry = {
                "text": insights,
                "category": category,
                "source": source,
                "timestamp": timestamp,
                "id": f"insight_{len(self.insights['insights']) + 1}"
            }
            
            self.insights["insights"].append(insight_entry)
            self.insights["last_updated"] = datetime.now().isoformat()
            
            # Update system state if available
            if self.system_state:
                self.system_state.add_event("memory_update", {
                    "insight_id": insight_entry["id"],
                    "category": category,
                    "source": source
                })
            
            self._save_memory()
    
    def get_insights(self, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve insights from memory, optionally filtered by category.
        
        Args:
            category: Optional category to filter by
            limit: Maximum number of insights to return
            
        Returns:
            List of insight entries
        """
        with self.lock:
            insights = self.insights["insights"]
            
            if category:
                insights = [i for i in insights if i["category"] == category]
                
            # Sort by timestamp (newest first)
            insights = sorted(insights, key=lambda x: x["timestamp"], reverse=True)
            
            return insights[:limit]
    
    def update(self, feedback: Dict[str, Any], narrative_data: Dict[str, Any], system_state: Dict[str, Any]) -> None:
        """
        Update memory with new feedback and narrative data.
        
        Args:
            feedback: Feedback data
            narrative_data: Narrative data
            system_state: Current system state
        """
        with self.lock:
            # Store feedback as insight
            if feedback and isinstance(feedback, dict) and "text" in feedback:
                self.store_insights(
                    insights=feedback["text"],
                    category=feedback.get("category", "feedback"),
                    source=feedback.get("source", "system")
                )
            
            # Store narrative elements
            if narrative_data and isinstance(narrative_data, dict):
                for key, value in narrative_data.items():
                    if isinstance(value, str) and value.strip():
                        self.store_insights(
                            insights=value,
                            category=f"narrative_{key}",
                            source="narrative_manager"
                        )
            
            # Update system state reference if available
            if system_state and self.system_state:
                self.system_state.update_state(system_state)
    
    def search_memory(self, query: str) -> List[Dict[str, Any]]:
        """
        Search memory for insights matching the query.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching insights
        """
        with self.lock:
            # Simple case-insensitive search
            query = query.lower()
            results = [
                insight for insight in self.insights["insights"]
                if query in insight["text"].lower()
            ]
            
            return results
    
    def generate_memory_report(self) -> Dict[str, Any]:
        """
        Generate a report of the current memory state.
        
        Returns:
            Dictionary containing memory statistics and insights
        """
        with self.lock:
            # Count insights by category
            categories = {}
            for insight in self.insights["insights"]:
                category = insight["category"]
                if category in categories:
                    categories[category] += 1
                else:
                    categories[category] = 1
            
            # Get recent insights
            recent_insights = self.get_insights(limit=5)
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "total_insights": len(self.insights["insights"]),
                "categories": categories,
                "recent_insights": recent_insights
            }
            
            # Save report to file
            report_file = PathManager.get_path('outputs', 'memory_report.json')
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(report_file), exist_ok=True)
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2)
                    logger.info(f"Memory report saved to {report_file}")
            except Exception as e:
                logger.error(f"Failed to save memory report: {e}")
            
            return report 
from typing import Dict, Any
import json
import os
from datetime import datetime
from .utils import get_timestamp, logger, ensure_directory, BASE_OUTPUT_PATH

class AuditManager:
    """Manages AI audits and audit reporting for the prompt cycle system."""
    
    def __init__(self, system_state):
        """
        Initialize the audit manager.
        
        Args:
            system_state: Reference to the system state manager
        """
        self.system_state = system_state
        self.audit_history = []
        ensure_directory(BASE_OUTPUT_PATH)
    
    def perform_audit(self, audit_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Perform an AI audit of the system.
        
        Args:
            audit_type: Type of audit to perform
            
        Returns:
            Dictionary containing audit results
        """
        try:
            # Generate audit prompt based on type
            audit_prompt = self._generate_audit_prompt(audit_type)
            
            # TODO: Implement actual audit execution
            # This would typically involve sending the prompt to an AI model
            # and processing the response
            
            # For now, return mock audit data
            audit_data = {
                "type": audit_type,
                "timestamp": get_timestamp(),
                "success": True,
                "score": 0.85,
                "findings": [
                    {
                        "category": "system_health",
                        "severity": "low",
                        "description": "System operating within normal parameters"
                    }
                ],
                "recommendations": [
                    "Consider optimizing memory usage",
                    "Review feedback loop effectiveness"
                ]
            }
            
            # Process and store audit results
            self._process_audit_response(audit_data)
            
            return audit_data
            
        except Exception as e:
            logger.error(f"Failed to perform audit: {e}")
            return {
                "type": audit_type,
                "timestamp": get_timestamp(),
                "success": False,
                "error": str(e)
            }
    
    def _generate_audit_prompt(self, audit_type: str) -> str:
        """
        Generate an appropriate audit prompt based on type.
        
        Args:
            audit_type: Type of audit to perform
            
        Returns:
            String containing the audit prompt
        """
        current_state = self.system_state.get_state()
        current_metrics = self.system_state.get_audit_metrics()
        
        prompt = f"""
        Perform a {audit_type} audit of the system with the following context:
        
        Current System State:
        {json.dumps(current_state, indent=2)}
        
        Current Audit Metrics:
        {json.dumps(current_metrics, indent=2)}
        
        Please analyze:
        1. System health and stability
        2. Memory management efficiency
        3. Narrative coherence
        4. Performance metrics
        5. Potential improvements
        
        Provide findings and recommendations in a structured format.
        """
        
        return prompt
    
    def _process_audit_response(self, audit_data: Dict[str, Any]) -> None:
        """
        Process and store audit response data.
        
        Args:
            audit_data: Dictionary containing audit results
        """
        try:
            # Update audit history
            self.audit_history.append(audit_data)
            
            # Update system state metrics
            self.system_state.update_audit_metrics(audit_data)
            
            # Generate and save audit report
            self._generate_audit_report(audit_data)
            
            logger.info("Audit response processed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process audit response: {e}")
    
    def _generate_audit_report(self, audit_data: Dict[str, Any]) -> None:
        """
        Generate and save an audit report.
        
        Args:
            audit_data: Dictionary containing audit results
        """
        try:
            # Create report directory if it doesn't exist
            report_dir = os.path.join(BASE_OUTPUT_PATH, "audit_reports")
            ensure_directory(report_dir)
            
            # Generate report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(report_dir, f"audit_report_{timestamp}.json")
            
            # Prepare report data
            report_data = {
                "audit_data": audit_data,
                "system_state": self.system_state.get_state(),
                "audit_metrics": self.system_state.get_audit_metrics(),
                "timestamp": get_timestamp()
            }
            
            # Save report
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"Audit report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate audit report: {e}")
    
    def get_audit_history(self) -> list:
        """Get the history of performed audits."""
        return self.audit_history.copy()
    
    def get_latest_audit(self) -> Dict[str, Any]:
        """Get the most recent audit data."""
        return self.audit_history[-1] if self.audit_history else {} 
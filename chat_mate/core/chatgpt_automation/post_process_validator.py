"""
Post-process validator for validating and processing model outputs.
"""

from typing import Any, Dict, Optional


class PostProcessValidator:
    """Validator for post-processing model outputs."""
    
    def __init__(self):
        """Initialize the post-process validator."""
        self.validation_rules = {}
    
    def validate_output(self, output: str, rules: Optional[Dict[str, Any]] = None) -> bool:
        """Validate model output against specified rules.
        
        Args:
            output (str): The model output to validate.
            rules (Optional[Dict[str, Any]]): Validation rules to apply.
            
        Returns:
            bool: True if validation passes, False otherwise.
        """
        if not output:
            return False
            
        if not rules:
            return True
            
        try:
            for rule_name, rule_config in rules.items():
                if not self._apply_rule(output, rule_name, rule_config):
                    return False
            return True
        except Exception as e:
            print(f"Error during validation: {e}")
            return False
    
    def _apply_rule(self, output: str, rule_name: str, rule_config: Any) -> bool:
        """Apply a specific validation rule.
        
        Args:
            output (str): The output to validate.
            rule_name (str): Name of the rule to apply.
            rule_config (Any): Configuration for the rule.
            
        Returns:
            bool: True if the rule passes, False otherwise.
        """
        if rule_name not in self.validation_rules:
            print(f"Unknown validation rule: {rule_name}")
            return False
            
        try:
            return self.validation_rules[rule_name](output, rule_config)
        except Exception as e:
            print(f"Error applying rule {rule_name}: {e}")
            return False
    
    def add_rule(self, rule_name: str, rule_func: callable):
        """Add a new validation rule.
        
        Args:
            rule_name (str): Name of the rule.
            rule_func (callable): Function implementing the rule.
        """
        self.validation_rules[rule_name] = rule_func
    
    def remove_rule(self, rule_name: str):
        """Remove a validation rule.
        
        Args:
            rule_name (str): Name of the rule to remove.
        """
        self.validation_rules.pop(rule_name, None)
    
    def clear_rules(self):
        """Clear all validation rules."""
        self.validation_rules.clear()
    
    def get_rules(self) -> Dict[str, callable]:
        """Get all validation rules.
        
        Returns:
            Dict[str, callable]: Dictionary of rule names and their functions.
        """
        return self.validation_rules.copy() 
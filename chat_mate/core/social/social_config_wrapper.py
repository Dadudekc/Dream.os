"""
Social Config Wrapper

This module provides a lightweight wrapper around social_config to break circular imports.
It delays the actual import until the get_social_config() function is called.
"""

_social_config_instance = None

def get_social_config():
    """
    Lazily import and instantiate the social_config.
    Returns the SocialConfig instance.
    """
    global _social_config_instance
    
    if _social_config_instance is None:
        # Only import when needed
        from social.social_config import SocialConfig
        _social_config_instance = SocialConfig()
        
    return _social_config_instance 

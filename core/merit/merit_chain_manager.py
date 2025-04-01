"""
Merit Chain Manager module for managing test merit chains.
"""
from typing import Optional, Any, Dict, List
import logging

class MeritChainManager:
    """Manager for test merit chains."""
    
    def __init__(
        self,
        prompt_manager: Any,
        chat_manager: Any,
        config: Any,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the merit chain manager.
        
        Args:
            prompt_manager: The prompt manager instance
            chat_manager: The chat manager instance
            config: The configuration manager
            logger: Optional logger instance
        """
        self.prompt_manager = prompt_manager
        self.chat_manager = chat_manager
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.chains = []
        
    def create_chain(self, test_id: str) -> Optional[Dict]:
        """
        Create a new merit chain.
        
        Args:
            test_id: The test identifier
            
        Returns:
            The created chain or None
        """
        try:
            chain = {
                "test_id": test_id,
                "status": "created",
                "links": []
            }
            self.chains.append(chain)
            self.logger.info(f"Created merit chain for test: {test_id}")
            return chain
        except Exception as e:
            self.logger.error(f"Error creating merit chain: {e}")
            return None
            
    def add_link(self, test_id: str, link_data: Dict) -> bool:
        """
        Add a link to a merit chain.
        
        Args:
            test_id: The test identifier
            link_data: The link data
            
        Returns:
            True if added successfully
        """
        try:
            for chain in self.chains:
                if chain["test_id"] == test_id:
                    chain["links"].append(link_data)
                    self.logger.info(f"Added link to chain {test_id}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error adding link: {e}")
            return False
            
    def get_chain(self, test_id: str) -> Optional[Dict]:
        """
        Get a merit chain.
        
        Args:
            test_id: The test identifier
            
        Returns:
            The merit chain or None
        """
        try:
            for chain in self.chains:
                if chain["test_id"] == test_id:
                    return chain
            return None
        except Exception as e:
            self.logger.error(f"Error getting chain: {e}")
            return None
            
    def get_all_chains(self) -> List[Dict]:
        """
        Get all merit chains.
        
        Returns:
            List of all merit chains
        """
        return self.chains 
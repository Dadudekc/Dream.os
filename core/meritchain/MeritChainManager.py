#!/usr/bin/env python3
"""
MeritChainManager - Manager for saving and retrieving merit chain entries
========================================================================

The MeritChainManager is responsible for:
1. Saving and validating entries to the merit chain JSON file
2. Retrieving entries from the merit chain
3. Validating entries against a JSON schema
4. Providing query interfaces to find entries by username, platform, etc.

This is used primarily by the MeredithDispatcher to save high-resonance matches.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import jsonschema

# Configure logger
logger = logging.getLogger(__name__)

class MeritChainManager:
    """
    Manager for the merit chain, a persistent record of resonance matches.
    Provides validation via JSON Schema and data access methods.
    """
    
    def __init__(self, filepath: str, schema_path: str):
        """
        Initialize the MeritChainManager.
        
        Args:
            filepath: Path to the JSON file storing the merit chain
            schema_path: Path to the JSON schema file for validation
        """
        self.filepath = filepath
        self.schema_path = schema_path
        self._schema = self._load_schema()
        self._chain = self._load()
        logger.info(f"MeritChainManager initialized with file: {filepath}")
        
    def _load_schema(self) -> Dict[str, Any]:
        """
        Load the JSON schema for validation.
        
        Returns:
            The loaded JSON schema
        """
        try:
            if os.path.exists(self.schema_path):
                with open(self.schema_path, 'r') as f:
                    schema = json.load(f)
                    logger.info(f"Loaded schema from {self.schema_path}")
                    return schema
            else:
                logger.warning(f"Schema file not found: {self.schema_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading schema: {e}")
            return {}
    
    def validate_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Validate an entry against the JSON schema.
        
        Args:
            entry: The entry to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self._schema:
            logger.warning("No schema loaded, skipping validation")
            return True
        
        try:
            jsonschema.validate(instance=entry, schema=self._schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def save(self, entry: Dict[str, Any]) -> bool:
        """
        Save an entry to the merit chain.
        
        Args:
            entry: The entry to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        # Validate entry
        if not self.validate_entry(entry):
            logger.error("Entry validation failed, not saving")
            return False
        
        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()
        
        # Append to chain
        self._chain.append(entry)
        
        # Save to file
        self._write()
        logger.info(f"Added entry for {entry.get('username', 'unknown')} to merit chain")
        
        return True
    
    def all(self) -> List[Dict[str, Any]]:
        """
        Get all entries in the merit chain.
        
        Returns:
            List of all entries
        """
        return self._chain
    
    def query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query the merit chain with filters.
        
        Args:
            filters: Dictionary of field names and values to match
            
        Returns:
            List of matching entries
        """
        results = []
        
        for entry in self._chain:
            match = True
            
            for key, value in filters.items():
                if key not in entry:
                    match = False
                    break
                
                # Handle list type filtering
                if isinstance(entry[key], list) and not isinstance(value, list):
                    if value not in entry[key]:
                        match = False
                        break
                # Direct comparison for other types
                elif entry[key] != value:
                    match = False
                    break
            
            if match:
                results.append(entry)
        
        return results
    
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get an entry by username.
        
        Args:
            username: Username to search for
            
        Returns:
            Matching entry or None if not found
        """
        results = self.query({"username": username})
        return results[0] if results else None
    
    def _load(self) -> List[Dict[str, Any]]:
        """
        Load the merit chain from the file.
        
        Returns:
            List of entries from the file or an empty list if file doesn't exist
        """
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} entries from {self.filepath}")
                    return data
            else:
                logger.info(f"Merit chain file not found, creating new chain: {self.filepath}")
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                return []
        except Exception as e:
            logger.error(f"Error loading merit chain: {e}")
            return []
    
    def _write(self) -> None:
        """Save the merit chain to the file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            
            with open(self.filepath, 'w') as f:
                json.dump(self._chain, f, indent=2)
            
            logger.info(f"Saved {len(self._chain)} entries to {self.filepath}")
        except Exception as e:
            logger.error(f"Error saving merit chain: {e}")

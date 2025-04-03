#!/usr/bin/env python3
"""
MeritChainManager.py

Handles persistent logging, querying, and filtering of resonance matches
detected by Meredith. Stores data in JSON format for durability and auditability.
Validates entries against a JSON schema to ensure data integrity.
"""

import json
import os
import threading
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import the jsonschema validation module
import jsonschema
from jsonschema import validators

# Set up logging
logger = logging.getLogger("MeritChainManager")

class MeritChainManager:
    def __init__(self, filepath: str = "memory/meritchain.json", schema_path: str = "core/schemas/merit_chain_schema.json"):
        self.filepath = filepath
        self.schema_path = schema_path
        self._lock = threading.Lock()
        self._schema = None
        
        # Create paths if they don't exist
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        # Initialize empty storage if file doesn't exist
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w") as f:
                json.dump([], f)
        
        # Load the schema
        self._load_schema()

    def _load_schema(self):
        """
        Load the JSON schema for validating merit chain entries.
        """
        try:
            if os.path.exists(self.schema_path):
                with open(self.schema_path, 'r') as f:
                    self._schema = json.load(f)
                logger.info(f"Loaded schema from {self.schema_path}")
            else:
                logger.warning(f"Schema file not found at {self.schema_path}, validation will be skipped")
        except Exception as e:
            logger.error(f"Error loading schema: {e}")
            self._schema = None

    def validate_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Validates an entry against the JSON schema.
        
        Returns:
            bool: True if validation passes, False otherwise
        """
        if not self._schema:
            logger.warning("No schema loaded, skipping validation")
            return True
            
        try:
            jsonschema.validate(instance=entry, schema=self._schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    def save(self, entry: Dict[str, Any]) -> bool:
        """
        Appends a new match entry to the merit chain after validating it.
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if not entry.get("should_save_to_meritchain"):
            logger.info("Entry marked as should_save_to_meritchain=False, skipping")
            return False

        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()

        # Validate the entry
        if not self.validate_entry(entry):
            logger.error("Entry failed validation, not saving to merit chain")
            return False

        with self._lock:
            try:
                chain = self._load()
                chain.append(entry)
                self._write(chain)
                logger.info(f"Successfully saved merit entry for {entry.get('username')}")
                return True
            except Exception as e:
                logger.error(f"Error saving entry: {e}")
                return False

    def query(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Returns all entries matching the given filters (e.g. username, platform, tags).
        """
        with self._lock:
            chain = self._load()
            results = []

            for entry in chain:
                match = True
                for key, value in filters.items():
                    if key not in entry:
                        match = False
                        break
                    if isinstance(value, list) and isinstance(entry.get(key), list):
                        # For list types, check if any item in the filter list is in the entry list
                        if not any(tag in entry.get(key, []) for tag in value):
                            match = False
                            break
                    elif isinstance(value, str) and str(entry.get(key)) != value:
                        match = False
                        break
                    elif not isinstance(value, (list, str)) and entry.get(key) != value:
                        match = False
                        break
                if match:
                    results.append(entry)

            return results

    def all(self) -> List[Dict[str, Any]]:
        """
        Returns the full meritchain.
        """
        with self._lock:
            return self._load()
            
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a merit chain entry by username.
        
        Returns:
            Dict or None: The entry if found, None otherwise
        """
        results = self.query({"username": username})
        return results[0] if results else None

    def _load(self) -> List[Dict[str, Any]]:
        """
        Loads the merit chain from the file.
        """
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading chain: {e}")
            return []

    def _write(self, chain: List[Dict[str, Any]]):
        """
        Writes the merit chain to the file.
        """
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(chain, f, indent=2)

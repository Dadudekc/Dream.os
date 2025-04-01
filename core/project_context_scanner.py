#!/usr/bin/env python3
"""
Project Context Scanner

This module provides a lightweight scanner for extracting project context
for use in prompt orchestration. It integrates with the existing ProjectScanner
implementation but focuses specifically on providing context for prompt generation.
"""

import os
import sys
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Union
from datetime import datetime

# Try to import the existing ProjectScanner implementation
try:
    from ProjectScanner import ProjectScanner as BaseProjectScanner
    HAS_PROJECT_SCANNER = True
except ImportError:
    HAS_PROJECT_SCANNER = False
    
logger = logging.getLogger(__name__)

class ProjectContextScanner:
    """
    Scans a project directory to extract context information for use in prompt generation.
    
    This scanner focuses on extracting project metadata, structure, and key components
    to provide context for task generation and execution.
    """
    
    def __init__(self, 
                project_root: Union[str, Path] = ".",
                memory_file: str = "memory/project_context.json",
                scan_on_init: bool = True,
                max_depth: int = 3,
                exclude_dirs: Optional[List[str]] = None,
                exclude_extensions: Optional[List[str]] = None,
                callbacks: Optional[Dict[str, callable]] = None):
        """
        Initialize the ProjectContextScanner.
        
        Args:
            project_root: Root directory of the project
            memory_file: File to store context data
            scan_on_init: Whether to scan the project during initialization
            max_depth: Maximum directory depth to scan
            exclude_dirs: Directories to exclude
            exclude_extensions: File extensions to exclude
            callbacks: Callbacks for scan events
        """
        self.project_root = Path(project_root)
        self.memory_file = memory_file
        self.max_depth = max_depth
        self.exclude_dirs = exclude_dirs or [
            ".git", ".cursor", "__pycache__", "venv", ".venv", "node_modules", 
            ".idea", ".vscode", ".ipynb_checkpoints", "__MACOSX"
        ]
        self.exclude_extensions = exclude_extensions or [
            ".pyc", ".dll", ".exe", ".obj", ".so", ".lib", ".dylib", ".a", ".o",
            ".zip", ".tar", ".gz", ".xz", ".7z", ".rar", ".jar",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".ico", ".webp",
            ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flv", ".wmv",
            ".pyd", ".ipynb", ".pkl", ".pickle", ".lock", ".db"
        ]
        
        self.callbacks = callbacks or {}
        
        # Used to track changes in context between scans
        self.last_scan_time = None
        self.context_changed = False
        
        # Core paths for project structure
        self.core_paths = set()
        
        # Ensure memory directory exists
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        
        # Initialize context data
        self.context: Dict[str, Any] = {
            "project_structure": {},
            "key_components": [],
            "file_metadata": {},
            "repository_info": {},
            "languages": {},
            "dependencies": {},
            "last_scan": None
        }
        
        # Load any existing context
        self._load_context()
        
        # Scan on initialization if requested
        if scan_on_init:
            self.scan()
    
    def _load_context(self) -> None:
        """Load context from the memory file if it exists."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    self.context = json.load(f)
                logger.info(f"Loaded project context from {self.memory_file}")
            except Exception as e:
                logger.error(f"Error loading project context: {e}")
    
    def _save_context(self) -> None:
        """Save context to the memory file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.context, f, indent=2)
            logger.info(f"Saved project context to {self.memory_file}")
        except Exception as e:
            logger.error(f"Error saving project context: {e}")
    
    def _trigger_callback(self, event: str, data: Any = None) -> None:
        """
        Trigger a callback for a specific event.
        
        Args:
            event: Name of the event
            data: Data to pass to the callback
        """
        if event in self.callbacks and callable(self.callbacks[event]):
            try:
                self.callbacks[event](data)
            except Exception as e:
                logger.error(f"Error in callback for event {event}: {e}")
    
    def scan(self) -> Dict[str, Any]:
        """
        Scan the project directory for context information.
        
        Returns:
            Updated context data
        """
        scan_start = datetime.now()
        
        # Trigger scan start callback
        self._trigger_callback("on_scan_start", {"timestamp": scan_start.isoformat()})
        
        # Check if we can use the existing ProjectScanner
        if HAS_PROJECT_SCANNER:
            logger.info("Using existing ProjectScanner for full project analysis")
            self._scan_with_project_scanner()
        else:
            logger.info("ProjectScanner not available, using lightweight scanning")
            self._scan_lightweight()
        
        # Update scan timestamp
        self.context["last_scan"] = datetime.now().isoformat()
        self.last_scan_time = datetime.now()
        
        # Save updated context
        self._save_context()
        
        # Trigger scan complete callback
        self._trigger_callback("on_scan_complete", {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - scan_start).total_seconds(),
            "changed": self.context_changed
        })
        
        return self.context
    
    def _scan_with_project_scanner(self) -> None:
        """Use the existing ProjectScanner to perform a detailed analysis."""
        try:
            # Initialize the base ProjectScanner
            scanner = BaseProjectScanner(project_root=self.project_root)
            
            # Scan project
            scanner.scan_project()
            
            # Get analysis data
            project_analysis_path = Path(self.project_root) / "project_analysis.json"
            if project_analysis_path.exists():
                with open(project_analysis_path, 'r') as f:
                    project_analysis = json.load(f)
                
                # Update our context with analysis data
                self.context["file_metadata"] = project_analysis
                
                # Extract language statistics
                self.context["languages"] = self._extract_language_stats(project_analysis)
                
                # Mark context as changed
                self.context_changed = True
            
            # Update project structure
            self._update_project_structure()
            
        except Exception as e:
            logger.error(f"Error using ProjectScanner: {e}")
            # Fall back to lightweight scanning
            self._scan_lightweight()
    
    def _extract_language_stats(self, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract language statistics from project analysis.
        
        Args:
            project_analysis: Project analysis data
            
        Returns:
            Language statistics
        """
        languages = {}
        
        # Count files by language
        for file_path, file_data in project_analysis.items():
            if isinstance(file_data, dict) and "language" in file_data:
                lang = file_data["language"].strip(".")
                if lang not in languages:
                    languages[lang] = {
                        "count": 0,
                        "complexity": 0,
                        "functions": 0,
                        "classes": 0
                    }
                
                languages[lang]["count"] += 1
                languages[lang]["complexity"] += file_data.get("complexity", 0)
                languages[lang]["functions"] += len(file_data.get("functions", []))
                languages[lang]["classes"] += len(file_data.get("classes", {}))
        
        return languages
    
    def _scan_lightweight(self) -> None:
        """Perform a lightweight scan of the project directory."""
        # Update project structure
        self._update_project_structure()
        
        # Count files by extension
        file_extensions = {}
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            
            for file in files:
                if self._should_exclude_file(file):
                    continue
                
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    file_extensions[ext] = file_extensions.get(ext, 0) + 1
        
        # Map extensions to languages
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react-typescript",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".less": "less",
            ".json": "json",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".md": "markdown",
            ".rst": "rst",
            ".txt": "text",
            ".sh": "shell",
            ".bat": "batch",
            ".ps1": "powershell",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c-header",
            ".hpp": "cpp-header",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".go": "go",
            ".rs": "rust",
            ".swift": "swift",
            ".kt": "kotlin",
            ".dart": "dart",
            ".lua": "lua"
        }
        
        # Create language statistics
        languages = {}
        for ext, count in file_extensions.items():
            lang = ext_to_lang.get(ext, ext.strip(".").lower())
            if lang not in languages:
                languages[lang] = {
                    "count": 0,
                    "extensions": []
                }
            languages[lang]["count"] += count
            if ext not in languages[lang]["extensions"]:
                languages[lang]["extensions"].append(ext)
        
        # Update context
        self.context["languages"] = languages
        
        # Mark context as changed
        self.context_changed = True
    
    def _update_project_structure(self) -> None:
        """Update the project structure in the context."""
        structure = {}
        
        def add_to_structure(path_parts, current_level):
            if not path_parts:
                return
            
            current = path_parts[0]
            if current not in current_level:
                current_level[current] = {}
            
            if len(path_parts) > 1:
                add_to_structure(path_parts[1:], current_level[current])
        
        # Find important directories (up to max_depth)
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            
            # Calculate relative path and depth
            rel_path = os.path.relpath(root, self.project_root)
            if rel_path == ".":
                rel_path = ""
            
            depth = 0 if rel_path == "" else rel_path.count(os.sep) + 1
            if depth > self.max_depth:
                continue
            
            # Add to core paths if it contains Python files
            has_python = any(f.endswith('.py') for f in files)
            if has_python:
                self.core_paths.add(rel_path if rel_path else ".")
            
            # Add to structure
            if rel_path:
                path_parts = rel_path.split(os.sep)
                add_to_structure(path_parts, structure)
            
            # Add directories at this level
            if depth < self.max_depth:
                if rel_path not in structure:
                    structure[rel_path] = {}
                
                for dir_name in dirs:
                    if rel_path:
                        current = structure
                        for part in rel_path.split(os.sep):
                            current = current[part]
                        current[dir_name] = {}
                    else:
                        structure[dir_name] = {}
        
        # Update context
        self.context["project_structure"] = structure
        
        # Update core paths list
        self.context["core_paths"] = sorted(list(self.core_paths))
    
    def _should_exclude_file(self, filename: str) -> bool:
        """
        Check if a file should be excluded.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if the file should be excluded, False otherwise
        """
        return any(filename.endswith(ext) for ext in self.exclude_extensions)
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get the current context.
        
        Returns:
            Current context data
        """
        return self.context
    
    def get_context_for_template(self, template_name: str) -> Dict[str, Any]:
        """
        Get context data specifically formatted for a template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Context data formatted for the template
        """
        # Base context with project metadata
        template_context = {
            "project_name": os.path.basename(self.project_root),
            "scan_time": self.context.get("last_scan"),
            "project_structure": self.context.get("project_structure", {}),
            "core_paths": self.context.get("core_paths", []),
            "languages": self.context.get("languages", {})
        }
        
        # Add specific context formatting based on template name
        if "service" in template_name.lower():
            # For service templates, include info about existing services
            template_context["existing_services"] = self._find_service_classes()
            
        elif "ui" in template_name.lower() or "tab" in template_name.lower():
            # For UI templates, include info about existing UI components
            template_context["existing_ui_components"] = self._find_ui_components()
            
        elif "test" in template_name.lower():
            # For test templates, include info about what should be tested
            template_context["testable_components"] = self._find_testable_components()
            
        elif "factory" in template_name.lower():
            # For factory templates, include info about existing factories
            template_context["existing_factories"] = self._find_factory_classes()
        
        return template_context
    
    def _find_service_classes(self) -> List[Dict[str, Any]]:
        """
        Find service classes in the project.
        
        Returns:
            List of service class information
        """
        services = []
        
        if not HAS_PROJECT_SCANNER:
            return services
        
        for file_path, metadata in self.context.get("file_metadata", {}).items():
            if not isinstance(metadata, dict) or "classes" not in metadata:
                continue
                
            for class_name, class_data in metadata.get("classes", {}).items():
                # Check if it's likely a service
                is_service = (
                    "Service" in class_name or 
                    "Manager" in class_name or 
                    "Engine" in class_name or
                    "Provider" in class_name or
                    "Handler" in class_name
                )
                
                if is_service:
                    services.append({
                        "name": class_name,
                        "file": file_path,
                        "methods": class_data.get("methods", []),
                        "base_classes": class_data.get("base_classes", [])
                    })
        
        return services
    
    def _find_ui_components(self) -> List[Dict[str, Any]]:
        """
        Find UI components in the project.
        
        Returns:
            List of UI component information
        """
        components = []
        
        if not HAS_PROJECT_SCANNER:
            return components
        
        for file_path, metadata in self.context.get("file_metadata", {}).items():
            if not isinstance(metadata, dict) or "classes" not in metadata:
                continue
                
            for class_name, class_data in metadata.get("classes", {}).items():
                # Check if it's likely a UI component
                is_ui = (
                    "Tab" in class_name or 
                    "Dialog" in class_name or 
                    "Window" in class_name or
                    "Widget" in class_name or
                    "Panel" in class_name or
                    "View" in class_name
                )
                
                if is_ui:
                    components.append({
                        "name": class_name,
                        "file": file_path,
                        "methods": class_data.get("methods", []),
                        "base_classes": class_data.get("base_classes", [])
                    })
        
        return components
    
    def _find_testable_components(self) -> List[Dict[str, Any]]:
        """
        Find testable components in the project.
        
        Returns:
            List of testable component information
        """
        components = []
        
        if not HAS_PROJECT_SCANNER:
            return components
        
        # First, get all normal classes
        for file_path, metadata in self.context.get("file_metadata", {}).items():
            if not isinstance(metadata, dict) or "classes" not in metadata:
                continue
                
            for class_name, class_data in metadata.get("classes", {}).items():
                # Skip test classes
                if "Test" in class_name:
                    continue
                    
                components.append({
                    "name": class_name,
                    "file": file_path,
                    "methods": class_data.get("methods", []),
                    "base_classes": class_data.get("base_classes", []),
                    "has_test": False
                })
        
        # Now check which ones have tests
        for file_path, metadata in self.context.get("file_metadata", {}).items():
            if not isinstance(metadata, dict) or "classes" not in metadata:
                continue
                
            for class_name, class_data in metadata.get("classes", {}).items():
                if "Test" not in class_name:
                    continue
                    
                # Extract the base name (remove "Test" suffix)
                base_name = class_name.replace("Test", "")
                
                # Mark corresponding component as having a test
                for component in components:
                    if component["name"] == base_name:
                        component["has_test"] = True
                        component["test_class"] = class_name
                        component["test_file"] = file_path
                        break
        
        return components
    
    def _find_factory_classes(self) -> List[Dict[str, Any]]:
        """
        Find factory classes in the project.
        
        Returns:
            List of factory class information
        """
        factories = []
        
        if not HAS_PROJECT_SCANNER:
            return factories
        
        for file_path, metadata in self.context.get("file_metadata", {}).items():
            if not isinstance(metadata, dict) or "classes" not in metadata:
                continue
                
            for class_name, class_data in metadata.get("classes", {}).items():
                # Check if it's likely a factory
                is_factory = (
                    "Factory" in class_name or 
                    "Builder" in class_name or 
                    "Provider" in class_name
                )
                
                if is_factory:
                    factories.append({
                        "name": class_name,
                        "file": file_path,
                        "methods": class_data.get("methods", []),
                        "base_classes": class_data.get("base_classes", [])
                    })
        
        return factories
    
    def has_context_changed(self) -> bool:
        """
        Check if the context has changed since the last scan.
        
        Returns:
            True if the context has changed, False otherwise
        """
        return self.context_changed 
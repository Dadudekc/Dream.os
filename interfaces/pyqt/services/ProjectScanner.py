"""
Project Scanner Service

This service analyzes the project structure and code to provide context 
for the ContextualChatTab. It can scan the current project or load cached results.
"""

import logging
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ProjectScanner:
    """
    Service for analyzing the project structure and code to provide context
    for AI prompts. Can scan the project or load cached results.
    """
    
    def __init__(self, project_root: str = '.', cache_path: Optional[str] = None):
        """
        Initialize the ProjectScanner.
        
        Args:
            project_root: Path to the project root directory
            cache_path: Optional path to store/load scan results cache
        """
        self.project_root = Path(project_root).resolve()
        self.cache_path = Path(cache_path).resolve() if cache_path else self.project_root / 'analysis_cache.json'
        self.logger = logger
        
        # Initialize with empty analysis
        self.cached_analysis = {
            "files": [],
            "structure": {},
            "imports": {},
            "dependencies": [],
            "classes": {},
            "functions": {},
        }
        
    def scan_project(self, max_files: int = 500, file_extensions: List[str] = ['.py', '.js', '.ts', '.html', '.css']) -> Dict[str, Any]:
        """
        Scan the project and generate a structure analysis.
        
        Args:
            max_files: Maximum number of files to scan
            file_extensions: List of file extensions to include
            
        Returns:
            Dictionary containing analysis results
        """
        self.logger.info(f"Scanning project at {self.project_root}")
        
        # Initialize analysis dict
        analysis = {
            "files": [],
            "structure": {},
            "imports": {},
            "dependencies": [],
            "classes": {},
            "functions": {},
        }
        
        # Basic file/folder structure scan
        try:
            analysis["structure"] = self._scan_directory_structure(self.project_root)
            
            # Find files
            file_paths = []
            for ext in file_extensions:
                file_paths.extend(list(self.project_root.glob(f"**/*{ext}")))
                
            # Limit to max_files
            file_paths = file_paths[:max_files]
            analysis["files"] = [str(f.relative_to(self.project_root)) for f in file_paths]
            
            # Extract metadata from each file
            for file_path in file_paths:
                rel_path = str(file_path.relative_to(self.project_root))
                analysis["classes"][rel_path] = self._extract_classes(file_path)
                analysis["functions"][rel_path] = self._extract_functions(file_path)
                analysis["imports"][rel_path] = self._extract_imports(file_path)
            
            # Save the results
            self.cached_analysis = analysis
            self._save_cache()
            
            self.logger.info(f"Project scan complete. Found {len(analysis['files'])} files.")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error scanning project: {e}", exc_info=True)
            return self.cached_analysis
        
    def load_cache(self) -> Dict[str, Any]:
        """
        Load the cached analysis results, if available.
        
        Returns:
            Dictionary containing analysis results
        """
        try:
            if self.cache_path.exists():
                with open(self.cache_path, 'r') as f:
                    self.cached_analysis = json.load(f)
                self.logger.info(f"Loaded cached analysis from {self.cache_path}")
            else:
                self.logger.warning(f"No cache file found at {self.cache_path}")
        except Exception as e:
            self.logger.error(f"Error loading cache: {e}", exc_info=True)
            
        return self.cached_analysis
        
    def _save_cache(self):
        """Save the analysis results to the cache file."""
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(self.cached_analysis, f, indent=2)
            self.logger.info(f"Saved analysis cache to {self.cache_path}")
        except Exception as e:
            self.logger.error(f"Error saving cache: {e}", exc_info=True)
            
    def _scan_directory_structure(self, path: Path, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
        """
        Recursively scan the directory structure.
        
        Args:
            path: Starting directory path
            max_depth: Maximum directory depth to scan
            current_depth: Current recursion depth
            
        Returns:
            Dictionary representing the directory structure
        """
        if current_depth > max_depth:
            return {"name": path.name, "type": "dir", "truncated": True}
            
        result = {
            "name": path.name,
            "type": "dir",
            "children": []
        }
        
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith('.') and not item.name == "__pycache__":
                    child = self._scan_directory_structure(item, max_depth, current_depth + 1)
                    result["children"].append(child)
                elif item.is_file():
                    result["children"].append({
                        "name": item.name,
                        "type": "file",
                        "ext": item.suffix
                    })
        except Exception as e:
            self.logger.error(f"Error scanning directory {path}: {e}")
            
        return result
        
    def _extract_classes(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extract class definitions from a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of dictionaries containing class information
        """
        # Simple regex-based class extraction
        classes = []
        
        if not file_path.suffix == '.py':
            return classes
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            import re
            class_matches = re.finditer(r'class\s+(\w+)(?:\(([^)]*)\))?:', content)
            
            for match in class_matches:
                class_name = match.group(1)
                base_classes = match.group(2) or ""
                
                classes.append({
                    "name": class_name,
                    "bases": [b.strip() for b in base_classes.split(',') if b.strip()],
                    "file": str(file_path.relative_to(self.project_root))
                })
                
        except Exception as e:
            self.logger.error(f"Error extracting classes from {file_path}: {e}")
            
        return classes
        
    def _extract_functions(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extract function definitions from a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of dictionaries containing function information
        """
        # Simple regex-based function extraction
        functions = []
        
        if not file_path.suffix == '.py':
            return functions
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            import re
            func_matches = re.finditer(r'def\s+(\w+)\s*\(([^)]*)\):', content)
            
            for match in func_matches:
                func_name = match.group(1)
                params = match.group(2) or ""
                
                functions.append({
                    "name": func_name,
                    "params": [p.strip() for p in params.split(',') if p.strip()],
                    "file": str(file_path.relative_to(self.project_root))
                })
                
        except Exception as e:
            self.logger.error(f"Error extracting functions from {file_path}: {e}")
            
        return functions
        
    def _extract_imports(self, file_path: Path) -> List[str]:
        """
        Extract import statements from a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of import statements
        """
        imports = []
        
        if not file_path.suffix == '.py':
            return imports
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            import re
            import_matches = re.finditer(r'^(?:from\s+(\S+)\s+import\s+(.+)|import\s+(.+))$', content, re.MULTILINE)
            
            for match in import_matches:
                if match.group(1) and match.group(2):  # from X import Y
                    imports.append(f"from {match.group(1)} import {match.group(2)}")
                elif match.group(3):  # import X
                    imports.append(f"import {match.group(3)}")
                
        except Exception as e:
            self.logger.error(f"Error extracting imports from {file_path}: {e}")
            
        return imports
        
    def get_analysis_summary(self) -> str:
        """
        Get a text summary of the project analysis.
        
        Returns:
            String containing a summary of the analysis
        """
        # Load cache if needed
        if not self.cached_analysis["files"]:
            self.load_cache()
            
        # Build a text summary
        summary = [
            f"# Project Analysis Summary",
            f"",
            f"## Statistics",
            f"- Files: {len(self.cached_analysis['files'])}",
            f"- Classes: {sum(len(classes) for classes in self.cached_analysis['classes'].values())}",
            f"- Functions: {sum(len(funcs) for funcs in self.cached_analysis['functions'].values())}",
            f"",
            f"## Key Components",
        ]
        
        # Add top-level directories
        if "children" in self.cached_analysis.get("structure", {}):
            summary.append("### Project Structure")
            for child in self.cached_analysis["structure"].get("children", []):
                if child.get("type") == "dir":
                    summary.append(f"- {child.get('name', 'Unknown')}/")
            summary.append("")
        
        # Add some key classes
        all_classes = []
        for file_classes in self.cached_analysis["classes"].values():
            all_classes.extend(file_classes)
            
        if all_classes:
            summary.append("### Key Classes")
            for cls in all_classes[:10]:  # limit to 10
                summary.append(f"- {cls.get('name', 'Unknown')} ({cls.get('file', 'Unknown file')})")
                
        return "\n".join(summary) 
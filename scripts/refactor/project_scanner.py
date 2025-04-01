#!/usr/bin/env python3
"""
Project Scanner for Dream.OS Source Reclamation

Performs deep analysis of the codebase to generate intelligence maps for:
- File metadata and types
- Import dependencies
- Class/function analysis
- Test coverage mapping
- Usage patterns and timestamps
"""

import ast
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)'
)
logger = logging.getLogger('dream_os.scanner')

@dataclass
class ImportInfo:
    """Information about module imports."""
    module_name: str
    imported_names: List[str]
    is_relative: bool
    level: int = 0

@dataclass
class FunctionInfo:
    """Information about function definitions."""
    name: str
    args: List[str]
    returns: Optional[str]
    is_async: bool
    decorators: List[str]
    docstring: Optional[str]
    start_line: int
    end_line: int

@dataclass
class ClassInfo:
    """Information about class definitions."""
    name: str
    bases: List[str]
    methods: List[FunctionInfo]
    decorators: List[str]
    docstring: Optional[str]
    start_line: int
    end_line: int

@dataclass
class FileAnalysis:
    """Complete analysis of a Python file."""
    path: str
    type: str  # service, test, utility, agent, interface, etc.
    imports: List[ImportInfo]
    classes: List[ClassInfo]
    functions: List[FunctionInfo]
    dependencies: List[str]
    has_tests: bool
    last_modified: str
    lines: int
    docstring: Optional[str]
    test_files: List[str]

class ProjectScanner:
    """
    Analyzes Dream.OS codebase to generate intelligence maps.
    
    Features:
    - AST-based code analysis
    - Import dependency tracking
    - Test coverage mapping
    - File categorization
    - Usage pattern detection
    """
    
    IGNORE_DIRS = {
        '__pycache__',
        '.git',
        '.pytest_cache',
        'venv',
        'env',
        'LEGACY'
    }
    
    FILE_TYPE_PATTERNS = {
        'service': ['service.py', 'manager.py'],
        'test': ['test_', '_test.py'],
        'agent': ['agent.py', 'bot.py'],
        'interface': ['tab.py', 'window.py', 'cli.py'],
        'utility': ['util.py', 'helper.py', 'tools.py']
    }
    
    def __init__(self, root_dir: str):
        """Initialize scanner with project root directory."""
        self.root_dir = Path(root_dir)
        self.analysis_cache: Dict[str, FileAnalysis] = {}
        self.import_graph: Dict[str, Set[str]] = {}
        self.test_map: Dict[str, List[str]] = {}
    
    def scan_project(self) -> Dict[str, Dict]:
        """
        Perform complete project scan.
        
        Returns:
            Dict mapping file paths to their analysis data
        """
        logger.info(f"Starting project scan in {self.root_dir}")
        
        # First pass: collect all Python files
        python_files = self._collect_python_files()
        logger.info(f"Found {len(python_files)} Python files")
        
        # Second pass: analyze each file
        for file_path in python_files:
            try:
                analysis = self._analyze_file(file_path)
                if analysis:
                    self.analysis_cache[str(file_path)] = analysis
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {str(e)}")
        
        # Third pass: build dependency graph
        self._build_dependency_graph()
        
        # Fourth pass: map tests to implementations
        self._map_tests_to_implementations()
        
        # Generate final analysis
        return self._generate_analysis_json()
    
    def _collect_python_files(self) -> List[Path]:
        """Collect all Python files in project."""
        python_files = []
        for root, dirs, files in os.walk(self.root_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        return python_files
    
    def _analyze_file(self, file_path: Path) -> Optional[FileAnalysis]:
        """Perform detailed analysis of a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Extract basic info
            imports = self._extract_imports(tree)
            classes = self._extract_classes(tree)
            functions = self._extract_functions(tree)
            docstring = ast.get_docstring(tree)
            
            # Determine file type
            rel_path = str(file_path.relative_to(self.root_dir))
            file_type = self._determine_file_type(rel_path)
            
            # Get file metadata
            stat = file_path.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            return FileAnalysis(
                path=rel_path,
                type=file_type,
                imports=imports,
                classes=classes,
                functions=functions,
                dependencies=[],  # Filled in dependency graph pass
                has_tests=False,  # Updated in test mapping pass
                last_modified=last_modified,
                lines=len(content.splitlines()),
                docstring=docstring,
                test_files=[]  # Updated in test mapping pass
            )
        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {str(e)}")
            return None
    
    def _extract_imports(self, tree: ast.AST) -> List[ImportInfo]:
        """Extract import information from AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(ImportInfo(
                        module_name=name.name,
                        imported_names=[name.asname or name.name],
                        is_relative=False
                    ))
            elif isinstance(node, ast.ImportFrom):
                imports.append(ImportInfo(
                    module_name=node.module or '',
                    imported_names=[n.name for n in node.names],
                    is_relative=node.level > 0,
                    level=node.level
                ))
        return imports
    
    def _extract_classes(self, tree: ast.AST) -> List[ClassInfo]:
        """Extract class information from AST."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(ClassInfo(
                    name=node.name,
                    bases=[self._get_name(base) for base in node.bases],
                    methods=self._extract_functions(node),
                    decorators=[self._get_name(d) for d in node.decorator_list],
                    docstring=ast.get_docstring(node),
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno
                ))
        return classes
    
    def _extract_functions(self, tree: ast.AST) -> List[FunctionInfo]:
        """Extract function information from AST."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(FunctionInfo(
                    name=node.name,
                    args=[arg.arg for arg in node.args.args],
                    returns=self._get_name(node.returns) if node.returns else None,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    decorators=[self._get_name(d) for d in node.decorator_list],
                    docstring=ast.get_docstring(node),
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno
                ))
        return functions
    
    def _get_name(self, node: ast.AST) -> str:
        """Get string representation of a name node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return str(node)
    
    def _determine_file_type(self, file_path: str) -> str:
        """Determine file type based on path and patterns."""
        for type_name, patterns in self.FILE_TYPE_PATTERNS.items():
            if any(pattern in file_path for pattern in patterns):
                return type_name
        return 'unknown'
    
    def _build_dependency_graph(self):
        """Build import dependency graph."""
        for file_path, analysis in self.analysis_cache.items():
            self.import_graph[file_path] = set()
            for imp in analysis.imports:
                # Convert import to potential file paths
                if imp.is_relative:
                    # Handle relative imports
                    current_dir = Path(file_path).parent
                    for _ in range(imp.level):
                        current_dir = current_dir.parent
                    module_path = current_dir / f"{imp.module_name}.py"
                else:
                    # Handle absolute imports
                    module_path = self.root_dir / f"{imp.module_name.replace('.', '/')}.py"
                
                if str(module_path) in self.analysis_cache:
                    self.import_graph[file_path].add(str(module_path))
                    analysis.dependencies.append(str(module_path))
    
    def _map_tests_to_implementations(self):
        """Map test files to their implementations."""
        for file_path, analysis in self.analysis_cache.items():
            if analysis.type == 'test':
                # Try to find implementation file
                impl_name = file_path.replace('test_', '').replace('_test', '')
                if impl_name in self.analysis_cache:
                    self.test_map[impl_name] = self.test_map.get(impl_name, [])
                    self.test_map[impl_name].append(file_path)
                    self.analysis_cache[impl_name].has_tests = True
                    self.analysis_cache[impl_name].test_files.append(file_path)
    
    def _generate_analysis_json(self) -> Dict[str, Dict]:
        """Generate final analysis JSON."""
        return {
            path: asdict(analysis)
            for path, analysis in self.analysis_cache.items()
        }
    
    def save_analysis(self, output_file: str):
        """Save analysis to JSON file."""
        analysis = self.scan_project()
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Analysis saved to {output_file}")

def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Dream.OS Project Scanner")
    parser.add_argument('root_dir', help="Root directory to scan")
    parser.add_argument(
        '-o', '--output',
        default='project_analysis.json',
        help="Output JSON file path"
    )
    args = parser.parse_args()
    
    scanner = ProjectScanner(args.root_dir)
    scanner.save_analysis(args.output)

if __name__ == '__main__':
    main() 
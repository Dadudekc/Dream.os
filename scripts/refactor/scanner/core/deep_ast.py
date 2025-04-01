"""
Deep AST Analysis for Dream.OS Intelligence Scanner.

Provides enhanced AST analysis with:
- Function argument details
- Return type annotations
- Decorator tracking
- Line number tracking
- Docstring collection
- Complexity metrics
"""

import ast
import logging
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

from ..models import (
    ImportInfo, FunctionInfo, ClassInfo, FileAnalysis
)

logger = logging.getLogger(__name__)

class DeepASTAnalyzer:
    """
    Enhanced AST analyzer that extracts detailed metadata from Python source files.
    Integrates with existing analysis to provide deeper insights.
    """

    def __init__(self):
        self.current_file: Optional[str] = None
        self.complexity_threshold = 10

    def enrich_analysis(self, file_path: Path, source_code: str, 
                       existing_analysis: Optional[FileAnalysis] = None) -> FileAnalysis:
        """
        Perform deep AST analysis on a file, enriching or creating a FileAnalysis.
        
        Args:
            file_path: Path to the source file
            source_code: The file's contents
            existing_analysis: Optional existing analysis to enrich
        
        Returns:
            Enriched FileAnalysis with detailed metadata
        """
        self.current_file = str(file_path)
        try:
            tree = ast.parse(source_code)
            
            # Extract all the detailed information
            imports = self._extract_imports(tree)
            functions = self._extract_functions(tree)
            classes = self._extract_classes(tree)
            
            # Calculate complexity
            complexity = self._calculate_complexity(tree)
            
            if existing_analysis:
                # Enrich existing analysis
                existing_analysis.imports = imports
                existing_analysis.functions = functions
                existing_analysis.classes = classes
                existing_analysis.complexity = complexity
                return existing_analysis
            else:
                # Create new analysis
                return FileAnalysis(
                    path=str(file_path),
                    type=self._determine_file_type(file_path),
                    imports=imports,
                    classes=classes,
                    functions=functions,
                    dependencies=[],  # Will be filled by dependency mapper
                    has_tests=False,  # Will be filled by test mapper
                    last_modified="",  # Will be filled by file processor
                    lines=len(source_code.splitlines()),
                    docstring=ast.get_docstring(tree),
                    test_files=[],
                    complexity=complexity
                )
        except Exception as e:
            logger.error(f"Error in deep AST analysis of {file_path}: {str(e)}")
            raise

    def _extract_imports(self, tree: ast.AST) -> List[ImportInfo]:
        """Extract detailed import information."""
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

    def _extract_functions(self, tree: ast.AST) -> List[FunctionInfo]:
        """Extract detailed function information."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Extract argument information
                args = []
                for arg in node.args.args:
                    arg_str = arg.arg
                    if arg.annotation:
                        arg_str += f": {self._format_annotation(arg.annotation)}"
                    args.append(arg_str)
                
                # Get return annotation if present
                returns = None
                if node.returns:
                    returns = self._format_annotation(node.returns)
                
                # Extract decorators
                decorators = [self._format_decorator(d) for d in node.decorator_list]
                
                # Calculate function complexity
                complexity = self._calculate_function_complexity(node)
                
                functions.append(FunctionInfo(
                    name=node.name,
                    args=args,
                    returns=returns,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    decorators=decorators,
                    docstring=ast.get_docstring(node),
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    complexity=complexity
                ))
        return functions

    def _extract_classes(self, tree: ast.AST) -> List[ClassInfo]:
        """Extract detailed class information."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get base classes with their full path
                bases = []
                for base in node.bases:
                    base_name = self._format_annotation(base)
                    bases.append(base_name)
                
                # Extract methods
                methods = self._extract_functions(node)
                
                # Calculate class complexity (includes method complexity)
                complexity = sum(m.complexity for m in methods)
                
                classes.append(ClassInfo(
                    name=node.name,
                    bases=bases,
                    methods=methods,
                    decorators=[self._format_decorator(d) for d in node.decorator_list],
                    docstring=ast.get_docstring(node),
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    complexity=complexity
                ))
        return classes

    def _format_annotation(self, node: ast.AST) -> str:
        """Format type annotations into readable strings."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._format_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._format_annotation(node.value)}[{self._format_annotation(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.List):
            items = [self._format_annotation(elt) for elt in node.elts]
            return f"[{', '.join(items)}]"
        elif isinstance(node, ast.Tuple):
            items = [self._format_annotation(elt) for elt in node.elts]
            return f"({', '.join(items)})"
        return str(node)

    def _format_decorator(self, node: ast.AST) -> str:
        """Format decorator into a readable string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            func_name = self._format_annotation(node.func)
            args = [self._format_annotation(arg) for arg in node.args]
            kwargs = [f"{kw.arg}={self._format_annotation(kw.value)}" 
                     for kw in node.keywords]
            all_args = args + kwargs
            return f"{func_name}({', '.join(all_args)})"
        elif isinstance(node, ast.Attribute):
            return f"{self._format_annotation(node.value)}.{node.attr}"
        return str(node)

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate overall file complexity."""
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity += self._calculate_function_complexity(node)
        return complexity

    def _calculate_function_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity of a function.
        Counts branches in control flow (if, for, while, etc.)
        """
        complexity = 1  # Base complexity
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                               ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _determine_file_type(self, file_path: Path) -> str:
        """Determine file type based on path and content patterns."""
        path_str = str(file_path)
        if 'test' in path_str:
            return 'test'
        elif 'service' in path_str or 'manager.py' in path_str:
            return 'service'
        elif 'agent' in path_str or 'bot.py' in path_str:
            return 'agent'
        elif any(pattern in path_str for pattern in ['cli.py', 'gui.py', 'window.py']):
            return 'interface'
        elif any(pattern in path_str for pattern in ['util.py', 'helper.py', 'tools.py']):
            return 'utility'
        return 'unknown' 
import ast
import astor
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import re

class CodeAnalyzer:
    """Utility class for analyzing Python code."""
    
    @staticmethod
    def get_function_bounds(tree: ast.AST, target_function: str) -> Optional[Tuple[int, int]]:
        """Get the line numbers for a function's start and end."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == target_function:
                return node.lineno, node.end_lineno
        return None
    
    @staticmethod
    def get_class_bounds(tree: ast.AST, target_class: str) -> Optional[Tuple[int, int]]:
        """Get the line numbers for a class's start and end."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == target_class:
                return node.lineno, node.end_lineno
        return None
    
    @staticmethod
    def get_variable_scope(tree: ast.AST, target_variable: str) -> Optional[Tuple[int, int]]:
        """Get the line numbers for a variable's scope."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == target_variable:
                        return node.lineno, node.end_lineno
        return None

class CodeTransformer:
    """Utility class for transforming Python code."""
    
    @staticmethod
    def extract_method(tree: ast.AST, start_line: int, end_line: int, new_method_name: str) -> ast.AST:
        """Extract a block of code into a new method."""
        # Find the parent function/class
        parent = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if start_line >= node.lineno and end_line <= node.end_lineno:
                    parent = node
                    break
        
        if not parent:
            raise ValueError("Could not find parent scope for method extraction")
        
        # Create new function with extracted code
        new_function = ast.FunctionDef(
            name=new_method_name,
            args=ast.arguments(
                args=[ast.arg(arg='self', annotation=None)],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
                kwarg=None
            ),
            body=parent.body[start_line - parent.lineno:end_line - parent.lineno + 1],
            decorator_list=[],
            returns=None
        )
        
        # Add new function to parent scope
        parent.body.insert(0, new_function)
        
        # Replace extracted code with method call
        parent.body[start_line - parent.lineno:end_line - parent.lineno + 1] = [
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr=new_method_name,
                        ctx=ast.Load()
                    ),
                    args=[],
                    keywords=[]
                )
            )
        ]
        
        return tree
    
    @staticmethod
    def rename_variable(tree: ast.AST, old_name: str, new_name: str) -> ast.AST:
        """Rename a variable throughout the code."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == old_name:
                node.id = new_name
        return tree
    
    @staticmethod
    def inline_function(tree: ast.AST, function_name: str) -> ast.AST:
        """Inline a function call by replacing it with the function body."""
        # Find the function definition
        target_function = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                target_function = node
                break
        
        if not target_function:
            raise ValueError(f"Function {function_name} not found")
        
        # Find all calls to this function
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == function_name:
                    # Replace call with function body
                    # Note: This is a simplified version - in practice, you'd need to handle
                    # parameter passing, return values, and variable scoping
                    node.parent = target_function.body
                    node = target_function.body
        
        return tree

class CodeFormatter:
    """Utility class for formatting Python code."""
    
    @staticmethod
    def format_code(code: str) -> str:
        """Format Python code using black-style formatting."""
        # This is a simplified version - in practice, you'd use black or another formatter
        lines = code.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.endswith(':'):
                formatted_lines.append('    ' * indent_level + stripped)
                indent_level += 1
            elif stripped.startswith('return '):
                indent_level -= 1
                formatted_lines.append('    ' * indent_level + stripped)
            else:
                formatted_lines.append('    ' * indent_level + stripped)
        
        return '\n'.join(formatted_lines)

def read_file(file_path: str) -> str:
    """Read a file's contents."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path: str, content: str) -> None:
    """Write content to a file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def parse_code(code: str) -> ast.AST:
    """Parse Python code into an AST."""
    return ast.parse(code)

def unparse_code(tree: ast.AST) -> str:
    """Convert an AST back to Python code."""
    return astor.to_source(tree) 

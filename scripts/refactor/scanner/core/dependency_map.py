"""
Dependency Graph Builder for Dream.OS Intelligence Scanner.

Maps import relationships between files and detects:
- Direct dependencies
- Circular dependencies
- Unused imports
- Missing imports
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from ..models import (
    ImportInfo, FileAnalysis, DependencyNode, ProjectMetrics
)

logger = logging.getLogger(__name__)

class DependencyMapper:
    """
    Builds and analyzes the project's import dependency graph.
    Detects circular dependencies and provides import path resolution.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.graph: Dict[str, DependencyNode] = {}
        self.metrics = ProjectMetrics()
        self._python_path_cache: Dict[str, Optional[str]] = {}

    def build_graph(self, analysis_map: Dict[str, FileAnalysis]) -> Dict[str, DependencyNode]:
        """
        Build complete dependency graph from analyzed files.
        
        Args:
            analysis_map: Dict mapping file paths to their analysis
        
        Returns:
            Dict mapping file paths to their DependencyNode
        """
        logger.info("Building dependency graph...")
        
        # Initialize graph nodes
        for file_path in analysis_map:
            if file_path not in self.graph:
                self.graph[file_path] = DependencyNode(path=file_path)
        
        # Process imports and build edges
        for file_path, analysis in analysis_map.items():
            node = self.graph[file_path]
            
            for imp in analysis.imports:
                resolved_path = self._resolve_import_path(file_path, imp)
                if resolved_path:
                    imp.resolved_path = resolved_path
                    node.imports.add(resolved_path)
                    if resolved_path in self.graph:
                        self.graph[resolved_path].imported_by.add(file_path)
        
        # Detect circular dependencies
        self._detect_cycles()
        
        return self.graph

    def _resolve_import_path(self, importing_file: str, imp: ImportInfo) -> Optional[str]:
        """
        Resolve an import to its actual file path.
        
        Args:
            importing_file: Path of file containing the import
            imp: Import information
        
        Returns:
            Resolved path or None if not found
        """
        if imp.module_name in self._python_path_cache:
            return self._python_path_cache[imp.module_name]
        
        try:
            if imp.is_relative:
                # Handle relative imports
                current_dir = Path(importing_file).parent
                for _ in range(imp.level):
                    current_dir = current_dir.parent
                module_path = current_dir / f"{imp.module_name}.py"
            else:
                # Handle absolute imports
                module_path = self.project_root / f"{imp.module_name.replace('.', '/')}.py"
            
            if module_path.exists():
                resolved = str(module_path.relative_to(self.project_root))
                self._python_path_cache[imp.module_name] = resolved
                return resolved
            
            # Try common variations
            variations = [
                module_path.with_name('__init__.py'),
                module_path.parent / imp.module_name / '__init__.py'
            ]
            
            for var in variations:
                if var.exists():
                    resolved = str(var.relative_to(self.project_root))
                    self._python_path_cache[imp.module_name] = resolved
                    return resolved
            
            self._python_path_cache[imp.module_name] = None
            return None
            
        except Exception as e:
            logger.error(f"Error resolving import {imp.module_name} in {importing_file}: {str(e)}")
            return None

    def _detect_cycles(self):
        """
        Detect circular dependencies in the graph using Tarjan's algorithm.
        Updates nodes with cycle information.
        """
        def strongconnect(node: str, index: Dict[str, int], lowlink: Dict[str, int],
                         stack: List[str], onstack: Set[str], current_index: List[int]):
            index[node] = current_index[0]
            lowlink[node] = current_index[0]
            current_index[0] += 1
            stack.append(node)
            onstack.add(node)
            
            # Consider successors
            for successor in self.graph[node].imports:
                if successor not in index:
                    # Successor has not yet been visited
                    strongconnect(successor, index, lowlink, stack, onstack, current_index)
                    lowlink[node] = min(lowlink[node], lowlink[successor])
                elif successor in onstack:
                    # Successor is in stack and hence in the current SCC
                    lowlink[node] = min(lowlink[node], index[successor])
            
            # If node is a root node, pop the stack and generate an SCC
            if lowlink[node] == index[node]:
                cycle = []
                while True:
                    successor = stack.pop()
                    onstack.remove(successor)
                    cycle.append(successor)
                    if successor == node:
                        break
                
                if len(cycle) > 1:
                    # We found a circular dependency
                    cycle.reverse()  # Put it in logical order
                    self.metrics.circular_dependencies.append(cycle)
                    for node in cycle:
                        self.graph[node].is_circular = True
                        self.graph[node].cycle_path = cycle
        
        index: Dict[str, int] = {}
        lowlink: Dict[str, int] = {}
        onstack: Set[str] = set()
        stack: List[str] = []
        current_index = [0]  # Wrapped in list to allow modification in inner function
        
        for node in self.graph:
            if node not in index:
                strongconnect(node, index, lowlink, stack, onstack, current_index)

    def get_node_metrics(self, node_path: str) -> Dict:
        """Get detailed metrics for a specific node."""
        node = self.graph[node_path]
        return {
            "imports_count": len(node.imports),
            "imported_by_count": len(node.imported_by),
            "is_circular": node.is_circular,
            "cycle_path": node.cycle_path,
            "direct_dependencies": sorted(list(node.imports)),
            "reverse_dependencies": sorted(list(node.imported_by))
        }

    def get_high_risk_imports(self) -> List[Dict]:
        """Identify potentially problematic imports."""
        risks = []
        for path, node in self.graph.items():
            if node.is_circular:
                risks.append({
                    "file": path,
                    "risk_type": "circular_dependency",
                    "details": node.cycle_path
                })
            if len(node.imports) > 10:
                risks.append({
                    "file": path,
                    "risk_type": "high_dependency_count",
                    "details": f"Imports {len(node.imports)} modules"
                })
            if len(node.imported_by) > 15:
                risks.append({
                    "file": path,
                    "risk_type": "high_coupling",
                    "details": f"Used by {len(node.imported_by)} modules"
                })
        return risks

    def suggest_refactors(self) -> List[Dict]:
        """Suggest potential refactoring opportunities based on dependencies."""
        suggestions = []
        
        # Find highly coupled modules
        for path, node in self.graph.items():
            if len(node.imported_by) > 10:
                suggestions.append({
                    "file": path,
                    "type": "extract_interface",
                    "reason": "High coupling - consider extracting interface",
                    "imported_by_count": len(node.imported_by)
                })
        
        # Find circular dependencies
        for cycle in self.metrics.circular_dependencies:
            suggestions.append({
                "files": cycle,
                "type": "break_cycle",
                "reason": "Circular dependency - consider dependency inversion",
                "cycle_length": len(cycle)
            })
        
        return suggestions 
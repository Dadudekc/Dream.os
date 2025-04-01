"""
Agent Mapping System for Dream.OS Intelligence Scanner.

Maps and analyzes agent-related code to:
- Identify agent types and capabilities
- Track agent dependencies and interactions
- Measure agent maturity and complexity
- Suggest agent optimizations and integrations
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from pathlib import Path

from ..models import FileAnalysis, ClassInfo

logger = logging.getLogger(__name__)

class AgentType(Enum):
    """Classification of agent types in the system."""
    CORE = "core"              # Core system agents (e.g. PromptManager)
    TASK = "task"              # Task-specific agents
    UTILITY = "utility"        # Utility/helper agents
    INTERFACE = "interface"    # Interface/communication agents
    ORCHESTRATOR = "orchestrator"  # Coordination agents
    SPECIALIST = "specialist"  # Domain-specific agents
    UNKNOWN = "unknown"

class AgentMaturity(Enum):
    """Maturity level of an agent implementation."""
    PROTOTYPE = "prototype"    # Early development/proof of concept
    BETA = "beta"             # Working but needs refinement
    STABLE = "stable"         # Production-ready
    MATURE = "mature"         # Well-tested and optimized
    LEGACY = "legacy"         # Outdated/needs replacement

@dataclass
class AgentProfile:
    """Detailed profile of an agent in the system."""
    name: str
    type: AgentType
    maturity: AgentMaturity
    file_path: str
    class_info: ClassInfo
    capabilities: Set[str]
    dependencies: Set[str]
    complexity_score: float
    test_coverage: float
    documentation_score: float

class AgentMapper:
    """
    Maps and analyzes agent-related code in the project.
    Provides insights into agent architecture and suggests improvements.
    """

    def __init__(self):
        self.agent_map: Dict[str, AgentProfile] = {}
        self.capability_registry: Dict[str, Set[str]] = {}  # capability -> agent names
        
        # Patterns for identifying agent types
        self.type_patterns = {
            AgentType.CORE: ["manager", "core", "system"],
            AgentType.TASK: ["task", "worker", "job"],
            AgentType.UTILITY: ["util", "helper", "tool"],
            AgentType.INTERFACE: ["interface", "adapter", "connector"],
            AgentType.ORCHESTRATOR: ["orchestrator", "coordinator", "supervisor"],
            AgentType.SPECIALIST: ["specialist", "expert", "analyzer"]
        }
        
        # Common agent capabilities
        self.capability_patterns = {
            "prompt_handling": ["prompt", "query", "question"],
            "memory_management": ["memory", "store", "cache"],
            "learning": ["learn", "train", "adapt"],
            "communication": ["communicate", "send", "receive"],
            "reasoning": ["reason", "think", "decide"],
            "planning": ["plan", "schedule", "organize"],
            "monitoring": ["monitor", "observe", "track"]
        }

    def map_agents(self, analysis_map: Dict[str, FileAnalysis]) -> Dict[str, AgentProfile]:
        """
        Build complete agent mapping for the project.
        
        Args:
            analysis_map: Dict mapping file paths to their analysis
            
        Returns:
            Dict mapping agent names to their profiles
        """
        logger.info("Mapping agent-related code...")
        
        # First pass: identify and profile agents
        for file_path, analysis in analysis_map.items():
            for class_info in analysis.classes:
                if self._is_agent_class(class_info):
                    profile = self._create_agent_profile(
                        class_info, file_path, analysis
                    )
                    self.agent_map[class_info.name] = profile
                    
                    # Register capabilities
                    for capability in profile.capabilities:
                        if capability not in self.capability_registry:
                            self.capability_registry[capability] = set()
                        self.capability_registry[capability].add(class_info.name)
        
        # Second pass: analyze dependencies and relationships
        self._analyze_agent_relationships(analysis_map)
        
        return self.agent_map

    def _is_agent_class(self, class_info: ClassInfo) -> bool:
        """Determine if a class represents an agent."""
        # Check name patterns
        if any(pattern in class_info.name.lower() for pattern in [
            "agent", "assistant", "bot", "worker", "manager"
        ]):
            return True
            
        # Check base classes
        if any(base in ["BaseAgent", "Agent", "AIAgent"] for base in class_info.bases):
            return True
            
        # Check for agent-like methods
        agent_methods = {"process", "handle", "respond", "execute", "run"}
        if any(method.name in agent_methods for method in class_info.methods):
            return True
            
        return False

    def _create_agent_profile(self, class_info: ClassInfo, file_path: str,
                            analysis: FileAnalysis) -> AgentProfile:
        """Create detailed profile for an agent class."""
        # Determine agent type
        agent_type = self._determine_agent_type(class_info)
        
        # Identify capabilities
        capabilities = self._identify_capabilities(class_info)
        
        # Calculate complexity score (0-1)
        complexity_score = self._calculate_complexity(class_info)
        
        # Calculate documentation score (0-1)
        documentation_score = self._calculate_documentation_score(class_info)
        
        # Determine maturity level
        maturity = self._determine_maturity(
            class_info, complexity_score,
            documentation_score, analysis.has_tests
        )
        
        return AgentProfile(
            name=class_info.name,
            type=agent_type,
            maturity=maturity,
            file_path=file_path,
            class_info=class_info,
            capabilities=capabilities,
            dependencies=set(),  # Will be populated in second pass
            complexity_score=complexity_score,
            test_coverage=analysis.test_coverage if hasattr(analysis, 'test_coverage') else 0.0,
            documentation_score=documentation_score
        )

    def _determine_agent_type(self, class_info: ClassInfo) -> AgentType:
        """Determine the type of agent based on its characteristics."""
        name_lower = class_info.name.lower()
        
        for agent_type, patterns in self.type_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                return agent_type
                
        # Check method patterns
        method_names = {method.name.lower() for method in class_info.methods}
        
        if {"orchestrate", "coordinate"} & method_names:
            return AgentType.ORCHESTRATOR
        if {"process", "execute"} & method_names:
            return AgentType.TASK
        if {"adapt", "learn"} & method_names:
            return AgentType.SPECIALIST
            
        return AgentType.UNKNOWN

    def _identify_capabilities(self, class_info: ClassInfo) -> Set[str]:
        """Identify agent capabilities based on methods and attributes."""
        capabilities = set()
        
        # Check method names against capability patterns
        method_text = " ".join(method.name.lower() for method in class_info.methods)
        for capability, patterns in self.capability_patterns.items():
            if any(pattern in method_text for pattern in patterns):
                capabilities.add(capability)
                
        # Check docstring for capability hints
        if class_info.docstring:
            doc_lower = class_info.docstring.lower()
            for capability, patterns in self.capability_patterns.items():
                if any(pattern in doc_lower for pattern in patterns):
                    capabilities.add(capability)
                    
        return capabilities

    def _calculate_complexity(self, class_info: ClassInfo) -> float:
        """Calculate complexity score for an agent (0-1)."""
        # Base complexity on number of methods and their complexity
        method_count = len(class_info.methods)
        avg_method_complexity = sum(
            method.complexity for method in class_info.methods
            if hasattr(method, 'complexity')
        ) / max(1, method_count)
        
        # Factor in inheritance depth
        inheritance_depth = len(class_info.bases)
        
        # Normalize to 0-1 range
        complexity = (
            (method_count * 0.4) +
            (avg_method_complexity * 0.4) +
            (inheritance_depth * 0.2)
        ) / 10  # Assuming max reasonable values
        
        return min(1.0, complexity)

    def _calculate_documentation_score(self, class_info: ClassInfo) -> float:
        """Calculate documentation completeness score (0-1)."""
        score = 0.0
        
        # Check class docstring
        if class_info.docstring:
            score += 0.3
            
        # Check method docstrings
        documented_methods = sum(1 for method in class_info.methods if method.docstring)
        method_doc_ratio = documented_methods / max(1, len(class_info.methods))
        score += 0.7 * method_doc_ratio
        
        return score

    def _determine_maturity(self, class_info: ClassInfo, complexity: float,
                          documentation: float, has_tests: bool) -> AgentMaturity:
        """Determine agent implementation maturity level."""
        if documentation < 0.2 or not has_tests:
            return AgentMaturity.PROTOTYPE
            
        if complexity > 0.8 and documentation > 0.8 and has_tests:
            return AgentMaturity.MATURE
            
        if complexity > 0.6 and documentation > 0.6 and has_tests:
            return AgentMaturity.STABLE
            
        if complexity > 0.4 and documentation > 0.4:
            return AgentMaturity.BETA
            
        return AgentMaturity.PROTOTYPE

    def _analyze_agent_relationships(self, analysis_map: Dict[str, FileAnalysis]):
        """Analyze dependencies and relationships between agents."""
        for agent_name, profile in self.agent_map.items():
            # Check imports in the agent's file
            file_analysis = analysis_map[profile.file_path]
            for import_info in file_analysis.imports:
                imported_name = import_info.module_name.split('.')[-1]
                if imported_name in self.agent_map:
                    profile.dependencies.add(imported_name)
                    
            # Check method signatures for agent parameters
            for method in profile.class_info.methods:
                for arg_type in method.args.values():
                    if arg_type in self.agent_map:
                        profile.dependencies.add(arg_type)

    def get_agent_metrics(self) -> Dict:
        """Get project-wide agent metrics and statistics."""
        return {
            "total_agents": len(self.agent_map),
            "by_type": {
                agent_type.value: len([a for a in self.agent_map.values()
                                     if a.type == agent_type])
                for agent_type in AgentType
            },
            "by_maturity": {
                maturity.value: len([a for a in self.agent_map.values()
                                   if a.maturity == maturity])
                for maturity in AgentMaturity
            },
            "capability_coverage": {
                capability: len(agents)
                for capability, agents in self.capability_registry.items()
            }
        }

    def suggest_improvements(self) -> List[Dict]:
        """Generate suggestions for agent improvements."""
        suggestions = []
        
        for agent_name, profile in self.agent_map.items():
            # Suggest documentation improvements
            if profile.documentation_score < 0.5:
                suggestions.append({
                    "agent": agent_name,
                    "type": "documentation",
                    "priority": "high",
                    "message": f"Improve documentation (current score: {profile.documentation_score:.0%})"
                })
                
            # Suggest test coverage improvements
            if profile.test_coverage < 0.7:
                suggestions.append({
                    "agent": agent_name,
                    "type": "testing",
                    "priority": "high",
                    "message": f"Increase test coverage (current: {profile.test_coverage:.0%})"
                })
                
            # Suggest complexity reduction
            if profile.complexity_score > 0.8:
                suggestions.append({
                    "agent": agent_name,
                    "type": "complexity",
                    "priority": "medium",
                    "message": "Consider breaking down into smaller components"
                })
                
            # Suggest capability additions
            missing_common_capabilities = {
                cap for cap in self.capability_patterns
                if cap not in profile.capabilities
                and len(self.capability_registry.get(cap, set())) > 2
            }
            if missing_common_capabilities:
                suggestions.append({
                    "agent": agent_name,
                    "type": "capabilities",
                    "priority": "low",
                    "message": f"Consider adding common capabilities: {', '.join(missing_common_capabilities)}"
                })
        
        return suggestions 
import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ProjectContextAnalyzer:
    """
    Analyzes project structure and context to generate recommendations
    for prompt blocks in the draggable prompt board.
    """
    
    def __init__(self, 
                 project_root: str = ".",
                 context_file: str = "memory/project_context.json",
                 prompt_service = None):
        """
        Initialize the project context analyzer.
        
        Args:
            project_root: Root directory of the project
            context_file: Path to the JSON file containing cached project context
            prompt_service: Optional PromptExecutionService to send prompts
        """
        self.project_root = Path(project_root)
        self.context_file = Path(context_file)
        self.prompt_service = prompt_service
        
        # Ensure context file directory exists
        self.context_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty context if file doesn't exist
        if not self.context_file.exists():
            self._initialize_context_file()
    
    def _initialize_context_file(self):
        """Initialize an empty context file."""
        empty_context = {
            "last_updated": datetime.now().isoformat(),
            "files": [],
            "directories": [],
            "components": [],
            "services": [],
            "modules": [],
            "dependencies": {}
        }
        
        with open(self.context_file, 'w') as f:
            json.dump(empty_context, f, indent=2)
    
    def update_project_context(self) -> Dict[str, Any]:
        """
        Analyze the project structure and update the context file.
        
        Returns:
            The updated context dictionary
        """
        logger.info("Updating project context...")
        
        try:
            # Start with basic file structure
            context = self._scan_file_structure()
            
            # Add more specific analysis
            context["components"] = self._identify_components()
            context["services"] = self._identify_services()
            context["modules"] = self._identify_modules()
            context["dependencies"] = self._analyze_dependencies()
            
            # Update timestamp
            context["last_updated"] = datetime.now().isoformat()
            
            # Save to file
            with open(self.context_file, 'w') as f:
                json.dump(context, f, indent=2)
                
            logger.info("Project context updated successfully")
            return context
            
        except Exception as e:
            logger.error(f"Error updating project context: {e}")
            
            # If we have an existing context file, load that instead
            if self.context_file.exists():
                try:
                    with open(self.context_file, 'r') as f:
                        return json.load(f)
                except:
                    pass
                    
            # Otherwise return a minimal context
            return {
                "last_updated": datetime.now().isoformat(),
                "files": [],
                "directories": [],
                "components": [],
                "services": [],
                "modules": [],
                "dependencies": {}
            }
    
    def _scan_file_structure(self) -> Dict[str, Any]:
        """
        Scan the file structure of the project.
        
        Returns:
            Dictionary with files and directories lists
        """
        context = {
            "files": [],
            "directories": []
        }
        
        # Walk through the directory structure
        for root, dirs, files in os.walk(self.project_root):
            # Skip hidden directories and specific directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env', 'node_modules']]
            
            # Add the relative path of this directory
            rel_root = os.path.relpath(root, self.project_root)
            if rel_root != '.':
                context["directories"].append(rel_root)
            
            # Add files (excluding hidden files)
            for file in files:
                if not file.startswith('.'):
                    rel_path = os.path.join(rel_root, file)
                    if rel_path != '.':
                        context["files"].append(rel_path)
        
        return context
    
    def _identify_components(self) -> List[Dict[str, Any]]:
        """
        Identify UI components in the project.
        
        Returns:
            List of component information dictionaries
        """
        components = []
        
        # Look for UI component files
        ui_patterns = [
            "interfaces/pyqt/tabs/*.py",
            "interfaces/pyqt/*.py",
            "ui/components/*.py",
            "*.ui"
        ]
        
        for pattern in ui_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.project_root)
                    components.append({
                        "name": file_path.stem,
                        "path": str(rel_path),
                        "type": "ui_component"
                    })
        
        return components
    
    def _identify_services(self) -> List[Dict[str, Any]]:
        """
        Identify service classes in the project.
        
        Returns:
            List of service information dictionaries
        """
        services = []
        
        # Look for service files
        service_patterns = [
            "core/*service.py",
            "core/*_service.py",
            "services/*.py",
            "*Service.py"
        ]
        
        for pattern in service_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.project_root)
                    services.append({
                        "name": file_path.stem,
                        "path": str(rel_path),
                        "type": "service"
                    })
        
        return services
    
    def _identify_modules(self) -> List[Dict[str, Any]]:
        """
        Identify key modules in the project.
        
        Returns:
            List of module information dictionaries
        """
        modules = []
        
        # Look for Python files that don't match component or service patterns
        for file_path in self.project_root.glob("**/*.py"):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.project_root)
                
                # Skip if already identified as component or service
                skip = False
                for component in self._identify_components():
                    if component["path"] == str(rel_path):
                        skip = True
                        break
                        
                for service in self._identify_services():
                    if service["path"] == str(rel_path):
                        skip = True
                        break
                
                if not skip:
                    modules.append({
                        "name": file_path.stem,
                        "path": str(rel_path),
                        "type": "module"
                    })
        
        return modules
    
    def _analyze_dependencies(self) -> Dict[str, List[str]]:
        """
        Analyze import dependencies between files.
        
        Returns:
            Dictionary mapping files to their imported dependencies
        """
        dependencies = {}
        
        # Process Python files
        for file_path in self.project_root.glob("**/*.py"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.project_root))
                file_deps = []
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            
                            # Simple import detection - not perfect but gives a rough idea
                            if line.startswith('import ') or line.startswith('from '):
                                parts = line.split()
                                if len(parts) >= 2:
                                    # Get the module name
                                    module = parts[1].split('.')[0]
                                    if module not in ['os', 'sys', 'json', 'time', 'datetime', 'logging', 'uuid', 'typing', 'enum', 'pathlib', 'PyQt5']:
                                        file_deps.append(module)
                
                except Exception as e:
                    logger.debug(f"Error analyzing dependencies in {file_path}: {e}")
                
                dependencies[rel_path] = file_deps
                
        return dependencies
    
    def get_project_context(self) -> Dict[str, Any]:
        """
        Get the current project context, updating if needed.
        
        Returns:
            The project context dictionary
        """
        # If context file exists and is fresh enough, use it
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r') as f:
                    context = json.load(f)
                    
                # Check if context is fresh (less than 24 hours old)
                last_updated = datetime.fromisoformat(context.get("last_updated", "2000-01-01T00:00:00"))
                now = datetime.now()
                
                if (now - last_updated).total_seconds() < 86400:  # 24 hours
                    return context
            except:
                pass
        
        # Otherwise, update the context
        return self.update_project_context()
    
    def generate_prompt_blocks(self, max_blocks: int = 10) -> List[Dict[str, Any]]:
        """
        Generate recommended prompt blocks based on project context.
        
        Args:
            max_blocks: Maximum number of blocks to generate
            
        Returns:
            List of prompt block data dictionaries
        """
        # Get project context
        context = self.get_project_context()
        
        # Generate blocks based on context
        blocks = []
        
        # Block 1: Project overview
        blocks.append({
            "id": str(uuid.uuid4()),
            "title": "Project Overview Analysis",
            "category": "analysis",
            "content": "Analyze the current project structure and provide a high-level overview of key components and architecture patterns.",
            "priority": 5,
            "dependencies": [],
            "created_at": datetime.now().isoformat(),
            "auto_execute": False,
            "requires_validation": True
        })
        
        # Blocks for improving identified services
        for i, service in enumerate(context.get("services", [])):
            if i >= max_blocks - 1:
                break
                
            blocks.append({
                "id": str(uuid.uuid4()),
                "title": f"Improve {service['name']}",
                "category": "refactoring",
                "content": f"Analyze and refactor the {service['name']} at {service['path']} to improve code quality, maintainability, and performance.",
                "priority": 4,
                "dependencies": [],
                "created_at": datetime.now().isoformat(),
                "auto_execute": False,
                "requires_validation": True
            })
        
        # Blocks for missing services based on common patterns
        missing_services = self._identify_missing_services(context)
        for i, service_name in enumerate(missing_services):
            if len(blocks) >= max_blocks:
                break
                
            blocks.append({
                "id": str(uuid.uuid4()),
                "title": f"Create {service_name}",
                "category": "generation",
                "content": f"Create a new {service_name} service class following the project's architecture patterns and style guides.",
                "priority": 3,
                "dependencies": [],
                "created_at": datetime.now().isoformat(),
                "auto_execute": False,
                "requires_validation": True
            })
        
        # Block for test generation
        blocks.append({
            "id": str(uuid.uuid4()),
            "title": "Generate Unit Tests",
            "category": "testing",
            "content": "Generate comprehensive unit tests for recent modules to ensure code quality and maintainability.",
            "priority": 3,
            "dependencies": [],
            "created_at": datetime.now().isoformat(),
            "auto_execute": False,
            "requires_validation": True
        })
        
        # Block for documentation
        blocks.append({
            "id": str(uuid.uuid4()),
            "title": "Update Documentation",
            "category": "other",
            "content": "Update the project documentation to reflect recent changes and improvements.",
            "priority": 2,
            "dependencies": [],
            "created_at": datetime.now().isoformat(),
            "auto_execute": False,
            "requires_validation": True
        })
        
        return blocks[:max_blocks]
    
    def _identify_missing_services(self, context: Dict[str, Any]) -> List[str]:
        """
        Identify potentially missing services based on project patterns.
        
        Args:
            context: Project context dictionary
            
        Returns:
            List of suggested service names
        """
        # Get existing service names
        existing_services = [service["name"].lower() for service in context.get("services", [])]
        
        # Common service patterns to check for
        common_services = [
            "ConfigurationService",
            "LoggingService",
            "DataService",
            "AuthenticationService",
            "NotificationService",
            "CacheService",
            "ValidationService",
            "AnalyticsService",
            "BackupService",
            "MonitoringService"
        ]
        
        # Check for project-specific patterns
        if any("dream" in file.lower() for file in context.get("files", [])):
            common_services.extend([
                "DreamscapeService",
                "EpisodeGenerationService",
                "MemoryService"
            ])
            
        if any("prompt" in file.lower() for file in context.get("files", [])):
            common_services.extend([
                "TemplateRenderingService",
                "PromptGenerationService",
                "ContextFormattingService"
            ])
            
        if any("cursor" in file.lower() for file in context.get("files", [])):
            common_services.extend([
                "CursorIntegrationService",
                "TaskSynchronizationService",
                "AutomationService"
            ])
        
        # Return services that don't already exist
        missing_services = []
        for service in common_services:
            if not any(service.lower() in existing.lower() for existing in existing_services):
                missing_services.append(service)
                
        return missing_services
    
    def get_ai_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get AI-generated recommendations for prompt blocks by sending
        project context to an LLM through the prompt service.
        
        Returns:
            List of prompt block data dictionaries
        """
        if not self.prompt_service:
            logger.warning("PromptExecutionService not available for AI recommendations")
            return self.generate_prompt_blocks()
            
        try:
            # Get project context
            context = self.get_project_context()
            
            # Prepare context for the LLM
            llm_context = {
                "services": context.get("services", [])[:20],  # Limit to 20 services
                "components": context.get("components", [])[:20],  # Limit to 20 components
                "modules": context.get("modules", [])[:20],  # Limit to 20 modules
                "directories": context.get("directories", [])[:20],  # Limit to 20 directories
                "file_count": len(context.get("files", [])),
                "patterns": self._identify_project_patterns(context)
            }
            
            # Convert to JSON for the prompt
            context_json = json.dumps(llm_context, indent=2)
            
            # Create the prompt
            prompt = f"""
            # Project Context Analysis
            
            Below is the context of the current project:
            
            ```json
            {context_json}
            ```
            
            ## Request
            
            Based on this project context, generate 5-10 recommended tasks that would benefit the project the most.
            For each task, provide:
            
            1. A title (short and descriptive)
            2. A category (analysis, generation, refactoring, testing, or other)
            3. Detailed prompt content (what should be done)
            4. Priority (1-5, with 5 being highest)
            
            ## Output Format
            
            Return a JSON array of task objects with the following structure:
            
            ```json
            [
              {{
                "title": "Task title",
                "category": "analysis|generation|refactoring|testing|other",
                "content": "Detailed prompt content...",
                "priority": 3
              }}
            ]
            ```
            
            Ensure your JSON is valid and properly formatted.
            """
            
            # Send to LLM through prompt service
            # This is a placeholder - in a real implementation, you would use your LLM API
            # response = self.prompt_service.get_completion(prompt)
            
            # For now, return the generated blocks instead
            logger.info("AI recommendations not implemented yet, returning generated blocks")
            return self.generate_prompt_blocks()
            
        except Exception as e:
            logger.error(f"Error getting AI recommendations: {e}")
            return self.generate_prompt_blocks()
    
    def _identify_project_patterns(self, context: Dict[str, Any]) -> Dict[str, bool]:
        """
        Identify common patterns in the project.
        
        Args:
            context: Project context dictionary
            
        Returns:
            Dictionary of pattern names mapped to boolean values
        """
        files = context.get("files", [])
        
        patterns = {
            "uses_testing": any("test" in file for file in files),
            "uses_database": any("database" in file or "db" in file for file in files),
            "uses_apis": any("api" in file for file in files),
            "uses_ui": any("ui" in file or "interface" in file for file in files),
            "uses_pyqt": any("PyQt" in file or "pyqt" in file for file in files),
            "uses_dreamscape": any("dream" in file.lower() for file in files),
            "uses_cursor": any("cursor" in file.lower() for file in files),
            "uses_templates": any("template" in file.lower() for file in files),
            "uses_prompts": any("prompt" in file.lower() for file in files),
            "uses_ai": any("ai" in file.lower() or "llm" in file.lower() for file in files)
        }
        
        return patterns 
import os
import sys
import logging # Add logging import
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl # Import QUrl
from typing import Dict, Any
from pathlib import Path # Import Path

# Import pyvis
try:
    from pyvis.network import Network
except ImportError:
    Network = None # Handle case where pyvis isn't installed

# Assuming PathManager is accessible or passed via services
# from core.PathManager import PathManager 

class DependencyMapTab(QWidget):
    # Updated __init__ signature
    def __init__(self, services: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.services = services
        self.logger = services.get('logger') # Get logger if available
        
        path_manager = services.get('path_manager')
        default_fallback_path = Path(os.getcwd()) / 'cache' / 'dependency_map.html' # Absolute fallback
        
        if path_manager:
            try:
                # Ensure the base path exists
                cache_path = path_manager.get_path('cache')
                if not cache_path.exists():
                     cache_path.mkdir(parents=True, exist_ok=True)
                self.html_file_path = cache_path / 'dependency_map.html'
                if self.logger:
                    self.logger.info(f"Dependency map HTML path set: {self.html_file_path}")
            except KeyError:
                if self.logger:
                    self.logger.error("PathManager missing 'cache' key. Using default absolute path.")
                self.html_file_path = default_fallback_path
                # Ensure fallback directory exists
                default_fallback_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            if self.logger:
                 self.logger.error("PathManager service not found. Using default absolute path.")
            self.html_file_path = default_fallback_path
            # Ensure fallback directory exists
            default_fallback_path.parent.mkdir(parents=True, exist_ok=True)
            
        if self.logger:
            self.logger.debug(f"Final html_file_path: {self.html_file_path}")

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.loading_label = QLabel("Loading dependency map...")
        layout.addWidget(self.loading_label)

        self.web_view = QWebEngineView()
        
        try:
            # Path should now always be absolute
            if isinstance(self.html_file_path, str):
                html_path = Path(self.html_file_path)
            else:
                html_path = self.html_file_path
                
            url_path = html_path.as_uri()
            if self.logger:
                self.logger.info(f"Setting WebView URL to: {url_path}")
            self.web_view.setUrl(QUrl(url_path)) # Use QUrl
        except Exception as e:
             if self.logger:
                  self.logger.error(f"Error creating/setting file URI for {self.html_file_path}: {e}")
             self.web_view.setUrl(QUrl("about:blank")) # Use QUrl
             
        layout.addWidget(self.web_view)

        self.refresh_button = QPushButton("Refresh Graph")
        self.refresh_button.clicked.connect(self.load_graph)
        layout.addWidget(self.refresh_button)

        self.setLayout(layout)
        self.load_graph()

    def load_graph(self):
        self.loading_label.setText("Generating/Loading dependency map...")
        
        # Call generation logic first
        if not self.generate_graph_html():
            # If generation failed, stop loading
            return 
            
        # Proceed to load if generation was successful or file already existed
        if not os.path.exists(self.html_file_path):
            self.loading_label.setText(f"Graph generation completed, but file still not found at {self.html_file_path}.")
            if self.logger:
                self.logger.error(f"Dependency map file still not found after attempted generation: {self.html_file_path}")
            return
            
        try:
            if isinstance(self.html_file_path, str):
                html_path = Path(self.html_file_path)
            else:
                html_path = self.html_file_path
            url_path = html_path.as_uri()
            if self.logger:
                 self.logger.info(f"Reloading WebView URL: {url_path}")
            # Force reload, bypassing cache
            self.web_view.load(QUrl(url_path)) 
            self.web_view.reload() # Explicitly reload
            self.web_view.loadFinished.connect(self._on_load_finished)
        except Exception as e:
             if self.logger:
                  self.logger.error(f"Error creating file URI for reloading {self.html_file_path}: {e}")
             self.loading_label.setText("Error creating URL for dependency map.")
        
    def _on_load_finished(self, ok):
        if ok:
            self.loading_label.setText("Dependency map loaded.")
            if self.logger:
                self.logger.info("WebView finished loading dependency map successfully.")
        else:
            self.loading_label.setText("Error loading dependency map HTML.")
            if self.logger:
                self.logger.error("WebView failed to load dependency map HTML.")

    def generate_graph_html(self) -> bool:
        """Generates the dependency graph HTML using ProjectScanner data and pyvis.
        
        Returns:
            bool: True if generation was successful or file already exists, False otherwise.
        """
        if Network is None:
            self.loading_label.setText("Error: 'pyvis' library not installed. Please install it.")
            if self.logger:
                self.logger.error("'pyvis' library is required but not found.")
            return False

        scanner = self.services.get('project_scanner')
        if not scanner:
            self.loading_label.setText("Project Scanner service unavailable. Cannot generate graph.")
            if self.logger:
                 self.logger.error("ProjectScanner service not found for graph generation.")
            return False

        try:
            # Get analysis data (load cache or scan if needed)
            analysis = scanner.load_cache()
            if not analysis or not analysis.get('files') or not analysis.get('imports'):
                self.loading_label.setText("Scanning project for dependencies...")
                analysis = scanner.scan_project() # Scan if cache is empty/invalid
                if not analysis or not analysis.get('files') or not analysis.get('imports'):
                    self.loading_label.setText("Failed to get analysis data from Project Scanner.")
                    if self.logger:
                         self.logger.error("Failed to retrieve valid analysis data from ProjectScanner.")
                    return False
            
            files = analysis.get('files', [])
            imports_data = analysis.get('imports', {})

            if not files:
                 self.loading_label.setText("No files found by Project Scanner.")
                 if self.logger:
                     self.logger.warning("No files found in ProjectScanner analysis.")
                 return False # Cannot generate graph without files

            # --- Create pyvis network ---
            net = Network(notebook=True, cdn_resources='remote', height='750px', width='100%')
            
            # Add nodes (files)
            file_nodes = {file: file for file in files} # Use path as ID and label
            for file_path in files:
                net.add_node(file_path, label=file_path, title=file_path)

            # Add edges (imports)
            for source_file, imported_items in imports_data.items():
                if source_file not in file_nodes: continue # Skip if source isn't in our scanned files
                
                source_dir = Path(source_file).parent

                for imp_statement in imported_items:
                    target_file = None
                    # Basic attempt to resolve imports
                    # 1. Relative imports (. or ..)
                    if imp_statement.startswith('.'):
                        parts = imp_statement.split('.')
                        level = 0
                        module_path_parts = []
                        for part in parts:
                            if part == '':
                                level += 1
                            else:
                                module_path_parts.append(part)
                        
                        if level > 0:
                            base_path = source_dir
                            for _ in range(level - 1):
                                base_path = base_path.parent
                            
                            potential_target = (base_path / Path('/'.join(module_path_parts))).with_suffix('.py')
                            potential_target_str = str(potential_target).replace('\\', '/') # Normalize path
                            
                            if potential_target_str in file_nodes:
                                target_file = potential_target_str
                            else:
                                # Check for __init__.py import
                                potential_init_target = (base_path / Path('/'.join(module_path_parts)) / '__init__.py')
                                potential_init_target_str = str(potential_init_target).replace('\\','/')
                                if potential_init_target_str in file_nodes:
                                    target_file = potential_init_target_str
                                
                    # 2. Absolute project imports (heuristic: starts with known top-level dirs like 'core', 'interfaces')
                    else:
                        top_level_dirs = ['core', 'interfaces', 'utils', 'chat_mate'] # Add known top-level dirs
                        imp_parts = imp_statement.split('.')
                        if imp_parts[0] in top_level_dirs:
                            potential_target = Path('/'.join(imp_parts)).with_suffix('.py')
                            potential_target_str = str(potential_target).replace('\\','/')
                            if potential_target_str in file_nodes:
                                target_file = potential_target_str
                            else:
                                # Check for __init__.py
                                potential_init_target = Path('/'.join(imp_parts)) / '__init__.py'
                                potential_init_target_str = str(potential_init_target).replace('\\','/')
                                if potential_init_target_str in file_nodes:
                                    target_file = potential_init_target_str

                    # Add edge if resolved
                    if target_file and target_file in file_nodes:
                        if source_file != target_file: # Avoid self-loops
                            net.add_edge(source_file, target_file)

            # Save the graph
            net.save_graph(str(self.html_file_path))
            if self.logger:
                self.logger.info(f"Successfully generated dependency graph HTML to {self.html_file_path}")
            return True
            
        except Exception as e:
            self.loading_label.setText(f"Error generating dependency graph: {e}")
            if self.logger:
                 self.logger.error(f"Failed to generate dependency graph: {e}", exc_info=True)
            # Try to delete potentially corrupted html file
            try:
                if os.path.exists(self.html_file_path):
                     os.remove(self.html_file_path)
            except OSError as rm_err:
                 if self.logger:
                     self.logger.error(f"Failed to remove potentially corrupt graph file {self.html_file_path}: {rm_err}")
            return False

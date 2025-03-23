import os
import ast
import json
import hashlib
import threading
import queue
from pathlib import Path
from typing import Dict, Union, Optional, List

# Try importing tree-sitter for Rust/JS/TS parsing
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language = None
    Parser = None
    print("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")

CACHE_FILE = "dependency_cache.json"


class LanguageAnalyzer:
    """Handles language-specific code analysis for different programming languages."""
    
    def __init__(self):
        """Initialize language analyzers and parsers."""
        self.rust_parser = self._init_tree_sitter_language("rust")
        self.js_parser = self._init_tree_sitter_language("javascript")

    def _init_tree_sitter_language(self, lang_name: str) -> Optional[Parser]:
        """
        Initializes and returns a Parser for the given language name.
        
        Args:
            lang_name: Name of the language (e.g. "rust", "javascript")
            
        Returns:
            Optional[Parser]: Configured parser instance or None if initialization fails
        """
        if not Language or not Parser:
            print(f"⚠️ tree-sitter not available. Skipping {lang_name} parser.")
            return None

        grammar_paths = {
            "rust": "path/to/tree-sitter-rust.so",
            "javascript": "path/to/tree-sitter-javascript.so",
        }

        if lang_name not in grammar_paths:
            print(f"⚠️ No grammar path for {lang_name}. Skipping.")
            return None

        grammar_path = grammar_paths[lang_name]
        if not Path(grammar_path).exists():
            print(f"⚠️ {lang_name} grammar not found at {grammar_path}")
            return None

        try:
            lang_lib = Language(grammar_path, lang_name)
            parser = Parser()
            parser.set_language(lang_lib)
            return parser
        except Exception as e:
            print(f"⚠️ Failed to initialize tree-sitter {lang_name} parser: {e}")
            return None

    def analyze_file(self, file_path: Path, source_code: str) -> Dict:
        """
        Analyzes source code based on file extension.
        
        Args:
            file_path: Path to the source file
            source_code: Contents of the source file
            
        Returns:
            Dict containing analysis results
        """
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            return self._analyze_python(source_code)
        elif suffix == ".rs" and self.rust_parser:
            return self._analyze_rust(source_code)
        elif suffix in [".js", ".ts"] and self.js_parser:
            return self._analyze_javascript(source_code)
        else:
            return {"language": suffix, "functions": [], "classes": {}, "routes": [], "complexity": 0}

    def _analyze_python(self, source_code: str) -> Dict:
        """
        Analyzes Python source code using AST.
        
        Args:
            source_code: Python source code string
            
        Returns:
            Dict containing extracted functions, classes, and routes
        """
        tree = ast.parse(source_code)
        functions = []
        classes = {}
        routes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr'):
                        func_attr = decorator.func.attr.lower()
                        if func_attr in {"route", "get", "post", "put", "delete", "patch"}:
                            path_arg = "/unknown"
                            methods = [func_attr.upper()]
                            if decorator.args:
                                arg0 = decorator.args[0]
                                if isinstance(arg0, ast.Str):
                                    path_arg = arg0.s
                            for kw in decorator.keywords:
                                if kw.arg == "methods" and isinstance(kw.value, ast.List):
                                    extracted_methods = []
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Str):
                                            extracted_methods.append(elt.s.upper())
                                    if extracted_methods:
                                        methods = extracted_methods
                            for m in methods:
                                routes.append({
                                    "function": node.name,
                                    "method": m,
                                    "path": path_arg
                                })
            elif isinstance(node, ast.ClassDef):
                method_names = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                classes[node.name] = method_names
                
        return {"functions": functions, "classes": classes, "routes": routes}

    def _analyze_rust(self, source_code: str) -> Dict:
        """
        Analyzes Rust source code using tree-sitter.
        
        Args:
            source_code: Rust source code string
            
        Returns:
            Dict containing extracted functions and classes
        """
        if not self.rust_parser:
            return {"functions": [], "classes": {}}
            
        tree = self.rust_parser.parse(bytes(source_code, "utf-8"))
        functions = []
        classes = {}

        def _traverse(node):
            if node.type == "function_item":
                fn_name_node = node.child_by_field_name("name")
                if fn_name_node:
                    functions.append(fn_name_node.text.decode("utf-8"))
            elif node.type == "struct_item":
                struct_name_node = node.child_by_field_name("name")
                if struct_name_node:
                    classes[struct_name_node.text.decode("utf-8")] = []
            elif node.type == "impl_item":
                impl_type_node = node.child_by_field_name("type")
                if impl_type_node:
                    impl_name = impl_type_node.text.decode("utf-8")
                    if impl_name not in classes:
                        classes[impl_name] = []
                    for child in node.children:
                        if child.type == "function_item":
                            method_node = child.child_by_field_name("name")
                            if method_node:
                                classes[impl_name].append(method_node.text.decode("utf-8"))
            for child in node.children:
                _traverse(child)

        _traverse(tree.root_node)
        return {"functions": functions, "classes": classes}

    def _analyze_javascript(self, source_code: str) -> Dict:
        """
        Analyzes JavaScript/TypeScript source code using tree-sitter.
        
        Args:
            source_code: JavaScript/TypeScript source code string
            
        Returns:
            Dict containing extracted functions, classes, and routes
        """
        if not self.js_parser:
            return {"functions": [], "classes": {}, "routes": []}
            
        tree = self.js_parser.parse(bytes(source_code, "utf-8"))
        root = tree.root_node
        functions = []
        classes = {}
        routes = []

        def get_node_text(node):
            return node.text.decode("utf-8")

        def _traverse(node):
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    functions.append(get_node_text(name_node))
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    cls_name = get_node_text(name_node)
                    classes[cls_name] = []
            elif node.type == "lexical_declaration":
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        value_node = child.child_by_field_name("value")
                        if name_node and value_node and value_node.type == "arrow_function":
                            functions.append(get_node_text(name_node))
            elif node.type == "call_expression":
                if node.child_count >= 2:
                    callee_node = node.child_by_field_name("function")
                    args_node = node.child_by_field_name("arguments")
                    if callee_node:
                        callee_text = get_node_text(callee_node)
                        parts = callee_text.split(".")
                        if len(parts) == 2:
                            obj, method = parts
                            if method.lower() in {"get", "post", "put", "delete", "patch"}:
                                path_str = "/unknown"
                                if args_node and args_node.child_count > 0:
                                    first_arg = args_node.child(0)
                                    if first_arg.type == "string":
                                        path_str = get_node_text(first_arg).strip('"\'')
                                routes.append({
                                    "object": obj,
                                    "method": method.upper(),
                                    "path": path_str
                                })
            for child in node.children:
                _traverse(child)

        _traverse(root)
        return {"functions": functions, "classes": classes, "routes": routes}


class FileProcessor:
    """Handles file operations including hashing, caching, and exclusion checks."""
    
    def __init__(self, project_root: Path, cache: Dict, cache_lock: threading.Lock, additional_ignore_dirs: set):
        """
        Initialize the file processor.
        
        Args:
            project_root: Root directory of the project
            cache: Cache dictionary for file hashes
            cache_lock: Thread lock for cache operations
            additional_ignore_dirs: Set of additional directories to ignore
        """
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        self.additional_ignore_dirs = additional_ignore_dirs

    def hash_file(self, file_path: Path) -> str:
        """
        Calculates an MD5 hash of a file's content.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            str: Hex digest string, or "" if an error occurs
        """
        try:
            with file_path.open("rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        """
        Checks if a file should be excluded from processing.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if file should be excluded, False otherwise
        """
        default_exclude_dirs = {"venv", "__pycache__", "node_modules", "migrations", "build", "target", ".git", "coverage", "chrome_profile"}
        file_abs = file_path.resolve()
        
        for ignore in self.additional_ignore_dirs:
            ignore_path = Path(ignore)
            if not ignore_path.is_absolute():
                ignore_path = (self.project_root / ignore_path).resolve()
            try:
                file_abs.relative_to(ignore_path)
                return True
            except ValueError:
                continue
                
        if any(excluded in file_path.parts for excluded in default_exclude_dirs):
            return True
        return False

    def process_file(self, file_path: Path, language_analyzer: LanguageAnalyzer) -> Optional[tuple]:
        """
        Processes a single file for analysis.
        
        Args:
            file_path: Path to the file to process
            language_analyzer: Language analyzer instance
            
        Returns:
            Optional[tuple]: Tuple of (relative_path, analysis_result) or None if file should be skipped
        """
        file_hash = self.hash_file(file_path)
        relative_path = str(file_path.relative_to(self.project_root))
        
        with self.cache_lock:
            if relative_path in self.cache and self.cache[relative_path]["hash"] == file_hash:
                return None
                
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            analysis_result = language_analyzer.analyze_file(file_path, source_code)
            
            # Calculate complexity
            complexity = len(analysis_result["functions"]) + sum(len(methods) for methods in analysis_result["classes"].values())
            analysis_result["complexity"] = complexity
            
            with self.cache_lock:
                self.cache[relative_path] = {"hash": file_hash}
            return (relative_path, analysis_result)
        except Exception as e:
            print(f"❌ Error analyzing {file_path}: {e}")
            return None


class ReportGenerator:
    """Handles report generation and file output operations."""
    
    def __init__(self, project_root: Path, analysis: Dict[str, Dict]):
        """
        Initialize the report generator.
        
        Args:
            project_root: Root directory of the project
            analysis: Analysis results dictionary
        """
        self.project_root = project_root
        self.analysis = analysis

    def save_report(self):
        """Writes the final analysis dictionary to a JSON file."""
        report_path = self.project_root / "project_analysis.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.analysis, f, indent=4)

    def generate_init_files(self, overwrite: bool = True):
        """
        Automatically generates __init__.py files for all Python packages.
        
        Args:
            overwrite: Whether to overwrite existing __init__.py files
        """
        from collections import defaultdict

        # Group python files by their directory based on the analysis context
        package_modules = defaultdict(list)
        for rel_path in self.analysis.keys():
            if rel_path.endswith(".py"):
                file_path = Path(rel_path)
                if file_path.name == "__init__.py":
                    continue  # Skip existing __init__.py files in analysis
                package_dir = file_path.parent
                module_name = file_path.stem  # remove .py extension
                package_modules[str(package_dir)].append(module_name)

        # For each package directory, generate or update __init__.py
        for package, modules in package_modules.items():
            package_path = self.project_root / package
            init_file = package_path / "__init__.py"
            # Ensure package directory exists (it should, since modules are there)
            package_path.mkdir(parents=True, exist_ok=True)

            # Build the auto-generated content
            lines = [
                "# AUTO-GENERATED __init__.py",
                "# DO NOT EDIT MANUALLY - changes may be overwritten\n"
            ]
            # Import each module relative to the package
            for module in sorted(modules):
                lines.append(f"from . import {module}")
            # Create __all__ list to expose the modules
            lines.append("\n__all__ = [")
            for module in sorted(modules):
                lines.append(f"    '{module}',")
            lines.append("]\n")
            content = "\n".join(lines)

            # Write or overwrite the __init__.py file based on the flag
            if overwrite or not init_file.exists():
                with open(init_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Generated __init__.py in {package_path}")
            else:
                print(f"ℹ️ Skipped {init_file} (already exists)")


class ProjectScanner:
    """
    A universal project scanner that:
      - Identifies Python, Rust, JavaScript, and TypeScript files.
      - Extracts functions, classes, and naive route definitions.
      - Caches file hashes to skip unchanged files.
      - Detects moved files by matching file hashes.
      - Writes a single JSON report (project_analysis.json) at the end.
      - Processes files asynchronously via background workers (BotWorker/MultibotManager).
      - Auto-generates __init__.py files for Python packages using the project analysis context.
    """
    def __init__(self, project_root: Union[str, Path] = "."):
        """
        Initialize the project scanner.
        
        Args:
            project_root: The root directory of the project to scan.
        """
        self.project_root = Path(project_root).resolve()
        self.analysis: Dict[str, Dict] = {}
        self.cache = self.load_cache()
        self.cache_lock = threading.Lock()
        self.additional_ignore_dirs = set()
        self.language_analyzer = LanguageAnalyzer()
        self.file_processor = FileProcessor(
            self.project_root,
            self.cache,
            self.cache_lock,
            self.additional_ignore_dirs
        )
        self.report_generator = ReportGenerator(self.project_root, self.analysis)

    def load_cache(self) -> Dict:
        """
        Loads a JSON cache from disk if present.
        
        Returns:
            Dict: Cache dictionary or empty dict if no cache exists
        """
        if Path(CACHE_FILE).exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_cache(self):
        """Writes the updated cache to disk."""
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=4)

    def scan_project(self):
        """
        Orchestrates the project scan:
        - Finds Python, Rust, JS, and TS files using os.walk()
        - Excludes certain directories
        - Detects moved files by comparing cached hashes
        - Offloads file analysis to background workers
        - Saves a single JSON report 'project_analysis.json'
        """
        print(f"🔍 Scanning project: {self.project_root} ...")

        # Collect files using os.walk to capture all files (even in hidden directories)
        file_extensions = {'.py', '.rs', '.js', '.ts'}
        valid_files = []
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            # Skip directories that should be excluded
            if self.file_processor.should_exclude(root_path):
                continue
            for file in files:
                file_path = root_path / file
                if file_path.suffix.lower() in file_extensions and not self.file_processor.should_exclude(file_path):
                    valid_files.append(file_path)
        
        print(f"📝 Found {len(valid_files)} valid files for analysis.")

        # Track old vs. new paths for cache update
        previous_files = set(self.cache.keys())
        current_files = {str(f.relative_to(self.project_root)) for f in valid_files}
        moved_files = {}
        missing_files = previous_files - current_files

        # Detect moved files by matching file hashes
        for old_path in previous_files:
            old_hash = self.cache.get(old_path, {}).get("hash")
            if not old_hash:
                continue
            for new_path in current_files:
                new_file = self.project_root / new_path
                if self.file_processor.hash_file(new_file) == old_hash:
                    moved_files[old_path] = new_path
                    break

        # Remove truly missing files from cache
        for missing_file in missing_files:
            if missing_file not in moved_files:
                with self.cache_lock:
                    if missing_file in self.cache:
                        del self.cache[missing_file]

        # Update cache for moved files
        for old_path, new_path in moved_files.items():
            with self.cache_lock:
                self.cache[new_path] = self.cache.pop(old_path)

        # --- Asynchronous processing with BotWorker/MultibotManager ---
        print("⏱️  Processing files asynchronously...")
        num_workers = os.cpu_count() or 4
        manager = MultibotManager(scanner=self, num_workers=num_workers,
                                status_callback=lambda fp, res: print(f"Processed: {fp}"))
        for file_path in valid_files:
            manager.add_task(file_path)
        manager.wait_for_completion()
        manager.stop_workers()
        for result in manager.results_list:
            if result is not None:
                file_path, analysis_result = result
                self.analysis[file_path] = analysis_result

        # Write final report and cache
        self.report_generator.save_report()
        self.save_cache()
        print(f"✅ Scan complete. Results saved to {self.project_root / 'project_analysis.json'}")

    def _process_file(self, file_path: Path):
        """
        Handles analysis of a single file.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Optional[tuple]: Tuple of (relative_path, analysis_result) or None if file should be skipped
        """
        return self.file_processor.process_file(file_path, self.language_analyzer)

    def generate_init_files(self, overwrite: bool = True):
        """
        Generates __init__.py files for Python packages.
        
        Args:
            overwrite: Whether to overwrite existing __init__.py files
        """
        self.report_generator.generate_init_files(overwrite)


# ----- Asynchronous Task Queue Components -----
class BotWorker(threading.Thread):
    """
    A background worker that continuously pulls file tasks from a queue,
    processes them using the scanner's _process_file method, and stores results.
    """
    def __init__(self, task_queue: queue.Queue, results_list: list, scanner: ProjectScanner, status_callback=None):
        threading.Thread.__init__(self)
        self.task_queue = task_queue
        self.results_list = results_list
        self.scanner = scanner
        self.status_callback = status_callback
        self.daemon = True
        self.start()

    def run(self):
        while True:
            file_path = self.task_queue.get()
            if file_path is None:
                break
            result = self.scanner._process_file(file_path)
            if result is not None:
                self.results_list.append(result)
            if self.status_callback:
                self.status_callback(file_path, result)
            self.task_queue.task_done()


class MultibotManager:
    """
    Manages a pool of BotWorker threads.
    """
    def __init__(self, scanner: ProjectScanner, num_workers=4, status_callback=None):
        self.task_queue = queue.Queue()
        self.results_list = []
        self.scanner = scanner
        self.status_callback = status_callback
        self.workers = [
            BotWorker(self.task_queue, self.results_list, scanner, status_callback)
            for _ in range(num_workers)
        ]

    def add_task(self, file_path: Path):
        self.task_queue.put(file_path)

    def wait_for_completion(self):
        self.task_queue.join()

    def stop_workers(self):
        for _ in self.workers:
            self.task_queue.put(None)


# ----- Interactive Entry Point -----
if __name__ == "__main__":
    project_root = input("Enter the project root directory to scan (default '.'): ").strip() or "."
    ignore_input = input("Enter additional directories to ignore (comma separated, or leave empty): ").strip()
    additional_ignore_dirs = {d.strip() for d in ignore_input.split(",") if d.strip()} if ignore_input else set()

    scanner = ProjectScanner(project_root=project_root)
    scanner.additional_ignore_dirs = additional_ignore_dirs
    scanner.scan_project()
    # Auto-generate __init__.py files after scanning
    scanner.generate_init_files(overwrite=True)

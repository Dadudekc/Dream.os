import os
import ast
import json
import hashlib
import threading
import queue
import logging
from pathlib import Path
from typing import Dict, Union, Optional, List, Any

logger = logging.getLogger(__name__)

# Try importing tree-sitter for Rust/JS/TS parsing
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language = None
    Parser = None
    logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")

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
            logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")
            return None

        grammar_paths = {
            "rust": "path/to/tree-sitter-rust.so",
            "javascript": "path/to/tree-sitter-javascript.so",
        }

        if lang_name not in grammar_paths:
            logger.warning(f"⚠️ No grammar path for {lang_name}. Skipping.")
            return None

        grammar_path = grammar_paths[lang_name]
        if not Path(grammar_path).exists():
            logger.warning(f"⚠️ {lang_name} grammar not found at {grammar_path}")
            return None

        try:
            lang_lib = Language(grammar_path, lang_name)
            parser = Parser()
            parser.set_language(lang_lib)
            return parser
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize tree-sitter {lang_name} parser: {e}")
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
            return {
                "language": suffix,
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0
            }

    # ----- AGENT CATEGORIZER CHANGES START (replaced _analyze_python) -----
    def _analyze_python(self, source_code: str) -> Dict:
        """
        Analyzes Python source code using AST.
        Returns dict of {functions, classes, routes, complexity}
        """
        tree = ast.parse(source_code)
        functions = []
        classes = {}
        routes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)

                # Existing route-detection logic
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr'):
                        func_attr = decorator.func.attr.lower()
                        if func_attr in {"route", "get", "post", "put", "delete", "patch"}:
                            path_arg = "/unknown"
                            methods = [func_attr.upper()]
                            # If there's an argument, capture it as route path
                            if decorator.args:
                                arg0 = decorator.args[0]
                                if isinstance(arg0, ast.Str):
                                    path_arg = arg0.s

                            # If there's a "methods" keyword, gather them
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
                # Capture docstring
                docstring = ast.get_docstring(node)

                # Capture method names
                method_names = [
                    n.name for n in node.body if isinstance(n, ast.FunctionDef)
                ]

                # Capture base classes
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_parts = []
                        attr_node = base
                        while isinstance(attr_node, ast.Attribute):
                            base_parts.append(attr_node.attr)
                            attr_node = attr_node.value
                        if isinstance(attr_node, ast.Name):
                            base_parts.append(attr_node.id)
                        base_classes.append(".".join(reversed(base_parts)))
                    else:
                        base_classes.append(None)

                classes[node.name] = {
                    "methods": method_names,
                    "docstring": docstring,
                    "base_classes": base_classes
                }

        # Complexity = count of functions + sum of all class methods
        complexity = len(functions) + sum(len(c["methods"]) for c in classes.values())

        return {
            "language": ".py",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity
        }
    # ----- AGENT CATEGORIZER CHANGES END -----

    def _analyze_rust(self, source_code: str) -> Dict:
        """
        Analyzes Rust source code using tree-sitter.
        Returns dict with {functions, classes}.
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
        # We won't do route detection for Rust. Complexity is just function + method count
        complexity = len(functions) + sum(len(m) for m in classes.values())
        return {
            "language": ".rs",
            "functions": functions,
            "classes": classes,
            "routes": [],
            "complexity": complexity
        }

    def _analyze_javascript(self, source_code: str) -> Dict:
        """
        Analyzes JavaScript/TypeScript source code using tree-sitter.
        Returns dict with {functions, classes, routes}.
        """
        if not self.js_parser:
            return {"functions": [], "classes": {}, "routes": [], "complexity": 0}

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
            # Keep traversing
            for child in node.children:
                _traverse(child)

        _traverse(root)
        # Complexity = function count + sum of method counts (not extracted in detail here for classes)
        complexity = len(functions)  # If we had method info in classes, we’d add them
        return {
            "language": ".js",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity
        }


class FileProcessor:
    """Handles file operations including hashing, caching, and exclusion checks."""

    def __init__(
        self,
        project_root: Path,
        cache: Dict,
        cache_lock: threading.Lock,
        additional_ignore_dirs: set
    ):
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
        Checks if a file or directory should be excluded from processing.
        Returns True if file/directory is excluded; otherwise False.
        """
        default_exclude_dirs = {
            "venv", "__pycache__", "node_modules", "migrations", "build",
            "target", ".git", "coverage", "chrome_profile"
        }
        file_abs = file_path.resolve()

        # Exclude this script itself if needed
        try:
            if file_abs == Path(__file__).resolve():
                return True
        except NameError:
            # If __file__ is undefined (interactive mode), ignore
            pass

        # Check user-specified ignore dirs
        for ignore in self.additional_ignore_dirs:
            ignore_path = Path(ignore)
            if not ignore_path.is_absolute():
                ignore_path = (self.project_root / ignore_path).resolve()
            try:
                file_abs.relative_to(ignore_path)
                return True
            except ValueError:
                continue

        # Check default ignore dirs
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
            Optional[tuple]: (relative_path, analysis_result) or None if file is skipped
        """
        file_hash = self.hash_file(file_path)
        relative_path = str(file_path.relative_to(self.project_root))

        with self.cache_lock:
            if (
                relative_path in self.cache
                and self.cache[relative_path]["hash"] == file_hash
            ):
                return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            analysis_result = language_analyzer.analyze_file(file_path, source_code)

            # We already set "complexity" in each language’s analyzer
            with self.cache_lock:
                self.cache[relative_path] = {"hash": file_hash}
            return (relative_path, analysis_result)
        except Exception as e:
            logger.error(f"❌ Error analyzing {file_path}: {e}")
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

        package_modules = defaultdict(list)
        for rel_path in self.analysis.keys():
            if rel_path.endswith(".py"):
                file_path = Path(rel_path)
                if file_path.name == "__init__.py":
                    continue
                package_dir = file_path.parent
                module_name = file_path.stem
                package_modules[str(package_dir)].append(module_name)

        for package, modules in package_modules.items():
            package_path = self.project_root / package
            init_file = package_path / "__init__.py"
            package_path.mkdir(parents=True, exist_ok=True)

            lines = [
                "# AUTO-GENERATED __init__.py",
                "# DO NOT EDIT MANUALLY - changes may be overwritten\n"
            ]
            for module in sorted(modules):
                lines.append(f"from . import {module}")
            lines.append("\n__all__ = [")
            for module in sorted(modules):
                lines.append(f"    '{module}',")
            lines.append("]\n")
            content = "\n".join(lines)

            if overwrite or not init_file.exists():
                with open(init_file, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"✅ Generated __init__.py in {package_path}")
            else:
                logger.info(f"ℹ️ Skipped {init_file} (already exists)")


class ProjectScanner:
    """
    A universal project scanner that:
      - Identifies Python, Rust, JS, and TS files.
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
        Returns a dict or empty if none found/corrupted.
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
        - Finds Python, Rust, JS, and TS files using os.walk().
        - Excludes certain directories.
        - Detects moved files by comparing cached hashes.
        - Offloads file analysis to background workers.
        - Saves a single JSON report 'project_analysis.json'.
        """
        logger.info(f"🔍 Scanning project: {self.project_root} ...")

        file_extensions = {'.py', '.rs', '.js', '.ts'}
        valid_files = []
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            if self.file_processor.should_exclude(root_path):
                continue
            for file in files:
                file_path = root_path / file
                if file_path.suffix.lower() in file_extensions and not self.file_processor.should_exclude(file_path):
                    valid_files.append(file_path)

        logger.info(f"📝 Found {len(valid_files)} valid files for analysis.")

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

        # Asynchronous processing
        logger.info("⏱️  Processing files asynchronously...")
        num_workers = os.cpu_count() or 4
        manager = MultibotManager(
            scanner=self,
            num_workers=num_workers,
            status_callback=lambda fp, res: logger.info(f"Processed: {fp}")
        )
        for file_path in valid_files:
            manager.add_task(file_path)
        manager.wait_for_completion()
        manager.stop_workers()

        # Gather results
        for result in manager.results_list:
            if result is not None:
                file_path, analysis_result = result
                self.analysis[file_path] = analysis_result

        # Write final report and cache
        self.report_generator.save_report()
        self.save_cache()
        print(f"✅ Scan complete. Results saved to {self.project_root / 'project_analysis.json'}")

    def _process_file(self, file_path: Path):
        """Internal wrapper to process a file via FileProcessor."""
        return self.file_processor.process_file(file_path, self.language_analyzer)

    def generate_init_files(self, overwrite: bool = True):
        """Generates __init__.py files for Python packages."""
        self.report_generator.generate_init_files(overwrite)

    def export_chatgpt_context(
        self,
        template_path: Optional[str] = None,
        output_path: Optional[str] = None
    ):
        """
        Exports the analysis results into a structured format suitable for ChatGPT or any AI assistant.
        If no template is provided, writes JSON. Otherwise uses Jinja to render.
        """
        if not output_path:
            output_path = "chatgpt_project_context.md" if template_path else "chatgpt_project_context.json"

        if not template_path:
            payload = {
                "project_root": str(self.project_root),
                "num_files_analyzed": len(self.analysis),
                "analysis_details": self.analysis
            }
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=4)
                print(f"✅ Exported project context (JSON) to: {output_path}")
            except Exception as e:
                logger.error(f"❌ Error writing JSON context: {e}")
            return

        # Render with Jinja
        try:
            from jinja2 import Template
            with open(template_path, "r", encoding="utf-8") as tf:
                template_content = tf.read()
            t = Template(template_content)

            context_dict = {
                "project_root": str(self.project_root),
                "analysis": self.analysis,
                "num_files_analyzed": len(self.analysis),
            }
            rendered = t.render(context=context_dict)
            with open(output_path, "w", encoding="utf-8") as outf:
                outf.write(rendered)
            print(f"✅ Exported project context (Jinja) to: {output_path}")
        except ImportError:
            print("⚠️ Jinja2 not installed. Run `pip install jinja2` and re-try.")
        except Exception as e:
            logger.error(f"❌ Error rendering Jinja template: {e}")

    # ----- AGENT CATEGORIZER CHANGES START -----
    def categorize_agents(self):
        """
        Loops over all analyzed Python classes, assigning:
          - maturity level (Kiddie Script, Prototype, Core Asset)
          - agent_type (ActionAgent, DataAgent, SignalAgent, Utility, etc.)
        """
        for file_path, result in self.analysis.items():
            if file_path.endswith(".py"):
                # result["classes"] is a dict: {class_name: {methods, docstring, base_classes}}
                for class_name, class_data in result["classes"].items():
                    class_data["maturity"] = self._maturity_level(class_name, class_data)
                    class_data["agent_type"] = self._agent_type(class_name, class_data)

    def _maturity_level(self, class_name: str, class_data: Dict[str, Any]) -> str:
        """
        Simple scoring approach:
          +1 if docstring is present
          +1 if >3 methods
          +1 if uses base class besides 'object'
          +1 if class name starts uppercase
        """
        score = 0
        if class_data.get("docstring"):
            score += 1
        if len(class_data.get("methods", [])) > 3:
            score += 1
        if any(base for base in class_data.get("base_classes", []) if base not in ("object", None)):
            score += 1
        if class_name and class_name[0].isupper():
            score += 1

        # 0 => Kiddie Script, 1 => Prototype, >=2 => Core Asset
        levels = ["Kiddie Script", "Prototype", "Core Asset", "Core Asset"]
        return levels[min(score, 3)]

    def _agent_type(self, class_name: str, class_data: Dict[str, Any]) -> str:
        """
        Naive classification approach based on docstring & method names.
        Customize your own logic for better results.
        """
        doc = (class_data.get("docstring") or "").lower()
        methods = class_data.get("methods", [])

        # If there's a 'run' method
        if "run" in methods:
            return "ActionAgent"
        # If docstring mentions "transform" or "parse"
        if "transform" in doc or "parse" in doc:
            return "DataAgent"
        # If there's a method like "predict" or "analyze"
        if any(m in methods for m in ["predict", "analyze"]):
            return "SignalAgent"
        # Otherwise treat as Utility
        return "Utility"
    # ----- AGENT CATEGORIZER CHANGES END -----


class BotWorker(threading.Thread):
    """
    A background worker that continuously pulls file tasks from a queue,
    processes them using the scanner's _process_file method, and stores results.
    """
    def __init__(self, task_queue: queue.Queue, results_list: list, scanner: ProjectScanner, status_callback=None):
        super().__init__()
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
        for _ in range(len(self.workers)):
            self.task_queue.put(None)


# ------------------------------
# Entry Point (for CLI usage)
# ------------------------------
if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Project scanner with optional agent categorization.")
    parser.add_argument("--project-root", default=".", help="Root directory to scan.")
    parser.add_argument("--ignore", nargs="*", default=[], help="Additional directories to ignore.")
    parser.add_argument("--categorize-agents", action="store_true",
                        help="If set, categorize Python classes into maturity level and agent type.")
    args = parser.parse_args()

    scanner = ProjectScanner(project_root=args.project_root)
    scanner.additional_ignore_dirs = set(args.ignore)

    scanner.scan_project()
    scanner.generate_init_files(overwrite=True)

    # Run agent categorization if requested
    if args.categorize_agents:
        scanner.categorize_agents()
        # Re-save the final report with updated fields
        scanner.report_generator.save_report()
        print("✅ Agent categorization complete. Updated 'project_analysis.json' with agent_type and maturity.")

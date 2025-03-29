import os
import ast
import json
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import subprocess
import csv
from pyvis.network import Network
from typing import Dict, Any, List
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import hashlib
from tqdm import tqdm

# === CONFIG ===
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

INTERNAL_PREFIXES = [
    "core", "utils", "interfaces.pyqt", "chatgpt_automation", "social", "memory"
]
PREFIX_COLORS = {
    "core": "skyblue",
    "utils": "lightgray",
    "interfaces": "lightgreen",
    "chatgpt_automation": "violet",
    "social": "mediumpurple",
    "memory": "orange",
    "default": "lightcoral",
}
KNOWN_VENV_NAMES = {"venv", ".venv", "env", ".env", "__pypackages__"}

OUTPUT_DIR = os.path.join(ROOT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
CACHE_FILE = os.path.join(OUTPUT_DIR, "analysis_cache.json")

# Import code metrics analyzer (assumed to be defined elsewhere)
from code_metrics import get_code_metrics

# === CACHING FUNCTIONS ===
def load_cache() -> Dict[str, Any]:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
    return {}

def save_cache(cache: Dict[str, Any]):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

def file_hash(file_path: str) -> str:
    """Calculate an MD5 hash of a file's contents."""
    h = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        print(f"Error hashing {file_path}: {e}")
        return ""

# === SEMANTIC ANALYSIS ===
class CodeAnalyzer(ast.NodeVisitor):
    """Analyzes Python code for semantic information."""
    def __init__(self):
        self.class_count = 0
        self.function_count = 0
        self.has_main = False
        self.docstring = None
        self.imports = []
    def visit_ClassDef(self, node):
        self.class_count += 1
        self.generic_visit(node)
    def visit_FunctionDef(self, node):
        self.function_count += 1
        self.generic_visit(node)
    def visit_If(self, node):
        # Check for if __name__ == "__main__"
        if (isinstance(node.test, ast.Compare) and
            isinstance(node.test.left, ast.Name) and
            node.test.left.id == "__name__" and
            isinstance(node.test.ops[0], ast.Eq) and
            isinstance(node.test.comparators[0], ast.Str) and
            node.test.comparators[0].s == "__main__"):
            self.has_main = True
        self.generic_visit(node)
    def visit_Import(self, node):
        self.imports.extend(alias.name for alias in node.names)
        self.generic_visit(node)
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

def analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a Python file for semantic information."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
        analyzer = CodeAnalyzer()
        analyzer.visit(tree)
        docstring = ast.get_docstring(tree)
        return {
            "class_count": analyzer.class_count,
            "function_count": analyzer.function_count,
            "has_main": analyzer.has_main,
            "docstring": docstring,
            "imports": analyzer.imports,
            "test_module": file_path.split(os.sep)[-1].startswith("test_") or "tests" in file_path.split(os.sep),
        }
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return {
            "class_count": 0,
            "function_count": 0,
            "has_main": False,
            "docstring": None,
            "imports": [],
            "test_module": False,
            "error": str(e)
        }

def get_git_metadata(file_path: str) -> Dict[str, str]:
    """Get Git metadata for a single file using batched commands."""
    try:
        rel_path = os.path.relpath(file_path, ROOT_DIR)
        commands = {
            "last_author": ['git', 'log', '-1', '--format=%an', '--', rel_path],
            "last_date": ['git', 'log', '-1', '--format=%ad', '--', rel_path],
            "commit_count": ['git', 'rev-list', '--count', 'HEAD', '--', rel_path],
            "first_commit": ['git', 'log', '--format=%ad', '--reverse', '--', rel_path],
        }
        metadata = {}
        for key, cmd in commands.items():
            try:
                result = subprocess.check_output(cmd, cwd=ROOT_DIR, stderr=subprocess.DEVNULL)
                metadata[key] = result.decode().strip()
            except:
                metadata[key] = None
        return metadata
    except Exception as e:
        return {
            "last_author": None,
            "last_date": None,
            "commit_count": None,
            "first_commit": None,
            "error": str(e)
        }

# === BATCH GIT METADATA RETRIEVAL ===
def get_all_git_metadata(file_list: List[str]) -> Dict[str, Dict[str, str]]:
    """Retrieve Git metadata for multiple files using ThreadPoolExecutor."""
    metadata_all = {}
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(get_git_metadata, file): file for file in file_list}
        for future in tqdm(as_completed(futures), total=len(futures), desc="📦 Fetching Git metadata"):
            file_path = futures[future]
            metadata_all[file_path] = future.result()
    return metadata_all

# === HOTSPOT ANALYSIS ===
def calculate_hotspot_score(node_data: Dict[str, Any]) -> float:
    """Calculate a hotspot score based on various metrics."""
    score = 0.0
    if node_data["size_kb"] > 0:
        size_score = min(node_data["size_kb"] / 100.0, 1.0)
        score += size_score * 0.2
    if node_data["degree"] > 0:
        coupling_score = min(node_data["degree"] / 20.0, 1.0)
        score += coupling_score * 0.2
    complexity_score = min((node_data["class_count"] + node_data["function_count"]) / 30.0, 1.0)
    score += complexity_score * 0.15
    if node_data.get("max_complexity", 0) > 0:
        cc_score = min(node_data["max_complexity"] / 20.0, 1.0)
        score += cc_score * 0.15
    if node_data.get("maintainability_index", 0) > 0:
        mi_score = (100 - node_data["maintainability_index"]) / 100.0
        score += mi_score * 0.15
    coverage = node_data.get("coverage_percentage", 0)
    if coverage < 80:
        score *= (1 + (0.8 - coverage/100) * 0.5)
    if node_data["test_module"]:
        score *= 0.5
    return round(score, 3)

# === UTILITY FUNCTIONS ===
def is_virtual_env_path(path):
    return (
        "pyvenv.cfg" in os.listdir(path)
        or os.path.basename(path) in KNOWN_VENV_NAMES
    )

def get_module_name(file_path: str) -> str:
    relative = os.path.relpath(file_path, ROOT_DIR)
    return relative.replace(os.sep, ".")[:-3] if relative.endswith(".py") else relative

def resolve_prefix(module_name: str) -> str:
    parts = module_name.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in INTERNAL_PREFIXES:
            return candidate
    return "default"

def shorten(name: str) -> str:
    parts = name.split(".")
    return ".".join(p[0] if i < len(parts) - 1 else p for i, p in enumerate(parts))

# === GENERATE DEPENDENCY GRAPH WITH CACHING ===
def generate_dependency_graph() -> (nx.DiGraph, Dict[str, Any]):
    import_graph = nx.DiGraph()
    module_metadata = {}
    cache = load_cache()

    # Use git ls-files to get all tracked Python files
    try:
        result = subprocess.check_output(['git', 'ls-files', '*.py'], cwd=ROOT_DIR)
        file_list = result.decode().splitlines()
        # Convert relative paths to absolute
        file_list = [os.path.join(ROOT_DIR, f) for f in file_list]
    except Exception as e:
        print("Error running git ls-files:", e)
        file_list = []
        for subdir, _, files in os.walk(ROOT_DIR):
            for file in files:
                if file.endswith(".py"):
                    file_list.append(os.path.join(subdir, file))

    print("🔍 Analyzing code metrics...")
    code_metrics = get_code_metrics(ROOT_DIR)

    # Filter out files in virtual environments
    files_to_process = [f for f in file_list if not is_virtual_env_path(os.path.dirname(f))]

    # For incremental analysis, check each file's last modified time and hash
    files_for_analysis = []
    for file_path in files_to_process:
        mtime = os.path.getmtime(file_path)
        mtime_str = str(mtime)
        file_hash_value = file_hash(file_path)
        cache_entry = cache.get(file_path)
        if cache_entry and cache_entry.get("mtime") == mtime_str and cache_entry.get("hash") == file_hash_value:
            # File unchanged; skip analysis (metadata will be reused)
            continue
        else:
            files_for_analysis.append(file_path)

    print(f"Processing {len(files_for_analysis)} changed files out of {len(files_to_process)} total.")

    # Use ProcessPoolExecutor for AST analysis concurrently on changed files
    analysis_results = {}
    if files_for_analysis:
        with ProcessPoolExecutor() as proc_executor:
            futures = {proc_executor.submit(analyze_file, f): f for f in files_for_analysis}
            for future in tqdm(as_completed(futures), total=len(futures), desc="🔍 Analyzing files"):
                fpath = futures[future]
                try:
                    analysis_results[fpath] = future.result()
                except Exception as e:
                    print(f"Error processing {fpath}: {e}")

    # Retrieve Git metadata concurrently for all files_to_process (I/O-bound)
    git_metadata_all = get_all_git_metadata(files_to_process)

    # Merge analysis results with cache; update cache for changed files
    for file_path in files_to_process:
        module_name = get_module_name(file_path)
        # Use cached analysis if file was not re-analyzed
        if file_path not in analysis_results and file_path in cache:
            analysis = cache[file_path].get("analysis", {})
        else:
            analysis = analysis_results.get(file_path, {})
            # Update cache for this file
            cache[file_path] = {
                "mtime": str(os.path.getmtime(file_path)),
                "hash": file_hash(file_path),
                "analysis": analysis
            }
        git_meta = git_metadata_all.get(file_path, {})
        metrics = code_metrics.get(file_path, {})
        file_size = round(os.path.getsize(file_path) / 1024, 2)
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        combined_meta = {
            **analysis,
            **git_meta,
            **metrics,
            "path": file_path,
            "size_kb": file_size,
            "last_modified": last_modified
        }
        module_metadata[module_name] = combined_meta
        # Add edges from imports (if any)
        for imp in analysis.get("imports", []):
            import_graph.add_edge(module_name, imp)

    # Save updated cache to disk
    save_cache(cache)
    print("\n✅ All files processed with progress feedback.")
    return import_graph, module_metadata

# === MAIN EXECUTION ===
import_graph, module_metadata = generate_dependency_graph()

# Filter internal dependencies
filtered_edges = [
    (u, v) for u, v in import_graph.edges()
    if any(v.startswith(prefix) for prefix in INTERNAL_PREFIXES)
]
internal_graph = nx.DiGraph()
internal_graph.add_edges_from(filtered_edges)

# === EXPORT JSON WITH METADATA ===
def export_graph_to_json(graph: nx.DiGraph, output_file: str):
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "root_dir": ROOT_DIR,
            "total_modules": len(graph.nodes()),
            "total_dependencies": len(graph.edges())
        },
        "nodes": [],
        "edges": [],
        "hotspots": [],
        "cycles": []
    }

    for node in graph.nodes():
        prefix = resolve_prefix(node)
        node_meta = module_metadata.get(node, {})
        degree = graph.degree[node]
        node_data = {
            "id": node,
            "label": shorten(node),
            "group": prefix,
            "degree": degree,
            **node_meta
        }
        node_data["hotspot_score"] = calculate_hotspot_score(node_data)
        if not node.startswith(tuple(INTERNAL_PREFIXES)):
            node_data['external'] = True
            node_data['color'] = 'lightpink'
        data["nodes"].append(node_data)

    for u, v in graph.edges():
        data["edges"].append({
            "from": u,
            "to": v,
            "type": "imports"
        })

    cycles = list(nx.simple_cycles(graph))
    if cycles:
        data["cycles"] = [
            {
                "modules": cycle,
                "length": len(cycle),
                "avg_complexity": sum(module_metadata.get(m, {}).get("avg_complexity", 0) for m in cycle) / len(cycle)
            }
            for cycle in cycles
        ]

    hotspots = sorted(
        data["nodes"],
        key=lambda x: x["hotspot_score"],
        reverse=True
    )[:10]
    data["hotspots"] = [
        {
            "module": h["id"],
            "score": h["hotspot_score"],
            "reasons": [
                f"High coupling (degree={h['degree']})" if h['degree'] > 5 else None,
                f"Large file ({h['size_kb']}KB)" if h['size_kb'] > 50 else None,
                f"Complex ({h['class_count']} classes, {h['function_count']} functions)" 
                if h['class_count'] + h['function_count'] > 10 else None,
                f"High cyclomatic complexity ({h.get('max_complexity', 0)})"
                if h.get('max_complexity', 0) > 10 else None,
                f"Low maintainability ({h.get('maintainability_index', 100):.0f})"
                if h.get('maintainability_index', 100) < 65 else None,
                f"Low test coverage ({h.get('coverage_percentage', 0):.0f}%)"
                if h.get('coverage_percentage', 100) < 80 else None
            ]
        }
        for h in hotspots
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"🧠 Graph with metadata exported to: {output_file}")

    csv_file = os.path.join(os.path.dirname(output_file), "dependency_summary.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data["nodes"][0].keys())
        writer.writeheader()
        writer.writerows(data["nodes"])
    print(f"📊 CSV export saved to: {csv_file}")

    history_dir = os.path.join(OUTPUT_DIR, "graph_history")
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(
        history_dir,
        f"dependency_graph_{datetime.now().strftime('%Y-%m-%d')}.json"
    )
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"📅 Historical snapshot saved to: {history_file}")

# === INTERACTIVE VISUALIZATION ===
def generate_interactive_graph(graph: nx.DiGraph, output_file: str):
    net = Network(
        height="800px",
        width="100%",
        bgcolor="#ffffff",
        font_color="black",
        directed=True,
        notebook=False
    )
    for node in graph.nodes():
        meta = module_metadata.get(node, {})
        prefix = resolve_prefix(node)
        tooltip = f"""
        <b>{node}</b><br>
        <hr>
        <b>Size & Structure:</b><br>
        Size: {meta.get('size_kb', 0)}KB<br>
        Classes: {meta.get('class_count', 0)}<br>
        Functions: {meta.get('function_count', 0)}<br>
        <hr>
        <b>Complexity:</b><br>
        Cyclomatic: {meta.get('max_complexity', 0)}<br>
        Maintainability: {meta.get('maintainability_index', 0):.0f}<br>
        Test Coverage: {meta.get('coverage_percentage', 0):.0f}%<br>
        <hr>
        <b>History:</b><br>
        Last modified: {meta.get('last_modified', 'N/A')}<br>
        Author: {meta.get('last_author', 'N/A')}<br>
        Hotspot Score: {meta.get('hotspot_score', 0):.2f}
        """
        color = PREFIX_COLORS.get(prefix, PREFIX_COLORS["default"])
        if meta.get('hotspot_score', 0) > 0.7:
            color = "#ff6b6b"
        elif meta.get('coverage_percentage', 0) < 60:
            color = "#ffd93d"
        net.add_node(
            node,
            label=shorten(node),
            title=tooltip,
            color=color,
            size=20 + (meta.get('hotspot_score', 0) * 30)
        )
    for u, v in graph.edges():
        net.add_edge(u, v)
    net.set_options("""
    const options = {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -100,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {
                "enabled": true,
                "iterations": 1000
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 200
        },
        "edges": {
            "color": {
                "inherit": false,
                "color": "#2B2B2B",
                "opacity": 0.3
            },
            "smooth": {
                "enabled": true,
                "type": "continuous"
            }
        }
    }
    """)
    net.show(output_file)
    print(f"🌐 Interactive visualization saved to: {output_file}")

# Generate outputs
export_graph_to_json(internal_graph, os.path.join(OUTPUT_DIR, "dependency_graph.json"))
generate_interactive_graph(internal_graph, os.path.join(OUTPUT_DIR, "interactive_graph.html"))

# Print enhanced summary
print("\n=== 📊 Dependency Analysis Summary ===")
print(f"Total modules: {len(internal_graph.nodes())}")
print(f"Total dependencies: {len(internal_graph.edges())}")

cycles = list(nx.simple_cycles(internal_graph))
if cycles:
    print(f"\n⚠️ Found {len(cycles)} circular dependencies:")
    for cycle in cycles[:5]:
        avg_complexity = sum(module_metadata.get(m, {}).get("avg_complexity", 0) for m in cycle) / len(cycle)
        print(f"  • {' -> '.join(cycle)}")
        print(f"    Average complexity: {avg_complexity:.2f}")

hotspots = sorted(
    [(n, module_metadata.get(n, {})) for n in internal_graph.nodes()],
    key=lambda x: x[1].get('hotspot_score', 0),
    reverse=True
)[:5]

print("\n🔥 Top 5 Hotspots:")
for module, meta in hotspots:
    reasons = []
    if meta.get('degree', 0) > 5:
        reasons.append(f"high coupling ({meta['degree']} connections)")
    if meta.get('size_kb', 0) > 50:
        reasons.append(f"large file ({meta['size_kb']}KB)")
    if meta.get('class_count', 0) + meta.get('function_count', 0) > 10:
        reasons.append(f"complex ({meta['class_count']} classes, {meta['function_count']} functions)")
    if meta.get('max_complexity', 0) > 10:
        reasons.append(f"high cyclomatic complexity ({meta['max_complexity']})")
    if meta.get('maintainability_index', 100) < 65:
        reasons.append(f"low maintainability ({meta['maintainability_index']:.0f})")
    if meta.get('coverage_percentage', 100) < 80:
        reasons.append(f"low test coverage ({meta['coverage_percentage']:.0f}%)")
    
    print(f"  • {module} (score: {meta.get('hotspot_score', 0):.2f})")
    print(f"    Reasons: {', '.join(filter(None, reasons))}")
    print(f"    Maintainability Index: {meta.get('maintainability_index', 0):.0f}")
    print(f"    Test Coverage: {meta.get('coverage_percentage', 0):.0f}%")

print("\n✅ Analysis complete! Open interactive_graph.html in your browser to explore the visualization.")

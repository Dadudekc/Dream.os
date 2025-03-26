import os
import ast
import networkx as nx
import matplotlib.pyplot as plt

# Root directory to scan for Python files
ROOT_DIR = os.getcwd()  # Use current working directory

# Create a directed graph for imports
import_graph = nx.DiGraph()

# Helper function to extract imports from a Python file
def extract_imports(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            node = ast.parse(f.read(), filename=file_path)
        imports = []
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    imports.append(alias.name)
            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module:
                    imports.append(stmt.module)
        return imports
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

# Walk through the directory and build the import graph
for subdir, _, files in os.walk(ROOT_DIR):
    for file in files:
        if file.endswith(".py"):
            full_path = os.path.join(subdir, file)
            module_name = os.path.relpath(full_path, ROOT_DIR).replace(os.sep, ".").rstrip(".py")
            module_name = module_name[:-1] if module_name.endswith(".") else module_name
            imports = extract_imports(full_path)
            for imp in imports:
                import_graph.add_edge(module_name, imp)

# Trim the graph to only internal project dependencies (those starting with known prefixes)
internal_prefixes = ["core", "utils", "chatgpt_automation", "social", "interfaces"]
filtered_edges = [(u, v) for u, v in import_graph.edges() if v.split('.')[0] in internal_prefixes]
internal_graph = nx.DiGraph()
internal_graph.add_edges_from(filtered_edges)

# Visualize the internal import graph
plt.figure(figsize=(16, 12))
pos = nx.spring_layout(internal_graph, k=0.5, iterations=50)
nx.draw(internal_graph, pos, with_labels=True, node_size=2000, node_color="skyblue", font_size=8, font_weight="bold", edge_color="gray")
plt.title("Internal Module Import Graph")
plt.axis("off")
plt.tight_layout()
plt.savefig("dependency_graph.png")
print("Dependency graph has been saved as 'dependency_graph.png'") 
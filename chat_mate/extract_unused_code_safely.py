import os
import sys
import subprocess
import shutil
import json
import tempfile
from pathlib import Path
import importlib.util
import ast

# --- Configuration Constants ---
PROJECT_ROOT = Path.cwd()  # Modify if needed
TRASH_DIR = PROJECT_ROOT / "trash_unused"
VULTURE_MODULE = "vulture"
FULL_UNUSED_THRESHOLD = 0.8  # for vulture full file heuristic

# --- Utility Print Functions ---
def print_info(msg): print(f"\n🧠 {msg}")
def print_error(msg): print(f"\n❌ {msg}")
def print_success(msg): print(f"\n✅ {msg}")

# --- Vulture Helpers ---
def is_vulture_available() -> bool:
    return importlib.util.find_spec(VULTURE_MODULE) is not None

def install_vulture() -> bool:
    print_info("Installing vulture...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", VULTURE_MODULE])
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"vulture installation failed: {e}")
        return False

def run_vulture(target_path: Path, extra_args: list = None) -> str:
    cmd = [sys.executable, "-m", "vulture", str(target_path)]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def group_vulture_output(raw_output: str) -> dict:
    """
    Returns a dict mapping file paths to list of reported unused line numbers.
    """
    grouped = {}
    for line in raw_output.strip().splitlines():
        if ".py" not in line or "unreachable code" in line:
            continue
        parts = line.split(":")
        if len(parts) < 3:
            continue
        file_path = parts[0].strip()
        try:
            lineno = int(parts[1])
        except ValueError:
            continue
        grouped.setdefault(file_path, []).append(lineno)
    return grouped

def detect_full_unused_files(grouped: dict, threshold: float = FULL_UNUSED_THRESHOLD) -> list:
    """
    A file is considered fully unused if the number of unique reported unused lines
    divided by its total lines is at least the threshold.
    """
    fully_unused = []
    for file, lines in grouped.items():
        try:
            with open(file, "r", encoding="utf-8") as f:
                total_lines = len(f.readlines())
            unique_lines = set(lines)
            ratio = len(unique_lines) / total_lines if total_lines > 0 else 0
            if ratio >= threshold:
                fully_unused.append(file)
        except Exception as e:
            print_error(f"Error reading {file}: {e}")
    return sorted(fully_unused)

# --- Basic AST Scan ---
def basic_ast_scan(target_path: Path) -> dict:
    """
    For each .py file under target_path, parse its AST and record function and class definitions.
    Then, naively check if the definition name appears anywhere else in the file (outside its def).
    Returns a dict mapping file path to a list of unused definitions.
    (Note: This is a very basic heuristic.)
    """
    unused_defs = {}
    for root, _, files in os.walk(target_path):
        for f in files:
            if not f.endswith(".py"):
                continue
            file_path = Path(root) / f
            try:
                with open(file_path, "r", encoding="utf-8") as source:
                    code = source.read()
                tree = ast.parse(code, filename=str(file_path))
                # Collect definitions
                defs = []
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        defs.append((node.name, node.lineno))
                # For each definition, check if its name appears outside its definition line
                unused_in_file = []
                for name, lineno in defs:
                    lines = code.splitlines()
                    def_line = lines[lineno - 1]
                    # Exclude the definition line
                    rest = "\n".join(lines[:lineno-1] + lines[lineno:])
                    if name not in rest:
                        unused_in_file.append({"name": name, "line": lineno})
                if unused_in_file:
                    unused_defs[str(file_path)] = unused_in_file
            except Exception as e:
                print_error(f"AST scan failed for {file_path}: {e}")
    return unused_defs

# --- Interactive Menu Functions ---
def menu_choice(prompt: str, choices: list) -> int:
    """
    Display a numbered list of choices and return the selected index (1-indexed).
    """
    print_info(prompt)
    for idx, choice in enumerate(choices, 1):
        print(f"  [{idx}] {choice}")
    while True:
        try:
            selection = input("Enter number: ").strip()
            if selection.isdigit():
                sel = int(selection)
                if 1 <= sel <= len(choices):
                    return sel
            print_error("Invalid selection. Try again.")
        except KeyboardInterrupt:
            sys.exit()

def interactive_delete_menu(files: list) -> list:
    """
    Interactive deletion menu that returns a list of files selected for deletion.
    """
    if not files:
        print_info("No unused Python files detected.")
        return []
    print_info("Unused Python Files Detected:")
    for idx, f in enumerate(files, 1):
        print(f"  [{idx}] {f}")
    print("\nEnter numbers (comma-separated) of files to delete, 'all' to delete all, or 'q' to cancel:")
    choice = input("Your choice: ").strip().lower()
    if choice == "q":
        print("No files will be deleted.")
        return []
    selected = []
    if choice == "all":
        selected = files
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(",") if x.strip().isdigit()]
            selected = [files[i-1] for i in indices if 1 <= i <= len(files)]
        except Exception as e:
            print_error(f"Invalid input: {e}")
    return selected

def move_to_trash(file_path: str):
    try:
        src = Path(file_path)
        if not TRASH_DIR.exists():
            TRASH_DIR.mkdir(parents=True)
        dest = TRASH_DIR / src.name
        shutil.move(str(src), dest)
        print_success(f"Moved to trash: {src} -> {dest}")
    except Exception as e:
        print_error(f"Failed to move {file_path} to trash: {e}")

# --- Main Interactive Menu ---
def interactive_menu():
    print_info("Welcome to the Unused Code Extractor Interactive Menu")
    print("Choose scan method:")
    method = menu_choice("Select method:", ["Vulture Scan (full file detection)", "Basic AST Scan (unused defs per file)"])
    
    if method == 1:
        scan_method = "vulture"
    else:
        scan_method = "ast"

    target = input("\nEnter target directory to scan (default is current directory): ").strip()
    if not target:
        target_path = PROJECT_ROOT
    else:
        target_path = Path(target)
        if not target_path.exists():
            print_error("Target path does not exist.")
            sys.exit(1)
    
    if scan_method == "vulture":
        if not is_vulture_available():
            if not install_vulture():
                print_error("vulture unavailable and fallback not implemented.")
                sys.exit(1)
        raw_output = run_vulture(target_path, extra_args=["--min-confidence", "100"])
        grouped = group_vulture_output(raw_output)
        # Ask if user wants to include deeper snippet details
        print_info("Include snippet details for unused lines? (unused functions/classes details)")
        include_snippets = input("Type 'y' for yes, or Enter for no: ").strip().lower() == 'y'
        if include_snippets:
            report = {}
            for file, lines in grouped.items():
                snippets = []
                for ln in sorted(set(lines)):
                    snippets.append({"line": ln, "snippet": extract_snippet(file, ln)})
                report[file] = snippets
            # Save report as JSON for review
            report_file = target_path / "unused_code_grouped.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print_success(f"Snippet report saved to: {report_file.resolve()}")
            files_to_consider = list(report.keys())
        else:
            files_to_consider = detect_full_unused_files(grouped, threshold=FULL_UNUSED_THRESHOLD)
    else:
        # Basic AST scan mode
        print_info("Running basic AST scan...")
        ast_report = basic_ast_scan(target_path)
        if not ast_report:
            print_info("No unused definitions detected via AST scan.")
            sys.exit(0)
        # Display results per file
        for file, defs in ast_report.items():
            print_info(f"In file: {file}")
            for d in defs:
                print(f"  Line {d['line']}: {d['name']}")
        # For AST scan, we won't delete individual definitions automatically.
        print_info("AST scan mode does not support deletion. Review the report above.")
        sys.exit(0)
    
    if not files_to_consider:
        print_info("✅ No unused files detected.")
        sys.exit(0)
    
    # Dry-run mode by default: list what would be deleted
    print_info("Dry-run: The following files are candidates for deletion:")
    for f in files_to_consider:
        print(f" - {f}")
    confirm = input("\nProceed to deletion? (y/N): ").strip().lower()
    if confirm != "y":
        print_info("Operation cancelled. No files were deleted.")
        sys.exit(0)
    
    # Interactive deletion menu
    selected_files = interactive_delete_menu(files_to_consider)
    if not selected_files:
        print_info("No files selected for deletion.")
        sys.exit(0)
    
    for f in selected_files:
        move_to_trash(f)
    print_success("Deletion complete.")

def extract_snippet(file: str, line: int, context: int = 10) -> str:
    try:
        with open(file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        start = max(0, line - 1)
        end = min(len(all_lines), start + context)
        return "".join(all_lines[start:end])
    except Exception as e:
        return f"# Could not extract snippet: {e}"

if __name__ == "__main__":
    interactive_menu()

import ast
import os
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)

def is_python_file(path: str) -> bool:
    return path.endswith(".py") and not any(skip in path for skip in ["venv", ".venv", "site-packages", "__pycache__"])

def scan_ast_for_unused_defs(directory: str):
    unused_defs = {}

    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            if not is_python_file(full_path):
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    tree = ast.parse(f.read(), filename=full_path)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        name = node.name
                        if full_path not in unused_defs:
                            unused_defs[full_path] = []
                        unused_defs[full_path].append(name)

            except Exception as e:
                print(f"❌ AST scan failed for {full_path}: {e}")

    return unused_defs

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Pattern, Union, Optional, Tuple
# Assuming PromptExecutionService is correctly located. Adjust if necessary.
# Option 1: If PromptExecutionService is directly in core
# from core.PromptExecutionService import PromptExecutionService
# Option 2: If it's in core.services
# from core.services.prompt_execution_service import PromptExecutionService
# Correcting based on previous initialization code
from core.PromptExecutionService import PromptExecutionService

logger = logging.getLogger(__name__)

# --- Regex Patterns ---

# General Comment Patterns (aligned with Rule 3)
COMMENT_PATTERNS = [
    re.compile(r'#\s*(?:TODO|FIXME|XXX)[:\s]*(.*)$', re.IGNORECASE),
    re.compile(r'#\s*PLACEHOLDER[:\s]*(.*)$', re.IGNORECASE), # Can be general or function related
    re.compile(r'#\s*REVIEW[:\s]*(.*)$', re.IGNORECASE),
    re.compile(r'#\s*BAD_NAMING[:\s]*(.*)$', re.IGNORECASE),
    re.compile(r'#\s*SMELL[:\s]*(.*)$', re.IGNORECASE),
    re.compile(r'#\s*TIGHT_COUPLING[:\s]*(.*)$', re.IGNORECASE),
    re.compile(r'#\s*MISSING_TEST[:\s]*(.*)$', re.IGNORECASE),
    re.compile(r'#\s*PERFORMANCE_WARNING[:\s]*(.*)$', re.IGNORECASE),
]

# Specific Placeholder Function Patterns
# Matches 'def func_name(...): pass # PLACEHOLDER ...' or 'def func_name(...):\n    pass # PLACEHOLDER ...' etc.
# Captures function name (group 1)
FUNC_PLACEHOLDER_PASS_PATTERN = re.compile(
    r'^\s*def\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*->?\s*[^:]*:\s*(?:(?:pass|\.\.\.)(?:\s*#\s*PLACEHOLDER.*)?$|$\n(?:\s*"""[^"""]*"""|\s*\'\'\'[^\'\']\'\'\')?\s*(?:pass|\.\.\.)(?:\s*#\s*PLACEHOLDER.*)?$)', 
    re.IGNORECASE | re.MULTILINE
)
# Matches 'def func_name(...): raise NotImplementedError # PLACEHOLDER ...'
# Captures function name (group 1)
FUNC_PLACEHOLDER_NOT_IMPLEMENTED_PATTERN = re.compile(
    r'^\s*def\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*->?\s*[^:]*:\s*(?:raise\s+NotImplementedError(?:\(.*\))?(?:\s*#\s*PLACEHOLDER.*)?$|$\n(?:\s*"""[^"""]*"""|\s*\'\'\'[^\'\']\'\'\')?\s*raise\s+NotImplementedError(?:\(.*\))?(?:\s*#\s*PLACEHOLDER.*)?$)',
    re.IGNORECASE | re.MULTILINE
)

# Combine all function placeholder patterns
FUNC_PLACEHOLDER_PATTERNS = [
    FUNC_PLACEHOLDER_PASS_PATTERN,
    FUNC_PLACEHOLDER_NOT_IMPLEMENTED_PATTERN
]

# Default directories to exclude (keep existing list)
DEFAULT_EXCLUDE_DIRS = [
    ".git", "__pycache__", "venv", "logs", "cache", "data", "outputs",
    "tests", "test_fortress", "htmlcov", "node_modules", "build", "dist",
    "memory", ".cursor", "templates", "assets", "coverage_report",
    "execution_results", "failed_tasks", "processed_tasks", "queued_tasks",
    "episodes", "metrics", "state", "web", "scripts", "prompts",
]

class TodoScanner:
    """
    Scans project files for specific comment patterns (e.g., # TODO) and 
    placeholder functions, then queues tasks via PromptExecutionService 
    to address them using appropriate templates.
    """

    def __init__(self,
                 prompt_execution_service: PromptExecutionService,
                 root_dir: Union[str, Path] = '.',
                 exclude_dirs: List[str] = DEFAULT_EXCLUDE_DIRS,
                 comment_patterns: List[Pattern] = COMMENT_PATTERNS,
                 func_placeholder_patterns: List[Pattern] = FUNC_PLACEHOLDER_PATTERNS,
                 context_lines: int = 5):
        """
        Initialize the TodoScanner.

        Args:
            prompt_execution_service: Instance of PromptExecutionService to queue tasks.
            root_dir: The root directory to start scanning from.
            exclude_dirs: A list of directory names to exclude from scanning.
            comment_patterns: Regex patterns for general comments (# TODO, # REVIEW, etc.).
            func_placeholder_patterns: Regex patterns for placeholder functions.
            context_lines: Number of lines before/after for general comment context.
        """
        self.prompt_execution_service = prompt_execution_service
        self.root_dir = Path(root_dir).resolve()
        self.exclude_dirs = set(exclude_dirs)
        self.comment_patterns = comment_patterns
        self.func_placeholder_patterns = func_placeholder_patterns
        self.context_lines = context_lines
        self.general_template_name = "fix_code_snippet.jinja"
        self.function_template_name = "implement_placeholder_function.jinja"
        logger.info(f"TodoScanner initialized. Root: {self.root_dir}, Exclusions: {len(self.exclude_dirs)}, "
                    f"Comment Patterns: {len(self.comment_patterns)}, Func Patterns: {len(self.func_placeholder_patterns)}")

    def _find_full_function_def(self, lines: List[str], start_line_index: int) -> Tuple[Optional[str], int, int]:
        """Attempts to find the full definition of a function starting at a given line."""
        code_block = []
        indentation = -1
        func_def_line = lines[start_line_index].lstrip()

        # Find initial indentation of the 'def' line
        initial_indent_match = re.match(r'^(\s*)', lines[start_line_index])
        initial_indent_level = len(initial_indent_match.group(1)) if initial_indent_match else 0

        for i in range(start_line_index, len(lines)):
            line = lines[i]
            current_indent_match = re.match(r'^(\s*)', line)
            current_indent_level = len(current_indent_match.group(1)) if current_indent_match else 0
            
            # Determine the base indentation level from the first line (def)
            if indentation == -1 and line.strip().startswith("def"):
                 indentation = current_indent_level
                 code_block.append(line)
                 continue

            # If we have found the start, append lines that are indented further
            # or are part of the function body (same indent or more)
            # Stop if we encounter a line with less or equal indentation than the starting 'def' line,
            # unless it's the very first line after def (might be the body start).
            if indentation != -1:
                 if current_indent_level >= indentation or line.strip() == "": # Keep indented lines and blank lines
                     # Special case: stop if a new function/class starts at the same indent level
                     if current_indent_level == indentation and re.match(r'^\s*(?:def|class)\s+', line) and i > start_line_index:
                         break
                     code_block.append(line)
                 elif current_indent_level < indentation and line.strip() != "": # Line less indented and not blank
                     break
            # Handle edge case where the line found by regex isn't the `def` line (e.g., comment inside)
            # This is simplified; a full AST parser would be more robust.
            elif i > start_line_index + 5: # Heuristic limit to search for def
                 logger.warning(f"Could not reliably find start of function near line {start_line_index + 1}")
                 return None, start_line_index, start_line_index # Fallback

        if not code_block:
             return None, start_line_index, start_line_index

        # Try to clean trailing whitespace/blank lines
        while code_block and not code_block[-1].strip():
             code_block.pop()
        
        end_line_index = start_line_index + len(code_block) -1
        return "".join(code_block), start_line_index, end_line_index


    def scan_and_queue_tasks(self) -> int:
        """
        Scans the project directory for specified patterns and placeholder functions, 
        then queues tasks using the appropriate templates.

        Returns:
            The number of tasks queued.
        """
        queued_count = 0
        processed_locations = set() # Track (file_path, line_num) to avoid duplicates
        logger.info(f"Starting scan in {self.root_dir}...")

        for file_path_obj in self.root_dir.rglob('*'):
            # Ensure we only process Python files
            if file_path_obj.is_file() and file_path_obj.suffix == '.py':
                resolved_path_str = str(file_path_obj.resolve())
                try:
                    relative_path = file_path_obj.relative_to(self.root_dir)

                    # Check exclude list
                    if any(part in self.exclude_dirs for part in relative_path.parts):
                        continue

                    with open(resolved_path_str, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.splitlines(True) # Keep newlines

                    # --- Pass 1: Scan for Placeholder Functions ---
                    # We use finditer to find all non-overlapping matches in the file content
                    for pattern in self.func_placeholder_patterns:
                        for match in pattern.finditer(content):
                            func_name = match.group(1)
                            # Estimate start line based on character position
                            start_char = match.start()
                            line_num_approx = content.count('\n', 0, start_char) + 1
                            
                            if (resolved_path_str, line_num_approx) in processed_locations:
                                continue

                            logger.info(f"Found placeholder function '{func_name}' in {relative_path} near line {line_num_approx}.")
                            
                            # Find the actual start line index by searching backwards slightly
                            actual_start_index = -1
                            search_start = max(0, line_num_approx - 5) # Search a few lines back
                            for idx in range(search_start, min(line_num_approx + 2, len(lines))):
                                if f"def {func_name}" in lines[idx]:
                                    actual_start_index = idx
                                    break
                            
                            if actual_start_index == -1:
                                actual_start_index = line_num_approx - 1 # Fallback to approximation
                                logger.warning(f"Could not precisely determine start line for {func_name} in {relative_path}, using approximation {line_num_approx}")

                            full_func_code, func_start_line_idx, func_end_line_idx = self._find_full_function_def(lines, actual_start_index)

                            if full_func_code:
                                task_context = {
                                    'file_path': resolved_path_str,
                                    'function_name': func_name,
                                    'function_code': full_func_code,
                                    'function_start_line': func_start_line_idx + 1,
                                }
                                
                                try:
                                    task_file_path = self.prompt_execution_service.execute_prompt(
                                        template_name=self.function_template_name,
                                        context=task_context,
                                        target_output=resolved_path_str,
                                        auto_execute=True
                                    )
                                    logger.debug(f"Function placeholder task queued: {task_file_path}")
                                    queued_count += 1
                                    # Mark all lines of this function as processed for comment scanning
                                    for i in range(func_start_line_idx, func_end_line_idx + 1):
                                         processed_locations.add((resolved_path_str, i + 1))
                                except AttributeError as ae:
                                    logger.error(f"PromptExecutionService missing execute_prompt? {ae}", exc_info=True); return queued_count
                                except Exception as queue_exc:
                                    logger.error(f"Error queueing function task for {relative_path}:{func_start_line_idx+1}: {queue_exc}", exc_info=True)
                            else:
                                logger.warning(f"Could not extract full function definition for {func_name} in {relative_path} near line {line_num_approx}. Skipping function task.")
                                processed_locations.add((resolved_path_str, line_num_approx)) # Mark as processed anyway

                    # --- Pass 2: Scan for General Comments ---
                    for i, line in enumerate(lines):
                        line_num = i + 1
                        if (resolved_path_str, line_num) in processed_locations:
                            continue # Skip lines already processed as part of a function task

                        for pattern in self.comment_patterns:
                            match = pattern.search(line)
                            if match:
                                comment_content = match.group(1).strip()
                                if not comment_content:
                                    keyword_match = re.search(r'#\s*(\w+)', pattern.pattern)
                                    comment_content = f"Address {keyword_match.group(1) if keyword_match else 'comment'} marker"

                                start_context_idx = max(0, i - self.context_lines)
                                end_context_idx = min(len(lines), i + self.context_lines + 1)
                                code_context = "".join(lines[start_context_idx:end_context_idx])

                                task_context = {
                                    'file_path': resolved_path_str,
                                    'line_number': line_num,
                                    'comment_content': comment_content,
                                    'code_context': code_context,
                                }

                                logger.info(f"Found comment pattern in {relative_path}:{line_num}. Queuing task...")

                                try:
                                    task_file_path = self.prompt_execution_service.execute_prompt(
                                        template_name=self.general_template_name,
                                        context=task_context,
                                        target_output=resolved_path_str,
                                        auto_execute=True
                                    )
                                    logger.debug(f"Comment task queued: {task_file_path}")
                                    queued_count += 1
                                    processed_locations.add((resolved_path_str, line_num))
                                    # Move to next line once a pattern is matched
                                    break 
                                except AttributeError as ae:
                                     logger.error(f"PromptExecutionService missing execute_prompt? {ae}", exc_info=True); return queued_count
                                except Exception as queue_exc:
                                     logger.error(f"Error queueing comment task for {relative_path}:{line_num}: {queue_exc}", exc_info=True)
                                     processed_locations.add((resolved_path_str, line_num)) # Mark as processed even if queueing fails

                except IsADirectoryError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing file {resolved_path_str}: {e}", exc_info=True)

        logger.info(f"Scan complete. Queued {queued_count} tasks.")
        return queued_count 
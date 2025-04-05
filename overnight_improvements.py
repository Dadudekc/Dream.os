#!/usr/bin/env python3
"""
Overnight Improvements Script

This script runs a scheduled improvement cycle to optimize code quality
and test coverage using stateful AI assistance. It leverages the cursor
session manager to maintain context between improvements.
"""

import os
import sys
import json
import logging
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/overnight_improvements.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OvernightImprovements")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from core.StatefulCursorManager import StatefulCursorManager
from core.system_loader import DreamscapeSystemLoader
from code_metrics import CodeMetricsAnalyzer

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run overnight code improvements')
    parser.add_argument('--config', type=str, default='memory/config.yml',
                      help='Path to config file')
    parser.add_argument('--modules', type=str, nargs='+',
                      help='Specific modules to improve (optional)')
    parser.add_argument('--dry-run', action='store_true',
                      help='Run without making actual changes')
    parser.add_argument('--max-modules', type=int, default=3,
                      help='Maximum number of modules to improve')
    parser.add_argument('--commit', action='store_true',
                      help='Commit changes if tests pass')
    return parser.parse_args()

def initialize_services(config_path: str):
    """Initialize required services."""
    logger.info("Initializing services...")
    
    # Initialize system loader
    system_loader = DreamscapeSystemLoader(config_path)
    
    # Get the project root directory
    project_root = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Initialize stateful cursor manager
    cursor_manager = StatefulCursorManager(
        config_manager=system_loader.get_service('config_manager'),
        state_file_path=str(project_root / "memory" / "cursor_state.json")
    )
    
    # Initialize code metrics analyzer
    metrics_analyzer = CodeMetricsAnalyzer(str(project_root))
    
    # Register services
    system_loader.register_service("stateful_cursor_manager", cursor_manager)
    
    return {
        "system_loader": system_loader,
        "cursor_manager": cursor_manager,
        "metrics_analyzer": metrics_analyzer,
        "project_root": project_root
    }

def collect_baseline_metrics(metrics_analyzer):
    """Collect baseline metrics for the entire codebase."""
    logger.info("Collecting baseline metrics...")
    
    try:
        metrics = metrics_analyzer.analyze_directory()
        logger.info(f"Collected metrics for {len(metrics)} files")
        return metrics
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return {}

def identify_improvement_targets(cursor_manager, metrics, max_modules: int, specified_modules: Optional[List[str]] = None):
    """Identify modules that need improvement."""
    logger.info("Identifying improvement targets...")
    
    # Update metrics history in cursor manager
    cursor_manager.update_metrics_history(metrics)
    
    # If specific modules are specified, prioritize those
    if specified_modules:
        targets = []
        for module in specified_modules:
            if module in metrics:
                targets.append({
                    "module": module,
                    "metrics": metrics[module],
                    "score": 100  # High priority since manually specified
                })
        
        logger.info(f"Using {len(targets)} manually specified modules")
        return targets[:max_modules]
    
    # Otherwise, use the improvement candidates algorithm
    candidates = cursor_manager.get_improvement_candidates(max_modules)
    
    # Add the metrics data to each candidate
    for candidate in candidates:
        module = candidate["module"]
        if module in metrics:
            candidate["metrics"] = metrics[module]
    
    logger.info(f"Identified {len(candidates)} improvement candidates")
    return candidates

def generate_improvement_prompt(cursor_manager, module: str, metrics: Dict[str, Any]):
    """Generate a context-aware improvement prompt for a module."""
    logger.info(f"Generating improvement prompt for {module}...")
    
    # Get module-specific context
    context = cursor_manager.get_latest_prompt_context(module)
    
    # Add module metrics to the prompt
    metrics_string = "\nCurrent metrics:\n"
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            metrics_string += f"- {key}: {value}\n"
    
    # Build the complete prompt
    prompt = f"""
{context}

{metrics_string}

Please analyze the code in {module} and suggest specific improvements to:
1. Reduce complexity (current: {metrics.get('avg_complexity', 'N/A')})
2. Improve test coverage (current: {metrics.get('coverage_percentage', 'N/A')}%)
3. Enhance readability and maintainability (current MI: {metrics.get('maintainability_index', 'N/A')})

For each improvement:
1. Explain the issue
2. Provide the exact code changes needed
3. Explain how this improves the metrics

Format your response as:
IMPROVEMENT 1:
<explanation>
CODE_BEFORE:
```python
<existing code>
```
CODE_AFTER:
```python
<improved code>
```
METRICS_IMPACT: <expected impact>

IMPROVEMENT 2:
...
"""
    
    return prompt

def process_improvement_response(response: str, module: str):
    """Process the AI response and extract improvements."""
    logger.info(f"Processing improvement response for {module}...")
    
    # Extract improvements from the response
    improvements = []
    
    # Simple parser for the response format
    current_improvement = None
    current_section = None
    section_content = ""
    
    for line in response.splitlines():
        if line.startswith("IMPROVEMENT "):
            # Save the previous improvement if any
            if current_improvement:
                improvements.append(current_improvement)
            
            # Start a new improvement
            current_improvement = {
                "module": module,
                "explanation": "",
                "code_before": "",
                "code_after": "",
                "metrics_impact": ""
            }
            current_section = "explanation"
            section_content = ""
        elif line.startswith("CODE_BEFORE:"):
            current_section = "code_before"
            section_content = ""
        elif line.startswith("CODE_AFTER:"):
            if current_improvement:
                current_improvement[current_section] = section_content.strip()
            current_section = "code_after"
            section_content = ""
        elif line.startswith("METRICS_IMPACT:"):
            if current_improvement:
                current_improvement[current_section] = section_content.strip()
            current_section = "metrics_impact"
            section_content = ""
        else:
            # Append to the current section
            section_content += line + "\n"
    
    # Save the last improvement
    if current_improvement and current_section:
        current_improvement[current_section] = section_content.strip()
        improvements.append(current_improvement)
    
    logger.info(f"Extracted {len(improvements)} improvements")
    return improvements

def apply_improvements(improvements: List[Dict[str, Any]], dry_run: bool = False):
    """Apply the proposed improvements to the codebase."""
    logger.info(f"Applying {len(improvements)} improvements (dry run: {dry_run})...")
    
    applied = []
    
    for improvement in improvements:
        module = improvement["module"]
        code_before = improvement["code_before"]
        code_after = improvement["code_after"]
        
        # Extract the code blocks (remove the ```python and ``` markers)
        code_before = code_before.replace("```python", "").replace("```", "").strip()
        code_after = code_after.replace("```python", "").replace("```", "").strip()
        
        if not code_before or not code_after:
            logger.warning(f"Missing code blocks for improvement in {module}")
            continue
        
        # In dry run mode, just log the changes
        if dry_run:
            logger.info(f"Would apply to {module}:\n{code_before[:100]}... -> {code_after[:100]}...")
            applied.append(improvement)
            continue
        
        try:
            # Check if the file exists
            if not os.path.exists(module):
                logger.warning(f"Module file not found: {module}")
                continue
            
            # Read the file content
            with open(module, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply the change (simple substring replacement)
            if code_before in content:
                new_content = content.replace(code_before, code_after)
                
                # Write back to the file
                with open(module, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                logger.info(f"Successfully applied improvement to {module}")
                applied.append(improvement)
            else:
                logger.warning(f"Could not find the exact code block in {module}")
        except Exception as e:
            logger.error(f"Error applying improvement to {module}: {e}")
    
    return applied

def run_tests(project_root: Path, module: str):
    """Run tests for a specific module."""
    logger.info(f"Running tests for {module}...")
    
    try:
        # Construct the test file path
        module_name = os.path.basename(module)
        if module_name.endswith('.py'):
            module_name = module_name[:-3]
        
        test_file = project_root / "tests" / f"test_{module_name}.py"
        
        # Check if the test file exists
        if not test_file.exists():
            logger.warning(f"No test file found for {module}")
            return False
        
        # Run pytest
        result = subprocess.run(
            ["pytest", str(test_file), "-v"],
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        
        # Check if the tests passed
        if result.returncode == 0:
            logger.info(f"Tests passed for {module}")
            return True
        else:
            logger.error(f"Tests failed for {module}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False

def commit_changes(project_root: Path, modules: List[str]):
    """Commit the changes to git."""
    logger.info(f"Committing changes for {len(modules)} modules...")
    
    try:
        # Create a commit message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        modules_str = ", ".join([os.path.basename(m) for m in modules])
        commit_message = f"chore: overnight self-improvement updates ({timestamp})\n\nModules improved: {modules_str}"
        
        # Add the changes
        subprocess.run(["git", "add"] + modules, cwd=str(project_root), check=True)
        
        # Commit
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=str(project_root),
            check=True
        )
        
        logger.info("Changes committed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        return False

def run_improvement_cycle(services, args):
    """Run a full improvement cycle."""
    logger.info("Starting improvement cycle...")
    
    cursor_manager = services["cursor_manager"]
    metrics_analyzer = services["metrics_analyzer"]
    project_root = services["project_root"]
    
    try:
        # 1. Collect baseline metrics
        baseline_metrics = collect_baseline_metrics(metrics_analyzer)
        if not baseline_metrics:
            logger.error("Failed to collect baseline metrics. Aborting.")
            return False
        
        # 2. Identify improvement targets
        targets = identify_improvement_targets(
            cursor_manager,
            baseline_metrics,
            args.max_modules,
            args.modules
        )
        
        if not targets:
            logger.info("No suitable improvement targets found. Ending cycle.")
            return True
        
        # 3. Process each target module
        successful_modules = []
        
        for target in targets:
            module = target["module"]
            metrics = target.get("metrics", {})
            
            logger.info(f"Processing module: {module}")
            
            # Generate improvement prompt
            prompt = generate_improvement_prompt(cursor_manager, module, metrics)
            
            # Queue the prompt for processing (dry run mode skips actual execution)
            if args.dry_run:
                logger.info(f"[DRY RUN] Would execute prompt for {module}")
                # Simulate a response for testing
                response = f"""
IMPROVEMENT 1:
The method is too complex with nested conditions.

CODE_BEFORE:
```python
def process_data(data):
    result = []
    if data:
        for item in data:
            if item.get('active'):
                if item.get('type') == 'special':
                    result.append(item['value'] * 2)
                else:
                    result.append(item['value'])
    return result
```

CODE_AFTER:
```python
def process_data(data):
    if not data:
        return []
        
    result = []
    for item in data:
        if not item.get('active'):
            continue
            
        multiplier = 2 if item.get('type') == 'special' else 1
        result.append(item['value'] * multiplier)
    
    return result
```

METRICS_IMPACT: Reduces cyclomatic complexity from 5 to 3, improves readability.
"""
            else:
                # Use the cursor manager to execute the prompt
                task_id = cursor_manager.queue_stateful_prompt(module, prompt)
                
                # Wait for the task to complete (this is synchronous, but you might want to make this async)
                while task_id in cursor_manager.get_active_sessions():
                    time.sleep(1)
                
                # Get the response
                session_history = cursor_manager.get_session_history()
                response = next((s["result"] for s in session_history if s["id"] == task_id), "")
            
            # Process the improvements
            improvements = process_improvement_response(response, module)
            
            # Apply the improvements
            applied = apply_improvements(improvements, args.dry_run)
            
            if not applied:
                logger.warning(f"No improvements applied to {module}")
                continue
            
            # Collect new metrics after improvements
            if not args.dry_run:
                new_metrics = metrics_analyzer.analyze_file(module)
                
                # Run tests to ensure no regressions
                tests_pass = run_tests(project_root, module)
                
                if tests_pass:
                    # Record the improvement in the state
                    for improvement in applied:
                        cursor_manager.add_improvement_record(
                            module=module,
                            changes={"summary": improvement["explanation"][:100]},
                            metrics_before=metrics,
                            metrics_after=new_metrics
                        )
                    
                    successful_modules.append(module)
                    logger.info(f"Successfully improved {module}")
                else:
                    logger.warning(f"Tests failed for {module}, improvements will not be recorded")
            else:
                # In dry run mode, just log what would happen
                logger.info(f"[DRY RUN] Would record improvements for {module}")
                successful_modules.append(module)
        
        # 4. Commit changes if requested
        if args.commit and successful_modules and not args.dry_run:
            commit_changes(project_root, successful_modules)
        
        # 5. Save the updated state
        cursor_manager.save_state()
        
        logger.info(f"Improvement cycle completed. Improved {len(successful_modules)} modules.")
        return True
        
    except Exception as e:
        logger.error(f"Error in improvement cycle: {e}")
        # Still save state on error
        cursor_manager.save_state()
        return False

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    logger.info("==== Starting overnight improvements ====")
    
    try:
        # Initialize services
        services = initialize_services(args.config)
        
        # Run improvement cycle
        success = run_improvement_cycle(services, args)
        
        if success:
            logger.info("Overnight improvements completed successfully")
        else:
            logger.error("Overnight improvements encountered errors")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
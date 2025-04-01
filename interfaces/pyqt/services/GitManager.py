"""
Git Manager Service

This service handles Git operations and repository management.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class GitManager:
    """Service for managing Git operations and repository state."""
    
    def __init__(self, project_root: str = '.'):
        """
        Initialize the git manager.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = Path(project_root)
        self.logger = logger
        
    def _run_git_command(self, cmd: List[str]) -> Tuple[bool, str, str]:
        """Run a git command and return the result."""
        try:
            result = subprocess.run(
                ["git"] + cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            self.logger.error(f"Git command failed: {e}")
            return False, "", str(e)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current Git repository status.
        
        Returns:
            Dictionary containing repository status information
        """
        success, output, error = self._run_git_command(["status", "--porcelain"])
        if not success:
            return {"error": error}
            
        return {
            "clean": not output,
            "changes": [line.split(maxsplit=1) for line in output.splitlines()],
            "error": None
        }
    
    def stage_file(self, file_path: str) -> bool:
        """
        Stage a file for commit.
        
        Args:
            file_path: Path to the file to stage
            
        Returns:
            bool: True if successful, False otherwise
        """
        success, _, error = self._run_git_command(["add", file_path])
        if not success:
            self.logger.error(f"Failed to stage file {file_path}: {error}")
        return success
    
    def commit(self, message: str, files: Optional[List[str]] = None) -> bool:
        """
        Create a commit with the specified message.
        
        Args:
            message: Commit message
            files: Optional list of specific files to commit
            
        Returns:
            bool: True if successful, False otherwise
        """
        cmd = ["commit", "-m", message]
        if files:
            cmd.extend(files)
            
        success, _, error = self._run_git_command(cmd)
        if not success:
            self.logger.error(f"Failed to create commit: {error}")
        return success
    
    def get_current_branch(self) -> str:
        """
        Get the name of the current branch.
        
        Returns:
            str: Name of the current branch
        """
        success, output, _ = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        return output.strip() if success else "unknown"
    
    def create_branch(self, branch_name: str) -> bool:
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the branch to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        success, _, error = self._run_git_command(["checkout", "-b", branch_name])
        if not success:
            self.logger.error(f"Failed to create branch {branch_name}: {error}")
        return success
    
    def checkout_branch(self, branch_name: str) -> bool:
        """
        Checkout an existing branch.
        
        Args:
            branch_name: Name of the branch to checkout
            
        Returns:
            bool: True if successful, False otherwise
        """
        success, _, error = self._run_git_command(["checkout", branch_name])
        if not success:
            self.logger.error(f"Failed to checkout branch {branch_name}: {error}")
        return success 
import logging
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
import git

from core.PathManager import PathManager

class GitIntegrationService:
    """Service for handling Git operations."""
    
    def __init__(self, path_manager: PathManager, logger: Optional[logging.Logger] = None):
        """
        Initialize the Git integration service.
        
        Args:
            path_manager: Path manager instance
            logger: Optional logger instance
        """
        self.path_manager = path_manager
        self.logger = logger or logging.getLogger(__name__)
        self.repo = self._get_repo()
        
    def _get_repo(self) -> Optional[git.Repo]:
        """Get Git repository instance for the workspace."""
        try:
            return git.Repo(str(self.path_manager.get_workspace_path()))
        except Exception as e:
            self.logger.error(f"Error getting Git repo: {str(e)}")
            return None
            
    async def commit_changes(self, message: str) -> Dict[str, Any]:
        """
        Commit changes to the repository.
        
        Args:
            message: Commit message
            
        Returns:
            Dict containing:
                - success: bool
                - error: Optional[str]
                - commit_hash: Optional[str]
        """
        try:
            if not self.repo:
                return {
                    "success": False,
                    "error": "Git repository not initialized",
                    "commit_hash": None
                }
                
            # Stage all changes
            self.repo.git.add(".")
            
            # Check if there are changes to commit
            if not self.repo.is_dirty(untracked_files=True):
                return {
                    "success": True,
                    "error": None,
                    "commit_hash": None,
                    "message": "No changes to commit"
                }
                
            # Create commit
            commit = self.repo.index.commit(message)
            
            return {
                "success": True,
                "error": None,
                "commit_hash": commit.hexsha,
                "message": "Changes committed successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error committing changes: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "commit_hash": None
            }
            
    async def create_branch(self, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the new branch
            base_branch: Branch to base the new branch on
            
        Returns:
            Dict containing operation result
        """
        try:
            if not self.repo:
                return {
                    "success": False,
                    "error": "Git repository not initialized"
                }
                
            # Check if branch exists
            if branch_name in self.repo.heads:
                return {
                    "success": False,
                    "error": f"Branch {branch_name} already exists"
                }
                
            # Get base branch
            base = self.repo.heads[base_branch]
            
            # Create new branch
            new_branch = self.repo.create_head(branch_name, base)
            
            # Switch to new branch
            new_branch.checkout()
            
            return {
                "success": True,
                "error": None,
                "message": f"Created and switched to branch {branch_name}"
            }
            
        except Exception as e:
            self.logger.error(f"Error creating branch: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def push_changes(self, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Push changes to remote repository.
        
        Args:
            branch: Optional branch name to push
            
        Returns:
            Dict containing operation result
        """
        try:
            if not self.repo:
                return {
                    "success": False,
                    "error": "Git repository not initialized"
                }
                
            # Get current branch if none specified
            branch = branch or self.repo.active_branch.name
            
            # Push changes
            origin = self.repo.remote("origin")
            push_info = origin.push(branch)
            
            if push_info[0].flags & push_info[0].ERROR:
                return {
                    "success": False,
                    "error": "Error pushing changes to remote"
                }
                
            return {
                "success": True,
                "error": None,
                "message": f"Changes pushed to {branch}"
            }
            
        except Exception as e:
            self.logger.error(f"Error pushing changes: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def get_status(self) -> Dict[str, Any]:
        """Get repository status."""
        try:
            if not self.repo:
                return {
                    "success": False,
                    "error": "Git repository not initialized"
                }
                
            return {
                "success": True,
                "error": None,
                "branch": self.repo.active_branch.name,
                "is_dirty": self.repo.is_dirty(untracked_files=True),
                "untracked_files": self.repo.untracked_files,
                "modified_files": [item.a_path for item in self.repo.index.diff(None)]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 
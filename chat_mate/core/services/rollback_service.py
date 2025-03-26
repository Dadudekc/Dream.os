import os
import logging
import shutil
from datetime import datetime
import glob

class RollbackService:
    def __init__(self, config):
        """
        Initialize the RollbackService with a configuration dictionary.
        Expects config to include:
            backup_dir: directory path for storing backups
        """
        self.config = config
        self.logger = logging.getLogger("RollbackService")
        self.backup_dir = self.config.get("backup_dir", "./backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.logger.info("RollbackService initialized. Backup directory: %s", self.backup_dir)

    def rollback(self, target, version=None):
        """
        Roll back the specified target file to a previous backup.
        
        Args:
            target (str): File path of the target to rollback.
            version (Optional[str]): Specific version identifier to rollback to.
            
        Returns:
            str: Confirmation message.
        """
        backup_file = self._find_backup(target, version)
        if backup_file:
            try:
                shutil.copy(backup_file, target)
                self.logger.info("Rolled back %s to backup %s", target, backup_file)
                return f"Rollback of {target} to backup {backup_file} successful."
            except Exception as e:
                self.logger.error("Failed to rollback %s: %s", target, e)
                return f"Failed to rollback {target}: {e}"
        else:
            self.logger.error("No backup found for %s", target)
            return f"No backup found for {target}."

    def create_backup(self, target):
        """
        Create a backup of the target file.
        
        Args:
            target (str): File path of the target to back up.
            
        Returns:
            str: Path to the backup file, or an error message.
        """
        if not os.path.exists(target):
            self.logger.error("Target file %s does not exist for backup.", target)
            return f"Target file {target} does not exist."
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        target_basename = os.path.basename(target)
        backup_file = os.path.join(self.backup_dir, f"{target_basename}.{timestamp}.bak")
        try:
            shutil.copy(target, backup_file)
            self.logger.info("Backup created for %s at %s", target, backup_file)
            return backup_file
        except Exception as e:
            self.logger.error("Failed to create backup for %s: %s", target, e)
            return f"Failed to create backup for {target}: {e}"

    def _find_backup(self, target, version):
        """
        Find a backup file for the target.
        If version is None, returns the most recent backup.
        """
        target_basename = os.path.basename(target)
        pattern = os.path.join(self.backup_dir, f"{target_basename}.*.bak")
        backups = glob.glob(pattern)
        if not backups:
            return None
        backups.sort(reverse=True)  # most recent first
        if version:
            # Return the backup file that contains the version string
            for b in backups:
                if version in b:
                    return b
            return None
        else:
            return backups[0]

# Example usage when run as a script
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = {"backup_dir": "./backups"}
    rollback_service = RollbackService(config)
    
    # Create a test file to backup and then rollback.
    test_file = "test_target.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Initial version of the file.")
    
    backup_path = rollback_service.create_backup(test_file)
    print("Backup created at:", backup_path)
    
    # Simulate an update to the file.
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Updated version of the file.")
    
    # Rollback to the backup.
    result = rollback_service.rollback(test_file)
    print(result)
    
    # Verify the file content.
    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
    print("Current file content:", content)

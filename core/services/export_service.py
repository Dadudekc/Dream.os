"""
Export Service

Handles exporting data (e.g., episodes, reports, configurations) 
to various formats in a structured output directory.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from core.PathManager import PathManager # Dependency for path management

logger = logging.getLogger(__name__)

class ExportService:
    """Handles exporting data to specified formats and locations."""
    
    EXPORT_PATH_KEY = "exports" # Key for PathManager

    def __init__(self, path_manager: Optional[PathManager] = None):
        """Initialize the ExportService.

        Args:
            path_manager: An instance of PathManager. If None, creates a new one.
        """
        self.path_manager = path_manager or PathManager()
        self.base_export_dir = self._get_export_directory()
        logger.info(f"ExportService initialized. Base export directory: {self.base_export_dir}")

    def _get_export_directory(self) -> Path:
        """Get the base directory for exports, creating it if necessary."""
        try:
            export_dir = self.path_manager.get_path(self.EXPORT_PATH_KEY)
        except KeyError:
            logger.warning(
                f"Path key '{self.EXPORT_PATH_KEY}' not found in PathManager. "
                f"Defaulting to 'outputs/exports' and attempting registration."
            )
            # Define default relative to project root or a known base path
            export_dir = Path("outputs") / self.EXPORT_PATH_KEY 
            # Register this default back to PathManager
            try:
                self.path_manager.add_path(self.EXPORT_PATH_KEY, export_dir)
                logger.info(f"Registered default path for '{self.EXPORT_PATH_KEY}': {export_dir}")
            except AttributeError:
                 logger.warning(f"PathManager instance does not support add_path. Cannot register default.")
            except Exception as e:
                logger.warning(f"Failed to register default path for '{self.EXPORT_PATH_KEY}': {e}")

        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir

    def export(
        self,
        data: Any,
        filename_base: str,
        format: str,
        subdir: Optional[str] = None,
    ) -> Optional[Path]:
        """Exports the given data to a file.

        Args:
            data: The data to export (e.g., dict, list, str).
            filename_base: The base name for the file (without extension).
            format: The desired file format ('json', 'md', 'txt').
            subdir: Optional subdirectory within the base export directory.

        Returns:
            The Path object of the created file, or None if export failed.
        """
        if format not in ["json", "md", "txt"]:
            logger.error(f"Unsupported export format: {format}")
            return None

        target_dir = self.base_export_dir
        if subdir:
            target_dir = target_dir / subdir
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            output_path = target_dir / f"{filename_base}.{format}"

            logger.info(f"Exporting data to: {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                if format == "json":
                    json.dump(data, f, indent=2)
                elif format in ["md", "txt"]:
                    if not isinstance(data, str):
                        logger.warning(f"Data for format '{format}' is not a string. Converting using str().")
                        data = str(data)
                    f.write(data)
                # Add other format handlers here if needed (e.g., csv)
            
            logger.info(f"Successfully exported data to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Export failed for {filename_base}.{format}: {e}")
            import traceback
            logger.debug(traceback.format_exc()) # Log full traceback for debugging
            return None 
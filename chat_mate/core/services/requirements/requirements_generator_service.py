import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from utils.git_utils import get_changed_directories  # Optional if `changed_only=True` is used


class RequirementsGeneratorService:
    def __init__(
        self,
        project_root: Path = Path("."),
        dry_run: bool = False,
        changed_only: bool = False,
        pin_versions: bool = True,
        verbose: bool = True,
    ):
        self.project_root = Path(project_root).resolve()
        self.dry_run = dry_run
        self.changed_only = changed_only
        self.pin_versions = pin_versions
        self.verbose = verbose

        self.requirements_map: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    def run(self) -> Dict[str, List[str]]:
        directories = self._get_target_directories()
        for dir_path in directories:
            reqs = self._get_requirements_for_directory(dir_path)
            if reqs:
                self.requirements_map[str(dir_path)] = reqs
                self._write_requirements_file(dir_path, reqs)
        return self.requirements_map

    def _get_target_directories(self) -> Set[Path]:
        if self.changed_only:
            return get_changed_directories(base_path=self.project_root)
        return {
            f.parent.resolve()
            for f in self.project_root.rglob("*.py")
            if "venv" not in str(f) and "__pycache__" not in str(f)
        }

    def _get_requirements_for_directory(self, dir_path: Path) -> List[str]:
        venv_path = dir_path / "venv" if (dir_path / "venv").exists() else None
        pip_path = (
            venv_path / "Scripts" / "pip.exe"
            if venv_path and (venv_path / "Scripts" / "pip.exe").exists()
            else None
        )

        if pip_path is None:
            pip_path = "pip"

        try:
            result = subprocess.run(
                [str(pip_path), "freeze"],
                capture_output=True,
                text=True,
                check=True,
                cwd=dir_path,
            )
            raw_lines = result.stdout.strip().splitlines()
            return self._filter_requirements(raw_lines)
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Could not get requirements for {dir_path}: {e}")
            return []

    def _filter_requirements(self, raw_lines: List[str]) -> List[str]:
        filtered = []
        for line in raw_lines:
            if "@" in line or "file://" in line:
                continue  # Skip editable installs or local paths
            if not self.pin_versions:
                line = line.split("==")[0]
            filtered.append(line)
        return filtered

    def _write_requirements_file(self, dir_path: Path, requirements: List[str]):
        if self.dry_run:
            self.logger.info(f"[Dry Run] Would write {len(requirements)} packages to {dir_path}/requirements.txt")
            return

        req_path = dir_path / "requirements.txt"
        with req_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(requirements))
        if self.verbose:
            self.logger.info(f"[✓] Wrote requirements.txt in {dir_path} ({len(requirements)} packages)")


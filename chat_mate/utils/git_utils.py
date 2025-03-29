from pathlib import Path
import subprocess
from typing import Set


def get_changed_directories(base_path: Path) -> Set[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRT"],
        capture_output=True,
        text=True,
        cwd=base_path,
    )
    changed_files = result.stdout.strip().splitlines()
    return {base_path / Path(f).parent for f in changed_files if f.endswith(".py")}

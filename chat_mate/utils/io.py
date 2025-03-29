import json
import os
from typing import Any, Dict, List, Union
from pathlib import Path

def read_file(file_path: str) -> str:
    """Read and return the contents of a file as a string."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path: str, content: str, mode: str = 'w') -> None:
    """Write a string to a file, creating directories as needed."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, mode, encoding='utf-8') as f:
        f.write(content)

def read_json(file_path: str) -> Dict[str, Any]:
    """Read a JSON file and return its contents as a dictionary."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(file_path: str, data: Union[Dict[str, Any], List[Any]], indent: int = 4) -> None:
    """Write a dictionary or list to a JSON file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

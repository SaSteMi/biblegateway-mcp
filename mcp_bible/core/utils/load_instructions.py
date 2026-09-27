"""
Simple instruction loader - reads markdown files at import time

This module loads dialect instruction markdown files and exposes them as
simple strings that can be interpolated into tool docstrings using f-strings.
"""

from pathlib import Path

def load_instruction(filename: str, module_path: str = None) -> str:
    """
    Load instruction markdown file and return as string

    Args:
        filename: Name of the .md file
        module_path: Optional __file__ path of the calling module for relative path resolution

    Returns:
        str: Contents of the markdown file
    """
    if module_path:
        filepath = Path(module_path).parent / filename
    else:
        filepath = Path(filename)
    
    return filepath.read_text()


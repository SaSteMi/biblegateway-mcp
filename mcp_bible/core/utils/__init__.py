"""
Core utilities for docstring injection and instruction loading.

This package provides utilities for dynamic docstring manipulation and
instruction file loading used throughout the MCP Weather service.
"""

from .docstring_injector import inject_docstring
from .load_instructions import load_instruction

__all__ = [
    'inject_docstring',
    'load_instruction',
]
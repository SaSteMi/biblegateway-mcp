"""
Decorator for dynamic docstring injection.

Usage:
    @inject_docstring("My docstring")
    def my_func(...):
        ...

    # Or with a callable for dynamic content
    @inject_docstring(lambda: f"Dynamic: {value}")
    def my_func(...):
        ...
"""
from functools import wraps
from typing import Callable, Union

def inject_docstring(doc: Union[str, Callable[[], str]]):
    """
    Decorator to inject a docstring into a function.
    Args:
        doc: The docstring to inject, or a callable returning a docstring.
    """
    def decorator(func):
        if callable(doc):
            func.__doc__ = doc()
        else:
            func.__doc__ = doc
        return func
    return decorator

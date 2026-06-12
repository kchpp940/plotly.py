"""
Optional dependency imports for Plotly.

This module provides both the legacy ``get_module`` function (backwards compatible)
and the unified dependency capability layer via ``deps``.

Prefer using ``deps`` for new code::

    from plotly.optional_imports import deps

    if deps.pandas.available:
        import pandas as pd

    deps.scipy.require("create_distplot")
    scipy = deps.scipy.module
"""

from _plotly_utils.optional_imports import get_module  # noqa: F401
from _plotly_utils.dependencies import deps, Dependency, DependencyRegistry  # noqa: F401

__all__ = ["get_module", "deps", "Dependency", "DependencyRegistry"]

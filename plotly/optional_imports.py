"""
Optional dependency imports for Plotly.

Exposes the **unified dependency capability layer** (``deps``, ``get_module``,
``requires``, ``skip_if_missing``, ``fallback_function``).

Quick reference
---------------
* Check availability – ``deps.pandas.available`` / ``deps.pandas.installed``
* Get the module – ``deps.pandas.module`` / ``deps.get_module("scipy.stats")``
* Guard a code path – ``deps.scipy.require("create_distplot")``
* Version query – ``deps.numpy.version`` / ``deps.kaleido.version_obj_installed.major``
* Build a fallback stub – ``fallback_function("pandas", "`create_choropleth`")``
* Skip a pytest test – ``@requires("pandas")`` / ``@skip_if_missing("kaleido")``

``get_module(name, should_load=True)`` preserves 100% backwards compatibility
with legacy call sites but is now backed by the unified registry.
"""

from _plotly_utils.optional_imports import (  # noqa: F401
    get_module,
    deps,
    Dependency,
    DependencyRegistry,
    requires,
    skip_if_missing,
    fallback_function,
)

__all__ = [
    "get_module",
    "deps",
    "Dependency",
    "DependencyRegistry",
    "requires",
    "skip_if_missing",
    "fallback_function",
]

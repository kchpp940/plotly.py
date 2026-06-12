"""
Legacy optional_imports module – now fully delegated to the unified
dependency capability layer in :mod:`_plotly_utils.dependencies`.

The legacy :func:`get_module` function is reimplemented as a thin shim that
forwards to :meth:`DependencyRegistry.get_module` but preserves the original
logging semantics (records unexpected import errors under the
``_plotly_utils.optional_imports`` logger).
"""

import logging
import sys
from importlib import import_module

from _plotly_utils.dependencies import (
    deps,
    Dependency,
    DependencyRegistry,
    requires,
    skip_if_missing,
    fallback_function,
    check_pyproject_consistency,
    require_capability,
    available_capability,
    capability_module,
    requires_capability,
    skip_if_missing_capability,
)

_not_importable = set()  # mirror of the original – keeps exploding_module sticky

logger = logging.getLogger(__name__)


def get_module(name, should_load=True):
    """
    Return module or None. Absolute import is required.

    Drop-in replacement for the historic implementation: caching, exception
    handling and logging behaviour are identical.  Where possible the call
    is short-circuited through the unified registry's cache so that
    availability answers are shared with the ``deps.<name>`` API.

    :param (str) name: Dot-separated module path. E.g., 'scipy.stats'.
    :return: (module|None) If import succeeds, the module will be returned.
    """
    if not should_load:
        return sys.modules.get(name, None)

    # Fast path: if a registered dep, use the unified cache
    for dep in deps.values():
        if dep.import_name == name:
            mod = dep.module_installed
            if mod is None:
                _not_importable.add(name)
            return mod

    # Historic behaviour below – intentionally exact copy of the old code
    if name not in _not_importable:
        try:
            return import_module(name)
        except ImportError:
            _not_importable.add(name)
        except Exception:
            _not_importable.add(name)
            msg = f"Error importing optional module {name}"
            logger.exception(msg)

    return None


__all__ = [
    "get_module",
    "deps",
    "Dependency",
    "DependencyRegistry",
    "requires",
    "skip_if_missing",
    "fallback_function",
    "check_pyproject_consistency",
    "require_capability",
    "available_capability",
    "capability_module",
    "requires_capability",
    "skip_if_missing_capability",
]

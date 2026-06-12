"""
Unified dependency capability layer for Plotly.py.

Centralizes optional dependency detection, minimum version validation,
error messaging, and fallback behavior so that all modules (express, I/O,
trendlines, figure factories, test helpers) read capability information
from the same source.

Usage::

    from _plotly_utils.dependencies import deps

    if deps.pandas.available:
        import pandas as pd

    deps.scipy.require("create_distplot")
    scipy = deps.scipy.module

    version = deps.numpy.version
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from packaging.version import Version, InvalidVersion

logger = logging.getLogger(__name__)


def _try_import(name: str) -> Optional[Any]:
    """Try to import a module by name, returning None on failure."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None
    except Exception:
        logger.exception("Unexpected error importing optional module %s", name)
        return None


def _try_get_version(dist_name: str) -> Optional[str]:
    """Try to get the version string of an installed distribution."""
    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _parse_version(version_str: Optional[str]) -> Optional[Version]:
    """Parse a version string, returning None on failure."""
    if version_str is None:
        return None
    try:
        return Version(version_str)
    except InvalidVersion:
        return None


@dataclass
class Dependency:
    """Metadata and runtime state for a single optional dependency.

    Attributes
    ----------
    name:
        Human-readable, canonical name for the dependency (e.g. "pandas").
        Used in error messages and capability lookups.
    import_name:
        The module name used for ``importlib.import_module()``.
        May differ from the distribution name (e.g. "skimage" vs "scikit-image").
    dist_name:
        The PyPI distribution name used for version lookup (e.g. "scikit-image").
        Defaults to ``import_name`` if not provided.
    min_version:
        Minimum required version string, or ``None`` if any version is fine.
    extra:
        Name of the pip extras install group that includes this dependency
        (e.g. "express", "kaleido"). Used in installation hints.
    description:
        Short description of what this dependency is used for.
    """

    name: str
    import_name: str
    dist_name: Optional[str] = None
    min_version: Optional[str] = None
    extra: Optional[str] = None
    description: str = ""

    _module: Optional[Any] = field(default=None, init=False, repr=False)
    _version_str: Optional[str] = field(default=None, init=False, repr=False)
    _version: Optional[Version] = field(default=None, init=False, repr=False)
    _available: Optional[bool] = field(default=None, init=False, repr=False)
    _import_tried: bool = field(default=False, init=False, repr=False)
    _version_tried: bool = field(default=False, init=False, repr=False)

    def _check_import(self) -> None:
        """Attempt import once and cache the result."""
        if self._import_tried:
            return
        self._import_tried = True
        self._module = _try_import(self.import_name)

    def _check_version(self) -> None:
        """Attempt version lookup once and cache the result."""
        if self._version_tried:
            return
        self._version_tried = True
        dist = self.dist_name or self.import_name
        self._version_str = _try_get_version(dist)
        self._version = _parse_version(self._version_str)

    @property
    def installed(self) -> bool:
        """Return True if the module can be imported (regardless of version)."""
        self._check_import()
        return self._module is not None

    @property
    def available(self) -> bool:
        """Return True if the dependency is importable AND meets min_version."""
        if self._available is not None:
            return self._available

        self._check_import()
        if self._module is None:
            self._available = False
            return False

        if self.min_version is not None:
            self._check_version()
            if self._version is None:
                self._available = False
                return False
            min_ver = Version(self.min_version)
            if self._version < min_ver:
                self._available = False
                return False

        self._available = True
        return True

    @property
    def module(self) -> Optional[Any]:
        """The imported module, or None if not available (i.e. not installed or version too old)."""
        if not self.available:
            return None
        return self._module

    @property
    def module_installed(self) -> Optional[Any]:
        """The imported module if installed at all, or None if not importable.

        Unlike ``module``, this returns the module even if the version is below
        ``min_version``. Useful for detecting legacy versions (e.g. kaleido v0).
        """
        self._check_import()
        return self._module

    @property
    def version(self) -> Optional[str]:
        """The installed version string, or None if unavailable."""
        if not self.available:
            return None
        self._check_version()
        return self._version_str

    @property
    def version_installed(self) -> Optional[str]:
        """The installed version string, or None if not installed.

        Unlike ``version``, this returns the version even if below ``min_version``.
        """
        if not self.installed:
            return None
        self._check_version()
        return self._version_str

    @property
    def version_obj(self) -> Optional[Version]:
        """The parsed version object, or None if unavailable."""
        if not self.available:
            return None
        self._check_version()
        return self._version

    @property
    def version_obj_installed(self) -> Optional[Version]:
        """The parsed version object if installed, or None.

        Unlike ``version_obj``, this returns the version even if below ``min_version``.
        """
        if not self.installed:
            return None
        self._check_version()
        return self._version

    @property
    def install_hint(self) -> str:
        """Return a helpful pip install command for this dependency."""
        dist = self.dist_name or self.import_name
        if self.min_version:
            pkg = f"'{dist}>={self.min_version}'"
        else:
            pkg = dist
        parts = [f"$ pip install {pkg}"]
        if self.extra:
            parts.append(f"Or install Plotly with this extra: $ pip install 'plotly[{self.extra}]'")
        return "\n".join(parts)

    def require(self, feature: Optional[str] = None) -> None:
        """Raise ImportError with a consistent message if not available.

        Parameters
        ----------
        feature:
            Name of the feature that requires this dependency, used in the
            error message (e.g. "create_distplot", "OLS trendlines").
        """
        if self.available:
            return

        self._check_import()
        if self._module is None:
            msg = f"The {self.name} package is required"
            if feature:
                msg += f" to use {feature}"
            msg += ".\n\n" + self.install_hint
            raise ImportError(msg)

        if self.min_version and self._version_str:
            msg = (
                f"Version {self._version_str} of {self.name} is installed, "
                f"but version >= {self.min_version} is required"
            )
            if feature:
                msg += f" to use {feature}"
            msg += ".\n\n" + self.install_hint
            raise ImportError(msg)

        msg = f"The {self.name} package is required"
        if feature:
            msg += f" to use {feature}"
        msg += ".\n\n" + self.install_hint
        raise ImportError(msg)


class DependencyRegistry:
    """Registry of all known optional and required dependencies.

    Provides both attribute-style (``deps.pandas``) and dict-style
    (``deps["pandas"]``) access.
    """

    def __init__(self) -> None:
        self._deps: Dict[str, Dependency] = {}

    def register(self, dep: Dependency) -> None:
        """Register a dependency under its canonical name."""
        self._deps[dep.name] = dep

    def __getattr__(self, name: str) -> Dependency:
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        if name in self._deps:
            return self._deps[name]
        raise AttributeError(
            f"No dependency registered under name '{name}'. "
            f"Available: {sorted(self._deps.keys())}"
        )

    def __getitem__(self, name: str) -> Dependency:
        return self._deps[name]

    def __contains__(self, name: str) -> bool:
        return name in self._deps

    def keys(self):
        return self._deps.keys()

    def items(self):
        return self._deps.items()

    def values(self):
        return self._deps.values()

    def summary(self) -> Dict[str, bool]:
        """Return a dict of {name: available} for all registered dependencies."""
        return {name: dep.available for name, dep in self._deps.items()}


# ---------------------------------------------------------------------------
# Build the global registry
# ---------------------------------------------------------------------------

deps = DependencyRegistry()

# --- Core / required-for-common-features dependencies ---

deps.register(Dependency(
    name="numpy",
    import_name="numpy",
    min_version="1.22",
    extra="express",
    description="Numerical arrays (required by plotly.express and figure_factory)",
))

deps.register(Dependency(
    name="narwhals",
    import_name="narwhals.stable.v1",
    dist_name="narwhals",
    min_version="1.15.1",
    description="DataFrame interoperability layer (core dependency)",
))

# --- Data libraries ---

deps.register(Dependency(
    name="pandas",
    import_name="pandas",
    extra="dev_optional",
    description="Tabular data analysis library",
))

deps.register(Dependency(
    name="polars",
    import_name="polars",
    extra="dev_optional",
    description="Alternative DataFrame library",
))

deps.register(Dependency(
    name="pyarrow",
    import_name="pyarrow",
    dist_name="pyarrow",
    extra="dev_optional",
    description="Arrow columnar format support",
))

deps.register(Dependency(
    name="xarray",
    import_name="xarray",
    extra="dev_optional",
    description="N-dimensional labeled arrays",
))

# --- Scientific computing ---

deps.register(Dependency(
    name="scipy",
    import_name="scipy",
    extra="dev_optional",
    description="Scientific computing (distplots, statistics)",
))

deps.register(Dependency(
    name="statsmodels",
    import_name="statsmodels",
    dist_name="statsmodels",
    extra="dev_optional",
    description="Statistical modeling (OLS, LOWESS trendlines)",
))

deps.register(Dependency(
    name="skimage",
    import_name="skimage",
    dist_name="scikit-image",
    extra="dev_optional",
    description="Image processing (ternary contour)",
))

# --- Image export ---

deps.register(Dependency(
    name="kaleido",
    import_name="kaleido",
    min_version="1.0.0",
    extra="kaleido",
    description="Static image export engine",
))

# --- Matplotlib interoperability ---

deps.register(Dependency(
    name="matplotlib",
    import_name="matplotlib",
    extra="dev_optional",
    description="Matplotlib conversion support",
))

# --- Geo ---

deps.register(Dependency(
    name="geopandas",
    import_name="geopandas",
    extra="dev_optional",
    description="Geospatial data support",
))

deps.register(Dependency(
    name="shapely",
    import_name="shapely",
    extra="dev_optional",
    description="Geometric operations",
))

# --- Miscellaneous extras ---

deps.register(Dependency(
    name="pillow",
    import_name="PIL",
    dist_name="pillow",
    extra="dev_optional",
    description="Image processing (PIL/Pillow)",
))

deps.register(Dependency(
    name="orjson",
    import_name="orjson",
    extra="dev_optional",
    description="Fast JSON serialization",
))

deps.register(Dependency(
    name="anywidget",
    import_name="anywidget",
    extra="dev_optional",
    description="Jupyter widget support",
))

deps.register(Dependency(
    name="colorcet",
    import_name="colorcet",
    extra="dev_optional",
    description="Perceptually uniform colormaps",
))

__all__ = ["Dependency", "DependencyRegistry", "deps"]

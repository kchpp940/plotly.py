"""
Unified dependency capability layer for Plotly.py.

Centralizes optional dependency detection, minimum version validation,
error messaging, fallback behavior, and test helpers so that all modules
(express, I/O, trendlines, figure factories, test helpers) read capability
information from the same source.

Core APIs
---------
``deps.<name>`` attribute / dict access to a :class:`Dependency`:

    * ``.installed`` – is the module importable (ignores min_version)?
    * ``.available`` – importable **and** meets ``min_version``?
    * ``.module`` / ``.module_installed`` – return the module or ``None``
    * ``.version`` / ``.version_installed`` – version strings
    * ``.version_obj`` / ``.version_obj_installed`` – parsed Version objects
    * ``.require(feature)`` – raise ImportError with a uniform message
    * ``.install_hint`` – pip install hint(s)

Backwards compatibility
-----------------------
``get_module(name, should_load=True)`` – identical semantics to the legacy
implementation, but backed by the unified registry's cache and supporting
arbitrary submodule paths (e.g. ``"scipy.stats"``, ``"IPython.display"``).

Test helpers
------------
``requires()``, ``skip_if_missing()`` – pytest decorators/fixtures helpers
that skip tests cleanly when a dependency (or min version) is not present.

Fallback helpers
----------------
``fallback_function(dep, feature)`` – build a stub that raises a uniform
ImportError when called, used by ``figure_factory.__init__`` and similar
conditional-import patterns.
"""

from __future__ import annotations

import functools
import importlib
import importlib.metadata
import logging
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from packaging.version import Version, InvalidVersion

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _try_import(name: str) -> Optional[Any]:
    """Try to import a module by dotted name, returning None on failure."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None
    except Exception:
        logger.exception("Unexpected error importing optional module %s", name)
        return None


def _try_get_version(dist_name: str) -> Optional[str]:
    """Try to get the installed version of a distribution."""
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


# ---------------------------------------------------------------------------
# Submodule cache – handles "scipy.stats", "PIL.Image", "IPython.display" etc.
# ---------------------------------------------------------------------------

_submodule_not_importable: set = set()


def _resolve_submodule(full_path: str, should_load: bool) -> Optional[Any]:
    """Resolve an arbitrary dotted module path (possibly a submodule).

    Mirrors the semantics of the legacy ``get_module``:

    * ``should_load=False`` – return ``sys.modules.get(name, None)`` (do NOT import)
    * ``should_load=True``  – attempt import once; remember failures
    """
    if not should_load:
        return sys.modules.get(full_path, None)

    if full_path in _submodule_not_importable:
        return None

    mod = sys.modules.get(full_path)
    if mod is not None:
        return mod

    mod = _try_import(full_path)
    if mod is None:
        _submodule_not_importable.add(full_path)
    return mod


def _lookup_registry_entry(full_path: str) -> Optional[Dependency]:
    """Given an arbitrary dotted path, find the closest registered
    :class:`Dependency` whose ``import_name`` is a prefix of *full_path*.

    E.g. ``"scipy.stats"`` → the registered ``scipy`` entry.
    """
    from _plotly_utils.dependencies import deps  # local import avoids circular

    # Exact match first
    if full_path in deps:
        return deps[full_path]

    # Try longest-prefix match
    parts = full_path.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        for dep in deps.values():
            if dep.import_name == candidate:
                return dep
    return None


# ---------------------------------------------------------------------------
# Dependency descriptor
# ---------------------------------------------------------------------------

@dataclass
class Dependency:
    """Metadata and runtime state for a single optional dependency.

    Attributes
    ----------
    name:
        Human-readable, canonical name used for lookups and error messages.
    import_name:
        The top-level module passed to ``importlib.import_module()``.
        May differ from the distribution name (e.g. ``"skimage"`` vs
        ``"scikit-image"``).
    dist_name:
        The PyPI distribution name used for version queries.
        Defaults to *import_name* when omitted.
    min_version:
        Minimum required version (PEP 440).  ``None`` = any version.
    extra:
        Name of the pip extras group (e.g. ``"express"``, ``"kaleido"``).
        Used in the generated install hint.
    description:
        Short human-readable summary of what the dep is used for.
    """

    name: str
    import_name: str
    dist_name: Optional[str] = None
    min_version: Optional[str] = None
    extra: Optional[str] = None
    description: str = ""

    # ---- cached runtime state ----
    _module: Optional[Any] = field(default=None, init=False, repr=False)
    _version_str: Optional[str] = field(default=None, init=False, repr=False)
    _version: Optional[Version] = field(default=None, init=False, repr=False)
    _available: Optional[bool] = field(default=None, init=False, repr=False)
    _import_tried: bool = field(default=False, init=False, repr=False)
    _version_tried: bool = field(default=False, init=False, repr=False)

    # ------------------------------------------------------------------
    # Check helpers (idempotent, cached)
    # ------------------------------------------------------------------
    def _check_import(self) -> None:
        if self._import_tried:
            return
        self._import_tried = True
        self._module = _try_import(self.import_name)

    def _check_version(self) -> None:
        if self._version_tried:
            return
        self._version_tried = True
        dist = self.dist_name or self.import_name
        self._version_str = _try_get_version(dist)
        self._version = _parse_version(self._version_str)

    # ------------------------------------------------------------------
    # Boolean properties
    # ------------------------------------------------------------------
    @property
    def installed(self) -> bool:
        """Can the module be imported, regardless of version?"""
        self._check_import()
        return self._module is not None

    @property
    def available(self) -> bool:
        """Installed **and** >= ``min_version`` (when min_version is set)."""
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
            if self._version < Version(self.min_version):
                self._available = False
                return False

        self._available = True
        return True

    @property
    def meets_min_version(self) -> bool:
        """Installed and version >= min_version. (Identical to ``available``
        for readability in contexts where you want to be explicit.)"""
        return self.available

    # ------------------------------------------------------------------
    # Module access
    # ------------------------------------------------------------------
    @property
    def module(self) -> Optional[Any]:
        """The module if ``available``, else ``None``."""
        if not self.available:
            return None
        return self._module

    @property
    def module_installed(self) -> Optional[Any]:
        """The module if ``installed`` at all, else ``None``.

        Unlike :attr:`module`, this returns the module even when
        ``version < min_version`` – useful for kaleido v0 / v1 branching.
        """
        self._check_import()
        return self._module

    # ------------------------------------------------------------------
    # Version access
    # ------------------------------------------------------------------
    @property
    def version(self) -> Optional[str]:
        """Installed version string, or None if not ``available``."""
        if not self.available:
            return None
        self._check_version()
        return self._version_str

    @property
    def version_installed(self) -> Optional[str]:
        """Installed version string, or None if not ``installed``.

        Returns the version even when < ``min_version``.
        """
        if not self.installed:
            return None
        self._check_version()
        return self._version_str

    @property
    def version_obj(self) -> Optional[Version]:
        """Parsed :class:`~packaging.version.Version`, or None."""
        if not self.available:
            return None
        self._check_version()
        return self._version

    @property
    def version_obj_installed(self) -> Optional[Version]:
        """Parsed :class:`~packaging.version.Version` (ignores min_version)."""
        if not self.installed:
            return None
        self._check_version()
        return self._version

    # ------------------------------------------------------------------
    # Error messaging
    # ------------------------------------------------------------------
    @property
    def install_hint(self) -> str:
        """Return a formatted ``pip install`` hint for this dependency."""
        dist = self.dist_name or self.import_name
        if self.min_version:
            pkg = f"'{dist}>={self.min_version}'"
        else:
            pkg = dist
        parts = [f"$ pip install {pkg}"]
        if self.extra:
            parts.append(
                f"Or install Plotly with this extra: $ pip install 'plotly[{self.extra}]'"
            )
        return "\n".join(parts)

    def require(self, feature: Optional[str] = None) -> None:
        """Raise a uniform :class:`ImportError` if not ``available``.

        Parameters
        ----------
        feature:
            Optional descriptive name (e.g. ``"create_distplot"``) that is
            woven into the error message so users know *what feature* needs
            the missing dep.
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


# ---------------------------------------------------------------------------
# DependencyRegistry – attribute / dict-style access
# ---------------------------------------------------------------------------

class _Capability:
    """A named semantic capability backed by one or more :class:`Dependency` entries.

    Capabilities let call sites declare *what they need to do* instead of
    *which module to import*, e.g. ``"trendline.ols"`` rather than
    ``"statsmodels"``.  This makes dependency intent clear and keeps error
    messages / installation hints consistent across every module.

    Attributes
    ----------
    name:
        Dotted capability name, e.g. ``"trendline.ols"``, ``"image.kaleido"``.
    dep_name:
        The registered :class:`Dependency` name that backs this capability.
    feature_label:
        Human-readable label woven into error messages when
        :meth:`require` is called.  Falls back to *name*.
    description:
        Short sentence describing what this capability enables.
    """

    __slots__ = ("name", "dep_name", "feature_label", "description")

    def __init__(
        self,
        name: str,
        dep_name: str,
        *,
        feature_label: Optional[str] = None,
        description: str = "",
    ) -> None:
        self.name = name
        self.dep_name = dep_name
        self.feature_label = feature_label or name
        self.description = description


class DependencyRegistry:
    """Registry of all known dependencies **and** semantic capabilities.

    Two layers of lookup:

    * **Dependency layer** – per-package metadata + runtime state.
      Accessed as ``deps.pandas`` / ``deps["pandas"]``.

    * **Capability layer** – semantic, intent-based names (e.g.
      ``"trendline.ols"``, ``"image.kaleido"``).  Accessed as
      ``deps.capability("trendline.ols")`` / ``deps.require("trendline.ols")``.

    Supports:
        * ``deps.pandas``              – attribute access (dependency)
        * ``deps["pandas"]``           – dict-style access (dependency)
        * ``"pandas" in deps``         – membership test (dependency)
        * ``deps.get_module(...)``     – arbitrary submodule lookup
        * ``deps.require(cap_name)``   – semantic capability guard
        * ``deps.capability(cap_name)``– fetch capability metadata
    """

    def __init__(self) -> None:
        self._deps: Dict[str, Dependency] = {}
        self._caps: Dict[str, _Capability] = {}

    def register(self, dep: Dependency) -> None:
        """Register a :class:`Dependency` under its canonical name."""
        self._deps[dep.name] = dep

    def register_capability(self, cap: _Capability) -> None:
        """Register a semantic :class:`_Capability`."""
        if cap.dep_name not in self._deps:
            raise ValueError(
                f"Cannot register capability '{cap.name}': "
                f"dependency '{cap.dep_name}' is not registered"
            )
        self._caps[cap.name] = cap

    # ------------------------------------------------------------------
    # Capability-layer API
    # ------------------------------------------------------------------
    def capability(self, name: str) -> _Capability:
        """Return the :class:`_Capability` registered under *name*.

        Raises :class:`KeyError` if no such capability is registered.
        """
        if name not in self._caps:
            raise KeyError(
                f"No capability registered under name '{name}'. "
                f"Available: {sorted(self._caps.keys())}"
            )
        return self._caps[name]

    def has_capability(self, name: str) -> bool:
        """Return ``True`` if *name* is a registered capability name."""
        return name in self._caps

    def require(self, cap_name: str) -> None:
        """Guard a code path against a missing semantic capability.

        Equivalent to fetching the capability's backing dependency and
        calling ``.require(cap.feature_label)`` on it – but the caller
        only has to name the *capability*, not the implementation package.

        Raises
        ------
        ImportError
            With a uniform message + install hint if the backing
            dependency is not installed or is below ``min_version``.
        """
        cap = self.capability(cap_name)
        dep = self._deps[cap.dep_name]
        dep.require(cap.feature_label)

    def available(self, cap_name: str) -> bool:
        """Return ``True`` if the capability's backing dependency is available."""
        cap = self.capability(cap_name)
        return self._deps[cap.dep_name].available

    def module(self, cap_name: str) -> Optional[Any]:
        """Return the module object for a capability's backing dependency,
        or ``None`` if not available."""
        cap = self.capability(cap_name)
        return self._deps[cap.dep_name].module

    def capability_summary(self) -> Dict[str, bool]:
        """Return ``{cap_name: available}`` for every registered capability."""
        return {name: self.available(name) for name in self._caps}

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def __getattr__(self, name: str) -> Dependency:
        if name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
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

    # ------------------------------------------------------------------
    # Unified get_module – fully backwards-compatible with the legacy API
    # ------------------------------------------------------------------
    def get_module(self, name: str, should_load: bool = True) -> Optional[Any]:
        """Return a module or None, with identical semantics to the legacy
        ``_plotly_utils.optional_imports.get_module``.

        Parameters
        ----------
        name:
            Dotted module path.  May be a registered top-level package
            (``"numpy"``, ``"pandas"``) or any submodule
            (``"scipy.stats"``, ``"IPython.display"``).
        should_load:
            If ``False``, only consult ``sys.modules`` (never trigger an
            import).  Used in hot paths / serializers to avoid importing
            heavy packages just to check for their presence.
        """
        # Fast path: exactly a registered top-level import_name
        for dep in self._deps.values():
            if dep.import_name == name:
                if should_load:
                    return dep.module_installed
                else:
                    # Same behaviour as legacy: sys.modules only
                    return sys.modules.get(name, None)

        # Slow path: arbitrary submodule (registered or not)
        return _resolve_submodule(name, should_load)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, bool]:
        """Return ``{name: available}`` for every registered dependency."""
        return {name: dep.available for name, dep in self._deps.items()}


# ---------------------------------------------------------------------------
# Legacy-compatible get_module (top-level convenience)
# ---------------------------------------------------------------------------

def get_module(name: str, should_load: bool = True) -> Optional[Any]:
    """Drop-in replacement for the old ``_plotly_utils.optional_imports.get_module``.

    Delegates to the unified registry so caching, behaviour, and error paths
    are all shared with the new ``deps.<name>`` API.
    """
    from _plotly_utils.dependencies import deps  # avoid circular at import-time
    return deps.get_module(name, should_load)


# ---------------------------------------------------------------------------
# Test helpers: pytest skip / require decorators
# ---------------------------------------------------------------------------

def _pytest_skip_decorator(reason: str):
    """Return ``pytest.mark.skipif(..., reason=reason)`` if pytest is
    installed, else a no-op lambda."""
    pytest = _try_import("pytest")
    if pytest is None:
        def _noop(func):
            return func
        return _noop
    return pytest.mark.skipif(True, reason=reason)


def requires(dep_name: str, min_version: Optional[str] = None, *,
             feature: Optional[str] = None) -> Callable:
    """Pytest decorator that skips a test when a dependency is missing
    (or is below *min_version*, when given).

    Usage::

        @requires("pandas")
        def test_something_with_pandas():
            ...

        @requires("kaleido", "1.0.0", feature="static image export")
        def test_image_export():
            ...
    """
    from _plotly_utils.dependencies import deps

    if dep_name not in deps:
        # Dynamic case – treat as "installed" via importability check
        mod = deps.get_module(dep_name)
        if mod is None:
            feature_part = f" for {feature}" if feature else ""
            return _pytest_skip_decorator(
                f"Requires module '{dep_name}'{feature_part} to be installed"
            )
        if min_version:
            v = _try_get_version(dep_name) or getattr(mod, "__version__", None)
            if v and _parse_version(v) < Version(min_version):
                return _pytest_skip_decorator(
                    f"Requires '{dep_name}'>={min_version}{' for ' + feature if feature else ''}, "
                    f"found {v}"
                )
        return lambda f: f

    dep = deps[dep_name]
    eff_min = min_version or dep.min_version
    needs_min = Version(eff_min) if eff_min else None

    if not dep.installed:
        feature_part = f" to use {feature}" if feature else ""
        return _pytest_skip_decorator(
            f"Requires {dep.name}{feature_part}"
        )

    if needs_min and dep.version_obj_installed and dep.version_obj_installed < needs_min:
        return _pytest_skip_decorator(
            f"Requires {dep.name}>={eff_min}{' for ' + feature if feature else ''}, "
            f"found {dep.version_installed}"
        )

    return lambda f: f


def skip_if_missing(dep_name: str, *,
                    feature: Optional[str] = None) -> Callable:
    """Convenience alias for ``requires(dep_name, feature=feature)``."""
    return requires(dep_name, feature=feature)


# ---------------------------------------------------------------------------
# Fallback-function builder (for conditional-import patterns like
# figure_factory.__init__)
# ---------------------------------------------------------------------------

def fallback_function(dep_name: str, feature: Optional[str] = None) -> Callable:
    """Return a function that, when called, raises a uniform
    :class:`ImportError` via :meth:`Dependency.require`.

    Used instead of a real imported function when its dependency is missing,
    so error messages stay identical regardless of which module calls it.

    Example::

        if deps.pandas.available:
            from ._impl import create_choropleth
        else:
            create_choropleth = fallback_function("pandas", "`create_choropleth`")
    """
    from _plotly_utils.dependencies import deps

    if dep_name in deps:
        dep = deps[dep_name]
    else:
        # Build an ephemeral Dependency for the missing case
        dep = Dependency(
            name=dep_name,
            import_name=dep_name,
            description="Unregistered dynamic dependency",
        )

    def _stub(*args, **kwargs):
        dep.require(feature)

    # Set a nicer repr for debugging
    _stub.__name__ = f"<fallback for {dep_name}>"
    _stub.__qualname__ = _stub.__name__
    _stub.__doc__ = (
        f"Fallback stub – requires {dep.name}"
        + (f" to use {feature}" if feature else "")
        + "."
    )
    return _stub


# ---------------------------------------------------------------------------
# Build the global registry (placed AFTER helpers above so the class body
# can reference helpers defined earlier via attribute methods)
# ---------------------------------------------------------------------------

deps = DependencyRegistry()

# ---------------------------------------------------------------------
# Core / required-for-common-features
# ---------------------------------------------------------------------

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

# ---------------------------------------------------------------------
# Data libraries
# ---------------------------------------------------------------------

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

# ---------------------------------------------------------------------
# Scientific computing
# ---------------------------------------------------------------------

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

# ---------------------------------------------------------------------
# Image export
# ---------------------------------------------------------------------

deps.register(Dependency(
    name="kaleido",
    import_name="kaleido",
    min_version="1.3.0",
    extra="kaleido",
    description="Static image export engine",
))

# ---------------------------------------------------------------------
# Matplotlib interoperability
# ---------------------------------------------------------------------

deps.register(Dependency(
    name="matplotlib",
    import_name="matplotlib",
    extra="dev_optional",
    description="Matplotlib conversion support",
))

# ---------------------------------------------------------------------
# Jupyter / display
# ---------------------------------------------------------------------

deps.register(Dependency(
    name="IPython",
    import_name="IPython",
    dist_name="ipython",
    description="Interactive Python shell (Jupyter display integration)",
))

deps.register(Dependency(
    name="nbformat",
    import_name="nbformat",
    dist_name="nbformat",
    min_version="4.2.0",
    description="Jupyter notebook format support",
))

deps.register(Dependency(
    name="ipywidgets",
    import_name="ipywidgets",
    dist_name="ipywidgets",
    min_version="7.0.0",
    description="Interactive Jupyter widgets (FigureWidget support)",
))

deps.register(Dependency(
    name="notebook",
    import_name="notebook",
    dist_name="notebook",
    description="Classic Jupyter notebook server detection",
))

deps.register(Dependency(
    name="jupyterlab",
    import_name="jupyterlab",
    dist_name="jupyterlab",
    description="JupyterLab server detection",
))

# ---------------------------------------------------------------------
# I/O / rendering
# ---------------------------------------------------------------------

deps.register(Dependency(
    name="psutil",
    import_name="psutil",
    dist_name="psutil",
    description="Process/System utilities (Orca, renderer detection)",
))

deps.register(Dependency(
    name="requests",
    import_name="requests",
    dist_name="requests",
    description="HTTP library (Orca management)",
))

deps.register(Dependency(
    name="chart_studio",
    import_name="chart_studio",
    dist_name="chart-studio",
    description="Chart Studio cloud API integration",
))

# ---------------------------------------------------------------------
# Geo
# ---------------------------------------------------------------------

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

deps.register(Dependency(
    name="shapefile",
    import_name="shapefile",
    dist_name="pyshp",
    extra="dev_optional",
    description="ESRI Shapefile reader",
))

# ---------------------------------------------------------------------
# Misc extras
# ---------------------------------------------------------------------

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

deps.register(Dependency(
    name="vaex",
    import_name="vaex",
    dist_name="vaex",
    extra="dev_optional",
    description="Out-of-core DataFrames",
))

# ---------------------------------------------------------------------------
# Build the semantic capability registry
# ---------------------------------------------------------------------------

def _register_caps(reg: DependencyRegistry) -> None:
    """Register all known semantic capabilities on *reg*.

    Kept as a plain function so it can be re-invoked by tests that need
    to rebuild the registry from scratch.
    """
    caps = [
        # ---- core / required ----
        _Capability(
            "core.narwhals",
            "narwhals",
            feature_label="the narwhals DataFrame compatibility layer",
            description="Core DataFrame interoperability",
        ),
        _Capability(
            "core.numpy",
            "numpy",
            feature_label="plotly.express and figure_factory",
            description="Numerical array support",
        ),
        # ---- dataframe libraries ----
        _Capability(
            "dataframe.pandas",
            "pandas",
            feature_label="pandas DataFrame support",
            description="Use pandas DataFrames with plotly.express",
        ),
        _Capability(
            "dataframe.polars",
            "polars",
            feature_label="Polars DataFrame support",
            description="Use Polars DataFrames with plotly.express",
        ),
        _Capability(
            "dataframe.pyarrow",
            "pyarrow",
            feature_label="PyArrow Table support",
            description="Use PyArrow Tables with plotly.express",
        ),
        _Capability(
            "dataframe.xarray",
            "xarray",
            feature_label="xarray support",
            description="Use xarray with plotly.express",
        ),
        # ---- trendlines ----
        _Capability(
            "trendline.ols",
            "statsmodels",
            feature_label="OLS trendlines",
            description="Ordinary Least Squares trendlines (statsmodels)",
        ),
        _Capability(
            "trendline.lowess",
            "statsmodels",
            feature_label="LOWESS trendlines",
            description="Locally Weighted Scatterplot Smoothing trendlines",
        ),
        _Capability(
            "trendline.rolling",
            "pandas",
            feature_label="rolling trendlines",
            description="Rolling-window trendlines",
        ),
        _Capability(
            "trendline.ewm",
            "pandas",
            feature_label="EWM trendlines",
            description="Exponentially-weighted moving average trendlines",
        ),
        _Capability(
            "trendline.expanding",
            "pandas",
            feature_label="expanding trendlines",
            description="Expanding-window trendlines",
        ),
        # ---- stats / scientific ----
        _Capability(
            "stats.scipy",
            "scipy",
            feature_label="`create_distplot` and other scipy-powered features",
            description="Scipy scientific computing support",
        ),
        # ---- image export ----
        _Capability(
            "image.kaleido",
            "kaleido",
            feature_label="static image export (Kaleido v1+)",
            description="Kaleido v1 static image export engine",
        ),
        # ---- jupyter / renderers ----
        _Capability(
            "render.ipython",
            "IPython",
            feature_label="IPython display integration",
            description="Display figures in IPython / Jupyter",
        ),
        _Capability(
            "render.nbformat",
            "nbformat",
            feature_label="Jupyter notebook format support",
            description="Notebook serialisation support",
        ),
        _Capability(
            "render.ipywidgets",
            "ipywidgets",
            feature_label="interactive FigureWidget (ipywidgets>=7)",
            description="Interactive FigureWidget support",
        ),
        _Capability(
            "render.notebook",
            "notebook",
            feature_label="Classic Jupyter notebook detection",
            description="Detect classic notebook server",
        ),
        _Capability(
            "render.jupyterlab",
            "jupyterlab",
            feature_label="JupyterLab detection",
            description="Detect JupyterLab server",
        ),
        # ---- I/O ----
        _Capability(
            "io.orjson",
            "orjson",
            feature_label="fast JSON serialisation",
            description="Use orjson for faster JSON serialisation",
        ),
        _Capability(
            "io.psutil",
            "psutil",
            feature_label="process/resource utilities",
            description="Process utilities (Orca, renderer detection)",
        ),
        _Capability(
            "io.chart_studio",
            "chart_studio",
            feature_label="Chart Studio cloud API",
            description="Chart Studio cloud upload/download",
        ),
        # ---- geo ----
        _Capability(
            "geo.geopandas",
            "geopandas",
            feature_label="GeoPandas geospatial support",
            description="GeoSpatial data support",
        ),
        _Capability(
            "geo.shapely",
            "shapely",
            feature_label="Shapely geometric operations",
            description="Geometric operations",
        ),
        _Capability(
            "geo.shapefile",
            "shapefile",
            feature_label="ESRI Shapefile support",
            description="Shapefile reader",
        ),
        # ---- figure_factory specific ----
        _Capability(
            "ff.skimage",
            "skimage",
            feature_label="`create_ternary_contour`",
            description="Scikit-image for ternary contour figure factory",
        ),
        _Capability(
            "ff.pillow",
            "pillow",
            feature_label="PIL/Pillow image processing",
            description="PIL/Pillow image processing support",
        ),
        # ---- widgets ----
        _Capability(
            "widget.anywidget",
            "anywidget",
            feature_label="anywidget Jupyter widget backend",
            description="anywidget support for FigureWidget",
        ),
        # ---- plot interop ----
        _Capability(
            "plot.matplotlib",
            "matplotlib",
            feature_label="Matplotlib conversion",
            description="Matplotlib → Plotly conversion",
        ),
        # ---- colors ----
        _Capability(
            "colors.colorcet",
            "colorcet",
            feature_label="colorcet perceptually uniform colormaps",
            description="Perceptually uniform colormaps",
        ),
    ]
    for cap in caps:
        reg.register_capability(cap)


_register_caps(deps)

# ---------------------------------------------------------------------------
# pyproject.toml extras / version consistency checker
# ---------------------------------------------------------------------------

def _parse_pyproject_extras(pyproject_path: Optional[str] = None) -> Dict[str, Dict[str, "Requirement"]]:
    """Parse ``[project.optional-dependencies]`` from pyproject.toml.

    Uses the standard library ``tomllib`` (or the ``tomli`` backport on
    Python < 3.11) and :class:`packaging.requirements.Requirement` so every
    specifier is normalised consistently with what PyPI/pip understand.

    Returns
    -------
    dict
        ``{extra_name: {canonical_pkg_name: packaging.requirements.Requirement}}``
    """
    import os

    if pyproject_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        pyproject_path = os.path.join(here, "..", "pyproject.toml")
        pyproject_path = os.path.normpath(pyproject_path)

    if not os.path.isfile(pyproject_path):
        return {}

    # Load TOML – stdlib tomllib on 3.11+, tomli on older Pythons
    try:
        import tomllib as _toml  # type: ignore[attr-defined]
    except ModuleNotFoundError:  # pragma: no cover - only on Py<3.11
        try:
            import tomli as _toml  # type: ignore[no-redef]
        except ModuleNotFoundError:
            logger.warning(
                "Cannot parse pyproject.toml – neither tomllib (py>=3.11) nor "
                "tomli is installed. pyproject consistency checks will be skipped."
            )
            return {}

    from packaging.requirements import Requirement

    with open(pyproject_path, "rb") as fh:
        data = _toml.load(fh)

    table = data.get("project", {}).get("optional-dependencies", {})
    result: Dict[str, Dict[str, Requirement]] = {}

    for extra_name, raw_specs in table.items():
        parsed: Dict[str, Requirement] = {}
        for raw in raw_specs:
            req = Requirement(raw)
            # Normalise package name (case-insensitive, underscore → dash)
            canonical = req.name.lower().replace("_", "-")
            parsed[canonical] = req
        result[extra_name] = parsed

    return result


def _canonical_pkg_name(name: str) -> str:
    """Return the PyPI-canonical form of a package name."""
    return name.lower().replace("_", "-")


def check_pyproject_consistency(
    pyproject_path: Optional[str] = None,
    registry: Optional[DependencyRegistry] = None,
) -> Dict[str, list]:
    """Compare the dependency registry against ``pyproject.toml`` extras.

    Uses real :mod:`tomllib`/:mod:`tomli` parsing and
    :class:`packaging.requirements.Requirement` so every specifier is
    compared on a canonical footing.

    Returns a dict of issues grouped by severity:

    * ``"mismatch_min_version"`` – a registered ``Dependency.min_version``
      disagrees with the version specifier declared in pyproject.toml.
    * ``"mismatch_dist_name"`` – the registered ``dist_name`` /
      ``import_name`` does not map to any package in pyproject.toml.
    * ``"dep_extra_missing"`` – a registered Dependency claims an ``extra``
      that does not exist in ``pyproject.toml``.
    * ``"capability_missing_dep"`` – a :class:`_Capability` references a
      dependency name that is not registered.
    * ``"unregistered_package"`` – a package that appears in a user-facing
      extra has no :class:`Dependency` registration at all.

    User-facing extras are defined as all extras *except* those whose name
    starts with ``dev_`` (internal build/test extras).
    """
    if registry is None:
        from _plotly_utils.dependencies import deps as registry

    extras = _parse_pyproject_extras(pyproject_path)
    issues: Dict[str, list] = {
        "mismatch_min_version": [],
        "mismatch_dist_name": [],
        "dep_extra_missing": [],
        "capability_missing_dep": [],
        "unregistered_package": [],
    }

    known_extras = set(extras.keys())

    # ----- Index registered deps by canonical package name -----
    reg_by_canonical: Dict[str, Dependency] = {}
    for dep in registry.values():
        names = {dep.import_name}
        if dep.dist_name:
            names.add(dep.dist_name)
        for n in names:
            reg_by_canonical.setdefault(_canonical_pkg_name(n), dep)

    # ----- 1. Walk every package in every user-facing extra -----
    user_extras = {name: pkgs for name, pkgs in extras.items()
                   if not name.startswith("dev_")}

    for extra_name, reqs in user_extras.items():
        for canonical_pkg, req in reqs.items():
            dep = reg_by_canonical.get(canonical_pkg)

            # --- 1a. Completely unregistered? ---
            if dep is None:
                issues["unregistered_package"].append(
                    f"Package '{req.name}' in extra '{extra_name}' has no "
                    "Dependency registration"
                )
                continue

            # --- 1b. Version mismatch? ---
            if dep.min_version is not None and req.specifier:
                # Requirement may carry multiple specifiers – pull out the
                # first >=, ~=, or == bound as the effective "minimum".
                min_from_pyproject: Optional[str] = None
                for spec in req.specifier:
                    if spec.operator in (">=", "~=", "=="):
                        min_from_pyproject = spec.version
                        break
                if min_from_pyproject and min_from_pyproject != dep.min_version:
                    issues["mismatch_min_version"].append(
                        f"{dep.name}: registry min_version='{dep.min_version}' "
                        f"but pyproject extra '{extra_name}' declares "
                        f"'{min_from_pyproject}' (full spec: {str(req)})"
                    )

            # --- 1c. Extra name on dep points somewhere nonexistent? ---
            if dep.extra and dep.extra not in known_extras:
                issues["dep_extra_missing"].append(
                    f"{dep.name} declares extra='{dep.extra}' "
                    "but that extra is not in pyproject.toml"
                )

    # ----- 2. Walk every registered dep with an explicit extra -----
    for dep in registry.values():
        if dep.extra and dep.extra not in known_extras:
            # Avoid double-reporting the same dep we flagged above under
            # dep_extra_missing for a *user* extra.  Here we just make sure
            # every explicitly declared extra actually exists.
            already = any(dep.name in item for item in issues["dep_extra_missing"])
            if not already:
                issues["dep_extra_missing"].append(
                    f"{dep.name} declares extra='{dep.extra}' "
                    "but that extra is not in pyproject.toml"
                )

    # ----- 3. Sanity-check every capability references a real dep -----
    for cap_name, cap in registry._caps.items():
        if cap.dep_name not in registry._deps:
            issues["capability_missing_dep"].append(
                f"Capability '{cap_name}' references unknown dep '{cap.dep_name}'"
            )

    return issues


# ---------------------------------------------------------------------------
# Top-level capability convenience functions
# ---------------------------------------------------------------------------

def require_capability(name: str) -> None:
    """Guard a code path against a missing semantic capability.

    Alias for ``deps.require(name)`` – kept as a free-standing function
    so business modules can import a single, descriptive name that clearly expresses intent::

        from plotly.optional_imports import require_capability
        require_capability("trendline.ols")

    Raises
    ------
    ImportError
        If the capability's backing dependency is not installed or below its
        ``min_version``.  the error message includes the capability's
        human-readable ``feature_label`` and the install hint.
    KeyError
        If *name* is not a registered capability name.
    """
    from _plotly_utils.dependencies import deps
    deps.require(name)


def available_capability(name: str) -> bool:
    """Return ``True`` if a semantic capability is available."""
    from _plotly_utils.dependencies import deps
    return deps.available(name)


def capability_module(name: str):
    """Return the module object backing a semantic capability, or ``None``.

    Equivalent to ``deps.module(name)``.
    """
    from _plotly_utils.dependencies import deps
    return deps.module(name)


# ---------------------------------------------------------------------
# Export list
# ---------------------------------------------------------------------

__all__ = [
    "Dependency",
    "DependencyRegistry",
    "deps",
    "get_module",
    "requires",
    "skip_if_missing",
    "fallback_function",
    "check_pyproject_consistency",
    "_Capability",
    "require_capability",
    "available_capability",
    "capability_module",
]

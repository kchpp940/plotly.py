"""
Optional dependency imports for Plotly.

Exposes the **unified dependency capability layer** with two complementary
interfaces:

* **Semantic capability layer (recommended for new code)** – declare *what*
  you need, not *which module* to import::

      from plotly.optional_imports import require_capability
      require_capability("trendline.ols")

      from plotly.optional_imports import available_capability
      if available_capability("image.kaleido"): ...

      from plotly.optional_imports import capability_module
      pd = capability_module("dataframe.pandas")

* **Package-centric layer (for advanced use)** – per-package metadata::

      from plotly.optional_imports import deps
      if deps.pandas.available: ...
      deps.scipy.require("create_distplot")

Quick reference – semantic capabilities
----------------------------------------
* ``core.narwhals`` – DataFrame interoperability
* ``core.numpy`` – numerical array support
* ``dataframe.pandas`` / ``dataframe.polars`` / ``dataframe.pyarrow`` / ``dataframe.xarray``
* ``trendline.ols`` / ``trendline.lowess`` / ``trendline.rolling`` / ``trendline.ewm`` / ``trendline.expanding``
* ``stats.scipy`` – scipy scientific computing
* ``image.kaleido`` – Kaleido v1 static image export
* ``render.ipython`` / ``render.nbformat`` / ``render.ipywidgets`` / ``render.notebook`` / ``render.jupyterlab``
* ``io.orjson`` / ``io.psutil`` / ``io.chart_studio``
* ``geo.geopandas`` / ``geo.shapely`` / ``geo.shapefile``
* ``ff.skimage`` / ``ff.pillow`` – figure-factory extras
* ``widget.anywidget`` / ``plot.matplotlib`` / ``colors.colorcet``

Backwards compatibility
-----------------------
``get_module(name, should_load=True)`` preserves 100% of the legacy behaviour
but is now backed by the unified registry so caching and error paths are shared.
"""

from _plotly_utils.optional_imports import (  # noqa: F401
    get_module,
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
)

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
]

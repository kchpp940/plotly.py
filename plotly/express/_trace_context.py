"""Trace Context Module.

Builds the pre-resolved :class:`TraceBuildContext` from raw Express args.

This module is the *single place* where column-name resolution and display-label
decoration happen for trace building. It depends on the low-level resolver
functions from ``_core.py`` (``_resolve_col``, ``get_decorated_label``, etc.)
but exposes only pure, structured output to the rest of the pipeline.

Module boundary:
    Input  → raw ``args`` dict (Express config)
    Output → :class:`TraceBuildContext` (fully pre-resolved)

The trace builder (``_trace_builder.py``) consumes the context and never
touches the raw ``args`` dict or calls back into ``_core.py``.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import narwhals.stable.v1 as nw


# ---------------------------------------------------------------------------
# Data structures – also imported by _trace_builder.py
# ---------------------------------------------------------------------------

@dataclass
class ResolvedAttr:
    """A single trace attribute fully pre-resolved before any phase runs.

    The caller (``_trace_context.make_trace_context``) is responsible for
    resolving column names (with the parameter-vs-column shadowing fix) and
    computing display labels (with aggregation decoration, etc.).
    """

    attr_name: str          # "x", "y", "color", "size", ...
    raw_value: Any          # original value from user args (column name or None)
    col_name: Optional[str] # actual DataFrame column name (None = not a column)
    display_label: Any      # display label for hover / legend / axes


@dataclass
class TraceBuildContext:
    """Pre-resolved build context – the single input to every trace-building phase.

    Everything the trace builder needs lives here. There is intentionally no
    reference to the raw ``args`` dict and no callback into ``_core.py``.
    """

    # Core inputs
    trace_data: nw.DataFrame
    trace_spec: Any
    initial_mapping_labels: "OrderedDict[str, str]"
    sizeref: float

    # Pre-resolved attributes: { attr_name -> ResolvedAttr }
    # Always includes "x", "y", "z" even if not in trace_spec.attrs,
    # because trendline fitting etc. needs them.
    resolved_attrs: Dict[str, ResolvedAttr] = field(default_factory=dict)

    # Pre-resolved column name mapping: { raw_column_name -> actual_column_name }
    # Covers every column name that might be referenced inside hover_data,
    # custom_data, etc. Populated during context construction.
    resolved_columns: Dict[str, str] = field(default_factory=dict)

    # ---- Config values extracted from args ----

    labels: Dict[str, str] = field(default_factory=dict)  # original labels dict

    # Dimensions
    dimensions_max_cardinality: int = 20

    # Trendline
    trendline: Optional[str] = None
    trendline_options: Dict[str, Any] = field(default_factory=dict)

    # Color
    color_is_continuous: bool = False
    color_discrete_map: Optional[Dict[str, str]] = None
    color_discrete_sequence: List[str] = field(default_factory=list)

    # Hover / custom data
    hover_data: Any = None          # list or dict or None
    custom_data: Any = None         # list or None

    # Line behaviour
    line_close: bool = False

    # --- Convenience lookups ------------------------------------------------

    def lookup(self, attr_name: str) -> ResolvedAttr:
        return self.resolved_attrs[attr_name]

    def has_attr(self, attr_name: str) -> bool:
        return (
            attr_name in self.resolved_attrs
            and self.resolved_attrs[attr_name].col_name is not None
        )

    def col(self, attr_name: str) -> Optional[str]:
        a = self.resolved_attrs.get(attr_name)
        return a.col_name if a is not None else None

    def label(self, attr_name: str):
        a = self.resolved_attrs.get(attr_name)
        return a.display_label if a is not None else None

    def get_column(self, attr_name: str) -> nw.Series:
        """Fetch a column from trace_data by attribute name."""
        col_name = self.col(attr_name)
        if col_name is None:
            raise KeyError(f"Attribute '{attr_name}' has no resolved column")
        return self.trace_data.get_column(col_name)

    def resolve_column(self, name: str) -> str:
        """Look up a pre-resolved column name.

        The caller guarantees that ``name`` was registered in
        ``resolved_columns`` during context construction. No fallback –
        if the name isn't there, that's a bug in the caller.
        """
        if name in self.resolved_columns:
            return self.resolved_columns[name]
        return name


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def make_trace_context(
    args,
    trace_spec,
    trace_data,
    mapping_labels,
    sizeref,
    _resolve_col_fn,
    _get_decorated_label_fn,
):
    """Build a fully pre-resolved :class:`TraceBuildContext` from raw args.

    This is the *single* place where column-name resolution and label
    decoration happen for trace building.

    Parameters
    ----------
    args : dict
        Raw Express args dict.
    trace_spec : TraceSpec
        Describes which trace type to build.
    trace_data : nw.DataFrame
        Per-trace curated data.
    mapping_labels : Mapping
        Pre-existing labels from ``make_splom_trace_names`` or similar.
    sizeref : float
        Marker sizeref value.
    _resolve_col_fn : callable
        ``(args, name) -> resolved_column_name`` (typically ``_resolve_col``).
    _get_decorated_label_fn : callable
        ``(args, column, role) -> display_label`` (typically ``get_decorated_label``).

    Returns
    -------
    TraceBuildContext
        Fully pre-resolved context ready for ``build_trace``.
    """

    # --- Step 1: collect every column name we might need ---------------
    # These all need to be resolved through _resolve_col (which handles the
    # parameter-name-vs-column-name shadowing fix).

    col_names_to_resolve: set = set()

    extra_attrs = ["x", "y", "z", "base"]
    all_attr_names = list(trace_spec.attrs) + [
        a for a in extra_attrs if a not in trace_spec.attrs
    ]

    for attr_name in all_attr_names:
        raw = args.get(attr_name)
        if raw is None:
            continue
        if isinstance(raw, str):
            col_names_to_resolve.add(raw)
        elif isinstance(raw, list) and all(isinstance(c, str) for c in raw):
            for c in raw:
                col_names_to_resolve.add(c)

    # hover_data columns
    hover_data = args.get("hover_data")
    if hover_data:
        if isinstance(hover_data, dict):
            for col in hover_data.keys():
                if isinstance(col, str):
                    col_names_to_resolve.add(col)
        elif isinstance(hover_data, (list, tuple)):
            for col in hover_data:
                if isinstance(col, str):
                    col_names_to_resolve.add(col)

    # custom_data columns
    custom_data = args.get("custom_data")
    if custom_data:
        for col in custom_data:
            if isinstance(col, str):
                col_names_to_resolve.add(col)

    # --- Step 2: resolve all column names in one go -------------------
    resolved_columns: Dict[str, str] = {}
    for name in col_names_to_resolve:
        resolved_columns[name] = _resolve_col_fn(args, name)

    # --- Step 3: build resolved attrs (with decorated labels) ---------
    resolved_attrs: Dict[str, ResolvedAttr] = {}
    for attr_name in all_attr_names:
        raw_value = args.get(attr_name)

        # Look up the resolved column name
        if raw_value is None:
            col_name = None
        elif isinstance(raw_value, str):
            col_name = resolved_columns.get(raw_value, raw_value)
        elif isinstance(raw_value, list):
            col_name = [
                resolved_columns.get(c, c) if isinstance(c, str) else c
                for c in raw_value
            ]
        else:
            col_name = raw_value

        display_label = _get_decorated_label_fn(args, raw_value, attr_name)

        resolved_attrs[attr_name] = ResolvedAttr(
            attr_name=attr_name,
            raw_value=raw_value,
            col_name=col_name,
            display_label=display_label,
        )

    # --- Step 4: assemble the context ---------------------------------
    ctx = TraceBuildContext(
        trace_data=trace_data,
        trace_spec=trace_spec,
        initial_mapping_labels=OrderedDict(mapping_labels),
        sizeref=sizeref,
        resolved_attrs=resolved_attrs,
        resolved_columns=resolved_columns,
        labels=dict(args.get("labels") or {}),
        dimensions_max_cardinality=args.get("dimensions_max_cardinality", 20),
        trendline=args.get("trendline"),
        trendline_options=args.get("trendline_options") or {},
        color_is_continuous=bool(args.get("color_is_continuous")),
        color_discrete_map=args.get("color_discrete_map"),
        color_discrete_sequence=list(args.get("color_discrete_sequence") or []),
        hover_data=hover_data,
        custom_data=custom_data,
        line_close=bool(args.get("line_close")),
    )
    return ctx

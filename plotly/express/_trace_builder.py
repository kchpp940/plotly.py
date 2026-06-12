"""Trace Builder Module.

Splits the Express -> graph_objects trace construction pipeline into clean phases
with well-defined, structured intermediate objects. The only public entry point
is ``build_trace``.

This module is *purely computational*: it never touches the raw ``args`` dict
and never calls back into ``_core.py``. All column names, display labels, and
configuration values are pre-resolved by the caller and handed in via the
:class:`TraceBuildContext` object.

Pipeline:
    TraceBuildContext (pre-resolved input)
        -> _bind_trace_data (data binding)
        -> _compute_trendline_fit (trendline fitting, if needed)
        -> _apply_visual_patches (visual attributes)
        -> _build_hover_config (hover template)
        -> TraceBuildResult (final output: trace_patch + fit_results)
"""

from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import narwhals.stable.v1 as nw
import plotly.graph_objs as go

from .trendline_functions import ols, lowess, rolling, expanding, ewm


# ---------------------------------------------------------------------------
# Internal helpers (pure – no dependency on args dict or _core.py)
# ---------------------------------------------------------------------------

trendline_functions = dict(
    lowess=lowess, rolling=rolling, ewm=ewm, expanding=expanding, ols=ols
)


def _is_continuous(df: nw.DataFrame, col_name: str) -> bool:
    if nw.dependencies.is_pandas_like_dataframe(df_native := df.to_native()):
        return df_native[col_name].dtype.kind in "ifc"
    return df.get_column(col_name).dtype.is_numeric()


def _to_unix_epoch_seconds(s: nw.Series) -> nw.Series:
    dtype = s.dtype
    if dtype == nw.Date:
        return s.dt.timestamp("ms") / 1_000
    if dtype == nw.Datetime:
        if dtype.time_unit in ("s", "ms"):
            return s.dt.timestamp("ms") / 1_000
        elif dtype.time_unit == "us":
            return s.dt.timestamp("us") / 1_000_000
        elif dtype.time_unit == "ns":
            return s.dt.timestamp("ns") / 1_000_000_000
        else:
            raise ValueError("Unexpected dtype, please report a bug")
    raise TypeError(f"Expected Date or Datetime, got {dtype}")


def _invert_label(labels: Dict[str, str], column: str) -> str:
    reversed_labels = {value: key for (key, value) in labels.items()}
    try:
        return reversed_labels[column]
    except Exception:
        return column


# ---------------------------------------------------------------------------
# Intermediate data structures
# ---------------------------------------------------------------------------

@dataclass
class ResolvedAttr:
    """A single trace attribute fully pre-resolved before any phase runs.

    The caller (``_core.py``) is responsible for resolving column names
    (with the shadowing fix) and computing display labels (with aggregation
    decoration, etc.). The trace builder only consumes these values.
    """

    attr_name: str          # "x", "y", "color", "size", ...
    raw_value: Any          # original value from user args (column name or None)
    col_name: Optional[str] # actual DataFrame column name (None = not a column)
    display_label: Any      # display label for hover / legend / axes


@dataclass
class TraceBuildContext:
    """Pre-resolved build context – the single input to every phase.

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
        return attr_name in self.resolved_attrs and self.resolved_attrs[attr_name].col_name is not None

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


@dataclass
class TraceDataBinding:
    data: Dict[str, Any] = field(default_factory=dict)
    customdata: Any = None
    hovertext: Any = None
    mapping_labels: "OrderedDict[str, str]" = field(default_factory=OrderedDict)


@dataclass
class TrendlineFitResult:
    x_data: Any = None
    y_data: Any = None
    fit_results: Any = None
    hover_header: str = ""
    x_label: str = ""
    y_label: str = ""


@dataclass
class TraceVisualConfig:
    marker: Dict[str, Any] = field(default_factory=dict)
    line: Dict[str, Any] = field(default_factory=dict)
    error_x: Dict[str, Any] = field(default_factory=dict)
    error_y: Dict[str, Any] = field(default_factory=dict)
    error_z: Dict[str, Any] = field(default_factory=dict)
    extra_labels: List[Tuple[str, str]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceHoverConfig:
    hover_header: str = ""
    hovertemplate: str = ""
    mapping_labels: "OrderedDict[str, str]" = field(default_factory=OrderedDict)


@dataclass
class TraceBuildResult:
    trace_patch: Dict[str, Any] = field(default_factory=dict)
    fit_results: Any = None


# ---------------------------------------------------------------------------
# Phase 1 – Data binding
# ---------------------------------------------------------------------------

_SKIP_BIND_ATTRS = {"size", "color", "trendline"}


def _bind_trace_data(ctx: TraceBuildContext) -> TraceDataBinding:
    binding = TraceDataBinding(mapping_labels=OrderedDict())

    for attr_name in ctx.trace_spec.attrs:
        if attr_name in _SKIP_BIND_ATTRS:
            continue
        attr = ctx.lookup(attr_name)
        attr_value = attr.raw_value
        attr_label = attr.display_label

        if attr_name == "dimensions":
            dims = [
                (name, ctx.trace_data.get_column(name))
                for name in ctx.trace_data.columns
                if ((not attr_value) or (name in attr_value))
                and (ctx.trace_spec.constructor != go.Parcoords or _is_continuous(ctx.trace_data, name))
                and (
                    ctx.trace_spec.constructor != go.Parcats
                    or (attr_value is not None and name in attr_value)
                    or nw.to_py_scalar(ctx.trace_data.get_column(name).n_unique())
                    <= ctx.dimensions_max_cardinality
                )
            ]
            binding.data["dimensions"] = [
                dict(label=ctx.labels.get(name, name), values=column)
                for (name, column) in dims
            ]
            if ctx.trace_spec.constructor == go.Splom:
                for d in binding.data["dimensions"]:
                    d["axis"] = dict(matches=True)
                binding.mapping_labels["%{xaxis.title.text}"] = "%{x}"
                binding.mapping_labels["%{yaxis.title.text}"] = "%{y}"
        elif attr_value is not None:
            if attr_name == "marginal_x":
                if ctx.trace_spec.constructor == go.Histogram:
                    binding.mapping_labels["count"] = "%{y}"
            elif attr_name == "marginal_y":
                if ctx.trace_spec.constructor == go.Histogram:
                    binding.mapping_labels["count"] = "%{x}"
            elif attr_name.startswith("error"):
                error_xy = attr_name[:7]
                arr = "arrayminus" if attr_name.endswith("minus") else "array"
                if error_xy not in binding.data:
                    binding.data[error_xy] = {}
                binding.data[error_xy][arr] = ctx.get_column(attr_name)
            elif attr_name == "custom_data":
                if len(attr_value) > 0:
                    cols = [ctx.col(c) if isinstance(c, str) and ctx.has_attr(c) else c for c in attr_value]
                    cols = [c for c in cols if c is not None]
                    if cols:
                        binding.customdata = ctx.trace_data.select(nw.col(cols))
            elif attr_name == "hover_name":
                if ctx.trace_spec.constructor not in [
                    go.Histogram,
                    go.Histogram2d,
                    go.Histogram2dContour,
                ]:
                    binding.hovertext = ctx.get_column(attr_name)
            elif attr_name == "hover_data":
                if ctx.trace_spec.constructor not in [
                    go.Histogram,
                    go.Histogram2d,
                    go.Histogram2dContour,
                ]:
                    hover_is_dict = isinstance(attr_value, dict)
                    customdata_cols = list(ctx.custom_data or [])
                    for col in attr_value:
                        if hover_is_dict and not attr_value[col]:
                            continue
                        # Skip axes / base (already in hover)
                        skip_cols = {ctx.col("x"), ctx.col("y"), ctx.col("z"), ctx.col("base")}
                        if col in skip_cols:
                            continue
                        try:
                            position = (ctx.custom_data or []).index(col)
                        except (ValueError, AttributeError, KeyError):
                            position = len(customdata_cols)
                            customdata_cols.append(col)
                        col_label = ctx.labels.get(col, col)
                        binding.mapping_labels[col_label] = "%%{customdata[%d]}" % (
                            position
                        )
                    if len(customdata_cols) > 0:
                        cols = []
                        for c in dict.fromkeys(customdata_cols):
                            rc = ctx.col(c) if isinstance(c, str) and ctx.has_attr(c) else c
                            if rc is not None:
                                cols.append(rc)
                        if cols:
                            binding.customdata = ctx.trace_data.select(nw.col(cols))
            elif attr_name == "animation_group":
                binding.data["ids"] = ctx.get_column(attr_name)
            elif attr_name == "locations":
                binding.data[attr_name] = ctx.get_column(attr_name)
                binding.mapping_labels[attr_label] = "%{location}"
            elif attr_name == "values":
                binding.data[attr_name] = ctx.get_column(attr_name)
                _label = "value" if attr_label == "values" else attr_label
                binding.mapping_labels[_label] = "%{value}"
            elif attr_name == "parents":
                binding.data[attr_name] = ctx.get_column(attr_name)
                _label = "parent" if attr_label == "parents" else attr_label
                binding.mapping_labels[_label] = "%{parent}"
            elif attr_name == "ids":
                binding.data[attr_name] = ctx.get_column(attr_name)
                _label = "id" if attr_label == "ids" else attr_label
                binding.mapping_labels[_label] = "%{id}"
            elif attr_name == "names":
                if ctx.trace_spec.constructor in [
                    go.Sunburst,
                    go.Treemap,
                    go.Icicle,
                    go.Pie,
                    go.Funnelarea,
                ]:
                    binding.data["labels"] = ctx.get_column(attr_name)
                    _label = "label" if attr_label == "names" else attr_label
                    binding.mapping_labels[_label] = "%{label}"
                else:
                    binding.data[attr_name] = ctx.get_column(attr_name)
            else:
                binding.data[attr_name] = ctx.get_column(attr_name)
                binding.mapping_labels[attr_label] = "%%{%s}" % attr_name
        elif (
            ctx.trace_spec.constructor == go.Histogram and attr_name in ["x", "y"]
        ) or (
            ctx.trace_spec.constructor in [go.Histogram2d, go.Histogram2dContour]
            and attr_name == "z"
        ):
            if attr_label is not None:
                binding.mapping_labels[attr_label] = "%%{%s}" % attr_name

    return binding


# ---------------------------------------------------------------------------
# Phase 2 – Trendline fit
# ---------------------------------------------------------------------------

def _compute_trendline_fit(ctx: TraceBuildContext) -> Optional[TrendlineFitResult]:
    x_col = ctx.col("x")
    y_col = ctx.col("y")
    if not (x_col and y_col):
        return None
    if len(ctx.trace_data.select(nw.col(x_col, y_col)).drop_nulls()) <= 1:
        return None

    sorted_df = ctx.trace_data.sort(by=x_col, nulls_last=True)
    y = sorted_df.get_column(y_col)
    x = sorted_df.get_column(x_col)

    if x.dtype == nw.Datetime or x.dtype == nw.Date:
        x = _to_unix_epoch_seconds(x)
    elif not x.dtype.is_numeric():
        try:
            x = x.cast(nw.Float64())
        except ValueError:
            raise ValueError(
                "Could not convert value of 'x' ('%s') into a numeric type. "
                "If 'x' contains stringified dates, please convert to a datetime column."
                % ctx.lookup("x").raw_value
            )

    if not y.dtype.is_numeric():
        try:
            y = y.cast(nw.Float64())
        except ValueError:
            raise ValueError("Could not convert value of 'y' into a numeric type.")

    non_missing = ~(x.is_null() | y.is_null())
    x_series = sorted_df.filter(non_missing).get_column(x_col)
    if x_series.dtype == nw.Datetime and x_series.dtype.time_zone is not None:
        x_data = x_series.dt.replace_time_zone(None).to_numpy()
    else:
        x_data = x_series.to_numpy()

    trendline_function = trendline_functions[ctx.trendline]
    y_out, hover_header, fit_results = trendline_function(
        ctx.trendline_options,
        sorted_df.get_column(x_col),
        x.to_numpy(),
        y.to_numpy(),
        ctx.lookup("x").raw_value,
        ctx.lookup("y").raw_value,
        non_missing.to_numpy(),
    )
    assert len(y_out) == len(x_data), "missing-data-handling failure in trendline code"

    return TrendlineFitResult(
        x_data=x_data,
        y_data=y_out,
        fit_results=fit_results,
        hover_header=hover_header,
        x_label=ctx.labels.get(ctx.lookup("x").raw_value, ctx.lookup("x").raw_value) if ctx.lookup("x").raw_value else "",
        y_label=ctx.labels.get(ctx.lookup("y").raw_value, ctx.lookup("y").raw_value) if ctx.lookup("y").raw_value else "",
    )


# ---------------------------------------------------------------------------
# Phase 3 – Visual attribute patching
# ---------------------------------------------------------------------------

_VISUAL_ATTRS = {"size", "color"}


def _apply_visual_patches(ctx: TraceBuildContext) -> TraceVisualConfig:
    vc = TraceVisualConfig()

    for attr_name in ctx.trace_spec.attrs:
        if attr_name not in _VISUAL_ATTRS:
            continue
        attr = ctx.lookup(attr_name)
        if attr.raw_value is None or attr.col_name is None:
            continue
        attr_label = attr.display_label
        col_name = attr.col_name

        if attr_name == "size":
            vc.marker["size"] = ctx.trace_data.get_column(col_name)
            vc.marker["sizemode"] = "area"
            vc.marker["sizeref"] = ctx.sizeref
            vc.extra_labels.append((attr_label, "%{marker.size}"))
        elif attr_name == "color":
            if ctx.trace_spec.constructor in [
                go.Choropleth,
                go.Choroplethmap,
                go.Choroplethmapbox,
            ]:
                vc.extra["z"] = ctx.trace_data.get_column(col_name)
                vc.extra["coloraxis"] = "coloraxis1"
                vc.extra_labels.append((attr_label, "%{z}"))
            elif ctx.trace_spec.constructor in [
                go.Sunburst,
                go.Treemap,
                go.Icicle,
                go.Pie,
                go.Funnelarea,
            ]:
                if ctx.color_is_continuous:
                    vc.marker["colors"] = ctx.trace_data.get_column(col_name)
                    vc.marker["coloraxis"] = "coloraxis1"
                    vc.extra_labels.append((attr_label, "%{color}"))
                else:
                    vc.marker["colors"] = []
                    if ctx.color_discrete_map is not None:
                        mapping = ctx.color_discrete_map.copy()
                    else:
                        mapping = {}
                    for cat in ctx.trace_data.get_column(col_name).to_list():
                        if mapping.get(cat) is None:
                            mapping[cat] = ctx.color_discrete_sequence[
                                len(mapping) % len(ctx.color_discrete_sequence)
                            ]
                        vc.marker["colors"].append(mapping[cat])
            else:
                colorable = "marker"
                if ctx.trace_spec.constructor in [go.Parcats, go.Parcoords]:
                    colorable = "line"
                if colorable == "marker":
                    vc.marker["color"] = ctx.trace_data.get_column(col_name)
                    vc.marker["coloraxis"] = "coloraxis1"
                else:
                    vc.line["color"] = ctx.trace_data.get_column(col_name)
                    vc.line["coloraxis"] = "coloraxis1"
                vc.extra_labels.append(
                    (attr_label, "%%{%s.color}" % colorable)
                )

    return vc


# ---------------------------------------------------------------------------
# Phase 4 – Hover / text configuration
# ---------------------------------------------------------------------------

def _build_hover_config(
    ctx: TraceBuildContext,
    mapping_labels: "OrderedDict[str, str]",
    hover_header: str,
) -> TraceHoverConfig:
    if ctx.trace_spec.constructor in [go.Parcoords, go.Parcats]:
        return TraceHoverConfig(
            hover_header=hover_header,
            mapping_labels=OrderedDict(mapping_labels),
        )

    labels_copy = OrderedDict(mapping_labels)
    if ctx.hover_data and isinstance(ctx.hover_data, dict):
        for k, v in mapping_labels.items():
            k_args = _invert_label(ctx.labels, k)
            if k_args in ctx.hover_data:
                formatter = ctx.hover_data[k_args][0]
                if formatter:
                    if isinstance(formatter, str):
                        labels_copy[k] = v.replace("}", "%s}" % formatter)
                else:
                    _ = labels_copy.pop(k)

    hover_lines = [k + "=" + v for k, v in labels_copy.items()]
    hovertemplate = hover_header + "<br>".join(hover_lines) + "<extra></extra>"

    return TraceHoverConfig(
        hover_header=hover_header,
        hovertemplate=hovertemplate,
        mapping_labels=labels_copy,
    )


# ---------------------------------------------------------------------------
# Internal: merge all phases into the final trace_patch dictionary
# ---------------------------------------------------------------------------

def _merge_phases(
    ctx: TraceBuildContext,
    binding: TraceDataBinding,
    trendline: Optional[TrendlineFitResult],
    visual: TraceVisualConfig,
) -> TraceBuildResult:
    patch: Dict[str, Any] = ctx.trace_spec.trace_patch.copy() or {}

    # ---- data binding ----
    patch.update(binding.data)
    if binding.customdata is not None:
        patch["customdata"] = binding.customdata
    if binding.hovertext is not None:
        patch["hovertext"] = binding.hovertext

    combined_labels = OrderedDict(ctx.initial_mapping_labels)
    combined_labels.update(binding.mapping_labels)

    hover_header = ""
    if binding.hovertext is not None:
        hover_header = "<b>%{hovertext}</b><br><br>"

    # ---- trendline (rewrites x / y) ----
    fit_results = None
    if trendline is not None:
        patch["x"] = trendline.x_data
        patch["y"] = trendline.y_data
        fit_results = trendline.fit_results
        hover_header = trendline.hover_header
        combined_labels[trendline.x_label] = "%{x}"
        combined_labels[trendline.y_label] = "%{y} <b>(trend)</b>"

    # ---- visual patches ----
    if visual.marker:
        patch.setdefault("marker", {}).update(visual.marker)
    if visual.line:
        patch.setdefault("line", {}).update(visual.line)
    for ek in ("error_x", "error_y", "error_z"):
        edict = getattr(visual, ek)
        if edict:
            patch.setdefault(ek, {}).update(edict)
    for lab_key, lab_val in visual.extra_labels:
        combined_labels[lab_key] = lab_val
    patch.update(visual.extra)

    # Drop empty containers that graph_objects doesn't like
    for key in ("marker", "line", "error_x", "error_y", "error_z"):
        if key in patch and not patch[key]:
            del patch[key]

    # ---- hover template (sees ALL merged labels) ----
    hover_config = _build_hover_config(ctx, combined_labels, hover_header)
    if hover_config.hovertemplate:
        patch["hovertemplate"] = hover_config.hovertemplate

    return TraceBuildResult(trace_patch=patch, fit_results=fit_results)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_trace(ctx: TraceBuildContext) -> TraceBuildResult:
    """Build a single trace's patch dict and optional trendline fit results.

    Parameters
    ----------
    ctx : TraceBuildContext
        Pre-resolved build context containing all data, labels, and config.

    Returns
    -------
    TraceBuildResult
        Contains ``trace_patch`` dict and ``fit_results`` (or None).
    """
    trace_data = ctx.trace_data
    if ctx.line_close:
        trace_data = nw.concat([trace_data, trace_data.head(1)], how="vertical")
        # Build a temporary context with the modified trace_data
        ctx = _ctx_with_trace_data(ctx, trace_data)

    # Run the first three phases independently – each takes only the Context
    binding = _bind_trace_data(ctx)

    trendline = None
    if "trendline" in ctx.trace_spec.attrs and ctx.trendline is not None:
        trendline = _compute_trendline_fit(ctx)

    visual = _apply_visual_patches(ctx)

    # The final merge step also triggers the hover-template phase (which needs
    # to see the merged label set, so it is intentionally run inside merge).
    return _merge_phases(ctx, binding, trendline, visual)


def _ctx_with_trace_data(ctx: TraceBuildContext, new_trace_data: nw.DataFrame) -> TraceBuildContext:
    """Return a copy of ctx with trace_data replaced."""
    import copy
    new_ctx = copy.copy(ctx)
    new_ctx.trace_data = new_trace_data
    return new_ctx

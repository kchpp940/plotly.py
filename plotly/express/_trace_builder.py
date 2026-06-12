"""Trace Builder Module.

Splits the Express -> graph_objects trace construction pipeline into clean phases
with well-defined, structured intermediate objects. The only public entry point
is ``build_trace_spec``.

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
# Public helpers used by the Context (also re-used by _core.py historically)
# ---------------------------------------------------------------------------

trendline_functions = dict(
    lowess=lowess, rolling=rolling, ewm=ewm, expanding=expanding, ols=ols
)


def _resolve_col(args, attr_name_or_col):
    """Resolve a semantic column name to the actual DataFrame column name.

    Wraps _resolve_col from the caller with the well-known "column name shadows
    a parameter name" safeguard: if ``_resolve_col`` returns ``None`` but the
    input was a plain string, we fall back to using that string directly as a
    column name (the string IS the column name).
    """
    try:
        col_map = args.get("_col_map", {})
        if attr_name_or_col in col_map:
            return col_map[attr_name_or_col]
        if attr_name_or_col in args:
            arg_val = args[attr_name_or_col]
            if isinstance(arg_val, str) and arg_val in col_map:
                return col_map[arg_val]
            if arg_val is None and isinstance(attr_name_or_col, str):
                return attr_name_or_col
            return arg_val
        return attr_name_or_col
    except Exception:
        return attr_name_or_col


def _get_label(args, column):
    try:
        return args["labels"][column]
    except Exception:
        return column


def _invert_label(args, column):
    reversed_labels = {value: key for (key, value) in args["labels"].items()}
    try:
        return reversed_labels[column]
    except Exception:
        return column


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


# ---------------------------------------------------------------------------
# Intermediate data structures
# ---------------------------------------------------------------------------

@dataclass
class ResolvedAttr:
    """A single attribute fully resolved before any phase runs.

    ``attr_name``  – semantic name ("x", "y", "color", "size", ...)
    ``raw_value``  – original ``args[attr_name]`` (column name or None)
    ``col_name``   – actual DataFrame column name (None means "not a column")
    ``label``      – display label, decorated with aggregation info etc.
    """

    attr_name: str
    raw_value: Any
    col_name: Optional[str]
    label: Any


@dataclass
class TraceBuildContext:
    """Pre-resolved build context – the single input to every phase.

    Constructing this object up-front means individual phases never have to
    repeat ``_resolve_col`` / ``get_decorated_label`` work. Phases only need
    to look up attributes via ``self.lookup(name)``.
    """

    args: Dict[str, Any]
    trace_spec: Any
    trace_data: nw.DataFrame
    initial_mapping_labels: "OrderedDict[str, str]"
    sizeref: float

    # Pre-resolved attributes: { attr_name -> ResolvedAttr }
    _attr_index: Dict[str, ResolvedAttr] = field(default_factory=dict)

    @classmethod
    def build(cls, args, trace_spec, trace_data, initial_mapping_labels, sizeref,
              decorated_label_fn):
        ctx = cls(
            args=args,
            trace_spec=trace_spec,
            trace_data=trace_data,
            initial_mapping_labels=OrderedDict(initial_mapping_labels),
            sizeref=sizeref,
        )

        extra_attrs = ["x", "y", "z"]
        all_attrs = list(trace_spec.attrs) + [
            a for a in extra_attrs if a not in trace_spec.attrs
        ]

        for attr_name in all_attrs:
            raw = args.get(attr_name)
            if isinstance(raw, list):
                col = [_resolve_col(args, c) if isinstance(c, str) else c for c in raw]
            else:
                col = _resolve_col(args, raw) if raw is not None else None
            label = decorated_label_fn(args, raw, attr_name)
            ctx._attr_index[attr_name] = ResolvedAttr(
                attr_name=attr_name, raw_value=raw, col_name=col, label=label
            )
        return ctx

    # --- Attribute lookup helpers -------------------------------------------

    def lookup(self, attr_name: str) -> ResolvedAttr:
        return self._attr_index[attr_name]

    def has(self, attr_name: str) -> bool:
        return attr_name in self._attr_index

    def col(self, attr_name: str) -> Optional[str]:
        """Return the resolved column name (or None if not set / not a col)."""
        a = self._attr_index.get(attr_name)
        return a.col_name if a is not None else None

    def label_for(self, attr_name: str):
        a = self._attr_index.get(attr_name)
        return a.label if a is not None else None

    def get_column(self, attr_name_or_direct_col: str) -> nw.Series:
        """Fetch a column from trace_data by resolved attr name OR raw col."""
        col_name = self.col(attr_name_or_direct_col) or _resolve_col(
            self.args, attr_name_or_direct_col
        )
        return self.trace_data.get_column(col_name)

    def rc(self, name):
        """Shortcut for list/string column resolving."""
        return _resolve_col(self.args, name)


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
    # Mapping labels that should be merged in after visual processing
    extra_labels: List[Tuple[str, str]] = field(default_factory=list)
    # Other trace-level keys (z, coloraxis, ...)
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
    df: nw.DataFrame = ctx.args["data_frame"]

    for attr_name in ctx.trace_spec.attrs:
        if attr_name in _SKIP_BIND_ATTRS:
            continue
        attr = ctx.lookup(attr_name)
        attr_value = attr.raw_value
        attr_label = attr.label

        if attr_name == "dimensions":
            dims = [
                (name, ctx.trace_data.get_column(name))
                for name in ctx.trace_data.columns
                if ((not attr_value) or (name in attr_value))
                and (ctx.trace_spec.constructor != go.Parcoords or _is_continuous(df, name))
                and (
                    ctx.trace_spec.constructor != go.Parcats
                    or (attr_value is not None and name in attr_value)
                    or nw.to_py_scalar(df.get_column(name).n_unique())
                    <= ctx.args["dimensions_max_cardinality"]
                )
            ]
            binding.data["dimensions"] = [
                dict(label=_get_label(ctx.args, name), values=column)
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
                    cols = [ctx.rc(c) for c in attr_value]
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
                    customdata_cols = ctx.args.get("custom_data") or []
                    for col in attr_value:
                        if hover_is_dict and not attr_value[col]:
                            continue
                        if col in [
                            ctx.args.get("x"),
                            ctx.args.get("y"),
                            ctx.args.get("z"),
                            ctx.args.get("base"),
                        ]:
                            continue
                        try:
                            position = ctx.args["custom_data"].index(col)
                        except (ValueError, AttributeError, KeyError):
                            position = len(customdata_cols)
                            customdata_cols.append(col)
                        col_label = ctx.args.get("_aggregation_plan")
                        if col_label is None:
                            col_label = _get_label(ctx.args, col)
                        else:
                            # reuse the "role=None" path from get_decorated_label
                            col_label = _get_label(ctx.args, col)
                        binding.mapping_labels[col_label] = "%%{customdata[%d]}" % (
                            position
                        )
                    if len(customdata_cols) > 0:
                        cols = [ctx.rc(c) for c in dict.fromkeys(customdata_cols)]
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
                % ctx.args["x"]
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

    trendline_function = trendline_functions[ctx.args["trendline"]]
    y_out, hover_header, fit_results = trendline_function(
        ctx.args["trendline_options"],
        sorted_df.get_column(x_col),
        x.to_numpy(),
        y.to_numpy(),
        ctx.args["x"],
        ctx.args["y"],
        non_missing.to_numpy(),
    )
    assert len(y_out) == len(x_data), "missing-data-handling failure in trendline code"

    return TrendlineFitResult(
        x_data=x_data,
        y_data=y_out,
        fit_results=fit_results,
        hover_header=hover_header,
        x_label=_get_label(ctx.args, ctx.args["x"]),
        y_label=_get_label(ctx.args, ctx.args["y"]),
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
        if attr.raw_value is None:
            continue
        attr_label = attr.label
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
                if ctx.args.get("color_is_continuous"):
                    vc.marker["colors"] = ctx.trace_data.get_column(col_name)
                    vc.marker["coloraxis"] = "coloraxis1"
                    vc.extra_labels.append((attr_label, "%{color}"))
                else:
                    vc.marker["colors"] = []
                    if ctx.args["color_discrete_map"] is not None:
                        mapping = ctx.args["color_discrete_map"].copy()
                    else:
                        mapping = {}
                    for cat in ctx.trace_data.get_column(col_name).to_list():
                        if mapping.get(cat) is None:
                            mapping[cat] = ctx.args["color_discrete_sequence"][
                                len(mapping) % len(ctx.args["color_discrete_sequence"])
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
    if ctx.args["hover_data"] and isinstance(ctx.args["hover_data"], dict):
        for k, v in mapping_labels.items():
            k_args = _invert_label(ctx.args, k)
            if k_args in ctx.args["hover_data"]:
                formatter = ctx.args["hover_data"][k_args][0]
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
    hover: TraceHoverConfig,
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

    # ---- hover template (re-uses combined_labels) ----
    # Note: we call _build_hover_config here so it sees ALL merged labels
    hover_config = _build_hover_config(ctx, combined_labels, hover_header)
    if hover_config.hovertemplate:
        patch["hovertemplate"] = hover_config.hovertemplate

    return TraceBuildResult(trace_patch=patch, fit_results=fit_results)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_trace_spec(
    args,
    trace_spec,
    trace_data,
    mapping_labels,
    sizeref,
    decorated_label_fn,
):
    """Build a single trace's patch dict and optional trendline fit results.

    Parameters
    ----------
    args : dict
        The fully populated Express args dict.
    trace_spec : TraceSpec
        Describes which trace type to build.
    trace_data : nw.DataFrame
        Per-trace curated data.
    mapping_labels : Mapping
        Pre-existing labels from ``make_splom_trace_names`` or similar.
    sizeref : float
        Marker sizeref value.
    decorated_label_fn : callable
        ``(args, column, role) -> display_label`` (typically ``get_decorated_label``).

    Returns
    -------
    (trace_patch : dict, fit_results : dict or None)
    """
    trace_data: nw.DataFrame

    if "line_close" in args and args["line_close"]:
        trace_data = nw.concat([trace_data, trace_data.head(1)], how="vertical")

    # Build the single pre-resolved context that every phase consumes
    ctx = TraceBuildContext.build(
        args, trace_spec, trace_data, mapping_labels, sizeref, decorated_label_fn
    )

    # Run the first three phases independently – each takes only the Context
    binding = _bind_trace_data(ctx)
    trendline = None
    if "trendline" in trace_spec.attrs and args["trendline"] is not None:
        trendline = _compute_trendline_fit(ctx)
    visual = _apply_visual_patches(ctx)

    # The final merge step also triggers the hover-template phase (which needs
    # to see the merged label set, so it is intentionally run inside merge).
    result = _merge_phases(ctx, binding, trendline, visual, None)

    return result.trace_patch, result.fit_results

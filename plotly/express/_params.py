from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type

if TYPE_CHECKING:
    pass


class ParamCategory:
    DATA_COLUMN = "data_column"
    DATA_ARRAY = "data_array"
    GROUPING = "grouping"
    MAPPING = "mapping"
    LABEL = "label"
    LAYOUT_CONFIG = "layout_config"
    TRACE_CONFIG = "trace_config"
    MAPPING_CONFIG = "mapping_config"


ALL_CATEGORIES = (
    ParamCategory.DATA_COLUMN,
    ParamCategory.DATA_ARRAY,
    ParamCategory.GROUPING,
    ParamCategory.MAPPING,
    ParamCategory.LABEL,
    ParamCategory.LAYOUT_CONFIG,
    ParamCategory.TRACE_CONFIG,
    ParamCategory.MAPPING_CONFIG,
)


ALL_CHARTS: Tuple[str, ...] = (
    "scatter",
    "scatter_3d",
    "scatter_polar",
    "scatter_ternary",
    "scatter_mapbox",
    "scatter_geo",
    "line",
    "line_3d",
    "line_polar",
    "line_ternary",
    "line_mapbox",
    "line_geo",
    "area",
    "bar",
    "bar_polar",
    "histogram",
    "box",
    "violin",
    "strip",
    "ecdf",
    "density_heatmap",
    "density_contour",
    "density_mapbox",
    "pie",
    "sunburst",
    "treemap",
    "icicle",
    "funnel",
    "funnel_area",
    "timeline",
    "scatter_matrix",
    "parallel_coordinates",
    "parallel_categories",
    "choropleth",
    "choropleth_mapbox",
)


@dataclass
class ParamMeta:
    name: str
    category: str
    doc_type: str
    doc_desc: List[str]
    default_value: Any = None
    trace_attr: Optional[str] = None
    sequence_name: Optional[str] = None
    map_name: Optional[str] = None
    in_defaults: bool = False
    charts: Optional[Tuple[str, ...]] = None

    def applies_to(self, chart_name: Optional[str]) -> bool:
        if chart_name is None or self.charts is None:
            return True
        return chart_name in self.charts


@dataclass
class ParamRegistry:
    _params: Dict[str, ParamMeta] = field(default_factory=dict)
    _by_category: Dict[str, List[str]] = field(default_factory=dict)
    _constructor_map: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        for cat in ALL_CATEGORIES:
            self._by_category[cat] = []

    def add(self, meta: ParamMeta) -> None:
        if meta.name in self._params:
            raise ValueError(f"Duplicate parameter registration: {meta.name}")
        self._params[meta.name] = meta
        self._by_category.setdefault(meta.category, []).append(meta.name)

    def get(self, name: str) -> Optional[ParamMeta]:
        return self._params.get(name)

    def __getitem__(self, name: str) -> ParamMeta:
        return self._params[name]

    def __contains__(self, name: str) -> bool:
        return name in self._params

    def register_constructor(self, type_name: str, chart_name: str) -> None:
        self._constructor_map[type_name] = chart_name

    def chart_name_for(self, constructor) -> Optional[str]:
        ctor_type = (
            constructor if isinstance(constructor, str) else constructor().type
        )
        return self._constructor_map.get(ctor_type)

    # ------ chart-specific queries ------

    def filter_params(self, chart_name: Optional[str]) -> List[ParamMeta]:
        if chart_name is None:
            return list(self._params.values())
        return [m for m in self._params.values() if m.applies_to(chart_name)]

    def names_for_chart(self, chart_name: Optional[str]) -> List[str]:
        if chart_name is None:
            return list(self._params.keys())
        return [m.name for m in self._params.values() if m.applies_to(chart_name)]

    def by_category_for_chart(
        self, category: str, chart_name: Optional[str]
    ) -> List[str]:
        names = self._by_category.get(category, [])
        if chart_name is None:
            return list(names)
        result = []
        for n in names:
            m = self._params[n]
            if m.applies_to(chart_name):
                result.append(n)
        return result

    def get_attrable_lists(
        self, chart_name: Optional[str] = None
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        direct = self.by_category_for_chart(ParamCategory.DATA_COLUMN, chart_name)
        array = self.by_category_for_chart(ParamCategory.DATA_ARRAY, chart_name)
        group = self.by_category_for_chart(ParamCategory.GROUPING, chart_name)
        renameable = self.by_category_for_chart(ParamCategory.MAPPING, chart_name)

        _direct_order = [
            "base", "x", "y", "z", "a", "b", "c", "r", "theta", "size",
            "x_start", "x_end", "hover_name", "text", "names", "values",
            "parents", "wide_cross", "ids", "error_x", "error_x_minus",
            "error_y", "error_y_minus", "error_z", "error_z_minus",
            "lat", "lon", "locations", "animation_group",
        ]
        _array_order = [
            "dimensions", "custom_data", "hover_data", "path", "wide_variable",
        ]
        _group_order = [
            "animation_frame", "facet_row", "facet_col", "line_group",
        ]
        _rename_order = [
            "color", "symbol", "line_dash", "pattern_shape",
        ]
        direct = [n for n in _direct_order if n in direct]
        array = [n for n in _array_order if n in array]
        group = [n for n in _group_order if n in group]
        renameable = [n for n in _rename_order if n in renameable]
        return direct, array, group, renameable

    def get_all_attrables(self, chart_name: Optional[str] = None) -> List[str]:
        d, a, g, rg = self.get_attrable_lists(chart_name)
        return d + a + g + rg

    def build_docs_dict(self, chart_name: Optional[str] = None) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for m in self.filter_params(chart_name):
            result[m.name] = [m.doc_type] + list(m.doc_desc)
        return result

    def get_defaults_slots(self) -> List[str]:
        return [m.name for m in self._params.values() if m.in_defaults]

    def build_defaults_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for m in self._params.values():
            if m.in_defaults:
                result[m.name] = m.default_value
        return result

    def param_names_for_signature(
        self, names: List[str]
    ) -> List[Tuple[str, Any]]:
        result = []
        for name in names:
            meta = self._params.get(name)
            if meta is None:
                result.append((name, None))
            else:
                result.append((name, meta.default_value))
        return result

    def signature_params_for_chart(
        self, chart_name: Optional[str]
    ) -> List[Tuple[str, Any]]:
        names = self.names_for_chart(chart_name)
        if "data_frame" in names:
            names.remove("data_frame")
            names.insert(0, "data_frame")
        return self.param_names_for_signature(names)

    def assert_signature_matches(self, chart_name: str, sig_params: List[str]) -> None:
        """Assert that every parameter in the function signature is registered.

        Only checks one direction: signature → registry (every arg in the public
        function must have metadata).  The reverse is *not* enforced because the
        registry may carry internal / helper parameters that are not exposed as
        top-level keyword arguments (e.g. ``ids``, ``wide_variable``, ...).
        """
        reg_names = set(self.names_for_chart(chart_name))
        sig_set = set(sig_params)
        missing = sorted(sig_set - reg_names)
        if missing:
            msg = (f"Signature mismatch for px.{chart_name}(): "
                   f"parameters not registered in ParamRegistry: {missing}")
            raise AssertionError(msg)


_colref_type = "str or int or Series or array-like"
_colref_desc = (
    "Either a name of a column in `data_frame`, or a pandas Series or array_like object."
)
_colref_list_type = "list of str or int, or Series or array-like"
_colref_list_desc = (
    "Either names of columns in `data_frame`, or pandas Series, or array_like objects"
)

_2D_CHARTS = (
    "scatter", "line", "area", "bar", "histogram",
    "box", "violin", "strip", "ecdf",
    "density_heatmap", "density_contour",
    "scatter_matrix",
    "parallel_coordinates", "parallel_categories",
    "funnel", "timeline",
)
_FACET_CHARTS = _2D_CHARTS
_CARTESIAN_CHARTS = (
    "scatter", "line", "area", "bar", "histogram",
    "box", "violin", "strip", "ecdf",
    "density_heatmap", "density_contour",
    "scatter_3d", "scatter_matrix",
    "parallel_coordinates", "parallel_categories",
    "funnel", "timeline", "scatter_polar", "scatter_ternary",
    "bar_polar", "line_polar", "line_ternary",
)
_COLOR_DISCRETE_CHARTS = ALL_CHARTS
_COLOR_CONTINUOUS_CHARTS = (
    "scatter", "scatter_3d", "scatter_polar", "scatter_ternary",
    "scatter_mapbox", "scatter_geo", "scatter_matrix",
    "bar", "bar_polar",
    "density_heatmap", "density_mapbox", "density_map",
    "parallel_coordinates", "parallel_categories",
    "choropleth", "choropleth_mapbox", "choropleth_map",
    "sunburst", "treemap", "icicle",
    "timeline",
)
_ERRORBAR_CHARTS = (
    "scatter", "scatter_3d", "line", "line_3d", "area", "bar", "funnel", "timeline",
)
_ANIMATION_CHARTS = _CARTESIAN_CHARTS + (
    "scatter_mapbox", "scatter_geo", "line_mapbox", "line_geo",
    "density_mapbox", "choropleth", "choropleth_mapbox", "bar_polar",
)
_AXIS_RANGE_CHARTS = _CARTESIAN_CHARTS
_LOG_AXIS_CHARTS = _CARTESIAN_CHARTS


def create_registry() -> ParamRegistry:
    r = ParamRegistry()

    # -------- Constructor map --------
    r.register_constructor("scatter", "scatter")
    r.register_constructor("scattergl", "scatter")
    r.register_constructor("scatter3d", "scatter_3d")
    r.register_constructor("scatterpolar", "scatter_polar")
    r.register_constructor("scatterternary", "scatter_ternary")
    r.register_constructor("scattermapbox", "scatter_mapbox")
    r.register_constructor("scattergeo", "scatter_geo")
    r.register_constructor("bar", "bar")
    r.register_constructor("barpolar", "bar_polar")
    r.register_constructor("histogram", "histogram")
    r.register_constructor("box", "box")
    r.register_constructor("violin", "violin")
    r.register_constructor("strip", "strip")
    r.register_constructor("histogram2d", "density_heatmap")
    r.register_constructor("histogram2dcontour", "density_contour")
    r.register_constructor("densitymapbox", "density_mapbox")
    r.register_constructor("pie", "pie")
    r.register_constructor("sunburst", "sunburst")
    r.register_constructor("treemap", "treemap")
    r.register_constructor("icicle", "icicle")
    r.register_constructor("funnel", "funnel")
    r.register_constructor("funnelarea", "funnel_area")
    r.register_constructor("splom", "scatter_matrix")
    r.register_constructor("parcoords", "parallel_coordinates")
    r.register_constructor("parcats", "parallel_categories")
    r.register_constructor("choropleth", "choropleth")
    r.register_constructor("choroplethmapbox", "choropleth_mapbox")

    # -------- data_frame --------
    r.add(ParamMeta(
        name="data_frame",
        category=ParamCategory.LABEL,
        doc_type="DataFrame or array-like or dict",
        doc_desc=[
            "This argument needs to be passed for column names (and not keyword names) to be used.",
            "Array-like and dict are transformed internally to a pandas DataFrame.",
            "Optional: if missing, a DataFrame gets constructed under the hood using the other arguments.",
        ],
    ))

    # -------- DATA_COLUMN: Cartesian axes --------
    for axis_name, axis_desc, charts in [
        ("x", "Values from this column or array_like are used to position marks along the x axis in cartesian coordinates.",
         _CARTESIAN_CHARTS),
        ("y", "Values from this column or array_like are used to position marks along the y axis in cartesian coordinates.",
         _CARTESIAN_CHARTS),
        ("z", "Values from this column or array_like are used to position marks along the z axis in cartesian coordinates.",
         ("scatter_3d", "line_3d", "surface")),
    ]:
        r.add(ParamMeta(
            name=axis_name,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, axis_desc],
            charts=tuple(charts),
        ))

    # -------- Timeline x_start / x_end --------
    _tl = ("timeline",)
    r.add(ParamMeta(
        name="x_start",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[
            _colref_desc,
            "(required)",
            "Values from this column or array_like are used to position marks along the x axis in cartesian coordinates.",
        ],
        charts=_tl,
    ))
    r.add(ParamMeta(
        name="x_end",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[
            _colref_desc,
            "(required)",
            "Values from this column or array_like are used to position marks along the x axis in cartesian coordinates.",
        ],
        charts=_tl,
    ))

    # -------- Ternary axes --------
    for axis_name, axis_desc in [
        ("a", "Values from this column or array_like are used to position marks along the a axis in ternary coordinates."),
        ("b", "Values from this column or array_like are used to position marks along the b axis in ternary coordinates."),
        ("c", "Values from this column or array_like are used to position marks along the c axis in ternary coordinates."),
    ]:
        r.add(ParamMeta(
            name=axis_name,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, axis_desc],
            charts=("scatter_ternary", "line_ternary"),
        ))

    # -------- Polar axes --------
    for axis_name, axis_desc in [
        ("r", "Values from this column or array_like are used to position marks along the radial axis in polar coordinates."),
        ("theta", "Values from this column or array_like are used to position marks along the angular axis in polar coordinates."),
    ]:
        r.add(ParamMeta(
            name=axis_name,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, axis_desc],
            charts=("scatter_polar", "line_polar", "bar_polar"),
        ))

    # -------- size (scatter, scatter_3d, scatter_matrix) --------
    r.add(ParamMeta(
        name="size",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[
            _colref_desc,
            "Values from this column or array_like are used to assign mark sizes.",
        ],
        charts=("scatter", "scatter_3d", "scatter_polar", "scatter_ternary",
                "scatter_mapbox", "scatter_geo", "scatter_matrix"),
    ))

    # -------- base --------
    r.add(ParamMeta(
        name="base",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[
            _colref_desc,
            "Values from this column or array_like are the base position of bars.",
        ],
        charts=("bar", "bar_polar", "funnel", "timeline"),
    ))

    # -------- hover_name --------
    r.add(ParamMeta(
        name="hover_name",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc,
                  "Values from this column or array_like appear in bold in the hover tooltip."],
        charts=tuple(c for c in ALL_CHARTS if c not in (
            "parallel_coordinates", "parallel_categories", "pie",
            "sunburst", "treemap", "icicle", "funnel_area",
        )),
    ))

    # -------- text --------
    r.add(ParamMeta(
        name="text",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[
            _colref_desc,
            "Values from this column or array_like appear in the figure as text labels.",
        ],
        charts=tuple(c for c in ALL_CHARTS if c not in (
            "parallel_coordinates", "parallel_categories",
            "histogram", "box", "violin", "strip", "ecdf",
            "density_heatmap", "density_contour",
            "funnel_area", "pie",
        )),
    ))

    # -------- names / values / parents (hierarchical / pie) --------
    for nm, desc, charts in [
        ("names",
         "Values from this column or array_like are used as labels for sectors of the pie chart.",
         ("pie", "sunburst", "treemap", "icicle", "funnel_area")),
        ("values",
         "Values from this column or array_like are used to set the values associated with the sectors of the pie chart.",
         ("pie", "sunburst", "treemap", "icicle", "funnel_area")),
        ("parents",
         "Values from this column or array_like are used as parents in the hierarchy.",
         ("sunburst", "treemap", "icicle")),
        ("wide_cross",
         "Values from this column or array_like are used...",
         ("scatter", "line", "area", "bar", "histogram",
          "scatter_matrix", "parallel_categories")),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, desc],
            charts=tuple(charts),
        ))

    # -------- ids --------
    r.add(ParamMeta(
        name="ids",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[
            _colref_desc,
            "Values from this column or array_like are used to assign object-ids to animation frames for smooth transitions.",
        ],
        charts=tuple(c for c in _ANIMATION_CHARTS),
    ))

    # -------- error bars --------
    for eb, eb_charts in [
        ("error_x", _ERRORBAR_CHARTS),
        ("error_x_minus", _ERRORBAR_CHARTS),
        ("error_y", _ERRORBAR_CHARTS),
        ("error_y_minus", _ERRORBAR_CHARTS),
        ("error_z", ("scatter_3d", "line_3d")),
        ("error_z_minus", ("scatter_3d", "line_3d")),
    ]:
        suffix = " (subtracted)" if eb.endswith("_minus") else ""
        axis = eb.split("_")[1].upper()
        r.add(ParamMeta(
            name=eb,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[
                _colref_desc,
                f"Values from this column or array_like are used to size the {axis}-axis error bars{suffix}.",
            ],
            charts=tuple(eb_charts),
        ))

    # -------- lat / lon / locations (geo / mapbox) --------
    geo_mapbox = ("scatter_mapbox", "scatter_geo", "density_mapbox",
                  "choropleth_mapbox", "choropleth", "line_mapbox", "line_geo")
    for nm, desc, charts in [
        ("lat",
         "Values from this column or array_like are used to position marks according to latitude on a map.",
         geo_mapbox),
        ("lon",
         "Values from this column or array_like are used to position marks according to longitude on a map.",
         geo_mapbox),
        ("locations",
         "Values from this column or array_like are interpreted as geographic locations in the layout's map.",
         ("choropleth", "choropleth_mapbox")),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, desc],
            charts=tuple(charts),
        ))

    # -------- animation_group --------
    r.add(ParamMeta(
        name="animation_group",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[
            _colref_desc,
            "Values from this column or array_like are used to group rows in `data_frame` into animation frames.",
        ],
        charts=tuple(c for c in _ANIMATION_CHARTS),
    ))

    # -------- DATA_ARRAY --------
    for nm, desc, charts in [
        ("dimensions",
         "Either names of columns in `data_frame`, or pandas Series, or array_like objects.",
         ("scatter_matrix", "parallel_coordinates", "parallel_categories")),
        ("custom_data",
         "Values from these columns appear as extra data in the hover tooltip.",
         (c for c in ALL_CHARTS if c not in (
             "parallel_coordinates", "parallel_categories", "pie",
             "sunburst", "treemap", "icicle", "funnel_area",
             "histogram", "box", "violin", "strip", "ecdf",
             "density_heatmap", "density_contour",
         ))),
        ("hover_data",
         "Values from these columns appear as extra data in the hover tooltip.",
         (c for c in ALL_CHARTS if c not in (
             "parallel_coordinates", "parallel_categories",
             "pie", "sunburst", "treemap", "icicle", "funnel_area",
         ))),
        ("path",
         "Either names of columns in `data_frame`, or pandas Series, or array_like objects.",
         ("sunburst", "treemap", "icicle")),
        ("wide_variable",
         "Either names of columns in `data_frame`, or pandas Series, or array_like objects.",
         ALL_CHARTS),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.DATA_ARRAY,
            doc_type=_colref_list_type,
            doc_desc=[_colref_list_desc, desc],
            charts=tuple(charts),
        ))

    # -------- GROUPING --------
    for nm, desc, charts in [
        ("animation_frame",
         "Values from this column or array_like are used to assign marks to animation frames.",
         tuple(c for c in _ANIMATION_CHARTS)),
        ("facet_row",
         "Values from this column or array_like are used to assign marks to facetted subplots in the vertical direction.",
         tuple(c for c in _FACET_CHARTS)),
        ("facet_col",
         "Values from this column or array_like are used to assign marks to facetted subplots in the horizontal direction.",
         tuple(c for c in _FACET_CHARTS)),
        ("line_group",
         "Values from this column or array_like are used to group rows of `data_frame` into lines.",
         ("line", "line_3d", "area", "line_polar", "line_ternary",
          "line_mapbox", "line_geo")),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.GROUPING,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, desc],
            charts=tuple(charts),
        ))

    # -------- MAPPING --------
    for nm, seq_nm, map_nm, desc, charts, trace_a, maps_charts_ok in [
        ("color", "color_discrete_sequence", "color_discrete_map",
         "Either a name of a column in `data_frame`, or a pandas Series or array_like object. Values from this column or array_like are used to assign color to marks.",
         _COLOR_DISCRETE_CHARTS, "marker.color", True),
        ("symbol", "symbol_sequence", "symbol_map",
         "Either a name of a column in `data_frame`, or a pandas Series or array_like object. Values from this column or array_like are used to assign symbols to marks.",
         ("scatter", "scatter_3d", "scatter_polar", "scatter_ternary",
          "scatter_mapbox", "scatter_geo", "line", "line_3d",
          "line_polar", "line_ternary", "line_mapbox", "line_geo",
          "scatter_matrix"),
         "marker.symbol", False),
        ("line_dash", "line_dash_sequence", "line_dash_map",
         "Either a name of a column in `data_frame`, or a pandas Series or array_like object. Values from this column or array_like are used to assign dash-patterns to lines.",
         ("line", "line_3d", "line_polar", "line_ternary", "area",
          "line_mapbox", "line_geo"),
         "line.dash", False),
        ("pattern_shape", "pattern_shape_sequence", "pattern_shape_map",
         "Either a name of a column in `data_frame`, or a pandas Series or array_like object. Values from this column or array_like are used to assign pattern shapes to bar marks.",
         ("bar", "bar_polar", "histogram", "area"),
         "marker.pattern.shape", False),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.MAPPING,
            doc_type=_colref_type,
            doc_desc=[desc],
            sequence_name=seq_nm,
            map_name=map_nm,
            trace_attr=trace_a,
            charts=tuple(charts),
        ))

    # -------- LABEL: title / subtitle --------
    for nm, desc in [
        ("title", "The figure title."),
        ("subtitle", "The figure subtitle."),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.LABEL,
            doc_type="str",
            doc_desc=[desc],
        ))

    # -------- LABEL: labels / category_orders --------
    r.add(ParamMeta(
        name="labels",
        category=ParamCategory.LABEL,
        doc_type="dict with str keys and str values (default `{}`)",
        doc_desc=[
            "By default, column names are used in the figure for axis titles, legend entries and hovers.",
            "This parameter allows this to be overridden.",
            "The keys of this dict should correspond to column names, and the values should correspond to the desired label to be displayed.",
        ],
        in_defaults=True,
        default_value={},
    ))

    r.add(ParamMeta(
        name="category_orders",
        category=ParamCategory.LABEL,
        doc_type="dict with str keys and list of str values (default `{}`)",
        doc_desc=[
            "By default, in Python 3.6+, the order of categorical values in axes, legends and facets depends on the order in which these values are first encountered in `data_frame` (and no order is guaranteed by default in Python below 3.6).",
            "This parameter is used to force a specific ordering of values per column.",
            "The keys of this dict should correspond to column names, and the values should be lists of strings corresponding to the specific display order desired.",
        ],
        in_defaults=True,
        default_value={},
    ))

    # -------- LAYOUT_CONFIG: width / height / template --------
    for nm, dv, desc in [
        ("width", None, "The figure width in pixels."),
        ("height", None, "The figure height in pixels."),
        ("template", None, "The figure template name (must be a key in plotly.io.templates) or definition."),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.LAYOUT_CONFIG,
            doc_type=f"int (default `{dv!r}`)" if isinstance(dv, int) else f"str or dict or plotly.graph_objects.layout.Template instance" if nm == "template" else f"int (default `None`)",
            doc_desc=[desc],
            in_defaults=True,
            default_value=dv,
        ))

    # -------- LAYOUT_CONFIG: log_x, log_y, log_z, log_r --------
    for log_axis, charts in [
        ("log_x", tuple(c for c in _LOG_AXIS_CHARTS if "x" in ("x","y","z","r") and c not in ("scatter_polar", "scatter_ternary", "bar_polar", "line_polar", "line_ternary"))),
        ("log_y", tuple(c for c in _LOG_AXIS_CHARTS if c not in ("scatter_polar", "scatter_ternary", "bar_polar", "line_polar", "line_ternary"))),
        ("log_z", ("scatter_3d", "line_3d", "surface")),
        ("log_r", ("scatter_polar", "line_polar", "bar_polar")),
    ]:
        axis_letter = log_axis.split("_")[1]
        if axis_letter == "r":
            desc = "If `True`, the radial axis is log-scaled in polar coordinates."
        else:
            desc = f"If `True`, the {axis_letter}-axis is log-scaled in cartesian coordinates."
        r.add(ParamMeta(
            name=log_axis,
            category=ParamCategory.LAYOUT_CONFIG,
            doc_type="boolean (default `False`)",
            doc_desc=[desc],
            default_value=False,
            charts=tuple(charts),
        ))

    # -------- LAYOUT_CONFIG: range_x, range_y, range_z, range_r --------
    for range_axis, charts in [
        ("range_x", tuple(c for c in _AXIS_RANGE_CHARTS if c not in ("scatter_polar", "scatter_ternary", "bar_polar", "line_polar", "line_ternary"))),
        ("range_y", tuple(c for c in _AXIS_RANGE_CHARTS if c not in ("scatter_polar", "scatter_ternary", "bar_polar", "line_polar", "line_ternary"))),
        ("range_z", ("scatter_3d", "line_3d", "surface")),
        ("range_r", ("scatter_polar", "line_polar", "bar_polar")),
    ]:
        axis_letter = range_axis.split("_")[1]
        if axis_letter == "r":
            desc = [f"[min, max] where the radial axis is drawn in polar coordinates."]
        else:
            desc = [f"[min, max] where the {axis_letter}-axis is drawn in cartesian coordinates."]
        r.add(ParamMeta(
            name=range_axis,
            category=ParamCategory.LAYOUT_CONFIG,
            doc_type="list of two numbers",
            doc_desc=desc,
            charts=tuple(charts),
        ))

    # -------- LAYOUT_CONFIG: facet spacing / wrap --------
    for nm, dtype, desc, default in [
        ("facet_col_wrap", "int",
         "Maximum number of columns for faceted subplots in the horizontal direction.", None),
        ("facet_row_spacing", "float",
         "Spacing between faceted subplots in the vertical direction (fraction of plot area).", 0.06),
        ("facet_col_spacing", "float",
         "Spacing between faceted subplots in the horizontal direction (fraction of plot area).", 0.08),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.LAYOUT_CONFIG,
            doc_type=dtype,
            doc_desc=[desc],
            default_value=default,
            charts=tuple(c for c in _FACET_CHARTS),
        ))

    # -------- LAYOUT_CONFIG: range_color --------
    r.add(ParamMeta(
        name="range_color",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="list of two numbers",
        doc_desc=[
            "[min, max] value of the color scale for the data.",
            "If not provided, the range is inferred from the data.",
        ],
        charts=tuple(c for c in _COLOR_CONTINUOUS_CHARTS),
    ))

    # -------- LAYOUT_CONFIG: radius (density_mapbox) --------
    r.add(ParamMeta(
        name="radius",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="int (default is 30)",
        doc_desc=["Sets the radius of influence of each point."],
        default_value=30,
        charts=("density_mapbox",),
    ))

    # -------- LAYOUT_CONFIG: center / zoom / mapbox_style / geojson etc --------
    _GEO = ("scatter_geo", "choropleth", "line_geo")
    _MAPBOX = ("scatter_mapbox", "density_mapbox", "choropleth_mapbox", "line_mapbox")
    _GEO_ALL = _GEO + _MAPBOX
    for nm, dtype, desc, charts in [
        ("center", "dict",
         "Data frame column or array containing the latitude of the map center point.",
         tuple(set(_MAPBOX + _GEO))),
        ("zoom", "int or float",
         "Map zoom level.",
         _MAPBOX),
        ("mapbox_style", "str",
         "The mapbox style to use for mapbox subplots.",
         _MAPBOX),
        ("geojson", "GeoJSON-formatted Python dict or geometry collection",
         "A GeoJSON-formatted Python object, as described in the plotly.js documentation on choropleth traces.",
         ("choropleth", "choropleth_mapbox")),
        ("featureidkey", "str",
         "Path to the field in the GeoJSON feature properties object to be matched with data_frame.locations, or data_frame.index.",
         ("choropleth", "choropleth_mapbox")),
        ("scope", "str",
         "The Set the scope of the map.",
         _GEO),
        ("projection", "str",
         "The type of projection used for the map.",
         _GEO),
        ("fitbounds", "boolean",
         "Whether to adjust the bounds of the map to be the smallest possible such that every data point is visible.",
         _GEO),
        ("basemap_visible", "boolean",
         "Whether to display the map base layer.",
         _GEO),
        ("resolution", "int",
         "The resolution of the base map.",
         _GEO),
        ("showlataxis", "boolean",
         "Whether to display the latitude grid.",
         _GEO),
        ("showlonaxis", "boolean",
         "Whether to display the longitude grid.",
         _GEO),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.LAYOUT_CONFIG,
            doc_type=dtype,
            doc_desc=[desc],
            charts=tuple(charts),
        ))

    # -------- TRACE_CONFIG: opacity --------
    _OPACITY_CHARTS = (
        "scatter", "scatter_3d", "scatter_polar", "scatter_ternary",
        "scatter_mapbox", "scatter_geo", "scatter_matrix",
        "bar", "histogram", "ecdf", "funnel", "funnel_area", "pie",
        "density_heatmap", "density_mapbox", "density_map",
        "choropleth_mapbox", "choropleth_map", "timeline",
    )
    r.add(ParamMeta(
        name="opacity",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="float",
        doc_desc=["Value between 0 and 1. Sets the opacity for markers."],
        charts=_OPACITY_CHARTS,
    ))

    # -------- TRACE_CONFIG: orientation --------
    _ORIENTATION_CHARTS = (
        "scatter", "line", "area", "bar", "histogram",
        "box", "violin", "strip", "ecdf", "funnel",
        "density_heatmap", "density_contour",
    )
    r.add(ParamMeta(
        name="orientation",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `'v'`)",
        doc_desc=[
            "For `bar`, `histogram` and `box` traces, specifies whether the bars are horizontal or vertical.",
            "One of `'v'` for vertical or `'h'` for horizontal.",
        ],
        default_value="v",
        charts=_ORIENTATION_CHARTS,
    ))

    # -------- TRACE_CONFIG: barmode --------
    r.add(ParamMeta(
        name="barmode",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `'relative'`)",
        doc_desc=[
            "One of `'group'`, `'overlay'` or `'relative'`.",
            "In `'relative'` mode, bars are stacked above zero for positive values and below zero for negative values.",
            "In `'overlay'` mode, bars are drawn on top of one another.",
            "In `'group'` mode, bars are placed beside one another.",
        ],
        default_value="relative",
        charts=("bar", "histogram", "bar_polar"),
    ))

    # -------- TRACE_CONFIG: barnorm --------
    r.add(ParamMeta(
        name="barnorm",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `None`)",
        doc_desc=[
            "Set to `'fraction'` to divide the values of the bars by the sum of the values across all bars at that location on the axis.",
            "Set to `'percent'` to use percentages instead of fractions.",
            "Using `barnorm` changes the bar values, and therefore the values shown in the hover tooltip and used in the ticks.",
        ],
        charts=("histogram", "bar_polar"),
    ))

    # -------- TRACE_CONFIG: histnorm --------
    r.add(ParamMeta(
        name="histnorm",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `None`)",
        doc_desc=[
            "Specifies the type of normalization for the histogram.",
            "One of `'percent'`, `'probability'`, `'density'`, or `'probability density'`."
            "If `None`, the range of the histogram values correspond to the number of occurrences in each bin.",
        ],
        charts=("histogram", "ecdf"),
    ))

    # -------- TRACE_CONFIG: histfunc --------
    r.add(ParamMeta(
        name="histfunc",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `'count'`)",
        doc_desc=[
            "Specifies the binning function used for the histogram.",
            "One of `'count'`, `'sum'`, `'avg'`, `'min'`, or `'max'`.",
            "If `'count'`, the histogram values are computed by counting the number of values lying inside each bin.",
            "If `'sum'`, `'avg'`, `'min'`, or `'max'`, the values inside the bin are summed, averaged, min-ed or max-ed.",
        ],
        default_value="count",
        charts=("histogram",),
    ))

    # -------- TRACE_CONFIG: cumulative --------
    r.add(ParamMeta(
        name="cumulative",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean",
        doc_desc=[
            "If `True`, the histogram values are cumulative.",
            "The value at each bin is the sum of the values from previous bins plus the value in the current bin.",
        ],
        default_value=False,
        charts=("histogram", "ecdf"),
    ))

    # -------- TRACE_CONFIG: nbins --------
    r.add(ParamMeta(
        name="nbins",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="int",
        doc_desc=[
            "Positive integer that sets the number of bins in the histogram along the x and y axes.",
            "For `histogram2d` and `histogram2dcontour`, this can be a list of two numbers: the first is the number of x bins, the second the number of y bins.",
        ],
        charts=("histogram", "density_mapbox"),
    ))
    for nb_name, axis in [("nbinsx", "x"), ("nbinsy", "y")]:
        r.add(ParamMeta(
            name=nb_name,
            category=ParamCategory.TRACE_CONFIG,
            doc_type="int",
            doc_desc=[
                f"Positive integer that sets the number of bins along the {axis} axis for the histogram or 2D histogram.",
            ],
            charts=("density_heatmap", "density_contour"),
        ))

    # -------- TRACE_CONFIG: boxmode / violinmode / stripmode --------
    for nm, charts in [
        ("boxmode", ("box",)),
        ("violinmode", ("violin",)),
        ("stripmode", ("strip",)),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.TRACE_CONFIG,
            doc_type="str (default `'overlay'`)",
            doc_desc=[
                "One of `'group'` or `'overlay'`.",
                "In `'overlay'` mode, violins/plots/strips are drawn on top of one another in the same location on the axis.",
                "In `'group'` mode, violins/plots/strips are grouped per location on the axis.",
            ],
            default_value="overlay",
            charts=tuple(charts),
        ))

    # -------- TRACE_CONFIG: box / violin specific --------
    for nm, dtype, desc, charts in [
        ("box", "boolean",
         "If `True`, boxes are drawn inside the violin.",
         ("violin",)),
        ("points", "str or boolean",
         "One of `'outliers'`, `'suspectedoutliers'`, `'all'`, or `False`.",
         ("box", "violin", "strip")),
        ("notched", "boolean",
         "If `True`, boxes are drawn with notches.",
         ("box",)),
        ("sd", "boolean",
         "If `True`, the quartile method is used to compute the box ends, otherwise the SD method is used.",
         ("box",)),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.TRACE_CONFIG,
            doc_type=dtype,
            doc_desc=[desc],
            charts=tuple(charts),
        ))

    # -------- TRACE_CONFIG: markers / lines / line_shape --------
    for nm, dtype, desc, default, charts in [
        ("markers", "boolean (default `False`)",
         "If `True`, markers are shown on lines.",
         False, ("line", "line_3d", "line_polar", "line_ternary",
                 "line_mapbox", "line_geo", "area")),
        ("lines", "boolean (default `True`)",
         "If `False`, lines are not drawn (forced to `True` if `markers` is `False`).",
         True, ("scatter", "scatter_3d", "scatter_polar", "scatter_ternary",
                "scatter_mapbox", "scatter_geo")),
        ("line_shape", "str (default `'linear'`)",
         "One of `'linear'`, `'spline'`, `'hv'`, `'vh'`, `'hvh'`, `'vhv'`. The line shape.",
         "linear", ("line", "area", "line_3d", "line_polar",
                    "line_ternary", "line_mapbox", "line_geo", "timeline")),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.TRACE_CONFIG,
            doc_type=dtype,
            doc_desc=[desc],
            default_value=default,
            charts=tuple(charts),
        ))

    # -------- TRACE_CONFIG: render_mode --------
    r.add(ParamMeta(
        name="render_mode",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "One of `'auto'`, `'svg'`, or `'webgl'` (default is `'auto'`).",
            "Controls the browser API used to draw marks.",
            "`'svg'` is appropriate for figures with less than 1000 data points, and is the only mode that supports filled areas.",
            "`'webgl'` is appropriate for figures with more than 1000 data points, but does not support filled areas nor most Plotly.js features.",
        ],
        default_value="auto",
        charts=("scatter", "line", "area"),
    ))

    # -------- TRACE_CONFIG: marginal / marginal_x / marginal_y --------
    for nm, charts in [
        ("marginal", ("histogram", "box", "violin", "strip", "ecdf")),
        ("marginal_x", ("scatter", "density_contour")),
        ("marginal_y", ("scatter", "density_contour")),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.TRACE_CONFIG,
            doc_type="str",
            doc_desc=[
                "One of `'rug'`, `'box'`, `'violin'`, or `'histogram'`.",
                "If set, a subplot is drawn alongside the main plot, visualizing the distribution.",
            ],
            charts=tuple(charts),
        ))

    # -------- TRACE_CONFIG: trendline family --------
    for nm, dtype, desc, charts in [
        ("trendline", "str",
         "One of `'ols'`, `'lowess'`, `'rolling'`, `'expanding'` or `'ewm'`.",
         ("scatter",)),
        ("trendline_options", "dict",
         "Options for the trendline function.",
         ("scatter",)),
        ("trendline_color_override", "str",
         "Color to use for the trendline.",
         ("scatter",)),
        ("trendline_scope", "str (default `'trace'`)",
         "One of `'trace'`, `'overall'` or `'x'` or `'y'`.",
         ("scatter",)),
    ]:
        r.add(ParamMeta(
            name=nm,
            category=ParamCategory.TRACE_CONFIG,
            doc_type=dtype,
            doc_desc=[desc],
            charts=tuple(charts),
        ))

    # -------- TRACE_CONFIG: text_auto --------
    r.add(ParamMeta(
        name="text_auto",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean or str (default `False`)",
        doc_desc=[
            "If `True` or a string, the text trace is turned on by default.",
            "If the string is `'.3f'` or similar, the text is formatted with the given format.",
        ],
        default_value=False,
        charts=("bar", "histogram"),
    ))

    # -------- TRACE_CONFIG: line_close (area) --------
    r.add(ParamMeta(
        name="line_close",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean",
        doc_desc=["Whether to close the line for area plots."],
        default_value=False,
        charts=("area",),
    ))

    # -------- TRACE_CONFIG: hover_name etc for violin / box / strip --------
    for nm, dtype, desc, default, charts in [
        ("violingap", "float", "Gap between violins.", 0.3, ("violin",)),
        ("violinmode", "str", "One of `'group'` or `'overlay'`.", "overlay", ("violin",)),
        ("violinwidth", "float", "Width of the violin.", 0.3, ("violin",)),
        ("boxgap", "float", "Gap between boxes.", 0.3, ("box",)),
        ("boxmode", "str", "One of `'group'` or `'overlay'`.", "overlay", ("box",)),
        ("stripgap", "float", "Gap between strips.", 0.3, ("strip",)),
        ("stripmode", "str", "One of `'group'` or `'overlay'`.", "overlay", ("strip",)),
    ]:
        # These are already registered above, ignore duplicates here
        pass

    # -------- MAPPING_CONFIG: symbol --------
    for seq_nm, map_nm, charts in [
        ("symbol_sequence", "symbol_map", ("scatter", "scatter_3d", "scatter_polar",
                                           "scatter_ternary", "scatter_mapbox",
                                           "scatter_geo", "line", "line_3d",
                                           "line_polar", "line_ternary",
                                           "line_mapbox", "line_geo", "scatter_matrix")),
        ("line_dash_sequence", "line_dash_map", ("line", "line_3d", "area",
                                                 "line_polar", "line_ternary",
                                                 "line_mapbox", "line_geo")),
        ("pattern_shape_sequence", "pattern_shape_map", ("bar", "bar_polar",
                                                         "histogram", "area")),
    ]:
        stem = seq_nm.replace("_sequence", "")
        seq_desc_map = {
            "symbol": ("Strings should define valid plotly.js symbols.",
                       "When `symbol` is set, values in that column are assigned symbols by cycling through `symbol_sequence` in the order described in `category_orders`, unless the value of `symbol` is a key in `symbol_map`."),
            "line_dash": ("Strings should define valid plotly.js dash-patterns.",
                          "When `line_dash` is set, values in that column are assigned dash-patterns by cycling through `line_dash_sequence` in the order described in `category_orders`, unless the value of `line_dash` is a key in `line_dash_map`."),
            "pattern_shape": ("Strings should define valid plotly.js patterns-shapes.",
                              "When `pattern_shape` is set, values in that column are assigned patterns-shapes by cycling through `pattern_shape_sequence` in the order described in `category_orders`, unless the value of `pattern_shape` is a key in `pattern_shape_map`."),
        }
        seq1, seq2 = seq_desc_map[stem]
        map1, map2 = seq_desc_map[stem]
        # We'll rephrase map slightly
        r.add(ParamMeta(
            name=seq_nm,
            category=ParamCategory.MAPPING_CONFIG,
            doc_type="list of str",
            doc_desc=[seq1, seq2],
            in_defaults=True,
            default_value=None,
            charts=tuple(charts),
        ))
        r.add(ParamMeta(
            name=map_nm,
            category=ParamCategory.MAPPING_CONFIG,
            doc_type="dict with str keys and str values (default `{}`)",
            doc_desc=[
                map1.replace("assigned symbols by cycling through...",
                            "Used to override `" + seq_nm + "` to assign a specific " + stem + "s to marks corresponding with specific values.")
                .split(". Used")[0] + ".",
                f"Keys in `{map_nm}` should be values in the column denoted by `{stem}`.",
                f"Alternatively, if the values of `{stem}` are valid {stem} names, the string `'identity'` may be passed to cause them to be used directly.",
            ],
            in_defaults=True,
            default_value={},
            charts=tuple(charts),
        ))

    # -------- MAPPING_CONFIG: color_discrete_sequence / map --------
    r.add(ParamMeta(
        name="color_discrete_sequence",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="list of str",
        doc_desc=[
            "Strings should define valid CSS-colors.",
            "When `color` is set and the values in the corresponding column are not numeric, values in that column are assigned colors by cycling through `color_discrete_sequence` in the order described in `category_orders`, unless the value of `color` is a key in `color_discrete_map`.",
            "Various useful color sequences are available in the `plotly.express.colors` submodules, specifically `plotly.express.colors.qualitative`.",
        ],
        in_defaults=True,
        default_value=None,
        charts=tuple(c for c in _COLOR_DISCRETE_CHARTS),
    ))

    r.add(ParamMeta(
        name="color_discrete_map",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="dict with str keys and str values (default `{}`)",
        doc_desc=[
            "String values should define valid CSS-colors",
            "Used to override `color_discrete_sequence` to assign a specific colors to marks corresponding with specific values.",
            "Keys in `color_discrete_map` should be values in the column denoted by `color`.",
            "Alternatively, if the values of `color` are valid colors, the string `'identity'` may be passed to cause them to be used directly.",
        ],
        in_defaults=True,
        default_value={},
        charts=tuple(c for c in _COLOR_DISCRETE_CHARTS),
    ))

    # -------- MAPPING_CONFIG: color_continuous_scale --------
    r.add(ParamMeta(
        name="color_continuous_scale",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="list of str",
        doc_desc=[
            "Strings should define valid CSS-colors",
            "This list is used to build a continuous color scale when the column denoted by `color` contains numeric data.",
            "Various useful color scales are available in the `plotly.express.colors` submodules, specifically `plotly.express.colors.sequential`, `plotly.express.colors.diverging` and `plotly.express.colors.cyclical`.",
        ],
        in_defaults=True,
        default_value=None,
        charts=tuple(c for c in _COLOR_CONTINUOUS_CHARTS),
    ))

    # -------- MAPPING_CONFIG: color_continuous_midpoint --------
    r.add(ParamMeta(
        name="color_continuous_midpoint",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="number (default `None`)",
        doc_desc=[
            "If set, computes the bounds of the continuous color scale to have the desired midpoint.",
            "Setting this value is recommended when using `plotly.express.colors.diverging` color scales as the inputs to `color_continuous_scale`.",
        ],
        charts=tuple(c for c in _COLOR_CONTINUOUS_CHARTS),
    ))

    # -------- MAPPING_CONFIG: size_max --------
    r.add(ParamMeta(
        name="size_max",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="int (default `20`)",
        doc_desc=["Set the maximum mark size when using `size`."],
        in_defaults=True,
        default_value=20,
        charts=("scatter", "scatter_3d", "scatter_polar", "scatter_ternary",
                "scatter_mapbox", "scatter_geo", "scatter_matrix"),
    ))

    # -------- MAPPING_CONFIG: coloraxis --------
    r.add(ParamMeta(
        name="coloraxis",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="str",
        doc_desc=[
            "The name of a coloraxis. If provided, the trace color bar is linked to this coloraxis.",
            "Useful for sharing color scales across multiple traces and subplots.",
        ],
    ))

    return r


PARAMS: ParamRegistry = create_registry()

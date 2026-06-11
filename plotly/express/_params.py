from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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


@dataclass
class ParamRegistry:
    _params: Dict[str, ParamMeta] = field(default_factory=dict)
    _by_category: Dict[str, List[str]] = field(default_factory=dict)

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

    def by_category(self, category: str) -> List[str]:
        return list(self._by_category.get(category, []))

    @property
    def all_names(self) -> List[str]:
        return list(self._params.keys())

    def get_attrable_lists(self) -> Tuple[List[str], List[str], List[str], List[str]]:
        direct_attrables = self.by_category(ParamCategory.DATA_COLUMN)
        array_attrables = self.by_category(ParamCategory.DATA_ARRAY)
        group_attrables = list(self.by_category(ParamCategory.GROUPING))
        renameable_group_attrables = list(self.by_category(ParamCategory.MAPPING))

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
        direct_attrables = [n for n in _direct_order if n in direct_attrables]
        array_attrables = [n for n in _array_order if n in array_attrables]
        group_attrables = [n for n in _group_order if n in group_attrables]
        renameable_group_attrables = [n for n in _rename_order if n in renameable_group_attrables]
        return direct_attrables, array_attrables, group_attrables, renameable_group_attrables

    def get_all_attrables(self) -> List[str]:
        d, a, g, rg = self.get_attrable_lists()
        return d + a + g + rg

    def build_docs_dict(self) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for name, meta in self._params.items():
            result[name] = [meta.doc_type] + list(meta.doc_desc)
        return result

    def get_defaults_slots(self) -> List[str]:
        return [
            name
            for name, meta in self._params.items()
            if meta.in_defaults
        ]

    def build_defaults_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for name, meta in self._params.items():
            if meta.in_defaults:
                result[name] = meta.default_value
        return result

    def param_names_for_signature(self, names: List[str]) -> List[Tuple[str, Any]]:
        result = []
        for name in names:
            meta = self._params.get(name)
            if meta is None:
                result.append((name, None))
            else:
                result.append((name, meta.default_value))
        return result


_colref_type = "str or int or Series or array-like"
_colref_desc = (
    "Either a name of a column in `data_frame`, or a pandas Series or array_like object."
)
_colref_list_type = "list of str or int, or Series or array-like"
_colref_list_desc = (
    "Either names of columns in `data_frame`, or pandas Series, or array_like objects"
)


def create_registry() -> ParamRegistry:
    r = ParamRegistry()

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

    for axis_name, axis_desc in [
        ("x", "Values from this column or array_like are used to position marks along the x axis in cartesian coordinates."),
        ("y", "Values from this column or array_like are used to position marks along the y axis in cartesian coordinates."),
        ("z", "Values from this column or array_like are used to position marks along the z axis in cartesian coordinates."),
    ]:
        r.add(ParamMeta(
            name=axis_name,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, axis_desc],
        ))

    r.add(ParamMeta(
        name="x_start",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[
            _colref_desc,
            "(required)",
            "Values from this column or array_like are used to position marks along the x axis in cartesian coordinates.",
        ],
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
    ))

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
        ))

    for axis_name, axis_desc in [
        ("r", "Values from this column or array_like are used to position marks along the radial axis in polar coordinates."),
        ("theta", "Values from this column or array_like are used to position marks along the angular axis in polar coordinates."),
    ]:
        r.add(ParamMeta(
            name=axis_name,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, axis_desc],
        ))

    r.add(ParamMeta(
        name="values",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to set values associated to sectors."],
    ))
    r.add(ParamMeta(
        name="parents",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used as parents in sunburst and treemap charts."],
    ))
    r.add(ParamMeta(
        name="ids",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to set ids of sectors"],
    ))
    r.add(ParamMeta(
        name="wide_cross",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, ""],
    ))

    r.add(ParamMeta(
        name="path",
        category=ParamCategory.DATA_ARRAY,
        doc_type=_colref_list_type,
        doc_desc=[
            _colref_list_desc,
            "List of columns names or columns of a rectangular dataframe defining the hierarchy of sectors, from root to leaves.",
            "An error is raised if path AND ids or parents is passed",
        ],
    ))

    r.add(ParamMeta(
        name="lat",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to position marks according to latitude on a map."],
    ))
    r.add(ParamMeta(
        name="lon",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to position marks according to longitude on a map."],
    ))
    r.add(ParamMeta(
        name="locations",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are to be interpreted according to `locationmode` and mapped to longitude/latitude."],
    ))
    r.add(ParamMeta(
        name="base",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to position the base of the bar."],
    ))

    r.add(ParamMeta(
        name="dimensions",
        category=ParamCategory.DATA_ARRAY,
        doc_type=_colref_list_type,
        doc_desc=[_colref_list_desc, "Values from these columns are used for multidimensional visualization."],
    ))
    r.add(ParamMeta(
        name="dimensions_max_cardinality",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="int (default 50)",
        doc_desc=[
            "When `dimensions` is `None` and `data_frame` is provided, "
            "columns with more than this number of unique values are excluded from the output.",
            "Not used when `dimensions` is passed.",
        ],
        default_value=50,
    ))

    for err_name, err_axis, err_desc_suffix in [
        ("error_x", "x", "x-axis"),
        ("error_x_minus", "x", "x-axis in the negative direction"),
        ("error_y", "y", "y-axis"),
        ("error_y_minus", "y", "y-axis in the negative direction"),
        ("error_z", "z", "z-axis"),
        ("error_z_minus", "z", "z-axis in the negative direction"),
    ]:
        minus = "_minus" in err_name
        desc = f"Values from this column or array_like are used to size {err_desc_suffix} error bars."
        if minus:
            desc += f" Ignored if `error_{err_axis}` is `None`."
        else:
            desc += f" If `error_{err_axis}_minus` is `None`, error bars will be symmetrical, otherwise `{err_name}` is used for the positive direction only."
        r.add(ParamMeta(
            name=err_name,
            category=ParamCategory.DATA_COLUMN,
            doc_type=_colref_type,
            doc_desc=[_colref_desc, desc],
        ))

    r.add(ParamMeta(
        name="color",
        category=ParamCategory.MAPPING,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to assign color to marks."],
        trace_attr=None,
        sequence_name="color_discrete_sequence",
        map_name="color_discrete_map",
    ))
    r.add(ParamMeta(
        name="symbol",
        category=ParamCategory.MAPPING,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to assign symbols to marks."],
        trace_attr="marker.symbol",
        sequence_name="symbol_sequence",
        map_name="symbol_map",
    ))
    r.add(ParamMeta(
        name="line_dash",
        category=ParamCategory.MAPPING,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to assign dash-patterns to lines."],
        trace_attr="line.dash",
        sequence_name="line_dash_sequence",
        map_name="line_dash_map",
    ))
    r.add(ParamMeta(
        name="pattern_shape",
        category=ParamCategory.MAPPING,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to assign pattern shapes to marks."],
        trace_attr=None,
        sequence_name="pattern_shape_sequence",
        map_name="pattern_shape_map",
    ))

    r.add(ParamMeta(
        name="size",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to assign mark sizes."],
    ))
    r.add(ParamMeta(
        name="radius",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="int (default is 30)",
        doc_desc=["Sets the radius of influence of each point."],
        default_value=30,
    ))
    r.add(ParamMeta(
        name="hover_name",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like appear in bold in the hover tooltip."],
    ))
    r.add(ParamMeta(
        name="hover_data",
        category=ParamCategory.DATA_ARRAY,
        doc_type="str, or list of str or int, or Series or array-like, or dict",
        doc_desc=[
            "Either a name or list of names of columns in `data_frame`, or pandas Series,",
            "or array_like objects",
            "or a dict with column names as keys, with values True (for default formatting)",
            "False (in order to remove this column from hover information),",
            "or a formatting string, for example ':.3f' or '|%a'",
            "or list-like data to appear in the hover tooltip",
            "or tuples with a bool or formatting string as first element,",
            "and list-like data to appear in hover as second element",
            "Values from these columns appear as extra data in the hover tooltip.",
        ],
    ))
    r.add(ParamMeta(
        name="custom_data",
        category=ParamCategory.DATA_ARRAY,
        doc_type="str, or list of str or int, or Series or array-like",
        doc_desc=[
            "Either name or list of names of columns in `data_frame`, or pandas Series, or array_like objects",
            "Values from these columns are extra data, to be used in widgets or Dash callbacks for example. This data is not user-visible but is included in events emitted by the figure (lasso selection etc.)",
        ],
    ))
    r.add(ParamMeta(
        name="text",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like appear in the figure as text labels."],
    ))
    r.add(ParamMeta(
        name="names",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used as labels for sectors."],
    ))
    r.add(ParamMeta(
        name="wide_variable",
        category=ParamCategory.DATA_ARRAY,
        doc_type=_colref_list_type,
        doc_desc=[_colref_list_desc],
    ))

    r.add(ParamMeta(
        name="locationmode",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "One of 'ISO-3', 'USA-states', or 'country names'",
            "Determines the set of locations used to match entries in `locations` to regions on the map.",
        ],
    ))

    r.add(ParamMeta(
        name="facet_row",
        category=ParamCategory.GROUPING,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to assign marks to facetted subplots in the vertical direction."],
    ))
    r.add(ParamMeta(
        name="facet_col",
        category=ParamCategory.GROUPING,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to assign marks to facetted subplots in the horizontal direction."],
    ))
    r.add(ParamMeta(
        name="facet_col_wrap",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="int",
        doc_desc=[
            "Maximum number of facet columns.",
            "Wraps the column variable at this width, so that the column facets span multiple rows.",
            "Ignored if 0, and forced to 0 if `facet_row` or a `marginal` is set.",
        ],
        default_value=0,
    ))
    r.add(ParamMeta(
        name="facet_row_spacing",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="float between 0 and 1",
        doc_desc=["Spacing between facet rows, in paper units. Default is 0.03 or 0.07 when facet_col_wrap is used."],
    ))
    r.add(ParamMeta(
        name="facet_col_spacing",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="float between 0 and 1",
        doc_desc=["Spacing between facet columns, in paper units Default is 0.02."],
    ))
    r.add(ParamMeta(
        name="animation_frame",
        category=ParamCategory.GROUPING,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to assign marks to animation frames."],
    ))
    r.add(ParamMeta(
        name="animation_group",
        category=ParamCategory.DATA_COLUMN,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to provide object-constancy across animation frames: rows with matching `animation_group`s will be treated as if they describe the same object in each frame."],
    ))
    r.add(ParamMeta(
        name="line_group",
        category=ParamCategory.GROUPING,
        doc_type=_colref_type,
        doc_desc=[_colref_desc, "Values from this column or array_like are used to group rows of `data_frame` into lines."],
    ))

    r.add(ParamMeta(
        name="symbol_sequence",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="list of str",
        doc_desc=[
            "Strings should define valid plotly.js symbols.",
            "When `symbol` is set, values in that column are assigned symbols by cycling through `symbol_sequence` in the order described in `category_orders`, unless the value of `symbol` is a key in `symbol_map`.",
        ],
        in_defaults=True,
        default_value=None,
    ))
    r.add(ParamMeta(
        name="symbol_map",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="dict with str keys and str values (default `{}`)",
        doc_desc=[
            "String values should define plotly.js symbols",
            "Used to override `symbol_sequence` to assign a specific symbols to marks corresponding with specific values.",
            "Keys in `symbol_map` should be values in the column denoted by `symbol`.",
            "Alternatively, if the values of `symbol` are valid symbol names, the string `'identity'` may be passed to cause them to be used directly.",
        ],
        in_defaults=True,
        default_value={},
    ))
    r.add(ParamMeta(
        name="line_dash_map",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="dict with str keys and str values (default `{}`)",
        doc_desc=[
            "Strings values define plotly.js dash-patterns.",
            "Used to override `line_dash_sequences` to assign a specific dash-patterns to lines corresponding with specific values.",
            "Keys in `line_dash_map` should be values in the column denoted by `line_dash`.",
            "Alternatively, if the values of `line_dash` are valid line-dash names, the string `'identity'` may be passed to cause them to be used directly.",
        ],
        in_defaults=True,
        default_value={},
    ))
    r.add(ParamMeta(
        name="line_dash_sequence",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="list of str",
        doc_desc=[
            "Strings should define valid plotly.js dash-patterns.",
            "When `line_dash` is set, values in that column are assigned dash-patterns by cycling through `line_dash_sequence` in the order described in `category_orders`, unless the value of `line_dash` is a key in `line_dash_map`.",
        ],
        in_defaults=True,
        default_value=None,
    ))
    r.add(ParamMeta(
        name="pattern_shape_map",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="dict with str keys and str values (default `{}`)",
        doc_desc=[
            "Strings values define plotly.js patterns-shapes.",
            "Used to override `pattern_shape_sequences` to assign a specific patterns-shapes to lines corresponding with specific values.",
            "Keys in `pattern_shape_map` should be values in the column denoted by `pattern_shape`.",
            "Alternatively, if the values of `pattern_shape` are valid patterns-shapes names, the string `'identity'` may be passed to cause them to be used directly.",
        ],
        in_defaults=True,
        default_value={},
    ))
    r.add(ParamMeta(
        name="pattern_shape_sequence",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="list of str",
        doc_desc=[
            "Strings should define valid plotly.js patterns-shapes.",
            "When `pattern_shape` is set, values in that column are assigned patterns-shapes by cycling through `pattern_shape_sequence` in the order described in `category_orders`, unless the value of `pattern_shape` is a key in `pattern_shape_map`.",
        ],
        in_defaults=True,
        default_value=None,
    ))
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
    ))
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
    ))
    r.add(ParamMeta(
        name="color_continuous_midpoint",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="number (default `None`)",
        doc_desc=[
            "If set, computes the bounds of the continuous color scale to have the desired midpoint.",
            "Setting this value is recommended when using `plotly.express.colors.diverging` color scales as the inputs to `color_continuous_scale`.",
        ],
    ))
    r.add(ParamMeta(
        name="size_max",
        category=ParamCategory.MAPPING_CONFIG,
        doc_type="int (default `20`)",
        doc_desc=["Set the maximum mark size when using `size`."],
        in_defaults=True,
        default_value=20,
    ))

    r.add(ParamMeta(
        name="opacity",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="float",
        doc_desc=["Value between 0 and 1. Sets the opacity for markers."],
    ))
    r.add(ParamMeta(
        name="markers",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean (default `False`)",
        doc_desc=["If `True`, markers are shown on lines."],
        default_value=False,
    ))
    r.add(ParamMeta(
        name="lines",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean (default `True`)",
        doc_desc=["If `False`, lines are not drawn (forced to `True` if `markers` is `False`)."],
        default_value=True,
    ))

    for log_axis in ["log_x", "log_y", "log_z", "log_r"]:
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
        ))

    for range_axis in ["range_x", "range_y", "range_z", "range_color", "range_r", "range_theta"]:
        axis_letter = range_axis.split("_")[1]
        if axis_letter == "color":
            desc = "If provided, overrides auto-scaling on the continuous color scale."
        elif axis_letter == "r":
            desc = "If provided, overrides auto-scaling on the radial axis in polar coordinates."
        elif axis_letter == "theta":
            desc = "If provided, overrides auto-scaling on the angular axis in polar coordinates."
        else:
            desc = f"If provided, overrides auto-scaling on the {axis_letter}-axis in cartesian coordinates."
        r.add(ParamMeta(
            name=range_axis,
            category=ParamCategory.LAYOUT_CONFIG,
            doc_type="list of two numbers",
            doc_desc=[desc],
        ))

    r.add(ParamMeta(
        name="title",
        category=ParamCategory.LABEL,
        doc_type="str",
        doc_desc=["The figure title."],
    ))
    r.add(ParamMeta(
        name="subtitle",
        category=ParamCategory.LABEL,
        doc_type="str",
        doc_desc=["The figure subtitle."],
    ))
    r.add(ParamMeta(
        name="template",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str or dict or plotly.graph_objects.layout.Template instance",
        doc_desc=["The figure template name (must be a key in plotly.io.templates) or definition."],
        in_defaults=True,
        default_value=None,
    ))
    r.add(ParamMeta(
        name="width",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="int (default `None`)",
        doc_desc=["The figure width in pixels."],
        in_defaults=True,
        default_value=None,
    ))
    r.add(ParamMeta(
        name="height",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="int (default `None`)",
        doc_desc=["The figure height in pixels."],
        in_defaults=True,
        default_value=None,
    ))
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

    r.add(ParamMeta(
        name="marginal",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "One of `'rug'`, `'box'`, `'violin'`, or `'histogram'`.",
            "If set, a subplot is drawn alongside the main plot, visualizing the distribution.",
        ],
    ))
    r.add(ParamMeta(
        name="marginal_x",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "One of `'rug'`, `'box'`, `'violin'`, or `'histogram'`.",
            "If set, a horizontal subplot is drawn above the main plot, visualizing the x-distribution.",
        ],
    ))
    r.add(ParamMeta(
        name="marginal_y",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "One of `'rug'`, `'box'`, `'violin'`, or `'histogram'`.",
            "If set, a vertical subplot is drawn to the right of the main plot, visualizing the y-distribution.",
        ],
    ))

    r.add(ParamMeta(
        name="trendline",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "One of `'ols'`, `'lowess'`, `'rolling'`, `'expanding'` or `'ewm'`.",
            "If `'ols'`, an Ordinary Least Squares regression line will be drawn for each discrete-color/symbol group.",
            "If `'lowess`', a Locally Weighted Scatterplot Smoothing line will be drawn for each discrete-color/symbol group.",
            "If `'rolling`', a Rolling (e.g. rolling average, rolling median) line will be drawn for each discrete-color/symbol group.",
            "If `'expanding`', an Expanding (e.g. expanding average, expanding sum) line will be drawn for each discrete-color/symbol group.",
            "If `'ewm`', an Exponentially Weighted Moment (e.g. exponentially-weighted moving average) line will be drawn for each discrete-color/symbol group.",
            "See the docstrings for the functions in `plotly.express.trendline_functions` for more details on these functions and how",
            "to configure them with the `trendline_options` argument.",
        ],
    ))
    r.add(ParamMeta(
        name="trendline_options",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="dict",
        doc_desc=[
            "Options passed as the first argument to the function from `plotly.express.trendline_functions` ",
            "named in the `trendline` argument.",
        ],
    ))
    r.add(ParamMeta(
        name="trendline_color_override",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "Valid CSS color.",
            "If provided, and if `trendline` is set, all trendlines will be drawn in this color rather than in the same color as the traces from which they draw their inputs.",
        ],
    ))
    r.add(ParamMeta(
        name="trendline_scope",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (one of `'trace'` or `'overall'`, default `'trace'`)",
        doc_desc=[
            "If `'trace'`, then one trendline is drawn per trace (i.e. per color, symbol, facet, animation frame etc) and if `'overall'` then one trendline is computed for the entire dataset, and replicated across all facets.",
        ],
        default_value="trace",
    ))

    r.add(ParamMeta(
        name="render_mode",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "One of `'auto'`, `'svg'` or `'webgl'`, default `'auto'`",
            "Controls the browser API used to draw marks.",
            "`'svg'` is appropriate for figures of less than 1000 data points, and will allow for fully-vectorized output.",
            "`'webgl'` is likely necessary for acceptable performance above 1000 points but rasterizes part of the output. ",
            "`'auto'` uses heuristics to choose the mode.",
        ],
        default_value="auto",
    ))

    r.add(ParamMeta(
        name="direction",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str",
        doc_desc=[
            "One of '`counterclockwise'` or `'clockwise'`. Default is `'clockwise'`",
            "Sets the direction in which increasing values of the angular axis are drawn.",
        ],
    ))
    r.add(ParamMeta(
        name="start_angle",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="int (default `90`)",
        doc_desc=["Sets start angle for the angular axis, with 0 being due east and 90 being due north."],
        default_value=90,
    ))
    r.add(ParamMeta(
        name="line_close",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean (default `False`)",
        doc_desc=["If `True`, an extra line segment is drawn between the first and last point."],
        default_value=False,
    ))
    r.add(ParamMeta(
        name="line_shape",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `'linear'`)",
        doc_desc=["One of `'linear'`, `'spline'`, `'hv'`, `'vh'`, `'hvh'`, or `'vhv'`"],
    ))
    r.add(ParamMeta(
        name="fitbounds",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str (default `False`).",
        doc_desc=["One of `False`, `locations` or `geojson`."],
    ))
    r.add(ParamMeta(
        name="basemap_visible",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="bool",
        doc_desc=["Force the basemap visibility."],
    ))
    r.add(ParamMeta(
        name="scope",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str (default `'world'`).",
        doc_desc=[
            "One of `'world'`, `'usa'`, `'europe'`, `'asia'`, `'africa'`, `'north america'`, or `'south america'`"
            "Default is `'world'` unless `projection` is set to `'albers usa'`, which forces `'usa'`.",
        ],
    ))
    r.add(ParamMeta(
        name="projection",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str ",
        doc_desc=[
            "One of `'equirectangular'`, `'mercator'`, `'orthographic'`, `'natural earth'`, `'kavrayskiy7'`, `'miller'`, `'robinson'`, `'eckert4'`, `'azimuthal equal area'`, `'azimuthal equidistant'`, `'conic equal area'`, `'conic conformal'`, `'conic equidistant'`, `'gnomonic'`, `'stereographic'`, `'mollweide'`, `'hammer'`, `'transverse mercator'`, `'albers usa'`, `'winkel tripel'`, `'aitoff'`, or `'sinusoidal'`"
            "Default depends on `scope`.",
        ],
    ))
    r.add(ParamMeta(
        name="center",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="dict",
        doc_desc=["Dict keys are `'lat'` and `'lon'`", "Sets the center point of the map."],
    ))
    r.add(ParamMeta(
        name="map_style",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str (default `'basic'`)",
        doc_desc=[
            "Identifier of base map style.",
            "Allowed values are `'basic'`, `'carto-darkmatter'`, `'carto-darkmatter-nolabels'`, `'carto-positron'`, `'carto-positron-nolabels'`, `'carto-voyager'`, `'carto-voyager-nolabels'`, `'dark'`, `'light'`, `'open-street-map'`, `'outdoors'`, `'satellite'`, `'satellite-streets'`, `'streets'`, `'white-bg'`.",
        ],
    ))
    r.add(ParamMeta(
        name="mapbox_style",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str (default `'basic'`, needs Mapbox API token)",
        doc_desc=[
            "Identifier of base map style, some of which require a Mapbox or Stadia Maps API token to be set using `plotly.express.set_mapbox_access_token()`.",
            "Allowed values which do not require a token are `'open-street-map'`, `'white-bg'`, `'carto-positron'`, `'carto-darkmatter'`.",
            "Allowed values which require a Mapbox API token are `'basic'`, `'streets'`, `'outdoors'`, `'light'`, `'dark'`, `'satellite'`, `'satellite-streets'`.",
            "Allowed values which require a Stadia Maps API token are `'stamen-terrain'`, `'stamen-toner'`, `'stamen-watercolor'`.",
        ],
    ))
    r.add(ParamMeta(
        name="zoom",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="int (default `8`)",
        doc_desc=["Between 0 and 20.", "Sets map zoom level."],
        default_value=8,
    ))
    r.add(ParamMeta(
        name="orientation",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str, one of `'h'` for horizontal or `'v'` for vertical. ",
        doc_desc=[
            "(default `'v'` if `x` and `y` are provided and both continuous or both categorical, ",
            "otherwise `'v'`(`'h'`) if `x`(`y`) is categorical and `y`(`x`) is continuous, ",
            "otherwise `'v'`(`'h'`) if only `x`(`y`) is provided) ",
        ],
    ))
    r.add(ParamMeta(
        name="points",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str or boolean (default `'outliers'`)",
        doc_desc=[
            "One of `'outliers'`, `'suspectedoutliers'`, `'all'`, or `False`.",
            "If `'outliers'`, only the sample points lying outside the whiskers are shown.",
            "If `'suspectedoutliers'`, all outlier points are shown and those less than 4*Q1-3*Q3 or greater than 4*Q3-3*Q1 are highlighted with the marker's `'outliercolor'`.",
            "If `'outliers'`, only the sample points lying outside the whiskers are shown.",
            "If `'all'`, all sample points are shown.",
            "If `False`, no sample points are shown and the whiskers extend to the full range of the sample.",
        ],
    ))
    r.add(ParamMeta(
        name="box",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean (default `False`)",
        doc_desc=["If `True`, boxes are drawn inside the violins."],
        default_value=False,
    ))
    r.add(ParamMeta(
        name="notched",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean (default `False`)",
        doc_desc=["If `True`, boxes are drawn with notches."],
        default_value=False,
    ))
    r.add(ParamMeta(
        name="geojson",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="GeoJSON-formatted dict",
        doc_desc=[
            "Must contain a Polygon feature collection, with IDs, which are references from `locations`.",
        ],
    ))
    r.add(ParamMeta(
        name="featureidkey",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default: `'id'`)",
        doc_desc=[
            "Path to field in GeoJSON feature object with which to match the values passed in to `locations`."
            "The most common alternative to the default is of the form `'properties.<key>`.",
        ],
        default_value="id",
    ))
    r.add(ParamMeta(
        name="cumulative",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="boolean (default `False`)",
        doc_desc=["If `True`, histogram values are cumulative."],
        default_value=False,
    ))
    r.add(ParamMeta(
        name="nbins",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="int",
        doc_desc=["Positive integer.", "Sets the number of bins."],
    ))
    r.add(ParamMeta(
        name="nbinsx",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="int",
        doc_desc=["Positive integer.", "Sets the number of bins along the x axis."],
    ))
    r.add(ParamMeta(
        name="nbinsy",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="int",
        doc_desc=["Positive integer.", "Sets the number of bins along the y axis."],
    ))
    r.add(ParamMeta(
        name="branchvalues",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str",
        doc_desc=[
            "'total' or 'remainder'",
            "Determines how the items in `values` are summed. When"
            "set to 'total', items in `values` are taken to be value"
            "of all its descendants. When set to 'remainder', items"
            "in `values` corresponding to the root and the branches"
            ":sectors are taken to be the extra part not part of the"
            "sum of the values at their leaves.",
        ],
    ))
    r.add(ParamMeta(
        name="maxdepth",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="int",
        doc_desc=[
            "Positive integer",
            "Sets the number of rendered sectors from any given `level`. Set `maxdepth` to -1 to render all the"
            "levels in the hierarchy.",
        ],
    ))
    r.add(ParamMeta(
        name="ecdfnorm",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="string or `None` (default `'probability'`)",
        doc_desc=[
            "One of `'probability'` or `'percent'`",
            "If `None`, values will be raw counts or sums.",
            "If `'probability', values will be probabilities normalized from 0 to 1.",
            "If `'percent', values will be percentages normalized from 0 to 100.",
        ],
        default_value="probability",
    ))
    r.add(ParamMeta(
        name="ecdfmode",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="string (default `'standard'`)",
        doc_desc=[
            "One of `'standard'`, `'complementary'` or `'reversed'`",
            "If `'standard'`, the ECDF is plotted such that values represent data at or below the point.",
            "If `'complementary'`, the CCDF is plotted such that values represent data above the point.",
            "If `'reversed'`, a variant of the CCDF is plotted such that values represent data at or above the point.",
        ],
        default_value="standard",
    ))
    r.add(ParamMeta(
        name="text_auto",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="bool or string (default `False`)",
        doc_desc=[
            "If `True` or a string, the x or y or z values will be displayed as text, depending on the orientation",
            "A string like `'.2f'` will be interpreted as a `texttemplate` numeric formatting directive.",
        ],
        default_value=False,
    ))

    r.add(ParamMeta(
        name="barmode",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str (default `'relative'`)",
        doc_desc=[
            "One of `'group'`, `'overlay'` or `'relative'`",
            "In `'relative'` mode, bars are stacked above zero for positive values and below zero for negative values.",
            "In `'overlay'` mode, bars are drawn on top of one another.",
            "In `'group'` mode, bars are placed beside each other.",
        ],
        default_value="relative",
    ))
    r.add(ParamMeta(
        name="barnorm",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `None`)",
        doc_desc=[
            "One of `'fraction'` or `'percent'`",
            "If set, bars are normalized with the fraction or percent of the total.",
        ],
    ))
    r.add(ParamMeta(
        name="histfunc",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `'count'`)",
        doc_desc=[
            "One of `'count'`, `'sum'`, `'avg'`, `'min'`, or `'max'`",
            "The aggregate function to use when binning data.",
        ],
    ))
    r.add(ParamMeta(
        name="histnorm",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `None`)",
        doc_desc=[
            "One of `'percent'`, `'probability'`, `'density'`, or `'probability density'`",
            "If set, the histogram data is normalized accordingly.",
        ],
    ))
    r.add(ParamMeta(
        name="groupnorm",
        category=ParamCategory.TRACE_CONFIG,
        doc_type="str (default `None`)",
        doc_desc=[
            "One of `'fraction'` or `'percent'`",
            "Only relevant when `stackgroup` is used (as in `px.area`).",
            "If set, the stacked areas are normalized to the fraction or percent of the total.",
        ],
    ))
    r.add(ParamMeta(
        name="stripmode",
        category=ParamCategory.LAYOUT_CONFIG,
        doc_type="str (default `'overlay'`)",
        doc_desc=[
            "One of `'overlay'` or `'group'`",
            "In `'overlay'` mode, strips are on drawn top of one another.",
            "In `'group'` mode, strips are placed beside each other.",
        ],
        default_value="overlay",
    ))

    return r


PARAMS: ParamRegistry = create_registry()

__all__ = [
    "ParamCategory",
    "ParamMeta",
    "ParamRegistry",
    "PARAMS",
]

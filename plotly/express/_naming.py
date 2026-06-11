import plotly.graph_objs as go
from collections import OrderedDict
from ._special_inputs import IdentityMap


def get_label(args, column):
    try:
        return args["labels"][column]
    except Exception:
        return column


def one_group(x):
    return ""


class NamingResult:
    __slots__ = [
        "name",
        "legendgroup",
        "showlegend",
        "offsetgroup",
        "alignmentgroup",
        "frame_name",
        "mapping_labels",
        "legend_title_labels",
    ]

    def __init__(
        self,
        name,
        legendgroup,
        showlegend,
        offsetgroup,
        alignmentgroup,
        frame_name,
        mapping_labels,
        legend_title_labels,
    ):
        self.name = name
        self.legendgroup = legendgroup
        self.showlegend = showlegend
        self.offsetgroup = offsetgroup
        self.alignmentgroup = alignmentgroup
        self.frame_name = frame_name
        self.mapping_labels = mapping_labels
        self.legend_title_labels = legend_title_labels

    def apply_to_trace(self, trace):
        trace.name = self.name
        if self.legendgroup is not None:
            trace.update(
                legendgroup=self.legendgroup,
                showlegend=self.showlegend,
            )
        if self.alignmentgroup is not None:
            trace.update(
                alignmentgroup=self.alignmentgroup,
                offsetgroup=self.offsetgroup,
            )


class NamingContext:
    _LEGENDLESS_CONSTRUCTORS = {
        go.Parcats,
        go.Parcoords,
        go.Choropleth,
        go.Choroplethmap,
        go.Choroplethmapbox,
        go.Densitymap,
        go.Densitymapbox,
        go.Histogram2d,
        go.Sunburst,
        go.Treemap,
        go.Icicle,
    }

    _ALIGNED_CONSTRUCTORS = {go.Bar, go.Box, go.Violin, go.Histogram}

    def __init__(self, args, grouped_mappings, grouper, orders, layout_patch):
        self.args = args
        self.grouped_mappings = grouped_mappings
        self.grouper = grouper
        self.orders = orders
        self.layout_patch = layout_patch
        self._trace_names_by_frame = {}
        self._last_legend_title_labels = None

    def _build_labels(self, group_name):
        mapping_labels = OrderedDict()
        legend_title_labels = OrderedDict()
        frame_name = ""
        for col, val, m in zip(self.grouper, group_name, self.grouped_mappings):
            if not callable(col):
                key = get_label(self.args, col)
                if not isinstance(m.val_map, IdentityMap):
                    mapping_labels[key] = str(val)
                    if m.show_in_trace_name:
                        legend_title_labels[key] = str(val)
                if m.variable == "animation_frame":
                    frame_name = val
        return mapping_labels, legend_title_labels, frame_name

    def _get_or_create_frame_names(self, frame_name):
        if frame_name not in self._trace_names_by_frame:
            self._trace_names_by_frame[frame_name] = set()
        return self._trace_names_by_frame[frame_name]

    def _compute_legend_fields(self, trace_name, trace_names, constructor):
        if constructor in self._LEGENDLESS_CONSTRUCTORS:
            return None, None
        return trace_name, (trace_name != "" and trace_name not in trace_names)

    def _compute_alignment_fields(self, trace_name, constructor):
        if constructor in self._ALIGNED_CONSTRUCTORS:
            barmode = self.layout_patch.get("barmode")
            if barmode == "group" or barmode is None:
                return trace_name, True
        return None, None

    def get_base_naming(self, group_name, trace_spec):
        mapping_labels, legend_title_labels, frame_name = self._build_labels(
            group_name
        )
        trace_name = ", ".join(legend_title_labels.values())
        trace_names = self._get_or_create_frame_names(frame_name)

        constructor = trace_spec.constructor
        legendgroup, showlegend = self._compute_legend_fields(
            trace_name, trace_names, constructor
        )
        offsetgroup, alignmentgroup = self._compute_alignment_fields(
            trace_name, constructor
        )

        trace_names.add(trace_name)
        self._last_legend_title_labels = legend_title_labels

        return NamingResult(
            name=trace_name,
            legendgroup=legendgroup,
            showlegend=showlegend,
            offsetgroup=offsetgroup,
            alignmentgroup=alignmentgroup,
            frame_name=frame_name,
            mapping_labels=mapping_labels,
            legend_title_labels=legend_title_labels,
        )

    def get_trendline_naming(self, base):
        trace_names = self._get_or_create_frame_names(base.frame_name)
        trendline_name = (
            base.name + " Trendline" if base.name else "Trendline"
        )

        return NamingResult(
            name=trendline_name,
            legendgroup=base.name if base.name else None,
            showlegend=trendline_name not in trace_names,
            offsetgroup=None,
            alignmentgroup=None,
            frame_name=base.frame_name,
            mapping_labels=OrderedDict(),
            legend_title_labels=base.legend_title_labels,
        )

    def get_overall_trendline_naming(self):
        return NamingResult(
            name="Overall Trendline",
            legendgroup="Overall Trendline",
            showlegend=False,
            offsetgroup=None,
            alignmentgroup=None,
            frame_name="",
            mapping_labels=OrderedDict(),
            legend_title_labels=OrderedDict(),
        )

    def get_legend_title(self):
        if self._last_legend_title_labels:
            return ", ".join(self._last_legend_title_labels)
        return None

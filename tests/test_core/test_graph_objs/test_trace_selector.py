import re
import warnings
from unittest import TestCase

import plotly.graph_objects as go
from plotly._trace_selector import TraceSelector
from plotly.subplots import make_subplots
from ...utils import TestCaseNoTemplate


class TestTraceSelectorInit(TestCase):
    def test_empty_selector(self):
        sel = TraceSelector()
        assert sel.type is None
        assert sel.row is None
        assert sel.col is None
        assert sel.secondary_y is None
        assert sel.legendgroup is None
        assert sel.name is None
        assert sel.customdata is None
        assert sel.meta is None
        assert sel.selector is None
        assert not sel.uses_subplot

    def test_type_string(self):
        sel = TraceSelector(type="scatter")
        assert sel._types == {"scatter"}

    def test_type_list(self):
        sel = TraceSelector(type=["scatter", "bar"])
        assert sel._types == {"scatter", "bar"}

    def test_type_case_insensitive(self):
        sel = TraceSelector(type="Scatter")
        assert sel._types == {"scatter"}

    def test_name_string_compiled_as_full_match(self):
        sel = TraceSelector(name="foo")
        assert sel._name_pattern.pattern == "^foo$"

    def test_name_pattern_preserved(self):
        pat = re.compile("series_\\d+")
        sel = TraceSelector(name=pat)
        assert sel._name_pattern is pat

    def test_legendgroup_string(self):
        sel = TraceSelector(legendgroup="g1")
        assert sel._legendgroup_pattern.pattern == "^g1$"

    def test_legendgroup_pattern(self):
        pat = re.compile("g\\d+")
        sel = TraceSelector(legendgroup=pat)
        assert sel._legendgroup_pattern is pat

    def test_customdata_callable(self):
        fn = lambda x: x is not None
        sel = TraceSelector(customdata=fn)
        assert sel._customdata_mode == "callable"

    def test_customdata_exact(self):
        sel = TraceSelector(customdata=[1, 2])
        assert sel._customdata_mode == "exact"

    def test_customdata_dict(self):
        sel = TraceSelector(customdata={"0": "APAC"})
        assert sel._customdata_mode == "dict"

    def test_meta_callable(self):
        fn = lambda x: True
        sel = TraceSelector(meta=fn)
        assert sel._meta_mode == "callable"

    def test_meta_exact(self):
        sel = TraceSelector(meta="experiment_a")
        assert sel._meta_mode == "exact"

    def test_meta_dict(self):
        sel = TraceSelector(meta={"source": "train"})
        assert sel._meta_mode == "dict"

    def test_uses_subplot_row(self):
        sel = TraceSelector(row=1)
        assert sel.uses_subplot

    def test_uses_subplot_col(self):
        sel = TraceSelector(col=2)
        assert sel.uses_subplot

    def test_uses_subplot_secondary_y(self):
        sel = TraceSelector(secondary_y=True)
        assert sel.uses_subplot

    def test_uses_subplot_none(self):
        sel = TraceSelector(type="scatter")
        assert not sel.uses_subplot

    def test_repr(self):
        sel = TraceSelector(type="scatter", row=1)
        r = repr(sel)
        assert "type='scatter'" in r
        assert "row=1" in r


class TestTraceSelectorMatches(TestCase):
    def setUp(self):
        self.fig = go.Figure()
        self.fig.add_scatter(
            y=[1, 2, 3],
            name="series_a",
            legendgroup="g1",
            customdata=[1, 2, 3],
            meta="exp_a",
        )
        self.fig.add_scatter(
            y=[4, 5, 6],
            name="series_b",
            legendgroup="g1",
            meta="exp_b",
        )
        self.fig.add_bar(y=[3, 2, 1], name="bar_1", legendgroup="g2")
        self.trace_scatter_a = self.fig.data[0]
        self.trace_scatter_b = self.fig.data[1]
        self.trace_bar = self.fig.data[2]

    def test_match_type(self):
        sel = TraceSelector(type="scatter")
        assert sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_scatter_b)
        assert not sel.matches(self.trace_bar)

    def test_match_type_list(self):
        sel = TraceSelector(type=["scatter", "bar"])
        assert sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_bar)

    def test_match_name_exact(self):
        sel = TraceSelector(name="series_a")
        assert sel.matches(self.trace_scatter_a)
        assert not sel.matches(self.trace_scatter_b)

    def test_match_name_regex(self):
        sel = TraceSelector(name=re.compile("series_"))
        assert sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_scatter_b)
        assert not sel.matches(self.trace_bar)

    def test_match_legendgroup_exact(self):
        sel = TraceSelector(legendgroup="g1")
        assert sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_scatter_b)
        assert not sel.matches(self.trace_bar)

    def test_match_legendgroup_regex(self):
        sel = TraceSelector(legendgroup=re.compile("g"))
        assert sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_bar)

    def test_match_customdata_predicate(self):
        sel = TraceSelector(customdata=lambda cd: cd is not None)
        assert sel.matches(self.trace_scatter_a)
        assert not sel.matches(self.trace_scatter_b)

    def test_match_customdata_exact(self):
        sel = TraceSelector(customdata=[1, 2, 3])
        assert sel.matches(self.trace_scatter_a)
        assert not sel.matches(self.trace_scatter_b)

    def test_match_customdata_predicate_exception(self):
        sel = TraceSelector(customdata=lambda cd: len(cd) > 0)
        assert not sel.matches(self.trace_scatter_b)

    def test_match_meta_exact(self):
        sel = TraceSelector(meta="exp_a")
        assert sel.matches(self.trace_scatter_a)
        assert not sel.matches(self.trace_scatter_b)

    def test_match_meta_callable(self):
        sel = TraceSelector(meta=lambda m: m is not None)
        assert sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_scatter_b)
        assert not sel.matches(self.trace_bar)

    def test_match_backward_compat_selector_dict(self):
        sel = TraceSelector(selector=dict(legendgroup="g2"))
        assert not sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_bar)

    def test_match_backward_compat_selector_fn(self):
        sel = TraceSelector(selector=lambda t: t.type == "bar")
        assert not sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_bar)

    def test_match_combined_and(self):
        sel = TraceSelector(type="scatter", legendgroup="g1")
        assert sel.matches(self.trace_scatter_a)
        assert sel.matches(self.trace_scatter_b)
        sel2 = TraceSelector(type="scatter", legendgroup="g2")
        assert not sel2.matches(self.trace_scatter_a)

    def test_match_none_name(self):
        sel = TraceSelector(name="bar_1")
        assert not sel.matches(self.trace_scatter_a)

    def test_match_none_legendgroup(self):
        sel = TraceSelector(legendgroup="g1")
        trace_no_lg = go.Scatter(y=[1])
        assert not sel.matches(trace_no_lg)


class TestSelectTracesBySelector(TestCaseNoTemplate):
    def test_type_filter(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="s1")
        fig.add_bar(y=[3, 2, 1], name="b1")
        sel = TraceSelector(type="scatter")
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].type == "scatter"

    def test_legendgroup_filter(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], legendgroup="g1")
        fig.add_scatter(y=[4, 5, 6], legendgroup="g2")
        sel = TraceSelector(legendgroup="g1")
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1

    def test_name_regex_filter(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="series_a")
        fig.add_scatter(y=[4, 5, 6], name="series_b")
        fig.add_bar(y=[3, 2, 1], name="bar_1")
        sel = TraceSelector(name=re.compile("series_"))
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 2

    def test_customdata_predicate_filter(self):
        fig = go.Figure()
        fig.add_scatter(y=[1], customdata=[1, 2, 3])
        fig.add_scatter(y=[2], customdata=[1, 2, 3, 4, 5])
        fig.add_scatter(y=[3])
        sel = TraceSelector(customdata=lambda cd: cd is not None and len(cd) > 3)
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1

    def test_meta_exact_filter(self):
        fig = go.Figure()
        fig.add_scatter(y=[1], meta="experiment_a")
        fig.add_scatter(y=[2], meta="experiment_b")
        sel = TraceSelector(meta="experiment_a")
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1

    def test_type_error_non_trace_selector(self):
        fig = go.Figure()
        with self.assertRaises(TypeError):
            fig.select_traces_by_selector({"type": "scatter"})

    def test_subplot_row_col(self):
        fig = make_subplots(rows=2, cols=2)
        fig.add_scatter(y=[1, 2, 3], row=1, col=1, name="s1")
        fig.add_scatter(y=[4, 5, 6], row=1, col=2, name="s2")
        fig.add_bar(y=[3, 2, 1], row=2, col=1, name="b1")
        fig.add_bar(y=[6, 5, 4], row=2, col=2, name="b2")

        sel = TraceSelector(row=1, type="scatter")
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 2

        sel2 = TraceSelector(row=2, col=1)
        matches2 = list(fig.select_traces_by_selector(sel2))
        assert len(matches2) == 1
        assert matches2[0].type == "bar"

    def test_subplot_secondary_y(self):
        fig = make_subplots(
            rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": True}]]
        )
        fig.add_scatter(y=[1, 2, 3], row=1, col=1, secondary_y=False, name="primary")
        fig.add_scatter(y=[4, 5, 6], row=1, col=1, secondary_y=True, name="secondary")
        fig.add_bar(y=[3, 2, 1], row=1, col=2, secondary_y=True, name="bar_sec")

        sel = TraceSelector(secondary_y=True, type="scatter")
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "secondary"

    def test_subplot_no_grid_fallback(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3])
        sel = TraceSelector(row=1, col=1)
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1

    def test_all_none_matches_all(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3])
        fig.add_bar(y=[3, 2, 1])
        sel = TraceSelector()
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 2


class TestUpdateTracesBySelector(TestCaseNoTemplate):
    def test_basic_update(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="s1")
        fig.add_bar(y=[3, 2, 1], name="b1")
        sel = TraceSelector(type="scatter")
        result = fig.update_traces_by_selector(sel, patch={"visible": "legendonly"})
        assert result is fig
        assert fig.data[0].visible == "legendonly"
        assert fig.data[1].visible != "legendonly"

    def test_kwargs_update(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="s1")
        fig.add_bar(y=[3, 2, 1], name="b1")
        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(
            sel, hovertemplate="x: %{x}<br>y: %{y}<extra></extra>"
        )
        assert fig.data[0].hovertemplate == "x: %{x}<br>y: %{y}<extra></extra>"
        assert fig.data[1].hovertemplate != "x: %{x}<br>y: %{y}<extra></extra>"

    def test_marker_update(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], marker=dict(color="red", size=5), name="s1")
        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(sel, patch={"marker": {"color": "blue"}})
        assert fig.data[0].marker.color == "blue"
        assert fig.data[0].marker.size == 5

    def test_line_update(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], line=dict(color="red", width=2), name="s1")
        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(sel, patch={"line": {"width": 4}})
        assert fig.data[0].line.width == 4
        assert fig.data[0].line.color == "red"

    def test_overwrite_mode(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], marker=dict(color="red", size=5), name="s1")
        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(
            sel, patch={"marker": {"color": "blue"}}, overwrite=True
        )
        assert fig.data[0].marker.color == "blue"
        assert fig.data[0].marker.size != 5

    def test_legendrank_update(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="s1")
        fig.add_bar(y=[3, 2, 1], name="b1")
        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(sel, patch={"legendrank": 100})
        assert fig.data[0].legendrank == 100

    def test_empty_match_warning(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3])
        sel = TraceSelector(type="nonexistent")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = fig.update_traces_by_selector(sel, patch={"visible": True})
            assert len(w) == 1
            assert "no traces matched" in str(w[0].message)
        assert result is fig

    def test_invalid_attribute_raises(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3])
        sel = TraceSelector(type="scatter")
        with self.assertRaises(ValueError):
            fig.update_traces_by_selector(sel, patch={"bogus_property": 123})

    def test_skip_invalid(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="s1")
        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(
            sel, patch={"bogus_property": 123, "visible": "legendonly"}, skip_invalid=True
        )
        assert fig.data[0].visible == "legendonly"

    def test_type_error_non_trace_selector(self):
        fig = go.Figure()
        with self.assertRaises(TypeError):
            fig.update_traces_by_selector({"type": "scatter"}, patch={"visible": True})

    def test_chaining(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="s1")
        fig.add_bar(y=[3, 2, 1], name="b1")
        result = fig.update_traces_by_selector(
            TraceSelector(type="scatter"), patch={"visible": "legendonly"}
        ).update_traces_by_selector(
            TraceSelector(type="bar"), patch={"visible": True}
        )
        assert result is fig
        assert fig.data[0].visible == "legendonly"
        assert fig.data[1].visible == True

    def test_patch_and_kwargs_precedence(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="s1")
        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(
            sel, patch={"visible": "legendonly"}, visible=True
        )
        assert fig.data[0].visible == True

    def test_update_across_subplot(self):
        fig = make_subplots(rows=2, cols=1)
        fig.add_scatter(y=[1, 2, 3], row=1, col=1, name="s1")
        fig.add_scatter(y=[4, 5, 6], row=2, col=1, name="s2")
        fig.add_bar(y=[3, 2, 1], row=1, col=1, name="b1")

        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(sel, patch={"visible": "legendonly"})
        for t in fig.data:
            if t.type == "scatter":
                assert t.visible == "legendonly"
            else:
                assert t.visible != "legendonly"

    def test_update_secondary_y(self):
        fig = make_subplots(
            rows=1, cols=1, specs=[[{"secondary_y": True}]]
        )
        fig.add_scatter(y=[1, 2, 3], secondary_y=False, name="primary")
        fig.add_scatter(y=[4, 5, 6], secondary_y=True, name="secondary")

        sel = TraceSelector(secondary_y=True, type="scatter")
        fig.update_traces_by_selector(sel, patch={"visible": "legendonly"})
        assert fig.data[0].visible != "legendonly"
        assert fig.data[1].visible == "legendonly"


class TestTraceSelectorFromGraphObjects(TestCaseNoTemplate):
    def test_go_trace_selector(self):
        sel = go.TraceSelector(type="scatter")
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3])
        fig.add_bar(y=[3, 2, 1])
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].type == "scatter"


class TestTraceSelectorWithPlotlyExpress(TestCaseNoTemplate):
    def test_pe_scatter_type(self):
        import plotly.express as px

        df = px.data.iris()
        fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species")
        sel = TraceSelector(type="scatter")
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == len(fig.data)

    def test_pe_update_marker(self):
        import plotly.express as px

        df = px.data.iris()
        fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species")
        sel = TraceSelector(type="scatter")
        fig.update_traces_by_selector(sel, patch={"marker": {"size": 15}})
        for t in fig.data:
            assert t.marker.size == 15

    def test_pe_faceted(self):
        import plotly.express as px

        df = px.data.tips()
        fig = px.scatter(df, x="total_bill", y="tip", facet_col="sex", color="time")
        sel = TraceSelector(type="scatter")
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == len(fig.data)

    def test_pe_name_regex(self):
        import plotly.express as px

        df = px.data.iris()
        fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species")
        sel = TraceSelector(name=re.compile("setosa"))
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1


class TestFilterInvalidTraceProps(TestCaseNoTemplate):
    def test_valid_prop_kept(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3])
        trace = fig.data[0]
        result = BaseFigure = fig._filter_invalid_trace_props(
            trace, {"visible": "legendonly", "name": "new_name"}
        )
        assert "visible" in result
        assert "name" in result

    def test_invalid_prop_removed(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3])
        trace = fig.data[0]
        result = fig._filter_invalid_trace_props(
            trace, {"bogus_property": 123, "visible": "legendonly"}
        )
        assert "bogus_property" not in result
        assert "visible" in result


class TestCustomdataFieldPath(TestCaseNoTemplate):
    def setUp(self):
        self.fig = go.Figure()
        self.fig.add_scatter(
            y=[1, 2, 3],
            customdata=[["APAC", 100], ["EMEA", 200], ["APAC", 300]],
            name="t1",
        )
        self.fig.add_scatter(
            y=[4, 5, 6],
            customdata=[["AMER", 400], ["AMER", 500], ["APAC", 600]],
            name="t2",
        )
        self.fig.add_scatter(
            y=[7, 8, 9],
            name="t3",
        )

    def test_field_0_match(self):
        sel = TraceSelector(customdata={"0": "APAC"})
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 2
        names = {m.name for m in matches}
        assert "t1" in names
        assert "t2" in names

    def test_field_1_match(self):
        sel = TraceSelector(customdata={"1": 400})
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "t2"

    def test_no_match(self):
        sel = TraceSelector(customdata={"0": "LATAM"})
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 0

    def test_trace_without_customdata(self):
        sel = TraceSelector(customdata={"0": "APAC"})
        matches = list(self.fig.select_traces_by_selector(sel))
        names = {m.name for m in matches}
        assert "t3" not in names

    def test_combined_with_type(self):
        sel = TraceSelector(customdata={"0": "AMER"}, type="scatter")
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "t2"


class TestMetaFieldPath(TestCaseNoTemplate):
    def setUp(self):
        self.fig = go.Figure()
        self.fig.add_scatter(
            y=[1, 2, 3],
            meta={"source": "train", "version": 2, "nested": {"key": "val_a"}},
            name="t1",
        )
        self.fig.add_scatter(
            y=[4, 5, 6],
            meta={"source": "test", "version": 1, "nested": {"key": "val_b"}},
            name="t2",
        )
        self.fig.add_scatter(
            y=[7, 8, 9],
            name="t3",
        )

    def test_single_field_match(self):
        sel = TraceSelector(meta={"source": "train"})
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "t1"

    def test_multiple_fields_match(self):
        sel = TraceSelector(meta={"source": "train", "version": 2})
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "t1"

    def test_nested_field_match(self):
        sel = TraceSelector(meta={"nested.key": "val_a"})
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "t1"

    def test_no_match(self):
        sel = TraceSelector(meta={"source": "validation"})
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 0

    def test_missing_key(self):
        sel = TraceSelector(meta={"nonexistent": "value"})
        matches = list(self.fig.select_traces_by_selector(sel))
        assert len(matches) == 0

    def test_trace_without_meta(self):
        sel = TraceSelector(meta={"source": "train"})
        matches = list(self.fig.select_traces_by_selector(sel))
        names = {m.name for m in matches}
        assert "t3" not in names

    def test_update_with_meta_field_path(self):
        sel = TraceSelector(meta={"source": "test"})
        self.fig.update_traces_by_selector(sel, patch={"visible": "legendonly"})
        assert self.fig.data[1].visible == "legendonly"
        assert self.fig.data[0].visible != "legendonly"


class TestAxisInferenceSubplotSelection(TestCaseNoTemplate):
    def test_manual_multi_axis_col1(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], xaxis="x", yaxis="y", name="s1")
        fig.add_scatter(y=[4, 5, 6], xaxis="x2", yaxis="y2", name="s2")
        fig.update_layout(xaxis2={}, yaxis2={})
        sel = TraceSelector(col=1)
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "s1"

    def test_manual_multi_axis_col2(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], xaxis="x", yaxis="y", name="s1")
        fig.add_scatter(y=[4, 5, 6], xaxis="x2", yaxis="y2", name="s2")
        fig.update_layout(xaxis2={}, yaxis2={})
        sel = TraceSelector(col=2)
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "s2"

    def test_simple_figure_row1_col1(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], name="s1")
        fig.add_bar(y=[3, 2, 1], name="b1")
        sel = TraceSelector(row=1, col=1)
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 2

    def test_pe_facet_col_selection(self):
        import plotly.express as px

        df = px.data.tips()
        fig = px.scatter(df, x="total_bill", y="tip", facet_col="sex", color="time")
        sel = TraceSelector(col=1)
        matches_col1 = list(fig.select_traces_by_selector(sel))
        sel2 = TraceSelector(col=2)
        matches_col2 = list(fig.select_traces_by_selector(sel2))
        assert len(matches_col1) + len(matches_col2) == len(fig.data)

    def test_pe_facet_row_col_selection(self):
        import plotly.express as px

        df = px.data.tips()
        fig = px.scatter(df, x="total_bill", y="tip", facet_row="time", facet_col="sex")
        sel = TraceSelector(row=1, col=1)
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) >= 1

    def test_make_subplots_still_primary(self):
        fig = make_subplots(rows=1, cols=2)
        fig.add_scatter(y=[1, 2, 3], row=1, col=1, name="s1")
        fig.add_scatter(y=[4, 5, 6], row=1, col=2, name="s2")
        sel = TraceSelector(col=1)
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "s1"

    def test_axis_inference_with_type_filter(self):
        fig = go.Figure()
        fig.add_scatter(y=[1, 2, 3], xaxis="x", yaxis="y", name="s1")
        fig.add_bar(y=[3, 2, 1], xaxis="x2", yaxis="y2", name="b1")
        fig.update_layout(xaxis2={}, yaxis2={})
        sel = TraceSelector(col=2, type="bar")
        matches = list(fig.select_traces_by_selector(sel))
        assert len(matches) == 1
        assert matches[0].name == "b1"

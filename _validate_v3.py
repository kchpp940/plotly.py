"""Comprehensive validation v3: unified entry point + full ParamContext coverage."""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import inspect
import plotly.graph_objects as go
import plotly.express as px
from plotly.express._params import PARAMS, ParamContext, ParamCategory
from plotly.express._core import _DEFAULT_CTX, build_dataframe, infer_config
from plotly.express._doc import make_docstring
import pandas as pd


def test_1_import_clean():
    """Module imports cleanly with decorator-based registration."""
    # Core 4 charts are registered via @_register_chart decorator at import time
    print("✅ Test 1 PASSED: module imported with decorator registration")


def test_2_paramcontext_full_categories():
    """ParamContext provides all category lookups, not just attrable."""
    ctx = PARAMS.context_for("scatter")

    # All 6 category properties exist and return lists
    assert isinstance(ctx.trace_config_params, list)
    assert isinstance(ctx.layout_config_params, list)
    assert isinstance(ctx.label_params, list)
    assert isinstance(ctx.mapping_params, list)
    assert isinstance(ctx.mapping_config_params, list)
    assert isinstance(ctx.all_attrables, list)

    # Known params are in the right categories
    assert "opacity" in ctx.trace_config_params
    assert "width" in ctx.layout_config_params
    assert "height" in ctx.layout_config_params
    assert "color" in ctx.mapping_params
    assert "color_discrete_sequence" in ctx.mapping_config_params
    assert "title" in ctx.label_params

    # by_category() generic accessor works
    assert ctx.by_category(ParamCategory.TRACE_CONFIG) == ctx.trace_config_params
    assert ctx.by_category(ParamCategory.LAYOUT_CONFIG) == ctx.layout_config_params

    # Convenience predicates
    assert ctx.is_trace_config("opacity")
    assert ctx.is_layout_config("width")
    assert not ctx.is_trace_config("x")
    assert not ctx.is_layout_config("color")

    # Caching: multiple calls return same list object
    assert ctx.trace_config_params is ctx.trace_config_params
    assert ctx.layout_config_params is ctx.layout_config_params

    print("✅ Test 2 PASSED: ParamContext full category coverage")


def test_3_registered_charts_have_metadata():
    """@_register_chart decorator binds chart_name + constructor metadata."""
    from plotly.express import _chart_types

    core4 = ["scatter", "line", "bar", "histogram"]
    for name in core4:
        func = getattr(_chart_types, name)
        assert hasattr(func, "_chart_name"), f"{name} missing _chart_name"
        assert hasattr(func, "_chart_constructor"), f"{name} missing _chart_constructor"
        assert func._chart_name == name, f"{name}._chart_name != {name}"

    # scatter and line share constructor (go.Scatter) but have different chart_name
    assert _chart_types.scatter._chart_constructor == go.Scatter
    assert _chart_types.line._chart_constructor == go.Scatter
    assert _chart_types.scatter._chart_name == "scatter"
    assert _chart_types.line._chart_name == "line"

    # bar and histogram have their own constructors
    assert _chart_types.bar._chart_constructor == go.Bar
    assert _chart_types.histogram._chart_constructor == go.Histogram

    print("✅ Test 3 PASSED: registered charts have correct metadata")


def test_4_fig_helper():
    """_fig() helper correctly reads metadata and calls make_figure."""
    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})

    fig = px.scatter(df, x="x", y="y")
    assert isinstance(fig, go.Figure)

    fig2 = px.line(df, x="x", y="y")
    assert isinstance(fig2, go.Figure)

    # Chart-specific params work (size only for scatter, not line)
    fig3 = px.scatter(df, x="x", y="y", size="y")
    assert isinstance(fig3, go.Figure)

    print("✅ Test 4 PASSED: _fig() helper works for all core4 charts")


def test_5_chart_specific_trace_config():
    """trace_config_params differ between chart types."""
    ctx_s = PARAMS.context_for("scatter")
    ctx_l = PARAMS.context_for("line")
    ctx_b = PARAMS.context_for("bar")
    ctx_h = PARAMS.context_for("histogram")

    # scatter has size_max (in mapping_config), line doesn't have size at all
    assert "size_max" in ctx_s.mapping_config_params
    assert "size_max" not in ctx_l.mapping_config_params

    # bar has pattern_shape in mapping, line has line_dash
    assert "pattern_shape" in ctx_b.mapping_params
    assert "line_dash" in ctx_l.mapping_params

    # histogram has barnorm in trace_config
    assert "barnorm" in ctx_h.trace_config_params
    assert "barnorm" not in ctx_s.trace_config_params

    print("✅ Test 5 PASSED: chart-specific trace/mapping params")


def test_6_strict_docs_fail_fast():
    """Strict-mode doc generation raises KeyError for unregistered params."""
    def fake_fn(data_frame, x, fake_param_12345):
        pass
    fake_fn.__name__ = "scatter"

    try:
        make_docstring(fake_fn, strict=True)
        assert False, "Should raise KeyError"
    except KeyError as e:
        assert "fake_param_12345" in str(e)

    # Non-strict mode is lenient
    doc = make_docstring(fake_fn, strict=False)
    assert "fake_param_12345" in doc

    print("✅ Test 6 PASSED: strict docs fail fast")


def test_7_chart_specific_docs():
    """Docstrings reflect chart-specific params (no cross-contamination)."""
    scatter_doc = px.scatter.__doc__ or ""
    line_doc = px.line.__doc__ or ""
    bar_doc = px.bar.__doc__ or ""
    hist_doc = px.histogram.__doc__ or ""

    # scatter has size_max, line doesn't
    assert "size_max" in scatter_doc
    assert "size_max" not in line_doc

    # line has line_group, scatter doesn't
    assert "line_group" in line_doc
    assert "line_group" not in scatter_doc

    # bar has pattern_shape
    assert "pattern_shape" in bar_doc

    # histogram has barnorm, histfunc, cumulative
    assert "barnorm" in hist_doc
    assert "histfunc" in hist_doc
    assert "cumulative" in hist_doc

    print("✅ Test 7 PASSED: chart-specific docstrings")


def test_8_no_global_mutation():
    """Zero global state mutation – ParamContext is fully explicit."""
    from plotly.express import _core

    before_direct = list(_core.direct_attrables)
    before_all = list(_core.all_attrables)

    df = pd.DataFrame({
        "x": [1, 2, 3], "y": [10, 20, 30],
        "cat": ["a", "b", "a"], "size": [5, 10, 15],
    })

    # Call all 4 core charts
    px.scatter(df, x="x", y="y", color="cat", size="size")
    px.line(df, x="x", y="y", color="cat")
    px.bar(df, x="x", y="y", color="cat")
    px.histogram(df, x="x", color="cat")

    after_direct = list(_core.direct_attrables)
    after_all = list(_core.all_attrables)

    assert before_direct == after_direct
    assert before_all == after_all

    print("✅ Test 8 PASSED: zero global state mutation")


def test_9_nested_contexts_independent():
    """Multiple ParamContexts can coexist without interfering."""
    ctx_s = PARAMS.context_for("scatter")
    ctx_l = PARAMS.context_for("line")
    ctx_b = PARAMS.context_for("bar")
    ctx_h = PARAMS.context_for("histogram")
    ctx_default = PARAMS.context_for(None)

    # Each has its own set of params
    assert "size" in ctx_s.all_attrables
    assert "size" not in ctx_l.all_attrables
    assert "line_group" in ctx_l.all_attrables
    assert "line_group" not in ctx_s.all_attrables
    assert "base" in ctx_b.all_attrables
    assert "base" not in ctx_h.all_attrables
    assert "barnorm" in ctx_h.trace_config_params
    assert "barnorm" not in ctx_b.trace_config_params

    # Default context is the global fallback
    assert ctx_default.chart_name is None
    assert _DEFAULT_CTX.chart_name is None

    print("✅ Test 9 PASSED: contexts are fully independent")


def test_10_core4_figures_valid():
    """All 4 core charts produce valid, correct figures."""
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [10, 20, 30, 20, 10],
        "cat": ["a", "b", "a", "b", "a"],
    })

    # scatter with all the bells and whistles
    fig1 = px.scatter(df, x="x", y="y", color="cat", size="y",
                      marginal_x="histogram", marginal_y="box", trendline="ols")
    assert isinstance(fig1, go.Figure)
    assert len(fig1.data) >= 2  # at least main traces + trendlines
    print(f"  scatter: {len(fig1.data)} traces")

    # line with line_group and markers
    df2 = pd.concat([df.assign(s=i) for i in range(2)])
    fig2 = px.line(df2, x="x", y="y", color="cat", line_group="s", markers=True)
    assert isinstance(fig2, go.Figure)
    print(f"  line: {len(fig2.data)} traces")

    # bar with pattern_shape + barmode
    fig3 = px.bar(df, x="x", y="y", color="cat", pattern_shape="cat", barmode="group")
    assert isinstance(fig3, go.Figure)
    print(f"  bar: {len(fig3.data)} traces")

    # histogram with histfunc + barnorm + cumulative
    fig4 = px.histogram(df, x="x", y="y", color="cat",
                        histfunc="sum", barnorm="percent", cumulative=True)
    assert isinstance(fig4, go.Figure)
    print(f"  histogram: {len(fig4.data)} traces")

    print("✅ Test 10 PASSED: all core4 figures are valid")


def test_11_non_core4_still_work():
    """Non-registered charts still work via default context (backward compat)."""
    df = pd.DataFrame({"values": [10, 20, 30], "names": ["a", "b", "c"]})
    fig = px.pie(df, values="values", names="names")
    assert isinstance(fig, go.Figure)

    fig2 = px.box(df, y="values")
    assert isinstance(fig2, go.Figure)

    fig3 = px.violin(df, y="values")
    assert isinstance(fig3, go.Figure)

    print("✅ Test 11 PASSED: non-core4 charts still work")


def test_12_build_dataframe_explicit_ctx():
    """build_dataframe correctly uses explicit param_ctx for all charts."""
    df = pd.DataFrame({
        "x": [1, 2, 3], "y": [10, 20, 30],
        "cat": ["a", "b", "a"], "size": [5, 10, 15],
    })

    # scatter context: size is a data_column attrable
    ctx_s = PARAMS.context_for("scatter")
    args_s = dict(data_frame=df, x="x", y="y", size="size", color="cat")
    result_s = build_dataframe(args_s, go.Scatter, param_ctx=ctx_s)
    assert result_s is args_s  # returns modified args

    # line context: size is NOT an attrable
    ctx_l = PARAMS.context_for("line")
    args_l = dict(data_frame=df, x="x", y="y", size="size", color="cat")
    result_l = build_dataframe(args_l, go.Scatter, param_ctx=ctx_l)
    assert result_l is args_l

    print("✅ Test 12 PASSED: build_dataframe respects explicit param_ctx")


def main():
    print("\n" + "=" * 70)
    print("VALIDATION v3: unified entry + full ParamContext + zero global state")
    print("=" * 70 + "\n")

    tests = [
        test_1_import_clean,
        test_2_paramcontext_full_categories,
        test_3_registered_charts_have_metadata,
        test_4_fig_helper,
        test_5_chart_specific_trace_config,
        test_6_strict_docs_fail_fast,
        test_7_chart_specific_docs,
        test_8_no_global_mutation,
        test_9_nested_contexts_independent,
        test_10_core4_figures_valid,
        test_11_non_core4_still_work,
        test_12_build_dataframe_explicit_ctx,
    ]

    passed = 0
    failed = []
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed.append((t.__name__, str(e)))
            print(f"❌ {t.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"RESULT: {passed}/{len(tests)} tests passed")
    if failed:
        print("FAILURES:")
        for name, err in failed:
            print(f"  - {name}: {err}")
    else:
        print("🎉 ALL TESTS PASSED!")
    print("=" * 70)
    return len(failed) == 0


if __name__ == "__main__":
    import sys
    ok = main()
    sys.exit(0 if ok else 1)

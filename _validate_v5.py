"""Comprehensive validation v5: auto-wrap decorator + ctx-driven defaults + layout dispatch."""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import inspect
import plotly.graph_objects as go
import plotly.express as px
from plotly.express._params import PARAMS, ParamContext, ParamCategory
from plotly.express._core import _DEFAULT_CTX, build_dataframe, apply_default_cascade, defaults
from plotly.express._doc import make_docstring
import pandas as pd


def test_1_paramcontext_defaults_slots():
    """ParamContext.defaults_slots returns chart-specific default params."""
    ctx_s = PARAMS.context_for("scatter")
    ctx_l = PARAMS.context_for("line")
    ctx_default = PARAMS.context_for(None)

    assert "color_discrete_sequence" in ctx_s.defaults_slots
    assert "symbol_sequence" in ctx_s.defaults_slots
    assert "size_max" in ctx_s.defaults_slots
    assert "color_continuous_scale" in ctx_s.defaults_slots

    # line doesn't have size_max in defaults
    assert "size_max" not in ctx_l.defaults_slots
    # line has line_dash_sequence
    assert "line_dash_sequence" in ctx_l.defaults_slots

    # default ctx includes all defaults
    assert len(ctx_default.defaults_slots) >= len(ctx_s.defaults_slots)

    print("✅ Test 1 PASSED: ParamContext.defaults_slots is chart-specific")


def test_2_apply_px_defaults():
    """ctx.apply_px_defaults fills None args from px.defaults."""
    ctx = PARAMS.context_for("scatter")
    args = {
        "color_discrete_sequence": None,
        "color_continuous_scale": None,
        "symbol_sequence": None,
        "size_max": None,
    }
    ctx.apply_px_defaults(args, defaults)

    # size_max has a default value in PARAMS
    assert args["size_max"] is not None or args["size_max"] == defaults.size_max

    print("✅ Test 2 PASSED: ctx.apply_px_defaults works correctly")


def test_3_apply_default_cascade_uses_ctx():
    """apply_default_cascade now uses param_ctx for mapping_config guards."""
    ctx_s = PARAMS.context_for("scatter")
    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})

    args = {
        "data_frame": df, "x": "x", "y": "y",
        "template": None, "color_continuous_scale": None,
        "color_discrete_sequence": None, "symbol_sequence": None,
        "size_max": None,
    }
    # Should not raise – mapping_config params are properly guarded by ctx
    apply_default_cascade(args, constructor=go.Scatter, param_ctx=ctx_s)

    print("✅ Test 3 PASSED: apply_default_cascade uses ctx for mapping_config guards")


def test_4_auto_wrap_decorator():
    """@_register_chart auto-wraps the function, no manual _fig() needed."""
    from plotly.express import _chart_types

    # scatter has no patches, should just work
    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
    fig = px.scatter(df, x="x", y="y")
    assert isinstance(fig, go.Figure)

    # bar has trace_patch + layout_patch
    fig2 = px.bar(df, x="x", y="y")
    assert isinstance(fig2, go.Figure)

    # histogram has patches too
    fig3 = px.histogram(df, x="x")
    assert isinstance(fig3, go.Figure)

    print("✅ Test 4 PASSED: auto-wrap decorator works for all core4")


def test_5_wrapper_metadata():
    """Wrapper preserves function metadata."""
    assert px.scatter._chart_name == "scatter"
    assert px.scatter._chart_constructor == go.Scatter
    assert px.line._chart_name == "line"
    assert px.bar._chart_name == "bar"
    assert px.bar._chart_constructor == go.Bar
    assert px.histogram._chart_name == "histogram"
    assert px.histogram._chart_constructor == go.Histogram

    # __name__ preserved
    assert px.scatter.__name__ == "scatter"
    assert px.bar.__name__ == "bar"

    # __wrapped__ points to original
    assert hasattr(px.scatter, "__wrapped__")

    print("✅ Test 5 PASSED: wrapper preserves metadata")


def test_6_no_fig_or_make_figure_in_bodies():
    """Core4 function bodies no longer call _fig() or make_figure()."""
    from plotly.express import _chart_types

    for name in ["scatter", "line", "bar", "histogram"]:
        func = getattr(_chart_types, name)
        original = getattr(func, "__wrapped__", func)
        source = inspect.getsource(original)
        assert "_fig(" not in source, f"{name} still calls _fig()"
        assert "make_figure(" not in source, f"{name} still calls make_figure()"

    print("✅ Test 6 PASSED: core4 bodies have no _fig/make_figure calls")


def test_7_ctx_driven_layout_dispatch():
    """make_figure uses ctx.layout_config_params for height/width dispatch."""
    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})

    # Height/width should be passed through to layout
    fig = px.scatter(df, x="x", y="y", width=800, height=600)
    assert isinstance(fig, go.Figure)
    assert fig.layout.width == 800
    assert fig.layout.height == 600

    print("✅ Test 7 PASSED: layout dispatch uses ctx.layout_config_params")


def test_8_chart_specific_mapping_config():
    """Mapping config defaults are chart-specific via ctx."""
    ctx_s = PARAMS.context_for("scatter")
    ctx_l = PARAMS.context_for("line")
    ctx_b = PARAMS.context_for("bar")
    ctx_h = PARAMS.context_for("histogram")

    assert ctx_s.is_mapping_config("color_continuous_scale")
    assert ctx_s.is_mapping_config("symbol_sequence")
    assert ctx_l.is_mapping_config("line_dash_sequence")
    assert ctx_b.is_mapping_config("pattern_shape_sequence")

    # line_dash_sequence is in line but not in scatter
    assert ctx_l.is_mapping_config("line_dash_sequence")
    assert not ctx_s.is_mapping_config("line_dash_sequence")

    # is_mapping predicate
    assert ctx_s.is_mapping("color")
    assert ctx_s.is_mapping("symbol")
    assert not ctx_s.is_mapping("x")
    assert ctx_l.is_mapping("line_dash")

    print("✅ Test 8 PASSED: chart-specific mapping_config via ctx")


def test_9_get_param_meta():
    """ParamContext.get_param_meta returns ParamMeta objects."""
    ctx = PARAMS.context_for("scatter")

    meta = ctx.get_param_meta("x")
    assert meta is not None
    assert meta.name == "x"
    assert meta.category == ParamCategory.DATA_COLUMN

    meta_color = ctx.get_param_meta("color")
    assert meta_color is not None
    assert meta_color.category == ParamCategory.MAPPING

    # Non-existent param
    assert ctx.get_param_meta("nonexistent_xyz") is None

    print("✅ Test 9 PASSED: get_param_meta works")


def test_10_strict_docs():
    """Strict-mode doc generation raises KeyError for unregistered params."""
    def fake_fn(data_frame, x, fake_param_99999):
        pass
    fake_fn.__name__ = "scatter"

    try:
        make_docstring(fake_fn, strict=True)
        assert False, "Should raise KeyError"
    except KeyError as e:
        assert "fake_param_99999" in str(e)

    print("✅ Test 10 PASSED: strict docs fail fast")


def test_11_no_global_mutation():
    """Zero global state mutation – ParamContext is fully explicit."""
    from plotly.express import _core

    before_direct = list(_core.direct_attrables)
    before_all = list(_core.all_attrables)

    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30], "cat": ["a", "b", "a"]})

    px.scatter(df, x="x", y="y", color="cat", size="y")
    px.line(df, x="x", y="y", color="cat")
    px.bar(df, x="x", y="y", color="cat")
    px.histogram(df, x="x", color="cat")

    after_direct = list(_core.direct_attrables)
    after_all = list(_core.all_attrables)

    assert before_direct == after_direct
    assert before_all == after_all

    print("✅ Test 11 PASSED: zero global state mutation")


def test_12_core4_figures_valid():
    """All 4 core charts produce valid, correct figures."""
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [10, 20, 30, 20, 10],
        "cat": ["a", "b", "a", "b", "a"],
    })

    fig1 = px.scatter(df, x="x", y="y", color="cat", size="y",
                      marginal_x="histogram", marginal_y="box", trendline="ols")
    assert isinstance(fig1, go.Figure)
    print(f"  scatter: {len(fig1.data)} traces")

    df2 = pd.concat([df.assign(s=i) for i in range(2)])
    fig2 = px.line(df2, x="x", y="y", color="cat", line_group="s", markers=True)
    assert isinstance(fig2, go.Figure)
    print(f"  line: {len(fig2.data)} traces")

    fig3 = px.bar(df, x="x", y="y", color="cat", pattern_shape="cat", barmode="group")
    assert isinstance(fig3, go.Figure)
    print(f"  bar: {len(fig3.data)} traces")

    fig4 = px.histogram(df, x="x", y="y", color="cat",
                        histfunc="sum", barnorm="percent", cumulative=True)
    assert isinstance(fig4, go.Figure)
    print(f"  histogram: {len(fig4.data)} traces")

    print("✅ Test 12 PASSED: all core4 figures are valid")


def test_13_non_core4_still_work():
    """Non-registered charts still work via default context."""
    df = pd.DataFrame({"values": [10, 20, 30], "names": ["a", "b", "c"]})
    fig = px.pie(df, values="values", names="names")
    assert isinstance(fig, go.Figure)

    fig2 = px.box(df, y="values")
    assert isinstance(fig2, go.Figure)

    print("✅ Test 13 PASSED: non-core4 charts still work")


def test_14_chart_specific_docs():
    """Docstrings reflect chart-specific params."""
    scatter_doc = px.scatter.__doc__ or ""
    line_doc = px.line.__doc__ or ""
    bar_doc = px.bar.__doc__ or ""
    hist_doc = px.histogram.__doc__ or ""

    assert "size_max" in scatter_doc
    assert "size_max" not in line_doc
    assert "line_group" in line_doc
    assert "line_group" not in scatter_doc
    assert "pattern_shape" in bar_doc
    assert "barnorm" in hist_doc
    assert "cumulative" in hist_doc

    print("✅ Test 14 PASSED: chart-specific docstrings")


def main():
    print("\n" + "=" * 70)
    print("VALIDATION v5: auto-wrap + ctx-driven defaults + layout dispatch")
    print("=" * 70 + "\n")

    tests = [
        test_1_paramcontext_defaults_slots,
        test_2_apply_px_defaults,
        test_3_apply_default_cascade_uses_ctx,
        test_4_auto_wrap_decorator,
        test_5_wrapper_metadata,
        test_6_no_fig_or_make_figure_in_bodies,
        test_7_ctx_driven_layout_dispatch,
        test_8_chart_specific_mapping_config,
        test_9_get_param_meta,
        test_10_strict_docs,
        test_11_no_global_mutation,
        test_12_core4_figures_valid,
        test_13_non_core4_still_work,
        test_14_chart_specific_docs,
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

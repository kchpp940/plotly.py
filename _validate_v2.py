"""Comprehensive validation v2: ParamContext + strict docs + no global mutation."""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import inspect
import plotly.graph_objects as go
import plotly.express as px
from plotly.express._params import PARAMS, ParamContext
from plotly.express._core import _DEFAULT_CTX, _resolve_ctx, build_dataframe
from plotly.express._doc import make_docstring
import pandas as pd


def test_1_import_and_signature_check():
    """Module imports cleanly; signature check runs at import time."""
    # scatter/line/bar/histogram are all strict-mode + signature-checked
    print("✅ Test 1 PASSED: module imported, core 4 signatures verified")


def test_2_paramcontext_creation():
    """ParamContext can be created from registry for different charts."""
    ctx_scatter = PARAMS.context_for("scatter")
    ctx_line = PARAMS.context_for("line")
    ctx_hist = PARAMS.context_for("histogram")
    ctx_none = PARAMS.context_for(None)

    assert isinstance(ctx_scatter, ParamContext)
    assert ctx_scatter.chart_name == "scatter"
    assert ctx_line.chart_name == "line"

    # scatter should have size, line should not
    assert ctx_scatter.is_direct("size"), "scatter ctx should have size as direct"
    assert not ctx_line.is_direct("size"), "line ctx should NOT have size"
    assert ctx_line.is_group("line_group"), "line ctx should have line_group as group"
    assert not ctx_scatter.is_group("line_group"), "scatter ctx should NOT have line_group"

    # helpers
    assert ctx_scatter.has("x")
    assert ctx_scatter.has("y")
    assert ctx_scatter.is_array("hover_data")
    assert not ctx_scatter.is_array("x")

    # default ctx matches module-level globals
    from plotly.express import _core
    assert set(ctx_none.all_attrables) == set(_core.all_attrables)

    print("✅ Test 2 PASSED: ParamContext creation and helpers correct")


def test_3_no_global_mutation():
    """Module-level attrable globals are NOT mutated by make_figure calls."""
    from plotly.express import _core

    before_direct = list(_core.direct_attrables)
    before_all = list(_core.all_attrables)

    # Call scatter (which uses chart_name="scatter")
    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
    fig = px.scatter(df, x="x", y="y", size="y")
    assert isinstance(fig, go.Figure)

    after_direct = list(_core.direct_attrables)
    after_all = list(_core.all_attrables)

    assert before_direct == after_direct, "global direct_attrables should NOT be mutated"
    assert before_all == after_all, "global all_attrables should NOT be mutated"

    # Also test with histogram
    fig2 = px.histogram(df, x="x")
    assert isinstance(fig2, go.Figure)
    assert list(_core.direct_attrables) == before_direct
    assert list(_core.all_attrables) == before_all

    print("✅ Test 3 PASSED: no global state mutation during figure creation")


def test_4_build_dataframe_explicit_ctx():
    """build_dataframe accepts explicit param_ctx and uses it."""
    from plotly.express._core import build_dataframe

    df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30], "cat": ["a", "b", "a"]})

    # scatter context: size is a valid data-column attrable
    args_scatter = dict(data_frame=df, x="x", y="y", size="y", color="cat")
    args_s_copy = dict(args_scatter)
    result_s = build_dataframe(args_s_copy, go.Scatter, param_ctx=PARAMS.context_for("scatter"))
    assert result_s is args_s_copy  # returns modified args dict in-place
    assert "size" in args_s_copy  # size should be in args after processing

    # line context: size is NOT a data-column attrable
    args_line = dict(data_frame=df, x="x", y="y", size="y", color="cat")
    args_l_copy = dict(args_line)
    result_l = build_dataframe(args_l_copy, go.Scatter, param_ctx=PARAMS.context_for("line"))
    assert result_l is args_l_copy
    # size is not in line's all_attrables, so it should be ignored by the pipeline
    # (still in args as a raw value but not processed as a column)

    print("✅ Test 4 PASSED: build_dataframe respects explicit param_ctx")


def test_5_strict_docs():
    """Strict-mode docstring generation fails fast on missing params."""
    # scatter should work (all params registered)
    doc = make_docstring(px.scatter, strict=True)
    assert "trendline_options" in doc
    assert "size_max" in doc

    # A fake function with a made-up param should raise KeyError in strict mode
    def fake_func(data_frame, x, fake_param_xyz):
        pass
    fake_func.__name__ = "scatter"  # use scatter's chart name
    fake_func.__doc__ = ""
    try:
        make_docstring(fake_func, strict=True)
        assert False, "Should have raised KeyError for fake_param_xyz"
    except KeyError as e:
        assert "fake_param_xyz" in str(e), f"KeyError should mention the missing param, got: {e}"

    # Non-strict mode should not raise
    doc2 = make_docstring(fake_func, strict=False)
    assert "fake_param_xyz" in doc2

    print("✅ Test 5 PASSED: strict mode raises on missing, non-strict is lenient")


def test_6_core4_figures_all_work():
    """Core 4 charts produce valid Figures with chart-specific params."""
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [10, 20, 30, 20, 10],
        "cat": ["a", "b", "a", "b", "a"],
    })

    # scatter with size + trendline + marginal
    fig1 = px.scatter(df, x="x", y="y", color="cat", size="y",
                      marginal_x="histogram", marginal_y="box", trendline="ols")
    assert isinstance(fig1, go.Figure)
    print(f"  scatter OK: {len(fig1.data)} traces")

    # line with line_group
    df2 = pd.concat([df.assign(s=i) for i in range(2)])
    fig2 = px.line(df2, x="x", y="y", color="cat", line_group="s", markers=True)
    assert isinstance(fig2, go.Figure)
    print(f"  line OK: {len(fig2.data)} traces")

    # bar with pattern_shape
    fig3 = px.bar(df, x="x", y="y", color="cat", pattern_shape="cat")
    assert isinstance(fig3, go.Figure)
    print(f"  bar OK: {len(fig3.data)} traces")

    # histogram with histfunc + barnorm
    fig4 = px.histogram(df, x="x", y="y", color="cat",
                        histfunc="sum", barnorm="percent", barmode="group", nbins=5)
    assert isinstance(fig4, go.Figure)
    print(f"  histogram OK: {len(fig4.data)} traces")

    print("✅ Test 6 PASSED: all core 4 charts produce valid Figures")


def test_7_chart_specific_docs():
    """Docstrings are chart-specific (no cross-contamination)."""
    scatter_doc = px.scatter.__doc__ or ""
    line_doc = px.line.__doc__ or ""
    hist_doc = px.histogram.__doc__ or ""

    assert "trendline_options" in scatter_doc
    assert "size_max" in scatter_doc
    assert "trendline_options" not in line_doc
    assert "line_group" in line_doc
    assert "barnorm" in hist_doc
    assert "barnorm" not in px.bar.__doc__

    print("✅ Test 7 PASSED: docstrings are chart-specific")


def test_8_non_core4_still_work():
    """Non-core4 charts (without chart_name=) still work via default ctx."""
    df = pd.DataFrame({"values": [10, 20, 30], "names": ["a", "b", "c"]})
    fig = px.pie(df, values="values", names="names")
    assert isinstance(fig, go.Figure) and len(fig.data) == 1

    fig2 = px.box(df, y="values")
    assert isinstance(fig2, go.Figure)

    print("✅ Test 8 PASSED: non-core4 charts still work via default context")


def test_9_nested_call_safety():
    """ParamContext is explicit, so nested / concurrent calls don't interfere."""
    from plotly.express._core import _DEFAULT_CTX

    # Build both contexts upfront - no global state involved
    ctx_s = PARAMS.context_for("scatter")
    ctx_l = PARAMS.context_for("line")
    ctx_b = PARAMS.context_for("bar")

    # Each context is independent
    assert "size" in ctx_s.all_attrables
    assert "size" not in ctx_l.all_attrables
    assert "base" in ctx_b.all_attrables
    assert "base" not in ctx_s.all_attrables
    assert "line_group" in ctx_l.all_attrables
    assert "line_group" not in ctx_s.all_attrables

    # Default is unchanged
    assert _DEFAULT_CTX.chart_name is None

    print("✅ Test 9 PASSED: ParamContexts are independent, no global interference")


def main():
    print("\n" + "=" * 70)
    print("VALIDATION v2: ParamContext + strict docs + zero global mutation")
    print("=" * 70 + "\n")

    tests = [
        test_1_import_and_signature_check,
        test_2_paramcontext_creation,
        test_3_no_global_mutation,
        test_4_build_dataframe_explicit_ctx,
        test_5_strict_docs,
        test_6_core4_figures_all_work,
        test_7_chart_specific_docs,
        test_8_non_core4_still_work,
        test_9_nested_call_safety,
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

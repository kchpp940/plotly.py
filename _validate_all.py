"""Comprehensive validation of the chart-specific ParamMeta refactoring."""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import inspect
import plotly.graph_objects as go
import plotly.express as px
from plotly.express._params import PARAMS, ParamMeta
from plotly.express._core import (
    _install_attrable_lists, _restore_attrable_lists,
    direct_attrables, all_attrables,
)
import pandas as pd


def test_1_import_and_signature_check():
    """Module imports cleanly; signature check runs at import time."""
    print("✅ Test 1 PASSED: module imported, _assert_signatures_match_registry ran")


def test_2_parammeta_charts_applies_to():
    """ParamMeta.applies_to() and registry filter_params work correctly."""
    # orientation has _ORIENTATION_CHARTS = scatter, line, area, bar, histogram, ...
    om = PARAMS.get("orientation")
    assert om is not None, "orientation not registered"
    assert om.applies_to("scatter"), "orientation should apply to scatter"
    assert om.applies_to("line"), "orientation should apply to line"
    assert not om.applies_to("scatter_3d"), "orientation should NOT apply to scatter_3d"
    assert not om.applies_to("pie"), "orientation should NOT apply to pie"

    # size should only apply to scatter-like charts
    sm = PARAMS.get("size")
    assert sm.applies_to("scatter")
    assert sm.applies_to("scatter_matrix")
    assert not sm.applies_to("line")
    assert not sm.applies_to("bar")
    print("✅ Test 2 PASSED: ParamMeta.applies_to and registry queries correct")


def test_3_chart_specific_attrable_lists():
    """Chart-specific attrable lists differ from each other as expected."""
    # scatter has size, line has line_group, bar has base
    scatter_d, scatter_a, scatter_g, scatter_rg = PARAMS.get_attrable_lists("scatter")
    line_d, line_a, line_g, line_rg = PARAMS.get_attrable_lists("line")
    bar_d, bar_a, bar_g, bar_rg = PARAMS.get_attrable_lists("bar")
    hist_d, hist_a, hist_g, hist_rg = PARAMS.get_attrable_lists("histogram")

    assert "size" in scatter_d, "scatter attrable should include size"
    assert "size" not in line_d, "line attrable should NOT include size"
    assert "line_group" in line_g, "line attrable should include line_group"
    assert "line_group" not in scatter_g, "scatter attrable should NOT include line_group"
    assert "base" in bar_d, "bar attrable should include base"
    assert "base" not in hist_d, "histogram attrable should NOT include base"
    print("✅ Test 3 PASSED: chart-specific attrable lists correctly differ")


def test_4_core4_figure_generation():
    """Core 4 charts produce valid Figure objects with real data."""
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [10, 20, 30, 20, 10],
        "cat": ["a", "b", "a", "b", "a"],
    })

    # scatter with all its specific params: size, trendline, marginal_x/y, symbol
    fig1 = px.scatter(
        df, x="x", y="y", color="cat", size="y", symbol="cat",
        marginal_x="histogram", marginal_y="box",
        trendline="ols",
    )
    assert isinstance(fig1, go.Figure)
    assert len(fig1.data) >= 1
    print(f"  scatter OK: {len(fig1.data)} traces")

    # line with line_group
    df2 = pd.concat([df.assign(s=i) for i in range(2)])
    fig2 = px.line(df2, x="x", y="y", color="cat", line_group="s", markers=True)
    assert isinstance(fig2, go.Figure)
    assert len(fig2.data) >= 1
    print(f"  line OK: {len(fig2.data)} traces")

    # bar with pattern_shape (base requires a column ref, not a literal)
    fig3 = px.bar(df, x="x", y="y", color="cat", pattern_shape="cat")
    assert isinstance(fig3, go.Figure)
    assert len(fig3.data) >= 1
    print(f"  bar OK: {len(fig3.data)} traces")

    # histogram with histfunc, barnorm
    fig4 = px.histogram(
        df, x="x", y="y", color="cat",
        histfunc="sum", barnorm="percent", barmode="group", nbins=5,
    )
    assert isinstance(fig4, go.Figure)
    assert len(fig4.data) >= 1
    print(f"  histogram OK: {len(fig4.data)} traces")

    print("✅ Test 4 PASSED: all core 4 charts produce valid Figures")


def test_5_docstring_chart_specific():
    """Docstrings contain chart-specific params, not global ones."""
    scatter_doc = px.scatter.__doc__ or ""
    line_doc = px.line.__doc__ or ""
    bar_doc = px.bar.__doc__ or ""
    hist_doc = px.histogram.__doc__ or ""

    # scatter-only params
    assert "trendline_options" in scatter_doc, "scatter doc should mention trendline_options"
    assert "size_max" in scatter_doc, "scatter doc should mention size_max"
    assert "trendline_options" not in line_doc, "line doc should NOT mention trendline"
    assert "trendline_options" not in hist_doc, "hist doc should NOT mention trendline"

    # line-only params
    assert "line_group" in line_doc
    assert "line_dash" in line_doc
    assert "line_group" not in bar_doc

    # histogram-only params
    assert "barnorm" in hist_doc
    assert "histfunc" in hist_doc
    assert "nbins" in hist_doc
    assert "barnorm" not in bar_doc
    assert "histfunc" not in scatter_doc

    # bar-only params
    assert "base" in bar_doc
    assert "base" not in hist_doc

    print("✅ Test 5 PASSED: docstrings are chart-specific")


def test_6_chart_attrable_switching():
    """_install_attrable_lists / _restore_attrable_lists really swap globals."""
    from plotly.express import _core as core_mod

    original_all = list(core_mod.all_attrables)

    # scatter: should have size, not line_group
    saved = _install_attrable_lists("scatter")
    assert "size" in core_mod.all_attrables, "scatter-mode should include size"
    assert "line_group" not in core_mod.all_attrables, f"scatter-mode should NOT include line_group, got: {core_mod.all_attrables}"
    _restore_attrable_lists(saved)
    assert list(core_mod.all_attrables) == original_all, "should restore to original"

    # line: should have line_group but not size
    saved = _install_attrable_lists("line")
    assert "line_group" in core_mod.all_attrables
    assert "size" not in core_mod.all_attrables, f"line-mode should NOT include size, got: {core_mod.all_attrables}"
    _restore_attrable_lists(saved)
    assert list(core_mod.all_attrables) == original_all

    # histogram: should not have size or line_group
    saved = _install_attrable_lists("histogram")
    assert "size" not in core_mod.all_attrables, f"hist should NOT include size, got: {core_mod.all_attrables}"
    assert "line_group" not in core_mod.all_attrables, f"hist should NOT include line_group, got: {core_mod.all_attrables}"
    _restore_attrable_lists(saved)
    assert list(core_mod.all_attrables) == original_all

    print("✅ Test 6 PASSED: attrable global switching works correctly")


def test_7_smoke_non_core4_still_work():
    """Non-core4 charts (without chart_name=) still work via default globals."""
    df = pd.DataFrame({"values": [10, 20, 30], "names": ["a", "b", "c"]})
    # pie doesn't pass chart_name= yet - should still produce figure via defaults
    fig = px.pie(df, values="values", names="names")
    assert isinstance(fig, go.Figure) and len(fig.data) == 1
    print("✅ Test 7 PASSED: non-core4 charts (pie) still work via default attrable lists")


def main():
    print("\n" + "=" * 70)
    print("COMPREHENSIVE VALIDATION: chart-specific ParamMeta refactoring")
    print("=" * 70 + "\n")

    tests = [
        test_1_import_and_signature_check,
        test_2_parammeta_charts_applies_to,
        test_3_chart_specific_attrable_lists,
        test_4_core4_figure_generation,
        test_5_docstring_chart_specific,
        test_6_chart_attrable_switching,
        test_7_smoke_non_core4_still_work,
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

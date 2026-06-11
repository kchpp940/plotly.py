import plotly.express as px
import pandas as pd
import sys

df = pd.DataFrame({
    "x": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
    "y": [2, 4, 5, 4, 5, 1, 2, 3, 4, 5],
    "group": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B"],
})

def run_test(name, func):
    try:
        print(f"\n{name}")
        func()
        print("   PASSED")
        return True
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test1():
    """Test trendline='trendline' shorthand type"""
    fig = px.scatter(
        df, x="x", y="y", color="group",
        trendline="ols",
        summary=dict(type="trendline", show="all")
    )
    assert len(fig.data) == 4, f"Expected 4 traces, got {len(fig.data)}"
    print(f"   - Number of traces: {len(fig.data)}")

    data_trace = fig.data[0]
    trend_trace = fig.data[1]
    print(f"   - Data trace name: {data_trace.name}")
    print(f"   - Trend trace name: {trend_trace.name}")

    assert "Trend" in trend_trace.name, "Trendline trace name should contain 'Trend'"
    assert "Slope" in trend_trace.name or "R²" in trend_trace.name, "Trendline trace should contain fit stats"

    assert len(fig.layout.annotations) == 2, f"Expected 2 trendline annotations, got {len(fig.layout.annotations)}"
    print(f"   - Number of annotations: {len(fig.layout.annotations)}")

    for i, a in enumerate(fig.layout.annotations):
        print(f"   - Annotation {i}: {a.text[:50]}...")

def test2():
    """Test trendline with separate slope/rsquared specs"""
    fig = px.scatter(
        df, x="x", y="y", color="group",
        trendline="ols",
        summary=[
            dict(type="mean", show="all", scope="data"),
            dict(type="rsquared", show="all", scope="trendline", format=".3f"),
        ]
    )
    assert len(fig.data) == 4, f"Expected 4 traces, got {len(fig.data)}"

    data_trace = fig.data[0]
    trend_trace = fig.data[1]
    print(f"   - Data trace name: {data_trace.name}")
    print(f"   - Trend trace name: {trend_trace.name}")

    assert "Mean" in data_trace.name, "Data trace should have Mean summary"
    assert "R²" in trend_trace.name, "Trend trace should have R² summary"
    assert "Mean" not in trend_trace.name, "Trend trace should NOT have Mean summary"
    assert "R²" not in data_trace.name, "Data trace should NOT have R² summary"

    print(f"   - Data hover extra: {data_trace.hovertemplate}")
    print(f"   - Trend hover extra: {trend_trace.hovertemplate}")

    assert "Mean" in data_trace.hovertemplate, "Data hover should have Mean"
    assert "R²" in trend_trace.hovertemplate, "Trend hover should have R²"

def test3():
    """Test trendline with scope='all'"""
    fig = px.scatter(
        df, x="x", y="y", color="group",
        trendline="ols",
        summary=[
            dict(type="mean", show="legend", scope="all"),
        ]
    )
    data_trace = fig.data[0]
    trend_trace = fig.data[1]
    print(f"   - Data trace name: {data_trace.name}")
    print(f"   - Trend trace name: {trend_trace.name}")

    assert "Mean" in data_trace.name, "Data trace should have Mean (scope=all)"
    assert "Mean" in trend_trace.name, "Trend trace should also have Mean (scope=all)"

def test4():
    """Test trendline with animation_frame"""
    df_anim = pd.DataFrame({
        "x": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3],
        "y": [2, 4, 5, 1, 2, 3, 3, 6, 8, 2, 4, 6],
        "group": ["A", "A", "A", "B", "B", "B", "A", "A", "A", "B", "B", "B"],
        "frame": ["f1", "f1", "f1", "f1", "f1", "f1", "f2", "f2", "f2", "f2", "f2", "f2"],
    })
    fig = px.scatter(
        df_anim, x="x", y="y", color="group",
        animation_frame="frame",
        trendline="ols",
        summary=dict(type="trendline", show="all")
    )
    print(f"   - Number of frames: {len(fig.frames)}")
    for i, frame in enumerate(fig.frames):
        frame_annots = frame.layout.annotations if frame.layout and frame.layout.annotations else []
        print(f"   - Frame {i} ('{frame.name}'): {len(frame_annots)} annotations")
        print(f"     Data traces: {len(frame.data)}")
        for j, trace in enumerate(frame.data):
            print(f"       Trace {j}: {trace.name}")

    assert len(fig.frames) == 2, f"Expected 2 frames, got {len(fig.frames)}"
    for frame in fig.frames:
        assert len(frame.data) == 4, f"Each frame should have 4 traces"
        frame_annots = frame.layout.annotations if frame.layout and frame.layout.annotations else []
        assert len(frame_annots) == 2, f"Each frame should have 2 trendline annotations"

def test5():
    """Test that summary without trendline doesn't affect trend traces"""
    fig = px.scatter(
        df, x="x", y="y", color="group",
        trendline="ols",
        summary=dict(type="mean", show="all", scope="data")
    )
    data_trace = fig.data[0]
    trend_trace = fig.data[1]
    print(f"   - Data trace name: {data_trace.name}")
    print(f"   - Trend trace name: {trend_trace.name}")

    assert "Mean" in data_trace.name, "Data trace should have Mean"
    assert "Trend" in trend_trace.name, "Trend trace should have Trend label"
    assert "Mean" not in trend_trace.name, "Trend trace should NOT have Mean (scope=data)"

print("=" * 60)
print("Testing Trendline Summary Feature")
print("=" * 60)

all_passed = True
all_passed &= run_test("1. Test 'trendline' shorthand type", test1)
all_passed &= run_test("2. Test separate slope/rsquared specs", test2)
all_passed &= run_test("3. Test scope='all'", test3)
all_passed &= run_test("4. Test animation_frame with trendline", test4)
all_passed &= run_test("5. Test scope='data' doesn't affect trend traces", test5)

print("\n" + "=" * 60)
if all_passed:
    print("All tests PASSED!")
else:
    print("Some tests FAILED!")
    sys.exit(1)
print("=" * 60)

import plotly.express as px
import pandas as pd
import sys

df = pd.DataFrame({
    "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "y": [2, 4, 5, 4, 6, 7, 8, 9, 10, 12],
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

def test_ols():
    """Test OLS trendline with summary"""
    fig = px.scatter(df, x="x", y="y",
                     trendline="ols",
                     summary=dict(type="trendline", show="all"))
    assert len(fig.data) == 2
    trend_trace = fig.data[1]
    assert "Trend" in trend_trace.name
    assert "Slope" in trend_trace.name
    assert "R²" in trend_trace.name
    assert "Intercept" in trend_trace.name
    print(f"   - Trend name: {trend_trace.name}")
    assert len(fig.layout.annotations) == 1
    print(f"   - Annotations: {len(fig.layout.annotations)}")

def test_lowess():
    """Test LOWESS trendline with summary (should not show stats)"""
    fig = px.scatter(df, x="x", y="y",
                     trendline="lowess",
                     summary=dict(type="trendline", show="all"))
    assert len(fig.data) == 2
    trend_trace = fig.data[1]
    print(f"   - Trend name: {trend_trace.name}")
    assert "Trend" in trend_trace.name
    assert "Slope" not in trend_trace.name
    assert "R²" not in trend_trace.name
    print(f"   - Annotations: {len(fig.layout.annotations)}")

def test_rolling():
    """Test rolling trendline with summary (should not show stats)"""
    fig = px.scatter(df, x="x", y="y",
                     trendline="rolling",
                     trendline_options=dict(window=3),
                     summary=dict(type="trendline", show="all"))
    assert len(fig.data) == 2
    trend_trace = fig.data[1]
    print(f"   - Trend name: {trend_trace.name}")
    assert "Trend" in trend_trace.name
    assert "Slope" not in trend_trace.name
    assert "R²" not in trend_trace.name

def test_expanding():
    """Test expanding trendline with summary (should not show stats)"""
    fig = px.scatter(df, x="x", y="y",
                     trendline="expanding",
                     summary=dict(type="trendline", show="all"))
    assert len(fig.data) == 2
    trend_trace = fig.data[1]
    print(f"   - Trend name: {trend_trace.name}")
    assert "Trend" in trend_trace.name
    assert "Slope" not in trend_trace.name
    assert "R²" not in trend_trace.name

def test_ewm():
    """Test EWM trendline with summary (should not show stats)"""
    fig = px.scatter(df, x="x", y="y",
                     trendline="ewm",
                     trendline_options=dict(alpha=0.5),
                     summary=dict(type="trendline", show="all"))
    assert len(fig.data) == 2
    trend_trace = fig.data[1]
    print(f"   - Trend name: {trend_trace.name}")
    assert "Trend" in trend_trace.name
    assert "Slope" not in trend_trace.name
    assert "R²" not in trend_trace.name

def test_ols_rsquared_only():
    """Test OLS trendline with rsquared only"""
    fig = px.scatter(df, x="x", y="y",
                     trendline="ols",
                     summary=dict(type="rsquared", show="legend", scope="trendline"))
    trend_trace = fig.data[1]
    print(f"   - Trend name: {trend_trace.name}")
    assert "R²" in trend_trace.name
    assert "Slope" not in trend_trace.name
    assert "Intercept" not in trend_trace.name

def test_no_trendline():
    """Test summary with no trendline (data summary still works)"""
    fig = px.scatter(df, x="x", y="y",
                     summary=dict(type="mean", show="legend"))
    assert len(fig.data) == 1
    print(f"   - Trace name: {fig.data[0].name}")
    assert "Mean" in fig.data[0].name

def test_data_and_trendline_mixed():
    """Test mixed data and trendline summaries"""
    fig = px.scatter(df, x="x", y="y",
                     trendline="ols",
                     summary=[
                         dict(type="mean", show="legend", scope="data"),
                         dict(type="rsquared", show="legend", scope="trendline"),
                     ])
    data_trace = fig.data[0]
    trend_trace = fig.data[1]
    print(f"   - Data name: {data_trace.name}")
    print(f"   - Trend name: {trend_trace.name}")
    assert "Mean" in data_trace.name
    assert "R²" in trend_trace.name
    assert "Mean" not in trend_trace.name
    assert "R²" not in data_trace.name

print("=" * 60)
print("Testing Trendline Summary Parser Dispatch")
print("=" * 60)

all_passed = True
all_passed &= run_test("1. OLS trendline with full summary", test_ols)
all_passed &= run_test("2. LOWESS trendline (no stats)", test_lowess)
all_passed &= run_test("3. Rolling trendline (no stats)", test_rolling)
all_passed &= run_test("4. Expanding trendline (no stats)", test_expanding)
all_passed &= run_test("5. EWM trendline (no stats)", test_ewm)
all_passed &= run_test("6. OLS with rsquared only", test_ols_rsquared_only)
all_passed &= run_test("7. No trendline, data summary only", test_no_trendline)
all_passed &= run_test("8. Mixed data + trendline summaries", test_data_and_trendline_mixed)

print("\n" + "=" * 60)
if all_passed:
    print("All tests PASSED!")
else:
    print("Some tests FAILED!")
    sys.exit(1)
print("=" * 60)

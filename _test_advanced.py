import plotly.graph_objects as go
import plotly.express as px
from plotly._trace_selector import TraceSelector
from plotly.subplots import make_subplots

# Test 1: PX custom_data field-name selection
print("=== Test 1: PX custom_data field-name selection ===")
df = px.data.iris()
fig = px.scatter(df, x="sepal_width", y="sepal_length", custom_data=["species", "petal_width"])

# Check that _customdata_columns is set on the trace
for i, t in enumerate(fig.data):
    print(f"  Trace {i}: _customdata_columns = {t._customdata_columns}")

# Test field-name selector
sel = TraceSelector(customdata={"species": "setosa"})
matches = list(fig.select_traces_by_selector(sel))
print(f"  customdata species=setosa: {len(matches)} matches")
assert len(matches) == 1, f"Expected 1, got {len(matches)}"

sel = TraceSelector(customdata={"petal_width": 0.2})
matches = list(fig.select_traces_by_selector(sel))
print(f"  customdata petal_width=0.2: {len(matches)} matches")
assert len(matches) == 1

# Test update with field-name selector
sel = TraceSelector(customdata={"species": "versicolor"})
fig.update_traces_by_selector(sel, patch={"visible": "legendonly"})
for t in fig.data:
    print(f"  Trace {t.name}: visible={t.visible}")
assert fig.data[1].visible == "legendonly"
print("  PASS")

# Test 2: Domain-based subplot inference with secondary_y
print("\n=== Test 2: Domain-based subplot inference with secondary_y ===")
fig2 = make_subplots(rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": True}]])
fig2.add_scatter(y=[1, 2, 3], row=1, col=1, secondary_y=False, name="s1_primary")
fig2.add_scatter(y=[4, 5, 6], row=1, col=1, secondary_y=True, name="s1_secondary")
fig2.add_scatter(y=[7, 8, 9], row=1, col=2, secondary_y=True, name="s2_secondary")

# Test with col=1 (should match both primary and secondary at col=1 if secondary_y not specified)
sel = TraceSelector(col=1, type="scatter")
matches = list(fig2.select_traces_by_selector(sel))
print(f"  col=1 type=scatter: {len(matches)} matches")
names = {m.name for m in matches}
assert "s1_primary" in names
assert "s1_secondary" in names
assert "s2_secondary" not in names

# Test with col=1, secondary_y=True
sel = TraceSelector(col=1, secondary_y=True, type="scatter")
matches = list(fig2.select_traces_by_selector(sel))
print(f"  col=1 secondary_y=True type=scatter: {len(matches)} matches")
assert len(matches) == 1
assert matches[0].name == "s1_secondary"

# Test with col=1, secondary_y=False
sel = TraceSelector(col=1, secondary_y=False, type="scatter")
matches = list(fig2.select_traces_by_selector(sel))
print(f"  col=1 secondary_y=False type=scatter: {len(matches)} matches")
assert len(matches) == 1
assert matches[0].name == "s1_primary"
print("  PASS")

# Test 3: Domain-based inference for manual axes
print("\n=== Test 3: Domain-based inference for manual axes ===")
fig3 = go.Figure()
fig3.add_scatter(y=[1, 2, 3], xaxis="x", yaxis="y", name="s1")
fig3.add_scatter(y=[4, 5, 6], xaxis="x2", yaxis="y2", name="s2")
fig3.update_layout(
    xaxis=dict(domain=[0.0, 0.48]),
    xaxis2=dict(domain=[0.52, 1.0]),
    yaxis=dict(domain=[0.0, 1.0]),
    yaxis2=dict(domain=[0.0, 1.0]),
)

sel = TraceSelector(col=1)
matches = list(fig3.select_traces_by_selector(sel))
print(f"  col=1: {len(matches)} matches")
assert len(matches) == 1
assert matches[0].name == "s1"

sel = TraceSelector(col=2)
matches = list(fig3.select_traces_by_selector(sel))
print(f"  col=2: {len(matches)} matches")
assert len(matches) == 1
assert matches[0].name == "s2"
print("  PASS")

# Test 4: PX facet figure with row/col
print("\n=== Test 4: PX facet figure with row/col ===")
df2 = px.data.tips()
fig4 = px.scatter(df2, x="total_bill", y="tip", facet_row="time", facet_col="sex")

# Total of 4 subplots: 2 rows x 2 cols
sel = TraceSelector(row=1, col=1)
matches = list(fig4.select_traces_by_selector(sel))
print(f"  row=1 col=1: {len(matches)} matches")
assert len(matches) >= 1

sel = TraceSelector(row=2, col=2)
matches = list(fig4.select_traces_by_selector(sel))
print(f"  row=2 col=2: {len(matches)} matches")
assert len(matches) >= 1

sel = TraceSelector(row=1)
matches = list(fig4.select_traces_by_selector(sel))
print(f"  row=1: {len(matches)} matches")
assert len(matches) >= 2

sel = TraceSelector(col=1)
matches = list(fig4.select_traces_by_selector(sel))
print(f"  col=1: {len(matches)} matches")
assert len(matches) >= 2
print("  PASS")

# Test 5: Manual field-name setup (non-PX)
print("\n=== Test 5: Manual field-name setup (non-PX) ===")
fig5 = go.Figure()
trace = go.Scatter(
    y=[1, 2, 3],
    customdata=[["APAC", 100], ["EMEA", 200], ["APAC", 300]],
    name="t1",
)
trace._customdata_columns = {"region": 0, "value": 1}
fig5.add_trace(trace)

sel = TraceSelector(customdata={"region": "APAC"})
matches = list(fig5.select_traces_by_selector(sel))
print(f"  customdata region=APAC: {len(matches)} matches")
assert len(matches) == 1
assert matches[0].name == "t1"

sel = TraceSelector(customdata={"value": 200})
matches = list(fig5.select_traces_by_selector(sel))
print(f"  customdata value=200: {len(matches)} matches")
assert len(matches) == 1
print("  PASS")

# Test 6: Mixed numeric index and field-name (col_map takes precedence)
print("\n=== Test 6: Mixed numeric index and field-name ===")
fig6 = go.Figure()
trace = go.Scatter(
    y=[1, 2, 3],
    customdata=[["APAC", 100], ["EMEA", 200]],
    name="t1",
)
trace._customdata_columns = {"region": 0, "value": 1}
fig6.add_trace(trace)

# Field-name "0" is ambiguous - since col_map has no "0", it falls back to numeric index
sel = TraceSelector(customdata={"0": "APAC"})
matches = list(fig6.select_traces_by_selector(sel))
print(f"  customdata 0=APAC (no col_map entry): {len(matches)} matches")
assert len(matches) == 1

# But field-name "region" uses col_map
sel = TraceSelector(customdata={"region": "APAC"})
matches = list(fig6.select_traces_by_selector(sel))
print(f"  customdata region=APAC (col_map entry): {len(matches)} matches")
assert len(matches) == 1
print("  PASS")

print("\n=== All smoke tests PASSED ===")

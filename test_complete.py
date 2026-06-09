import pandas as pd
import plotly.express as px

# Test duplicate column names with full trace info
print("=" * 60)
print("Test: Duplicate column names - all traces")
print("=" * 60)
df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=["a", "a", "b"])
print("Original columns:", df.columns.tolist())
fig = px.line(df, y=["a", "a", "b"])
print("Number of traces:", len(fig.data))
for i, t in enumerate(fig.data):
    print(f"  Trace {i}:")
    print(f"    name: {t.name!r}")
    print(f"    legendgroup: {t.legendgroup!r}")
    print(f"    hovertemplate: {t.hovertemplate}")
    print(f"    y: {list(t.y)}")
    print(f"    x: {list(t.x)}")
    if hasattr(t, 'marker') and t.marker and hasattr(t.marker, 'color'):
        print(f"    marker.color: {list(t.marker.color) if t.marker.color is not None else None}")

print()
print("=" * 60)
print("Test: Duplicate columns with labels - verify labels work")
print("=" * 60)
df2 = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=["a", "a", "b"])
fig2 = px.line(
    df2, y=["a", "a", "b"], 
    labels={"variable": "MySeries", "value": "MyValue", "a": "LabelForA"}
)
print("Number of traces:", len(fig2.data))
print("Legend title:", fig2.layout.legend.title.text if fig2.layout.legend.title else None)
print("Y-axis title:", fig2.layout.yaxis.title.text)
for i, t in enumerate(fig2.data):
    print(f"  Trace {i}:")
    print(f"    name: {t.name!r}")
    print(f"    hovertemplate: {t.hovertemplate}")

print()
print("=" * 60)
print("Test: hover_data dict + custom_data - verify wide_id_vars")
print("=" * 60)
df3 = pd.DataFrame({
    "x": [1, 2, 3],
    "y1": [4, 5, 6],
    "y2": [7, 8, 9],
    "h1": [10, 11, 12],
    "h2": [100, 200, 300],
})
print("Original columns:", df3.columns.tolist())

# Scenario: hover_data is dict
fig3 = px.line(
    df3, x="x", y=["y1", "y2"],
    hover_data={"h1": True, "h2": ":,.2f"},
    custom_data=["h1"]
)
print("Number of traces:", len(fig3.data))
for i, t in enumerate(fig3.data):
    print(f"  Trace {i}:")
    print(f"    name: {t.name!r}")
    print(f"    hovertemplate: {t.hovertemplate}")
    cd = t.customdata
    ncols = len(cd[0]) if (cd is not None and len(cd) > 0) else 0
    print(f"    customdata cols: {ncols}")
    if ncols > 0:
        for j in range(min(3, len(cd))):
            print(f"    customdata[{j}]: {list(cd[j])}")

print()
print("=" * 60)
print("Test: px.bar, px.area with wide-form - consistency")
print("=" * 60)
df4 = pd.DataFrame({"cat": ["A", "B", "C"], "v1": [1, 2, 3], "v2": [4, 5, 6]})

print("px.bar:")
fig_bar = px.bar(df4, x="cat", y=["v1", "v2"], labels={"variable": "Type", "value": "Count"})
print(f"  legend title: {fig_bar.layout.legend.title.text if fig_bar.layout.legend.title else None}")
print(f"  y-axis title: {fig_bar.layout.yaxis.title.text}")
for i, t in enumerate(fig_bar.data):
    print(f"  Trace {i}: name={t.name!r}, hovertemplate={t.hovertemplate}")

print()
print("px.area:")
df5 = pd.DataFrame({"x": [1, 2, 3], "y1": [4, 5, 6], "y2": [7, 8, 9]})
fig_area = px.area(df5, x="x", y=["y1", "y2"], labels={"variable": "Series", "value": "Amount"})
print(f"  legend title: {fig_area.layout.legend.title.text if fig_area.layout.legend.title else None}")
print(f"  y-axis title: {fig_area.layout.yaxis.title.text}")
for i, t in enumerate(fig_area.data):
    print(f"  Trace {i}: name={t.name!r}, stackgroup={t.stackgroup}, hovertemplate={t.hovertemplate}")

print()
print("=" * 60)
print("Test: Named Index")
print("=" * 60)
df6 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
df6.index.name = "time_idx"
fig6 = px.line(df6, labels={"variable": "Metric", "value": "Value"})
print(f"  x-axis title: {fig6.layout.xaxis.title.text}")
print(f"  y-axis title: {fig6.layout.yaxis.title.text}")
print(f"  legend title: {fig6.layout.legend.title.text if fig6.layout.legend.title else None}")
for i, t in enumerate(fig6.data):
    print(f"  Trace {i}: name={t.name!r}, hovertemplate={t.hovertemplate}")

# Check for internal name leaks
print()
print("=" * 60)
print("Test: No internal name leaks (wide_variable, wide_cross)")
print("=" * 60)
all_figs = [("duplicate cols", fig), ("labels", fig2), ("hover+custom", fig3), ("bar", fig_bar), ("area", fig_area), ("named index", fig6)]
all_ok = True
for name, f in all_figs:
    for i, t in enumerate(f.data):
        ht = str(t.hovertemplate) if t.hovertemplate else ""
        for bad in ["wide_variable", "wide_cross"]:
            if bad in ht:
                print(f"  LEAK in {name} trace[{i}]: found '{bad}'")
                all_ok = False
if all_ok:
    print("  ✓ All figures: no internal name leaks found")

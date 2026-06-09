import pandas as pd
import plotly.express as px

# Test duplicate column names - trace names should show original column names
print("=" * 60)
print("Test 1: Duplicate column names with trace names")
print("=" * 60)
df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=["a", "a", "b"])
print("Original columns:", df.columns.tolist())
fig = px.line(df, y=["a", "a", "b"])
print("Trace names:", [t.name for t in fig.data])
for i, t in enumerate(fig.data):
    print(f"  Trace {i}: name={t.name!r}, y={list(t.y)}")
print()
print("hovertemplate:", fig.data[0].hovertemplate)

# Also test with labels
print()
print("=" * 60)
print("Test 2: Duplicate columns with labels")
print("=" * 60)
df2 = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=["a", "a", "b"])
fig2 = px.line(df2, y=["a", "a", "b"], labels={"variable": "Series", "value": "Measure"})
print("With labels:")
print("  legend title:", fig2.layout.legend.title.text if fig2.layout.legend.title else None)
print("  y-axis title:", fig2.layout.yaxis.title.text)
print("  trace names:", [t.name for t in fig2.data])
print("  hovertemplate[0]:", fig2.data[0].hovertemplate)

# Test hover_data + custom_data with wide-form
print()
print("=" * 60)
print("Test 3: hover_data dict + custom_data with wide-form")
print("=" * 60)
df3 = pd.DataFrame({
    "x": [1, 2, 3],
    "y1": [4, 5, 6],
    "y2": [7, 8, 9],
    "h1": [10, 11, 12],
    "h2": [100, 200, 300],
})
# Scenario 1: hover_data list + custom_data list
print("Scenario 1: hover_data=list, custom_data=list")
fig3a = px.line(df3, x="x", y=["y1", "y2"], hover_data=["h1", "h2"], custom_data=["h1"])
for i, t in enumerate(fig3a.data):
    print(f"  Trace {i}:")
    print(f"    hovertemplate: {t.hovertemplate}")
    cd = t.customdata
    ncols = len(cd[0]) if (cd is not None and len(cd) > 0) else 0
    print(f"    customdata cols: {ncols}")
    if ncols > 0:
        print(f"    customdata[0]: {list(cd[0])}")

# Scenario 2: hover_data dict + custom_data list
print()
print("Scenario 2: hover_data=dict, custom_data=list")
fig3b = px.line(df3, x="x", y=["y1", "y2"], hover_data={"h1": True, "h2": ":,.2f"}, custom_data=["h1"])
for i, t in enumerate(fig3b.data):
    print(f"  Trace {i}:")
    print(f"    hovertemplate: {t.hovertemplate}")
    cd = t.customdata
    ncols = len(cd[0]) if (cd is not None and len(cd) > 0) else 0
    print(f"    customdata cols: {ncols}")
    if ncols > 0:
        print(f"    customdata[0]: {list(cd[0])}")

# Test px.bar and px.area
print()
print("=" * 60)
print("Test 4: px.bar and px.area wide-form")
print("=" * 60)
df4 = pd.DataFrame({"cat": ["A", "B", "C"], "v1": [1, 2, 3], "v2": [4, 5, 6]})
print("px.bar:")
fig_bar = px.bar(df4, x="cat", y=["v1", "v2"])
print(f"  trace names: {[t.name for t in fig_bar.data]}")
print(f"  hovertemplate[0]: {fig_bar.data[0].hovertemplate}")
print(f"  no internal names (wide_variable/wide_cross): {all('wide_variable' not in t.hovertemplate and 'wide_cross' not in t.hovertemplate for t in fig_bar.data)}")

print()
print("px.area:")
fig_area = px.area(df3, x="x", y=["y1", "y2"])
print(f"  trace names: {[t.name for t in fig_area.data]}")
print(f"  hovertemplate[0]: {fig_area.data[0].hovertemplate}")
print(f"  no internal names (wide_variable/wide_cross): {all('wide_variable' not in t.hovertemplate and 'wide_cross' not in t.hovertemplate for t in fig_area.data)}")

print()
print("=" * 60)
print("Test 5: Named Index with px.line")
print("=" * 60)
df5 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
df5.index.name = "time"
fig5 = px.line(df5)
print(f"  x-axis title: {fig5.layout.xaxis.title.text}")
print(f"  y-axis title: {fig5.layout.yaxis.title.text}")
print(f"  legend title: {fig5.layout.legend.title.text if fig5.layout.legend.title else None}")
print(f"  trace names: {[t.name for t in fig5.data]}")
print(f"  hovertemplate[0]: {fig5.data[0].hovertemplate}")

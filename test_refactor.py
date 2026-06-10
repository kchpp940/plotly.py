from plotly.express._core import build_dataframe
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Test case 1: columns named 'index', 'value', 'variable'
print("=== Test 1: columns collide with reserved names ===")
df = pd.DataFrame(
    dict(index=[7, 8], value=[1, 3], variable=[2, 4]),
    index=[7, 8]
)
args = dict(data_frame=df, x=None, y=None, color=None)
result = build_dataframe(args, go.Scatter)
print("x:", result.get("x"))
print("y:", result.get("y"))
print("color:", result.get("color"))
print("labels:", result.get("labels"))
print("_col_map:", result.get("_col_map"))
print("df columns:", list(result["data_frame"].columns))
assert result.get("x") == "index", f"Expected 'index', got {result.get('x')}"
assert result.get("y") == "value", f"Expected 'value', got {result.get('y')}"
assert result.get("color") == "variable", f"Expected 'variable', got {result.get('color')}"
assert "_col_map" in result, "Expected _col_map"
assert result["_col_map"]["index"] == "_index"
assert result["_col_map"]["value"] == "_value"
assert result["_col_map"]["variable"] == "_variable"
print("PASS")
print()

# Test case 2: named index and columns
print("=== Test 2: named index/columns that collide with data columns ===")
df2 = pd.DataFrame(dict(a=[1, 2], b=[3, 4]), index=[7, 8])
df2.index.name = "a"
df2.columns.name = "b"
args2 = dict(data_frame=df2, x=None, y=None, color=None)
result2 = build_dataframe(args2, go.Scatter)
print("x:", result2.get("x"))
print("y:", result2.get("y"))
print("color:", result2.get("color"))
print("labels:", result2.get("labels"))
print("_col_map:", result2.get("_col_map"))
print("df columns:", list(result2["data_frame"].columns))
assert result2.get("x") == "a", f"Expected 'a', got {result2.get('x')}"
assert result2.get("y") == "value", f"Expected 'value', got {result2.get('y')}"
assert result2.get("color") == "b", f"Expected 'b', got {result2.get('color')}"
assert result2["_col_map"]["a"] == "index"
assert result2["_col_map"]["b"] == "variable"
print("PASS")
print()

# Test case 3: px.line end-to-end
print("=== Test 3: px.line end-to-end ===")
df3 = pd.DataFrame(
    dict(index=[7, 8], value=[1, 3], variable=[2, 4]),
    index=[7, 8]
)
fig = px.line(df3)
print("xaxis title:", fig.layout.xaxis.title.text)
print("yaxis title:", fig.layout.yaxis.title.text)
print("legend title:", fig.layout.legend.title.text)
print("trace names:", [t.name for t in fig.data])
assert fig.layout.xaxis.title.text == "index"
assert fig.layout.yaxis.title.text == "value"
assert fig.layout.legend.title.text == "variable"
print("PASS")
print()

# Test case 4: px.line with named index and columns
print("=== Test 4: px.line with named index/columns ===")
df4 = pd.DataFrame(dict(a=[1, 2], b=[3, 4]), index=[7, 8])
df4.index.name = "idx"
df4.columns.name = "cols"
fig4 = px.line(df4)
print("xaxis title:", fig4.layout.xaxis.title.text)
print("yaxis title:", fig4.layout.yaxis.title.text)
print("legend title:", fig4.layout.legend.title.text)
print("trace names:", [t.name for t in fig4.data])
assert fig4.layout.xaxis.title.text == "idx"
assert fig4.layout.yaxis.title.text == "value"
assert fig4.layout.legend.title.text == "cols"
print("PASS")
print()

# Test case 5: duplicate column names
print("=== Test 5: duplicate column names ===")
df5 = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=['a', 'a', 'b'])
fig5 = px.line(df5)
print("trace names:", [t.name for t in fig5.data])
print("legend title:", fig5.layout.legend.title.text)
print("PASS")
print()

# Test case 6: px.area
print("=== Test 6: px.area ===")
df6 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
fig6 = px.area(df6)
print("xaxis title:", fig6.layout.xaxis.title.text)
print("yaxis title:", fig6.layout.yaxis.title.text)
print("legend title:", fig6.layout.legend.title.text)
print("trace names:", [t.name for t in fig6.data])
print("trace 0 hovertemplate:", fig6.data[0].hovertemplate)
assert "wide_variable" not in fig6.data[0].hovertemplate
assert "wide_cross" not in fig6.data[0].hovertemplate
print("PASS")
print()

# Test case 7: px.bar
print("=== Test 7: px.bar ===")
df7 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
fig7 = px.bar(df7)
print("xaxis title:", fig7.layout.xaxis.title.text)
print("yaxis title:", fig7.layout.yaxis.title.text)
print("legend title:", fig7.layout.legend.title.text)
print("trace names:", [t.name for t in fig7.data])
print("trace 0 hovertemplate:", fig7.data[0].hovertemplate)
assert "wide_variable" not in fig7.data[0].hovertemplate
assert "wide_cross" not in fig7.data[0].hovertemplate
print("PASS")
print()

# Test case 8: hover_data with wide-form
print("=== Test 8: hover_data with wide-form ===")
df8 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
fig8 = px.line(df8, hover_data={"new": [10, 20, 30, 40, 50, 60]})
print("trace 0 hovertemplate:", fig8.data[0].hovertemplate)
print("trace 0 customdata shape:", len(fig8.data[0].customdata[0]) if fig8.data[0].customdata is not None else "None")
print("PASS")
print()

# Test case 9: custom_data with wide-form
print("=== Test 9: custom_data with wide-form ===")
df9 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
fig9 = px.line(df9, custom_data=[[10, 20, 30, 40, 50, 60]])
print("trace 0 customdata shape:", len(fig9.data[0].customdata[0]) if fig9.data[0].customdata is not None else "None")
print("PASS")
print()

print("=== ALL TESTS PASSED ===")

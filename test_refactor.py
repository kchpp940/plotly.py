from plotly.express._core import build_dataframe
import plotly.graph_objects as go
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
print()

# Test case 3: test px.line end-to-end
print("=== Test 3: px.line end-to-end ===")
import plotly.express as px
df3 = pd.DataFrame(
    dict(index=[7, 8], value=[1, 3], variable=[2, 4]),
    index=[7, 8]
)
try:
    fig = px.line(df3)
    print("xaxis title:", fig.layout.xaxis.title.text)
    print("yaxis title:", fig.layout.yaxis.title.text)
    print("legend title:", fig.layout.legend.title.text)
    print("trace names:", [t.name for t in fig.data])
    print("hovertemplate:", fig.data[0].hovertemplate)
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()

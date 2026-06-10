from plotly.express._core import build_dataframe
import plotly.graph_objects as go
import pandas as pd

# Test case: everything is called value
df = pd.DataFrame(dict(b=[1, 2], value=[3, 4]), index=[7, 8])
df.index.name = "value"
df.columns.name = "value"
args = dict(data_frame=df, x=None, y=None, color=None)
result = build_dataframe(args, go.Scatter)
print("x:", result.get("x"))
print("y:", result.get("y"))
print("color:", result.get("color"))
print("labels:", result.get("labels"))
print("_col_map:", result.get("_col_map"))
print("df columns:", list(result["data_frame"].columns))
print("df head:")
print(result["data_frame"].to_pandas())

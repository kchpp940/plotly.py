import plotly.express as px
import pandas as pd
import numpy as np
import narwhals.stable.v1 as nw

print("=== Test 1: Named Index ===")
df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6], c=[7, 8, 9]))
df.index.name = "my_index"
df.columns.name = "my_columns"
print("DF index name:", df.index.name)
print("DF columns name:", df.columns.name)
fig = px.line(df)
print("x-axis title:", fig.layout.xaxis.title.text)
print("y-axis title:", fig.layout.yaxis.title.text)
print("legend title:", fig.layout.legend.title.text)
print()

print("=== Test 2: Duplicate column names ===")
try:
    df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=["a", "a", "b"])
    print("DF columns:", df.columns.tolist())
    fig = px.line(df)
    print("Success - Number of traces:", len(fig.data))
    for i, d in enumerate(fig.data):
        print(f"  Trace {i}: y = {list(d.y)}, name = {d.name}")
except Exception as e:
    print("Error:", type(e).__name__, str(e))
print()

print("=== Test 3: labels, hover_data and custom_data mixing ===")
df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6], extra=["x", "y", "z"]))
df.index.name = "time"
fig = px.line(
    df,
    y=["a", "b"],
    labels={"variable": "Series", "value": "Measurement", "time": "Time"},
    hover_data={"extra": True},
    custom_data=["extra"],
)
print("x-axis title:", fig.layout.xaxis.title.text)
print("y-axis title:", fig.layout.yaxis.title.text)
print("legend title:", fig.layout.legend.title.text)
print(
    "customdata sample:",
    fig.data[0].customdata[:2] if hasattr(fig.data[0], "customdata") else "None",
)
print("hovertemplate:", fig.data[0].hovertemplate)
print()

print("=== Test 4: Internal names in hover template ===")
df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6]))
fig = px.area(df, hover_data={"variable": True, "value": True})
print("hovertemplate:", fig.data[0].hovertemplate)
print()

print("=== Test 5: Explicit y=columns with named index/columns ===")
df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6]), index=[10, 20, 30])
df.index.name = "x_name"
df.columns.name = "y_name"
fig = px.line(df, y=df.columns, x=df.index)
print("x-axis title:", fig.layout.xaxis.title.text)
print("y-axis title:", fig.layout.yaxis.title.text)
print("legend title:", fig.layout.legend.title.text)
print()

print("=== Test 6: Wide form with hover_data dict (raw data) ===")
df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6]))
df.index.name = "c"
df.columns.name = "d"
fig = px.bar(df, hover_data=dict(new=[5, 6, 7, 8, 9, 10]))
print("x-axis title:", fig.layout.xaxis.title.text)
print("y-axis title:", fig.layout.yaxis.title.text)
print("legend title:", fig.layout.legend.title.text)
print("hovertemplate:", fig.data[0].hovertemplate)
print()

print("=== Test 7: Bar with wide mode and named index ===")
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]), index=[7, 8])
df.index.name = "c"
df.columns.name = "d"
fig = px.bar(df)
print("x-axis title:", fig.layout.xaxis.title.text)
print("y-axis title:", fig.layout.yaxis.title.text)
print("legend title:", fig.layout.legend.title.text)
print()

print("=== Test 8: Narwhals DataFrame consistency ===")
import polars as pl

df_pd = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6]))
df_pd.index.name = "idx"
df_pd.columns.name = "cols"
df_pl = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "idx": [0, 1, 2]})

fig_pd = px.line(df_pd)
fig_pl = px.line(df_pl, x="idx", y=["a", "b"])
print("Pandas - x-axis:", fig_pd.layout.xaxis.title.text)
print("Pandas - y-axis:", fig_pd.layout.yaxis.title.text)
print("Pandas - legend:", fig_pd.layout.legend.title.text)
print("Polars - x-axis:", fig_pl.layout.xaxis.title.text)
print("Polars - y-axis:", fig_pl.layout.yaxis.title.text)
print("Polars - legend:", fig_pl.layout.legend.title.text)

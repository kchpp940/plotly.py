import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Test PX facet figure
df = px.data.tips()
fig = px.scatter(df, x="total_bill", y="tip", facet_row="time", facet_col="sex")
print("=== PX facet_row+col ===")
for key in sorted(fig.layout):
    if "axis" in key.lower() and not key.startswith("_"):
        val = fig.layout[key]
        if hasattr(val, "domain") and val.domain is not None:
            print(f"  {key}.domain = {val.domain}")
        else:
            print(f"  {key} (no domain attr)")

# Test make_subplots with secondary_y
fig2 = make_subplots(rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": True}]])
fig2.add_scatter(y=[1, 2, 3], row=1, col=1, secondary_y=False)
fig2.add_scatter(y=[4, 5, 6], row=1, col=1, secondary_y=True)
fig2.add_scatter(y=[7, 8, 9], row=1, col=2, secondary_y=True)
print("\n=== make_subplots with secondary_y ===")
for key in sorted(fig2.layout):
    if "axis" in key.lower() and not key.startswith("_"):
        val = fig2.layout[key]
        if hasattr(val, "domain") and val.domain is not None:
            print(f"  {key}.domain = {val.domain}")

# Test simple PE figure with shared axes
fig3 = px.scatter(df, x="total_bill", y="tip", facet_col="sex")
print("\n=== PX facet_col (shared xaxis) ===")
for key in sorted(fig3.layout):
    if "axis" in key.lower() and not key.startswith("_"):
        val = fig3.layout[key]
        if hasattr(val, "domain") and val.domain is not None:
            print(f"  {key}.domain = {val.domain}")

# Test PX customdata column names
df2 = px.data.iris()
fig4 = px.scatter(df2, x="sepal_width", y="sepal_length", custom_data=["species", "petal_width"])
print("\n=== PX custom_data ===")
for i, t in enumerate(fig4.data):
    print(f"  Trace {i}: customdata type={type(t.customdata)} len={len(t.customdata)}")
    if t.customdata:
        print(f"    first row type={type(t.customdata[0])} val={t.customdata[0]}")

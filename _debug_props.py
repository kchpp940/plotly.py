import copy
import plotly.graph_objs as go
from plotly.subplots import make_subplots

fig = make_subplots(
    rows=3,
    cols=2,
    specs=[
        [{}, {"type": "scene"}],
        [{"secondary_y": True}, {"type": "polar"}],
        [{"type": "domain", "colspan": 2}, None],
    ],
).update(layout={"height": 800})

fig.add_scatter3d(
    x=[0, 0, 0],
    y=[0, 0, 0],
    z=[0, 1, 2],
    mode="markers",
    marker={"color": "green", "size": 10},
    name="E",
    row=1,
    col=2,
)

print("Before deepcopy and update:")
print(f"  fig.data[0]._props: {fig.data[0]._props}")

fig_orig = copy.deepcopy(fig)
for trace1, trace2 in zip(fig_orig.data, fig.data):
    trace1.uid = trace2.uid

print("\nAfter deepcopy (before update):")
print(f"  fig.data[0]._props: {fig.data[0]._props}")
print(f"  fig_orig.data[0]._props: {fig_orig.data[0]._props}")
print(f"  Are _props equal? {fig.data[0]._props == fig_orig.data[0]._props}")
print(f"  fig.data[0] == fig_orig.data[0]: {fig.data[0] == fig_orig.data[0]}")

patch = {"marker": {"line": {"color": "yellow"}}}
fig.update_traces(patch, selector={"type": "scatter3d"})

print("\nAfter fig.update_traces:")
print(f"  fig.data[0]._props: {fig.data[0]._props}")
print(f"  fig_orig.data[0]._props: {fig_orig.data[0]._props}")
print(f"  Are _props equal? {fig.data[0]._props == fig_orig.data[0]._props}")
print(f"  fig.data[0] == fig_orig.data[0]: {fig.data[0] == fig_orig.data[0]}")

# Now update fig_orig manually
fig_orig.data[0].update(patch)

print("\nAfter manual update of fig_orig.data[0]:")
print(f"  fig.data[0]._props: {fig.data[0]._props}")
print(f"  fig_orig.data[0]._props: {fig_orig.data[0]._props}")
print(f"  Are _props equal? {fig.data[0]._props == fig_orig.data[0]._props}")
print(f"  fig.data[0] == fig_orig.data[0]: {fig.data[0] == fig_orig.data[0]}")

# Also check if _customdata_columns is set
print(f"\nfig.data[0]._customdata_columns: {fig.data[0]._customdata_columns}")
print(f"fig_orig.data[0]._customdata_columns: {fig_orig.data[0]._customdata_columns}")

# Check _vals_equal
from plotly.basedatatypes import BasePlotlyType
print(f"\n_vals_equal result: {BasePlotlyType._vals_equal(fig.data[0]._props, fig_orig.data[0]._props)}")

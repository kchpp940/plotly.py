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

print(f"Trace type: {fig.data[0].type}")
print(f"Initial marker: {fig.data[0].marker}")

# Test selecting
selected = list(fig.select_traces(selector={"type": "scatter3d"}))
print(f"Number of selected traces: {len(selected)}")

# Test update
fig.update_traces(
    {"marker": {"line": {"color": "yellow"}}},
    selector={"type": "scatter3d"},
)

print(f"After update marker: {fig.data[0].marker}")

# Also try direct update
fig.data[0].update({"marker": {"line": {"color": "yellow"}}})
print(f"After direct update marker: {fig.data[0].marker}")

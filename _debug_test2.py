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

# data[0], (1, 1)
fig.add_scatter(
    mode="markers",
    y=[2, 3, 1],
    name="A",
    marker={"color": "green", "size": 10},
    row=1,
    col=1,
)

# data[1], (1, 1)
fig.add_bar(y=[2, 3, 1], row=1, col=1, name="B")

# data[2], (2, 1)
fig.add_scatter(
    mode="lines", y=[1, 2, 0], line={"color": "purple"}, name="C", row=2, col=1
)

# data[3], (2, 1)
fig.add_heatmap(z=[[2, 3, 1], [2, 1, 3], [3, 2, 1]], row=2, col=1, name="D")

# data[4], (1, 2)
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

# data[5], (1, 2)
fig.add_scatter3d(
    x=[0, 0, -1],
    y=[-1, 0, 0],
    z=[0, 1, 2],
    mode="lines",
    line={"color": "purple", "width": 4},
    name="F",
    row=1,
    col=2,
)

# data[6], (2, 2)
fig.add_scatterpolar(
    mode="markers",
    r=[0, 3, 2],
    theta=[0, 20, 87],
    marker={"color": "green", "size": 8},
    name="G",
    row=2,
    col=2,
)

# data[7], (2, 2)
fig.add_scatterpolar(
    mode="lines", r=[0, 3, 2], theta=[20, 87, 111], name="H", row=2, col=2
)

# data[8], (3, 1)
fig.add_parcoords(
    dimensions=[{"values": [1, 2, 3, 2, 1]}, {"values": [3, 2, 1, 3, 2, 1]}],
    line={"color": "purple"},
    name="I",
    row=3,
    col=1,
)

# data[9], (2, 1) with secondary_y
fig.add_scatter(
    mode="lines",
    y=[1, 2, 0],
    line={"color": "purple"},
    name="C",
    row=2,
    col=1,
    secondary_y=True,
)

print("Before update:")
print(f"  Trace 4 (E) marker: {fig.data[4].marker}")
print(f"  Trace 5 (F) marker: {fig.data[5].marker}")

# Deepcopy like the test does
fig_orig = copy.deepcopy(fig)
for trace1, trace2 in zip(fig_orig.data, fig.data):
    trace1.uid = trace2.uid

# Check if deepcopy preserved the marker
print("\nAfter deepcopy (fig_orig):")
print(f"  Trace 4 (E) marker: {fig_orig.data[4].marker}")
print(f"  fig.data[4] == fig_orig.data[4]: {fig.data[4] == fig_orig.data[4]}")

# Now call update_traces like the test does
patch = {"marker": {"line": {"color": "yellow"}}}
fig.update_traces(patch, selector={"type": "scatter3d"})

print("\nAfter fig.update_traces:")
print(f"  Trace 4 (E) marker: {fig.data[4].marker}")
print(f"  Trace 5 (F) marker: {fig.data[5].marker}")

print(f"\n  fig.data[4] == fig_orig.data[4]: {fig.data[4] == fig_orig.data[4]}")

# Now update fig_orig manually
fig_orig.data[4].update(patch)
fig_orig.data[5].update(patch)

print("\nAfter manual update of fig_orig:")
print(f"  Trace 4 (E) marker: {fig_orig.data[4].marker}")
print(f"  fig.data[4] == fig_orig.data[4]: {fig.data[4] == fig_orig.data[4]}")

# Now check if the trace objects are the same after update
print(f"\nTrace 4 id before update: (we lost it)")
print(f"Trace 4 id after update: {id(fig.data[4])}")

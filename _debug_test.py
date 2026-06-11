import copy
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Recreate the test setup
fig = make_subplots(rows=2, cols=2)

fig.add_scatter(y=[1, 2], row=1, col=1, name="A")
fig.add_bar(y=[1, 2], row=1, col=2, name="B")
fig.add_scatter(y=[1, 2], row=2, col=1, name="C")
fig.add_heatmap(z=[[1, 2], [3, 4]], row=2, col=2, name="D")
fig.add_scatter3d(x=[0, 0], y=[0, 0], z=[0, 1], row=1, col=1, name="E")
fig.add_scatter3d(x=[0, 0], y=[0, 0], z=[0, 1], row=1, col=2, name="F")
fig.add_mesh3d(x=[0, 0, 0], y=[0, 0, 0], z=[0, 0, 1], row=2, col=1, name="G")
fig.add_cone(x=[0], y=[0], z=[0], u=[0], v=[0], w=[1], row=2, col=2, name="H")
fig.add_streamtube(x=[0, 0], y=[0, 0], z=[0, 1], u=[0, 0], v=[0, 0], w=[0, 1], row=1, col=1, name="I")
fig.add_scatter(y=[1, 2], row=1, col=1, name="J")

print(f"Trace types: {[t.type for t in fig.data]}")
print(f"Trace 0 type: {fig.data[0].type}")
print(f"Trace 2 type: {fig.data[2].type}")
print(f"Trace 9 type: {fig.data[9].type}")

# Test deepcopy
fig_orig = copy.deepcopy(fig)
for trace1, trace2 in zip(fig_orig.data, fig.data):
    trace1.uid = trace2.uid

print("\nAfter deepcopy:")
print(f"fig.data[0] == fig_orig.data[0]: {fig.data[0] == fig_orig.data[0]}")
print(f"fig.data[0]._customdata_columns: {fig.data[0]._customdata_columns}")
print(f"fig_orig.data[0]._customdata_columns: {fig_orig.data[0]._customdata_columns}")

# Now test update_traces
fig.update_traces({"visible": "legendonly"}, selector={"type": "scatter"})

print("\nAfter update_traces:")
print(f"fig.data[0].visible: {fig.data[0].visible}")
print(f"fig.data[1].visible: {fig.data[1].visible}")
print(f"fig.data[2].visible: {fig.data[2].visible}")
print(f"fig.data[9].visible: {fig.data[9].visible}")

print(f"fig.data[0] == fig_orig.data[0]: {fig.data[0] == fig_orig.data[0]}")
print(f"fig.data[1] == fig_orig.data[1]: {fig.data[1] == fig_orig.data[1]}")

# Now update fig_orig
fig_orig.data[0].update({"visible": "legendonly"})
print("\nAfter updating fig_orig.data[0]:")
print(f"fig.data[0] == fig_orig.data[0]: {fig.data[0] == fig_orig.data[0]}")
print(f"fig.data[0]: {fig.data[0]}")
print(f"fig_orig.data[0]: {fig_orig.data[0]}")

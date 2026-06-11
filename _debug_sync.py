import copy
import plotly.graph_objs as go

# Test: create a trace, add it to a figure, then check marker sync
trace = go.Scatter3d(
    x=[0, 0, 0],
    y=[0, 0, 0],
    z=[0, 1, 2],
    mode="markers",
    marker={"color": "green", "size": 10},
    name="E",
)

print(f"Before add_trace:")
print(f"  trace._props['marker'] is trace.marker._props: {trace._props['marker'] is trace.marker._props}")

fig = go.Figure()
fig.add_trace(trace)

print(f"\nAfter add_trace:")
print(f"  fig.data[0]._props['marker']: {fig.data[0]._props['marker']}")
print(f"  fig.data[0].marker._props: {fig.data[0].marker._props}")
print(f"  fig.data[0]._props['marker'] is fig.data[0].marker._props: {fig.data[0]._props['marker'] is fig.data[0].marker._props}")

# Now check if the marker dict in figure._data is the same as trace.marker._props
print(f"\nFigure._data[0]['marker']: {fig._data[0]['marker']}")
print(f"  fig._data[0]['marker'] is fig.data[0]._props['marker']: {fig._data[0]['marker'] is fig.data[0]._props['marker']}")
print(f"  fig._data[0]['marker'] is fig.data[0].marker._props: {fig._data[0]['marker'] is fig.data[0].marker._props}")

# Now let's try to update
patch = {"marker": {"line": {"color": "yellow"}}}
print(f"\nCalling fig.update_traces with patch: {patch}")
fig.update_traces(patch, selector={"type": "scatter3d"})

print(f"\nAfter fig.update_traces:")
print(f"  fig._data[0]['marker']: {fig._data[0].get('marker')}")
print(f"  fig.data[0].marker._props: {fig.data[0].marker._props}")

import plotly.graph_objs as go

# Simple test without subplots
trace = go.Scatter3d(
    x=[0, 0, 0],
    y=[0, 0, 0],
    z=[0, 1, 2],
    mode="markers",
    marker={"color": "green", "size": 10},
    name="E",
)

fig = go.Figure(data=[trace])

print(f"Before update:")
print(f"  trace._props['marker']: {trace._props.get('marker')}")
print(f"  trace.marker._props: {trace.marker._props}")
print(f"  Are they the same object? {trace._props.get('marker') is trace.marker._props}")

# Now update trace directly
patch = {"marker": {"line": {"color": "yellow"}}}
trace.update(patch)

print(f"\nAfter direct trace.update():")
print(f"  trace._props['marker']: {trace._props.get('marker')}")
print(f"  trace.marker._props: {trace.marker._props}")
print(f"  Are they the same object? {trace._props.get('marker') is trace.marker._props}")

# Now test with fig.update_traces
trace2 = go.Scatter3d(
    x=[0, 0, 0],
    y=[0, 0, 0],
    z=[0, 1, 2],
    mode="markers",
    marker={"color": "green", "size": 10},
    name="E",
)
fig2 = go.Figure(data=[trace2])

print(f"\nBefore fig.update_traces:")
print(f"  fig2.data[0]._props['marker']: {fig2.data[0]._props.get('marker')}")
print(f"  fig2.data[0].marker._props: {fig2.data[0].marker._props}")

fig2.update_traces(patch, selector={"type": "scatter3d"})

print(f"\nAfter fig.update_traces:")
print(f"  fig2.data[0]._props['marker']: {fig2.data[0]._props.get('marker')}")
print(f"  fig2.data[0].marker._props: {fig2.data[0].marker._props}")

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

print(f"Before update_traces, fig.data id: {id(fig.data)}")
print(f"Before update_traces, fig.data[0] id: {id(fig.data[0])}")
print(f"Before update_traces, fig.data[0]._props['marker']: {fig.data[0]._props.get('marker')}")
print(f"Before update_traces, fig.data[0].marker._props: {fig.data[0].marker._props}")

# Check if self.data is a property
import plotly.basedatatypes as bt
print(f"\nIs BaseFigure.data a property? {isinstance(bt.BaseFigure.__dict__.get('data'), property)}")

patch = {"marker": {"line": {"color": "yellow"}}}
fig.update_traces(patch, selector={"type": "scatter3d"})

print(f"\nAfter update_traces, fig.data id: {id(fig.data)}")
print(f"After update_traces, fig.data[0] id: {id(fig.data[0])}")
print(f"After update_traces, fig.data[0]._props['marker']: {fig.data[0]._props.get('marker')}")
print(f"After update_traces, fig.data[0].marker._props: {fig.data[0].marker._props}")

# Now direct update
fig.data[0].update(patch)
print(f"\nAfter direct update, fig.data[0]._props['marker']: {fig.data[0]._props.get('marker')}")
print(f"After direct update, fig.data[0].marker._props: {fig.data[0].marker._props}")

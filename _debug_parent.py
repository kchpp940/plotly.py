import copy
import plotly.graph_objs as go

trace = go.Scatter3d(
    x=[0, 0, 0],
    y=[0, 0, 0],
    z=[0, 1, 2],
    mode="markers",
    marker={"color": "green", "size": 10},
    name="E",
)

print("Before add_trace:")
marker1 = trace.marker
print(f"  id(trace._compound_props['marker']): {id(trace._compound_props['marker'])}")
print(f"  trace._orphan_props: {trace._orphan_props}")
print(f"  marker1._parent is trace: {marker1._parent is trace}")
print(f"  marker1._props: {marker1._props}")
print(f"  marker1._props is trace._orphan_props['marker']: {marker1._props is trace._orphan_props['marker']}")

fig = go.Figure()

# Now simulate what add_traces does
data = [trace]
# Validate and coerce (this creates new traces in our modified code)
data = fig._data_validator.validate_coerce(data)

new_trace = data[0]
print(f"\nAfter validate_coerce:")
print(f"  new_trace is original trace: {new_trace is trace}")
print(f"  new_trace._orphan_props: {new_trace._orphan_props}")
print(f"  new_trace._customdata_columns: {getattr(new_trace, '_customdata_columns', 'NOT FOUND')}")

# Check marker
marker2 = new_trace.marker
print(f"\nMarker after validate_coerce:")
print(f"  new_trace._compound_props.get('marker'): {new_trace._compound_props.get('marker')}")
print(f"  marker2._parent is new_trace: {marker2._parent is new_trace}")
print(f"  marker2._props: {marker2._props}")
print(f"  marker2._props is new_trace._orphan_props['marker']: {marker2._props is new_trace._orphan_props.get('marker')}")

# Now set parent
new_trace_data_deepcopy = copy.deepcopy(new_trace._props)
print(f"\nDeepcopy of _props: {new_trace_data_deepcopy}")
print(f"  new_trace._orphan_props['marker'] is new_trace_data_deepcopy['marker']: {new_trace._orphan_props.get('marker') is new_trace_data_deepcopy.get('marker')}")

# Add to figure
fig._data.append(new_trace_data_deepcopy)
fig._data_defaults.append({})
fig._data_objs = fig._data_objs + (new_trace,)
new_trace._parent = fig
new_trace._trace_ind = 0
new_trace._orphan_props.clear()

print(f"\nAfter setting parent to figure:")
print(f"  new_trace._props: {new_trace._props}")
print(f"  new_trace._props is fig._data[0]: {new_trace._props is fig._data[0]}")

# Now check marker again
marker3 = new_trace.marker
print(f"\nMarker after parent set:")
print(f"  marker3 is marker2: {marker3 is marker2}")
print(f"  new_trace._compound_props.get('marker') is marker2: {new_trace._compound_props.get('marker') is marker2}")
print(f"  marker3._parent is new_trace: {marker3._parent is new_trace}")
print(f"  marker3._props: {marker3._props}")
print(f"  new_trace._props['marker']: {new_trace._props['marker']}")
print(f"  marker3._props is new_trace._props['marker']: {marker3._props is new_trace._props['marker']}")
print(f"  marker3._props is fig._data[0]['marker']: {marker3._props is fig._data[0]['marker']}")

# Now call _get_child_props directly
print(f"\nDirect _get_child_props call:")
child_props = new_trace._get_child_props(marker3)
print(f"  child_props: {child_props}")
print(f"  child_props is new_trace._props['marker']: {child_props is new_trace._props['marker']}")
print(f"  child_props is fig._data[0]['marker']: {child_props is fig._data[0]['marker']}")

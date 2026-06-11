import plotly.graph_objs as go

# Test 1: Create a trace directly
trace1 = go.Scatter3d(
    marker={"color": "green", "size": 10},
)
print("Direct trace creation:")
print(f"  trace1._props['marker'] is trace1.marker._props: {trace1._props['marker'] is trace1.marker._props}")

# Test 2: Create a trace from _props dict
trace2 = go.Scatter3d(**trace1._props)
print("\nFrom _props dict:")
print(f"  trace2._props['marker'] is trace2.marker._props: {trace2._props['marker'] is trace2.marker._props}")

# Test 3: What does the marker constructor do with the dict?
marker_props = {"color": "green", "size": 10}
marker = go.scatter3d.Marker(**marker_props)
print("\nMarker creation:")
print(f"  marker_props is marker._props: {marker_props is marker._props}")
print(f"  marker_props == marker._props: {marker_props == marker._props}")

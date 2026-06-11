import plotly.graph_objs as go

trace = go.Scatter3d(
    x=[0, 0, 0],
    y=[0, 0, 0],
    z=[0, 1, 2],
    mode="markers",
    marker={"color": "green", "size": 10},
    name="E",
)

fig = go.Figure(data=[trace])

print("First access:")
t1 = fig.data[0]
print(f"  id(t1): {id(t1)}")
print(f"  t1._props['marker'] is t1.marker._props: {t1._props['marker'] is t1.marker._props}")

print("\nSecond access:")
t2 = fig.data[0]
print(f"  id(t2): {id(t2)}")
print(f"  t1 is t2: {t1 is t2}")
print(f"  t2._props['marker'] is t2.marker._props: {t2._props['marker'] is t2.marker._props}")

print("\nWhat about t1._props and t2._props?")
print(f"  t1._props is t2._props: {t1._props is t2._props}")
print(f"  t1._props == t2._props: {t1._props == t2._props}")

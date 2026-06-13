import plotly.express as px
import pandas as pd
import numpy as np

df = pd.DataFrame({
    'category': ['A', 'A', 'B', 'B', 'C', 'C'],
    'value': [1, 2, 3, 4, 5, 6],
    'x': [1, 2, 3, 4, 5, 6],
    'y': [10, 20, 30, 40, 50, 60],
})

print("=== Test 1: px.histogram count ===")
fig = px.histogram(df, x='value')
print("Y axis title:", fig.layout.yaxis.title.text)
print("Trace histfunc:", fig.data[0].histfunc)
print("OK")

print("\n=== Test 2: px.histogram sum ===")
fig = px.histogram(df, x='category', y='value')
print("Y axis title:", fig.layout.yaxis.title.text)
print("Trace histfunc:", fig.data[0].histfunc)
print("OK")

print("\n=== Test 3: px.histogram with histnorm ===")
fig = px.histogram(df, x='value', histnorm='percent')
print("Y axis title:", fig.layout.yaxis.title.text)
print("Trace histnorm:", fig.data[0].histnorm)
print("OK")

print("\n=== Test 4: px.bar basic ===")
fig = px.bar(df, x='category', y='value')
print("Y axis title:", fig.layout.yaxis.title.text)
print("OK")

print("\n=== Test 5: px.bar with count (single dim) ===")
fig = px.bar(df, x='category')
print("Y axis title:", fig.layout.yaxis.title.text)
print("Data Y first few:", fig.data[0].y[:3])
print("OK")

print("\n=== Test 6: px.density_heatmap ===")
fig = px.density_heatmap(df, x='x', y='y')
print("Colorbar title:", fig.layout.coloraxis.colorbar.title.text)
print("Trace histfunc:", fig.data[0].histfunc)
print("OK")

print("\n=== Test 7: px.density_heatmap with z ===")
fig = px.density_heatmap(df, x='x', y='y', z='value')
print("Colorbar title:", fig.layout.coloraxis.colorbar.title.text)
print("Trace histfunc:", fig.data[0].histfunc)
print("OK")

print("\n=== Test 8: px.density_contour ===")
fig = px.density_contour(df, x='x', y='y', z='value')
print("Trace histfunc:", fig.data[0].histfunc)
print("OK")

print("\n=== Test 9: px.histogram with barnorm ===")
fig = px.histogram(df, x='category', y='value', color='category', barnorm='percent')
print("Y axis title:", fig.layout.yaxis.title.text)
print("Layout barnorm:", fig.layout.barnorm)
print("OK")

print("\n=== All tests passed! ===")

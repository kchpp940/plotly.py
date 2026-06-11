import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    "category": ["A", "A", "B", "B", "C", "C"],
    "value": [10, 20, 30, 40, 50, 60],
    "group": ["X", "Y", "X", "Y", "X", "Y"],
})

print("Testing dict format summary...")
print()

fig = px.bar(
    df, x="category", y="value", color="group",
    summary=dict(type="percent", show="all", format=".2f")
)

print(f"Number of traces: {len(fig.data)}")
print(f"Number of annotations: {len(fig.layout.annotations)}")
print()

for i, trace in enumerate(fig.data):
    print(f"Trace {i}:")
    print(f"  name: {trace.name}")
    print(f"  hovertemplate: {trace.hovertemplate[:100] if trace.hovertemplate else 'None'}...")
    print()

print("Annotations:")
for i, a in enumerate(fig.layout.annotations):
    print(f"  {i}: {a.text[:50]}...")

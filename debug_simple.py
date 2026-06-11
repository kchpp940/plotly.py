import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    "category": ["A", "A", "B", "B", "C", "C"],
    "value": [10, 20, 30, 40, 50, 60],
    "group": ["X", "Y", "X", "Y", "X", "Y"],
})

print("Test 1: summary='percent' (str format)")
fig1 = px.bar(df, x="category", y="value", color="group", summary="percent")
print(f"  annotations: {len(fig1.layout.annotations)}")
print(f"  trace 0 name: {fig1.data[0].name}")
print()

print("Test 2: summary=dict(type='percent', show='annotation')")
fig2 = px.bar(df, x="category", y="value", color="group", summary=dict(type="percent", show="annotation"))
print(f"  annotations: {len(fig2.layout.annotations)}")
print(f"  trace 0 name: {fig2.data[0].name}")
print()

print("Test 3: summary=dict(type='percent', show='all')")
fig3 = px.bar(df, x="category", y="value", color="group", summary=dict(type="percent", show="all"))
print(f"  annotations: {len(fig3.layout.annotations)}")
print(f"  trace 0 name: {fig3.data[0].name}")
print()

print("Test 4: summary=['percent'] (list format with str)")
fig4 = px.bar(df, x="category", y="value", color="group", summary=["percent"])
print(f"  annotations: {len(fig4.layout.annotations)}")
print(f"  trace 0 name: {fig4.data[0].name}")
print()

print("Test 5: summary=[dict(type='percent', show='all')] (list format with dict)")
fig5 = px.bar(df, x="category", y="value", color="group", summary=[dict(type="percent", show="all")])
print(f"  annotations: {len(fig5.layout.annotations)}")
print(f"  trace 0 name: {fig5.data[0].name}")

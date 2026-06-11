import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    "x": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
    "y": [2, 4, 5, 4, 5, 1, 2, 3, 4, 5],
    "group": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B"],
})

print("Testing trendline with summary...")
print()

try:
    fig = px.scatter(
        df, x="x", y="y", color="group",
        trendline="ols",
        summary=dict(type="mean", show="all")
    )

    print(f"Number of traces: {len(fig.data)}")
    for i, trace in enumerate(fig.data):
        print(f"Trace {i}: name='{trace.name}', mode='{trace.mode}'")
    print()
    print(f"Number of annotations: {len(fig.layout.annotations)}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

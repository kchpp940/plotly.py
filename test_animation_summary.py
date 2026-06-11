import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    "x": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3],
    "y": [1, 2, 3, 2, 4, 6, 3, 6, 9, 4, 8, 12],
    "group": ["A", "A", "A", "B", "B", "B", "A", "A", "A", "B", "B", "B"],
    "frame": ["f1", "f1", "f1", "f1", "f1", "f1", "f2", "f2", "f2", "f2", "f2", "f2"],
})

print("Testing animation frame annotations...")
print()

# Test 1: animation with summary
fig = px.scatter(
    df, x="x", y="y", color="group",
    animation_frame="frame",
    summary=dict(type="mean", show="all", format=".2f")
)

print(f"Number of frames: {len(fig.frames)}")
print(f"Initial layout annotations: {len(fig.layout.annotations)}")
print()

for i, frame in enumerate(fig.frames):
    frame_annots = frame.layout.annotations if frame.layout and frame.layout.annotations else []
    print(f"Frame {i} ('{frame.name}'): {len(frame_annots)} annotations")
    for j, a in enumerate(frame_annots):
        print(f"  Annotation {j}: {a.text[:60]}...")
print()

# Test 2: animation with bar chart
print("Testing bar chart animation...")
df2 = pd.DataFrame({
    "category": ["A", "B", "C", "A", "B", "C"],
    "value": [10, 20, 30, 15, 25, 35],
    "frame": ["f1", "f1", "f1", "f2", "f2", "f2"],
})

fig2 = px.bar(
    df2, x="category", y="value",
    animation_frame="frame",
    summary=dict(type="sum", show="all")
)

print(f"Number of frames: {len(fig2.frames)}")
print(f"Initial layout annotations: {len(fig2.layout.annotations)}")
for i, frame in enumerate(fig2.frames):
    frame_annots = frame.layout.annotations if frame.layout and frame.layout.annotations else []
    print(f"Frame {i} ('{frame.name}'): {len(frame_annots)} annotations")
    if frame_annots:
        print(f"  text: {frame_annots[0].text[:50]}...")

print()
print("Testing legend names across frames...")
for i, frame in enumerate(fig2.frames):
    print(f"Frame {i} ('{frame.name}') trace names:")
    for j, trace in enumerate(frame.data):
        print(f"  Trace {j}: {trace.name}")

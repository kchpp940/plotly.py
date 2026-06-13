import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from plotly.express._core import (
    AnnotationTarget,
    AnnotationSpec,
    AnnotationCollector,
    AnnotationApplier,
    create_facet_annotations,
    create_trendline_annotation,
    create_stat_annotation,
    create_marginal_annotation,
    create_frame_annotation,
)

print("=== Test 1: AnnotationSpec basic functionality ===")
ann = AnnotationSpec(
    text="Test Annotation",
    x=0.5,
    y=0.5,
    xref="paper",
    yref="paper",
    target=AnnotationTarget.INITIAL_LAYOUT,
)
ann_dict = ann.to_dict()
print(f"  text: {ann_dict['text']}")
print(f"  x: {ann_dict['x']}")
print(f"  y: {ann_dict['y']}")
print(f"  showarrow: {ann_dict['showarrow']}")
assert ann_dict["text"] == "Test Annotation"
assert ann_dict["x"] == 0.5
assert ann_dict["y"] == 0.5
print("  PASSED")
print()

print("=== Test 2: AnnotationCollector functionality ===")
collector = AnnotationCollector()
ann1 = AnnotationSpec(text="Ann1", x=0.1, y=0.1, target=AnnotationTarget.INITIAL_LAYOUT)
ann2 = AnnotationSpec(text="Ann2", x=0.2, y=0.2, target=AnnotationTarget.FRAME_LAYOUT, frame_name="frame1")
ann3 = AnnotationSpec(text="Ann3", x=0.3, y=0.3, target=AnnotationTarget.BOTH)

collector.add(ann1)
collector.add_many([ann2, ann3])

all_anns = collector.get_all()
print(f"  Total annotations: {len(all_anns)}")
assert len(all_anns) == 3

initial_anns = collector.get_by_target(AnnotationTarget.INITIAL_LAYOUT)
print(f"  Initial layout annotations: {len(initial_anns)}")
assert len(initial_anns) == 1

frame_anns = collector.get_by_target(AnnotationTarget.FRAME_LAYOUT)
print(f"  Frame layout annotations: {len(frame_anns)}")
assert len(frame_anns) == 1

both_anns = collector.get_by_target(AnnotationTarget.BOTH)
print(f"  Both target annotations: {len(both_anns)}")
assert len(both_anns) == 1

frame1_anns = collector.get_by_frame("frame1")
print(f"  Annotations for frame1: {len(frame1_anns)}")
assert len(frame1_anns) == 2
print("  PASSED")
print()

print("=== Test 3: Facet annotations generation ===")
df = pd.DataFrame({
    "x": [1, 2, 3, 4, 5, 6],
    "y": [1, 4, 9, 16, 25, 36],
    "category": ["A", "A", "A", "B", "B", "B"],
    "row": ["R1", "R1", "R2", "R2", "R1", "R1"],
})

fig = px.scatter(df, x="x", y="y", facet_col="category", facet_row="row")
print(f"  Number of annotations: {len(fig.layout.annotations)}")
assert len(fig.layout.annotations) == 4

ann_texts = [a.text for a in fig.layout.annotations]
print(f"  Annotation texts: {ann_texts}")
assert any("category=A" in t for t in ann_texts)
assert any("category=B" in t for t in ann_texts)
assert any("row=R1" in t for t in ann_texts)
assert any("row=R2" in t for t in ann_texts)
print("  PASSED")
print()

print("=== Test 4: Facet annotations with facet_col_wrap ===")
df2 = pd.DataFrame({
    "x": [1, 2, 3, 4, 5, 6, 7, 8],
    "y": [1, 4, 9, 16, 25, 36, 49, 64],
    "category": ["A", "A", "B", "B", "C", "C", "D", "D"],
})

fig2 = px.scatter(df2, x="x", y="y", facet_col="category", facet_col_wrap=2)
print(f"  Number of annotations with wrap: {len(fig2.layout.annotations)}")
assert len(fig2.layout.annotations) == 4
print("  PASSED")
print()

print("=== Test 5: Trendline annotations ===")
np.random.seed(42)
x = np.linspace(0, 10, 50)
y = 2 * x + 1 + np.random.normal(0, 1, 50)
df3 = pd.DataFrame({"x": x, "y": y})

fig3 = px.scatter(df3, x="x", y="y", trendline="ols", trendline_scope="overall")
print(f"  Number of annotations with trendline: {len(fig3.layout.annotations)}")
trendline_anns = [a for a in fig3.layout.annotations if "R²" in a.text]
print(f"  Trendline annotations: {len(trendline_anns)}")
assert len(trendline_anns) >= 1
if trendline_anns:
    print(f"  Trendline text: {trendline_anns[0].text}")
print("  PASSED")
print()

print("=== Test 6: Animation frame annotations ===")
df4 = pd.DataFrame({
    "x": [1, 2, 3, 1, 2, 3],
    "y": [1, 4, 9, 2, 5, 10],
    "frame": ["2020", "2020", "2020", "2021", "2021", "2021"],
})

fig4 = px.scatter(df4, x="x", y="y", animation_frame="frame", trendline="ols")
print(f"  Number of frames: {len(fig4.frames)}")
assert len(fig4.frames) == 2

frame_with_ann = [f for f in fig4.frames if hasattr(f, "layout") and f.layout and getattr(f.layout, "annotations", None)]
print(f"  Frames with annotations: {len(frame_with_ann)}")
print("  PASSED")
print()

print("=== Test 7: AnnotationApplier functionality ===")
fig5 = go.Figure()
collector2 = AnnotationCollector()
collector2.add(AnnotationSpec(text="Test1", x=0.5, y=0.9, target=AnnotationTarget.INITIAL_LAYOUT))
collector2.add(AnnotationSpec(text="Test2", x=0.5, y=0.1, target=AnnotationTarget.FRAME_LAYOUT, frame_name="f1"))

fig5.frames = [go.Frame(name="f1"), go.Frame(name="f2")]
AnnotationApplier.apply_all(fig5, collector2, frame_names=["f1", "f2"])

print(f"  Initial layout annotations: {len(fig5.layout.annotations)}")
assert len(fig5.layout.annotations) == 1

frame1 = [f for f in fig5.frames if f.name == "f1"][0]
print(f"  Frame f1 annotations: {len(frame1.layout['annotations'])}")
assert len(frame1.layout["annotations"]) == 1
print("  PASSED")
print()

print("=== Test 8: Custom annotation functions ===")
args = {"facet_col": "cat", "facet_row": "row", "labels": {"cat": "Category", "row": "Row"}}
col_labels = ["A", "B"]
row_labels = ["R1", "R2"]

facet_anns = create_facet_annotations(args, col_labels, row_labels, None, 2, 2, 0)
print(f"  Generated facet annotations: {len(facet_anns)}")
assert len(facet_anns) == 4

stat_ann = create_stat_annotation("Mean: 42", x=0.1, y=0.9)
print(f"  Stat annotation text: {stat_ann.text}")
assert stat_ann.text == "Mean: 42"

marginal_ann = create_marginal_annotation("Distribution", x=0.5, y=0.05)
print(f"  Marginal annotation text: {marginal_ann.text}")
assert marginal_ann.text == "Distribution"

frame_ann = create_frame_annotation("Frame Label", x=0.5, y=0.5, frame_name="f1")
print(f"  Frame annotation frame_name: {frame_ann.frame_name}")
assert frame_ann.frame_name == "f1"
assert frame_ann.target == AnnotationTarget.FRAME_LAYOUT
print("  PASSED")
print()

print("=== All tests passed! ===")

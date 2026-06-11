import plotly.express as px
import pandas as pd
import numpy as np

print("=" * 60)
print("Testing Plotly Express Summary Feature")
print("=" * 60)

df = pd.DataFrame({
    "category": ["A", "A", "B", "B", "C", "C"],
    "value": [10, 20, 30, 40, 50, 60],
    "group": ["X", "Y", "X", "Y", "X", "Y"],
})

print("\n1. Test px.scatter with summary='mean'")
try:
    fig = px.scatter(df, x="category", y="value", color="group", summary="mean")
    print(f"   - Figure created successfully")
    print(f"   - Number of traces: {len(fig.data)}")
    print(f"   - Number of annotations: {len(fig.layout.annotations)}")
    for i, annot in enumerate(fig.layout.annotations):
        print(f"   - Annotation {i}: {annot.text[:50]}...")
    print("   PASSED")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n2. Test px.bar with summary=['mean', 'sum']")
try:
    fig = px.bar(df, x="category", y="value", color="group", summary=["mean", "sum"])
    print(f"   - Figure created successfully")
    print(f"   - Number of traces: {len(fig.data)}")
    print(f"   - Number of annotations: {len(fig.layout.annotations)}")
    for i, annot in enumerate(fig.layout.annotations):
        print(f"   - Annotation {i}: {annot.text[:60]}...")
    print("   PASSED")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n3. Test px.line with summary='median'")
try:
    fig = px.line(df, x="category", y="value", color="group", summary="median")
    print(f"   - Figure created successfully")
    print(f"   - Number of traces: {len(fig.data)}")
    print(f"   - Number of annotations: {len(fig.layout.annotations)}")
    print("   PASSED")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n4. Test px.histogram with summary='count'")
try:
    fig = px.histogram(df, x="value", color="group", summary="count")
    print(f"   - Figure created successfully")
    print(f"   - Number of traces: {len(fig.data)}")
    print(f"   - Number of annotations: {len(fig.layout.annotations)}")
    print("   PASSED")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n5. Test summary with dict format")
try:
    fig = px.scatter(
        df, x="category", y="value", color="group",
        summary=dict(type="percent", show="all", format=".2f")
    )
    print(f"   - Figure created successfully")
    print(f"   - Number of traces: {len(fig.data)}")
    print(f"   - Number of annotations: {len(fig.layout.annotations)}")
    print(f"   - Trace 0 name: {fig.data[0].name}")
    print(f"   - Trace 0 hovertemplate: {fig.data[0].hovertemplate[:80]}...")
    print("   PASSED")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n6. Test summary with facet_col")
try:
    fig = px.bar(
        df, x="category", y="value", color="group",
        facet_col="group", summary="mean"
    )
    print(f"   - Figure created successfully")
    print(f"   - Number of traces: {len(fig.data)}")
    print(f"   - Number of annotations: {len(fig.layout.annotations)}")
    print("   PASSED")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n7. Test no summary (default behavior)")
try:
    fig = px.scatter(df, x="category", y="value", color="group")
    print(f"   - Figure created successfully")
    print(f"   - Number of traces: {len(fig.data)}")
    print(f"   - Number of annotations (facet titles only): {len(fig.layout.annotations)}")
    print("   PASSED")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n8. Test summary with invalid type (should raise ValueError)")
try:
    fig = px.scatter(df, x="category", y="value", summary="invalid_type")
    print("   FAILED: Should have raised ValueError")
except ValueError as e:
    print(f"   - Correctly raised ValueError: {e}")
    print("   PASSED")
except Exception as e:
    print(f"   FAILED: Wrong exception type: {e}")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)

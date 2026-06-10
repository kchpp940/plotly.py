import pandas as pd
import numpy as np
import json
import tempfile
import os
import plotly.graph_objects as go

print("=== 1. Table Int64 + orjson ===")
s1 = pd.Series([1, pd.NA, 3], dtype="Int64")
s2 = pd.Series([1.5, pd.NA, 3.5], dtype="Float64")
s3 = pd.Series([True, pd.NA, False], dtype="boolean")
s4 = pd.Series(["a", pd.NA, "c"], dtype="string")

fig = go.Figure(go.Table(
    header=dict(values=["Int", "Float", "Bool", "Str"]),
    cells=dict(values=[s1, s2, s3, s4])
))

try:
    j_orjson = fig.to_json(engine="orjson")
    parsed = json.loads(j_orjson)
    vals = parsed["data"][0]["cells"]["values"]
    print("  Int64:", vals[0], "types:", [type(v).__name__ for v in vals[0]])
    print("  Float64:", vals[1], "types:", [type(v).__name__ for v in vals[1]])
    print("  boolean:", vals[2], "types:", [type(v).__name__ for v in vals[2]])
    print("  string:", vals[3], "types:", [type(v).__name__ for v in vals[3]])
    assert isinstance(vals[0][0], int)
    assert isinstance(vals[1][0], float)
    assert isinstance(vals[2][0], bool)
    assert isinstance(vals[3][0], str)
    assert vals[0][1] is None
    assert vals[1][1] is None
    assert vals[2][1] is None
    assert vals[3][1] is None
    print("  ORJSON OK")
except ImportError:
    print("  orjson not installed, skipping")

print()
print("=== 2. Table write_json Int64 ===")
fig2 = go.Figure(go.Table(
    header=dict(values=["A"]),
    cells=dict(values=[s1])
))
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    fname = f.name
try:
    fig2.write_json(fname)
    with open(fname) as f:
        loaded = json.load(f)
    vals = loaded["data"][0]["cells"]["values"]
    print("  Int64:", vals[0])
    assert isinstance(vals[0][0], int), "Expected int, got " + type(vals[0][0]).__name__
    assert vals[0][1] is None
    assert vals[0][2] == 3
    print("  WRITE_JSON OK")
finally:
    os.unlink(fname)

print()
print("=== 3. Table mixed: Int64 + MaskedArray ===")
ma = np.ma.array([10, 20, 30], mask=[False, True, False])
fig3 = go.Figure(go.Table(
    header=dict(values=["Int64", "Masked"]),
    cells=dict(values=[s1, ma])
))
j3 = fig3.to_json(engine="json")
parsed3 = json.loads(j3)
vals3 = parsed3["data"][0]["cells"]["values"]
print("  Int64:", vals3[0], "types:", [type(v).__name__ for v in vals3[0]])
print("  Masked:", vals3[1], "types:", [type(v).__name__ for v in vals3[1]])
assert isinstance(vals3[0][0], int), "Int64 non-null must be int"
assert isinstance(vals3[1][0], int), "MaskedArray non-null must be int"
assert vals3[0][1] is None
assert vals3[1][1] is None

print()
print("=== 4. Heatmap 2D MaskedArray ===")
data2d = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
masked2d = np.ma.masked_where(data2d % 3 == 0, data2d)
fig4 = go.Figure(go.Heatmap(z=masked2d))
j4 = fig4.to_json(engine="json")
parsed4 = json.loads(j4)
z = parsed4["data"][0]["z"]
print("  z shape:", len(z), "x", len(z[0]))
print("  z[0]:", z[0])
assert len(z) == 3
assert len(z[0]) == 3
assert z[0][2] is None
assert z[1][2] is None
assert z[2][2] is None
assert isinstance(z[0][0], float)

print()
print("=== ALL PASSED ===")

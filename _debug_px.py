import plotly.express as px

df = px.data.iris()
fig = px.scatter(df, x="sepal_width", y="sepal_length", custom_data=["species", "petal_width"])

for i, t in enumerate(fig.data):
    print(f"Trace {i}:")
    print(f"  _customdata_columns = {t._customdata_columns}")
    cd = t.customdata
    print(f"  customdata shape = {len(cd) if cd is not None else 'None'}")
    if cd is not None and len(cd) > 0:
        print(f"  first row = {cd[0]}")

# Let me check if the custom_data parameter is passed properly
print()
print("Looking at how PX processes custom_data...")
from plotly.express._core import _extract_customdata_columns

# Simulate the args dict
args = {
    "custom_data": ["species", "petal_width"],
    "x": "sepal_width",
    "y": "sepal_length",
    "hover_data": None,
    "z": None,
    "base": None,
}
mapping_labels = {}
col_map = _extract_customdata_columns(args, mapping_labels)
print(f"Extracted col_map (custom_data only): {col_map}")

import plotly.express as px
from plotly.express._params import PARAMS
import inspect
import sys

PUBLIC_CHART_FUNCTIONS = [
    "scatter", "scatter_3d", "scatter_polar", "scatter_ternary",
    "scatter_mapbox", "scatter_geo",
    "line", "line_3d", "line_polar", "line_ternary", "line_mapbox", "line_geo",
    "area", "bar", "bar_polar", "histogram",
    "box", "violin", "strip", "ecdf",
    "density_heatmap", "density_contour", "density_mapbox",
    "pie", "sunburst", "treemap", "icicle",
    "funnel", "funnel_area", "timeline",
    "scatter_matrix", "parallel_coordinates", "parallel_categories",
    "choropleth", "choropleth_mapbox",
]

all_ok = True
print("Checking ALL px chart functions signatures vs PARAMS registry...\n")
for fn_name in PUBLIC_CHART_FUNCTIONS:
    try:
        fn = getattr(px, fn_name, None)
        if fn is None:
            # Try mapbox with trailing 'x' etc
            continue
        if not callable(fn):
            continue
        sig_params = list(inspect.signature(fn).parameters.keys())
        reg_names = set(PARAMS.names_for_chart(fn_name))
        sig_set = set(sig_params)
        missing = sorted(reg_names - sig_set)
        extra = sorted(sig_set - reg_names)
        status = "MATCH" if not missing and not extra else "MISMATCH"
        if status != "MATCH":
            all_ok = False
        print(f"{fn_name:25s} registry={len(reg_names):3d} sig={len(sig_params):3d} {status}")
        if missing:
            print(f"  MISSING (in registry NOT in sig): {missing}")
        if extra:
            print(f"  EXTRA   (in sig NOT in registry): {extra}")
    except Exception as e:
        all_ok = False
        print(f"{fn_name:25s} ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print()
if all_ok:
    print("ALL SIGNATURES MATCH!")
    sys.exit(0)
else:
    print("SOME MISMATCHES FOUND -- see above")
    sys.exit(1)

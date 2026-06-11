import inspect
import plotly.express as px
from plotly.graph_objs import Scatter, Scattergl, Bar, Histogram

charts = {
    "scatter": px.scatter,
    "line": px.line,
    "bar": px.bar,
    "histogram": px.histogram,
}

chart_params = {}
for name, fn in charts.items():
    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())
    chart_params[name] = params
    print(f"\n=== {name} ({len(params)} params) ===")
    print(params)

all_params = set()
for p in chart_params.values():
    all_params.update(p)

common = set(chart_params["scatter"])
for p in chart_params.values():
    common &= set(p)
print(f"\n=== COMMON ({len(common)}) ===")
print(sorted(common))

for name in charts:
    others = set()
    for n2 in charts:
        if n2 != name:
            others |= set(chart_params[n2])
    unique = set(chart_params[name]) - others
    print(f"\n=== ONLY IN {name} ({len(unique)}) ===")
    print(sorted(unique))

print("\n=== IN scatter BUT NOT line ===")
print(sorted(set(chart_params["scatter"]) - set(chart_params["line"])))

print("\n=== IN line BUT NOT scatter ===")
print(sorted(set(chart_params["line"]) - set(chart_params["scatter"])))

print("\n=== IN bar BUT NOT scatter ===")
print(sorted(set(chart_params["bar"]) - set(chart_params["scatter"])))

print("\n=== IN histogram BUT NOT scatter ===")
print(sorted(set(chart_params["histogram"]) - set(chart_params["scatter"])))

print("\n=== IN scatter BUT NOT bar ===")
print(sorted(set(chart_params["scatter"]) - set(chart_params["bar"])))

print("\n=== IN scatter BUT NOT histogram ===")
print(sorted(set(chart_params["scatter"]) - set(chart_params["histogram"])))

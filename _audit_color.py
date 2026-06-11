"""Quick audit: check color_continuous params presence in all chart signatures."""
from __future__ import annotations
import inspect, warnings
warnings.filterwarnings("ignore")
import plotly.express as px

TARGET_PARAMS = ["color_continuous_scale", "range_color", "color_continuous_midpoint",
                 "opacity", "orientation", "barnorm", "coloraxis"]

funcs = {n: getattr(px, n) for n in dir(px) if callable(getattr(px, n)) and not n.startswith("_")
         and n not in ("set_mapbox_access_token", "colors", "data", "imshow", "get_trendline_results")}

print("Chart function param audit:")
print(f"{'chart':25s} " + " ".join(f"{p[:8]:8s}" for p in TARGET_PARAMS))
print("-" * 95)
results = {p: {"have": [], "missing": []} for p in TARGET_PARAMS}
for name in sorted(funcs.keys()):
    try:
        sig = inspect.signature(funcs[name])
        params = set(sig.parameters.keys())
    except Exception:
        continue
    flags = []
    for p in TARGET_PARAMS:
        has = "✓" if p in params else "·"
        flags.append(f"{has:^8s}")
        if p in params:
            results[p]["have"].append(name)
        else:
            results[p]["missing"].append(name)
    print(f"{name:25s} " + " ".join(flags))

print("\n\n" + "=" * 80)
for p in TARGET_PARAMS:
    print(f"\n### {p}")
    print(f"  HAS:     {sorted(results[p]['have'])}")
    print(f"  MISSING: {sorted(results[p]['missing'])}")

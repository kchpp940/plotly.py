"""Full signature audit: check ALL public px functions against PARAMS registry."""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import inspect
import plotly.express as px
from plotly.express._params import PARAMS


def main():
    # Get all public callables that look like chart functions
    skip = {
        "set_mapbox_access_token", "colors", "data",
        "imshow", "get_trendline_results",
        "Defaults", "NO_COLOR",
    }
    chart_funcs = {}
    for name in dir(px):
        if name.startswith("_") or name in skip:
            continue
        obj = getattr(px, name)
        if callable(obj) and hasattr(obj, "__code__"):
            try:
                sig = inspect.signature(obj)
                params = list(sig.parameters.keys())
                if "data_frame" in params or "x" in params:
                    chart_funcs[name] = params
            except Exception:
                pass

    print(f"Found {len(chart_funcs)} chart-like functions\n")

    all_missing: dict[str, list[str]] = {}
    passed = 0
    failed = 0

    for name in sorted(chart_funcs.keys()):
        sig_params = chart_funcs[name]
        reg_set = set(PARAMS.names_for_chart(name))
        sig_set = set(sig_params)
        missing = sorted(sig_set - reg_set)
        extra = sorted(reg_set - sig_set)

        status = "✅" if not missing else "❌"
        if missing:
            all_missing[name] = missing
            failed += 1
            print(f"{status} {name:25s} sig={len(sig_params):2d}  MISSING: {missing}")
        else:
            passed += 1
            print(f"{status} {name:25s} sig={len(sig_params):2d}  OK")

    print(f"\n\n{'='*60}")
    print(f"SUMMARY: {passed}/{passed+failed} passed, {failed} failed")
    print(f"{'='*60}")

    # Aggregate distinct missing params and which charts need them
    param_to_charts: dict[str, list[str]] = {}
    for chart, missing_list in all_missing.items():
        for p in missing_list:
            param_to_charts.setdefault(p, []).append(chart)

    print(f"\nDistinct missing params: {len(param_to_charts)}")
    for p in sorted(param_to_charts.keys()):
        charts = sorted(param_to_charts[p])
        print(f"  {p!r:35s}  needed by: {charts}")


if __name__ == "__main__":
    main()

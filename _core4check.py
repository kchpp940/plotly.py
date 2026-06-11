"""Real signature vs registry checker for core 4 charts."""
from __future__ import annotations

import inspect
import warnings
warnings.filterwarnings("ignore")

import plotly.express as px
from plotly.express._params import PARAMS


def check_chart(chart_name: str, func) -> tuple[list[str], list[str]]:
    """Return (missing_in_registry, extra_in_registry_only)."""
    sig = inspect.signature(func)
    sig_params = list(sig.parameters.keys())
    reg_params = set(PARAMS.names_for_chart(chart_name))
    sig_set = set(sig_params)

    missing = sorted(p for p in sig_params if p not in reg_params)
    extra = sorted(p for p in reg_params if p not in sig_set)
    defaults = {p: sig.parameters[p].default for p in sig_params
                if sig.parameters[p].default is not inspect.Parameter.empty}

    print(f"\n{'='*60}")
    print(f"  px.{chart_name}()  signature={len(sig_params)}  registry={len(reg_params)}")
    print(f"{'='*60}")
    if missing:
        print(f"  ❌ MISSING (in sig but NOT registered):")
        for m in missing:
            dv = defaults.get(m, "<NO DEFAULT>")
            print(f"     {m!r:35s} default={dv!r}")
    if extra:
        print(f"  ⚠️  EXTRA (registered but NOT in sig):")
        for e in extra:
            meta = PARAMS.get(e)
            charts_note = ""
            if meta and meta.charts:
                charts_note = f" charts={len(meta.charts)} types"
            print(f"     {e!r:35s}{charts_note}")
    if not missing and not extra:
        print(f"  ✅ PERFECT MATCH!")
    print(f"  sig order: {sig_params}")
    return missing, extra


def main():
    core4 = {
        "scatter": px.scatter,
        "line": px.line,
        "bar": px.bar,
        "histogram": px.histogram,
    }
    print(f"PARAMS total registered params: {len(PARAMS._params)}")

    all_missing = {}
    for name, func in core4.items():
        m, e = check_chart(name, func)
        if m:
            all_missing[name] = m

    print("\n\n" + "#" * 60)
    print("SUMMARY of core 4 missing params")
    print("#" * 60)
    for name in core4:
        m = all_missing.get(name, [])
        print(f"  {name}: {len(m)} missing -> {m}")


if __name__ == "__main__":
    main()

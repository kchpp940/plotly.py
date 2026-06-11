import plotly.express as px
from plotly.express._params import PARAMS
import inspect

charts_to_check = ["scatter", "line", "bar", "histogram"]

for cn in charts_to_check:
    try:
        names = sorted(PARAMS.names_for_chart(cn))
        fn = getattr(px, cn)
        sig_params = sorted(inspect.signature(fn).parameters.keys())
        print(f"\n=== {cn}: registry={len(names)} actual={len(sig_params)} ===")
        reg_set = set(names)
        sig_set = set(sig_params)
        missing = sorted(reg_set - sig_set)
        extra = sorted(sig_set - reg_set)
        if missing:
            print(f"  MISSING from registry: {missing}")
        if extra:
            print(f"  EXTRA (not in signature): {extra}")
        if not missing and not extra:
            print(f"  MATCH!")
        else:
            print(f"  Registry names: {names[:10]}...")
            print(f"  Actual sig: {sig_params[:10]}...")
    except Exception as e:
        print(f"\n=== {cn}: ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

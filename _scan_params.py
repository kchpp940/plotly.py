import re

with open('/Users/pkcha/plotly.py/plotly/express/_chart_types.py') as f:
    src = f.read()

# Find all def blocks and extract all parameters
def extract_all_params_from_source():
    # Match "def funcname(" ... up to the matching "):"
    all_params = set()
    fn_params = {}
    pattern = re.compile(r'^def\s+(\w+)\s*\((.*?)\)\s*:', re.DOTALL | re.MULTILINE)
    for m in pattern.finditer(src):
        fn_name = m.group(1)
        args_str = m.group(2).strip()
        # Parse individual params
        params = []
        # Remove line continuations and split by comma
        args_str = args_str.replace('\\\n', ' ').replace('\n', ' ')
        # Split by comma, but careful with tuples/lists in default values
        depth = 0
        cur = ''
        for ch in args_str:
            if ch in '([{':
                depth += 1
                cur += ch
            elif ch in ')]}':
                depth -= 1
                cur += ch
            elif ch == ',' and depth == 0:
                p = cur.strip().split('=')[0].strip()
                if p:
                    params.append(p)
                cur = ''
            else:
                cur += ch
        p = cur.strip().split('=')[0].strip()
        if p:
            params.append(p)
        if fn_name.startswith('_'):
            continue
        fn_params[fn_name] = params
        all_params.update(params)
    return fn_params, all_params

fn_params, all_params = extract_all_params_from_source()

# Try to import PARAMS and see which are missing
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_params_only",
        "/Users/pkcha/plotly.py/plotly/express/_params.py",
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    PARAMS = m.PARAMS

    reg_all = set(PARAMS.names_for_chart(None))
    missing = sorted(all_params - reg_all)
    extra = sorted(reg_all - all_params)
    print("All params in signatures:", sorted(all_params))
    print()
    print(f"Missing from PARAMS registry ({len(missing)}):")
    for x in missing:
        print(f"  {x}")
    print()
    print(f"In registry but not in any function sig ({len(extra)}):")
    for x in extra:
        print(f"  {x}")
    print()
    print("Per function:")
    for fn, params in sorted(fn_params.items()):
        reg = set(PARAMS.names_for_chart(fn))
        sig_set = set(params)
        miss = sorted(sig_set - reg)
        if miss:
            print(f"  {fn}: missing = {miss}")
except Exception as e:
    print(f"ERROR importing PARAMS: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    print("\nAll params from signatures:", sorted(all_params))

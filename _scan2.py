import re

with open('/Users/pkcha/plotly.py/plotly/express/_chart_types.py') as f:
    src = f.read()

# Better parser: extract the actual function signature lines by looking at `def funcname(` to the matching `)` on same or later lines
def better_parse():
    fn_map = {}
    lines = src.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^def\s+(\w+)\s*\((.*)$', line)
        if not m:
            i += 1
            continue
        fn_name = m.group(1)
        if fn_name.startswith('_'):
            i += 1
            continue
        args_part = m.group(2)
        depth = args_part.count('(') - args_part.count(')')
        j = i + 1
        while depth > 0 and j < len(lines):
            next_line = lines[j]
            args_part += ' ' + next_line
            depth += next_line.count('(') - next_line.count(')')
            j += 1
        # Find the first unmatched ')'
        k = 0
        paren = 0
        while k < len(args_part):
            ch = args_part[k]
            if ch == '(':
                paren += 1
            elif ch == ')':
                paren -= 1
                if paren == 0:
                    args_part = args_part[:k]
                    break
            k += 1
        # Now parse args
        params = []
        depth2 = 0
        cur = ''
        for ch in args_part:
            if ch in '([{':
                depth2 += 1
                cur += ch
            elif ch in ')]}':
                depth2 -= 1
                cur += ch
            elif ch == ',' and depth2 == 0:
                p = cur.strip().split('=')[0].strip()
                if p:
                    params.append(p)
                cur = ''
            else:
                cur += ch
        p = cur.strip().split('=')[0].strip()
        if p:
            params.append(p)
        fn_map[fn_name] = [p for p in params if p not in ('self', '*')]
        i = j
    return fn_map

fn_map = better_parse()

# Now try importing PARAMS - need proper way
import sys
sys.path.insert(0, '/Users/pkcha/plotly.py')
try:
    from plotly.express._params import PARAMS
    from plotly.express._params import create_registry
    # Check
    PARAMS2 = create_registry()
    missing_global = set()
    for fn, params in sorted(fn_map.items()):
        reg = set(PARAMS2.names_for_chart(fn))
        sig_set = set(params)
        for p in params:
            # Skip internal args
            if p in ('constructor', 'trace_patch', 'layout_patch',
                     'override_dict', 'append_dict', 'stacklevel'):
                continue
            if p not in reg:
                missing_global.add(p)
    print(f"MISSING from PARAMS ({len(missing_global)}):")
    for p in sorted(missing_global):
        print(f"  {p}")
        # Find which functions have p
        owners = [fn for fn, ps in fn_map.items() if p in ps]
        print(f"     used in: {owners}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    print("\nAll functions params collected:")
    for fn, params in sorted(fn_map.items()):
        print(f"  {fn}: {params}")

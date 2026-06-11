"""AST-based signature analyzer for _chart_types.py - no import needed."""
from __future__ import annotations

import ast
import sys
from collections import defaultdict


def extract_chart_functions(path: str) -> dict[str, list[tuple[str, object]]]:
    """Return {func_name: [(param_name, default_value_or_None), ...]} for public fns."""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=path)

    def _default_value(node: ast.expr | None) -> object:
        if node is None:
            return None  # no default
        # Try literal evaluation
        try:
            return ast.literal_eval(node)
        except (ValueError, SyntaxError):
            # e.g. None, builtins, simple names
            if isinstance(node, ast.NameConstant):
                return node.value
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Name) and node.id == "None":
                return None
            if isinstance(node, ast.Name) and node.id == "False":
                return False
            if isinstance(node, ast.Name) and node.id == "True":
                return True
            # For everything else, store the name as string
            return f"<{type(node).__name__}>"

    funcs: dict[str, list[tuple[str, object]]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            args = node.args
            params: list[tuple[str, object]] = []
            # Positional args + defaults alignment
            num_no_default = len(args.args) - len(args.defaults)
            for i, a in enumerate(args.args):
                if a.arg == "self":
                    continue
                def_idx = i - num_no_default
                default = args.defaults[def_idx] if def_idx >= 0 else None
                params.append((a.arg, _default_value(default)))
            funcs[node.name] = params
    return funcs


def get_registry_params():
    """Directly parse _params.py to get registered names and their charts, avoiding import."""
    import re
    with open("/Users/pkcha/plotly.py/plotly/express/_params.py", "r") as f:
        src = f.read()
    # Find all r.add(ParamMeta(... name="xxx", ... charts=(...) ...)) blocks
    # Use a simpler approach: find all ParamMeta( blocks and extract name= and charts=
    # Match ParamMeta opening, then capture lines until closing paren on its own or balanced
    result: dict[str, set[str]] = {}  # name -> set of chart names or {ALL}
    i = 0
    while i < len(src):
        idx = src.find("ParamMeta(", i)
        if idx == -1:
            break
        # Find balanced closing paren
        depth = 0
        j = idx
        started = False
        while j < len(src):
            c = src[j]
            if c == "(":
                depth += 1
                started = True
            elif c == ")":
                depth -= 1
                if started and depth == 0:
                    break
            j += 1
        block = src[idx:j + 1]
        i = j + 1
        # Extract name
        m = re.search(r'name\s*=\s*"([^"]+)"', block)
        if not m:
            continue
        name = m.group(1)
        # Extract charts
        charts: set[str] = set()
        cm = re.search(r"charts\s*=\s*([^,\n\)]+)", block)
        if cm:
            cexpr = cm.group(1).strip()
            if cexpr == "None":
                charts.add("__ALL__")
            else:
                # Extract all string literals from charts expression (may be tuple or var ref)
                for sm in re.finditer(r'"([^"]+)"', block):
                    # find strings in the whole block after charts= line
                    pass
                # Simpler: find all identifiers or strings after charts= up to comma/newline
                # Actually just re-scan block for charts = ... to the end of the line/expression
                cm2 = re.search(r"charts\s*=\s*(.+?)(?:,\s*\w+\s*=|\)$)", block, re.DOTALL)
                if cm2:
                    cexpr_full = cm2.group(1)
                    for sm in re.finditer(r'"([^"]+)"', cexpr_full):
                        charts.add(sm.group(1))
                    # Also check for tuple(var_ref) - we can't evaluate so mark as needing review
                    if re.search(r"[A-Z_]{3,}", cexpr_full):
                        charts.add("__HAS_VAR__")
        else:
            charts.add("__ALL__")  # no charts specified => applies to all
        result[name] = charts
    return result


def main():
    chart_types_path = "/Users/pkcha/plotly.py/plotly/express/_chart_types.py"
    funcs = extract_chart_functions(chart_types_path)
    reg = get_registry_params()

    print("=== All chart function signatures ===")
    for name in sorted(funcs.keys()):
        params = funcs[name]
        pnames = [p[0] for p in params]
        print(f"\n{name} ({len(pnames)} params):")
        print(f"  {pnames}")

    print("\n\n=== Missing: params in sig but NOT in registry (per-chart) ===")
    per_chart_missing = defaultdict(list)
    all_missing_names: set[str] = set()
    for fname, params in funcs.items():
        for pname, pdefault in params:
            if pname not in reg:
                per_chart_missing[fname].append((pname, pdefault))
                all_missing_names.add(pname)
    for fname in sorted(per_chart_missing.keys()):
        items = per_chart_missing[fname]
        if items:
            print(f"\n  {fname}: {items}")

    print(f"\n\n=== Total distinct missing param names: {len(all_missing_names)} ===")
    for n in sorted(all_missing_names):
        # which charts use it?
        charts_using = sorted(f for f, pl in per_chart_missing.items() if any(p[0]==n for p in pl))
        # find default
        defaults_used = []
        for f in charts_using:
            for pn, dv in per_chart_missing[f]:
                if pn == n:
                    defaults_used.append(dv)
                    break
        print(f"  {n!r:35s}  used_by={charts_using}  defaults={defaults_used}")

    print("\n\n=== Extra: params in registry but NOT used by any chart sig? (unlikely but check) ===")
    all_sig_names: set[str] = set()
    for params in funcs.values():
        for pn, _ in params:
            all_sig_names.add(pn)
    extra_reg = sorted(n for n in reg.keys() if n not in all_sig_names)
    if extra_reg:
        for n in extra_reg:
            print(f"  registry-only: {n!r}")
    else:
        print("  (none)")

    # Also just check the core four
    print("\n\n=== Core 4 focus: scatter / line / bar / histogram ===")
    for target in ("scatter", "line", "bar", "histogram"):
        params = funcs.get(target, [])
        pnames = [p[0] for p in params]
        missing = [p for p in pnames if p not in reg]
        extra = [p for p in reg if p not in pnames and reg[p] in ({"__ALL__"}, ) and
                 any(k == target or (isinstance(reg[p], set) and target in reg[p])
                     for _ in [1])]
        print(f"\n  {target}: {len(pnames)} sig params, missing={missing}")


if __name__ == "__main__":
    main()

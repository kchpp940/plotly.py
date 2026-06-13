"""
Schema artifact consistency checker for plotly.py

Validates that codegen outputs (validators, graph_objects, exports) and
documentation examples stay in sync with the plot-schema.json source of truth.

Uses the codegen PlotlyNode infrastructure to compute the authoritative
set of property paths, then cross-checks against _validators.json,
graph_objs _valid_props, __init__ exports, and doc examples.

Checks performed:
  1. Codegen paths vs _validators.json: every property the codegen would
     produce has a matching entry in _validators.json (and vice versa)
  2. Validators vs graph_objects _valid_props: every compound validator's
     property is present in the corresponding class's _valid_props set
  3. Export sync: graph_objs and graph_objects __init__.py stay in sync
  4. Trace class coverage: every trace in schema has a generated class file
  5. Layout property coverage: Layout._valid_props covers codegen layout props
  6. Doc attribute references: go.* attribute refs in docs are valid

Exit code is non-zero if any inconsistencies are found.
"""

import ast
import json
import os
import re
import sys
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

SCHEMA_PATH = os.path.join(PROJECT_ROOT, "codegen", "resources", "plot-schema.json")
VALIDATORS_PATH = os.path.join(PROJECT_ROOT, "plotly", "validators", "_validators.json")
GRAPH_OBJS_INIT = os.path.join(PROJECT_ROOT, "plotly", "graph_objs", "__init__.py")
GRAPH_OBJECTS_INIT = os.path.join(
    PROJECT_ROOT, "plotly", "graph_objects", "__init__.py"
)
GRAPH_OBJS_DIR = os.path.join(PROJECT_ROOT, "plotly", "graph_objs")
DOC_PYTHON_DIR = os.path.join(PROJECT_ROOT, "doc", "python")


class ConsistencyError:
    def __init__(self, check, message, severity="error", suggestion=None):
        self.check = check
        self.message = message
        self.severity = severity
        self.suggestion = suggestion

    def __str__(self):
        tag = "ERROR" if self.severity == "error" else "WARN"
        msg = f"[{tag}] [{self.check}] {self.message}"
        if self.suggestion:
            msg += f"\n        Suggestion: {self.suggestion}"
        return msg


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def load_file(path):
    with open(path, "r") as f:
        return f.read()


def _preprocess_schema(plotly_schema):
    layout = plotly_schema["layout"]["layoutAttributes"]

    template = {
        "data": {
            trace + "s": {"items": {trace: {}}, "role": "object"}
            for trace in plotly_schema["traces"]
        },
        "layout": {},
        "description": "",
    }

    layout["template"] = template

    items = plotly_schema["traces"]["sankey"]["attributes"]["link"]["colorscales"][
        "items"
    ]

    if "concentrationscales" in items:
        items["colorscale"] = items.pop("concentrationscales")


def collect_codegen_property_paths(plotly_schema):
    from codegen.utils import PlotlyNode, TraceNode, LayoutNode, FrameNode

    all_trace_nodes = PlotlyNode.get_all_datatype_nodes(plotly_schema, TraceNode)
    all_layout_nodes = PlotlyNode.get_all_datatype_nodes(plotly_schema, LayoutNode)
    all_frame_nodes = PlotlyNode.get_all_datatype_nodes(plotly_schema, FrameNode)

    trace_paths = set()
    for node in all_trace_nodes:
        if node.plotly_name and not node.is_array:
            key = ".".join(node.parent_path_parts + (node.name_property,))
            trace_paths.add(key)

    layout_paths = set()
    for node in all_layout_nodes:
        if node.plotly_name and not node.is_array:
            key = ".".join(node.parent_path_parts + (node.name_property,))
            layout_paths.add(key)

    frame_paths = set()
    for node in all_frame_nodes:
        if node.plotly_name and not node.is_array:
            key = ".".join(node.parent_path_parts + (node.name_property,))
            frame_paths.add(key)

    return trace_paths, layout_paths, frame_paths


def collect_codegen_trace_info(plotly_schema):
    """Collect (trace_name -> set of property_names) from codegen nodes."""
    from codegen.utils import PlotlyNode, TraceNode

    all_trace_nodes = PlotlyNode.get_all_datatype_nodes(plotly_schema, TraceNode)

    trace_info = {}
    for node in all_trace_nodes:
        if not node.is_array and len(node.node_path) <= 1:
            trace_name = node.plotly_name
            props = set()
            for child in node.child_datatypes:
                props.add(child.name_property)
            for child in node.child_literals:
                if child.plotly_name == "type":
                    props.add("type")
            trace_info[trace_name] = props

    return trace_info


def collect_codegen_layout_info(plotly_schema):
    """Collect top-level layout property names from codegen."""
    from codegen.utils import PlotlyNode, LayoutNode

    compound_layout_nodes = PlotlyNode.get_all_compound_datatype_nodes(
        plotly_schema, LayoutNode
    )
    layout_node = compound_layout_nodes[0]

    props = set()
    for child in layout_node.child_datatypes:
        props.add(child.name_property)
    for child in layout_node.child_literals:
        if child.plotly_name == "type":
            props.add("type")

    return props


def collect_valid_props_from_file(filepath):
    """Parse a Python file and extract _valid_props set literal."""
    try:
        source = load_file(filepath)
    except FileNotFoundError:
        return None

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == "_valid_props":
                            if isinstance(item.value, ast.Set):
                                elems = set()
                                for el in item.value.elts:
                                    if isinstance(el, ast.Constant):
                                        elems.add(str(el.value))
                                return elems
    return None


_BASE_CLASS_NAMES = {
    "BaseTraceType",
    "BaseLayoutType",
    "BaseLayoutHierarchyType",
    "BaseTraceHierarchyType",
    "BaseFrameHierarchyType",
    "BaseFigure",
}


def _resolve_base_class_names(source):
    """Scan imports to find alias mappings for base datatype classes.

    Returns a set of names (including potential aliases like '_BaseTraceType')
    that refer to the plotly base datatype classes.
    """
    result = set()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "basedatatypes" in module:
                for alias in node.names:
                    orig = alias.name
                    local = alias.asname or alias.name
                    if orig in _BASE_CLASS_NAMES:
                        result.add(local)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                orig = alias.name
                local = alias.asname or alias.name
                if any(b in orig for b in _BASE_CLASS_NAMES):
                    result.add(local)

    result.update(_BASE_CLASS_NAMES)
    return result


def collect_class_info_from_file(filepath):
    """Parse a Python file and extract (class_name, valid_props, parent_path)."""
    try:
        source = load_file(filepath)
    except FileNotFoundError:
        return None

    tree = ast.parse(source)
    valid_base_names = _resolve_base_class_names(source)
    class_name = None
    valid_props = None
    parent_path = None

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ""
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name in valid_base_names:
                    class_name = node.name
                    break

            if class_name:
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "_valid_props":
                                if isinstance(item.value, ast.Set):
                                    elems = set()
                                    for el in item.value.elts:
                                        if isinstance(el, ast.Constant):
                                            elems.add(str(el.value))
                                    valid_props = elems
                            if (
                                isinstance(target, ast.Name)
                                and target.id == "_parent_path_str"
                            ):
                                if isinstance(item.value, ast.Constant):
                                    parent_path = str(item.value)
                break

    if class_name:
        return {
            "class_name": class_name,
            "valid_props": valid_props or set(),
            "parent_path": parent_path or "",
            "filepath": filepath,
        }
    return None


def _relative_module_path(full_path, graph_objs_dir):
    """Convert an absolute file path to a dotted module path relative to graph_objs_dir."""
    rel = os.path.relpath(full_path, graph_objs_dir)
    rel_no_ext = rel[:-3] if rel.endswith(".py") else rel
    parts = rel_no_ext.split(os.sep)
    parts = [p for p in parts if p not in ("", "__init__")]
    if parts and parts[-1].startswith("_"):
        parts[-1] = parts[-1][1:]
    return ".".join(parts)


def collect_all_go_classes(graph_objs_dir):
    """Walk graph_objs directory and collect class info indexed by full dotted path.

    Returns dict with two keys:
      'by_full_path': { 'waterfall.marker.Marker': {...class info...}, ... }
      'by_class_name': { 'Waterfall': [...class infos...], 'Marker': [...], ... }
    """
    by_full_path = {}
    by_class_name = defaultdict(list)

    for dirpath, dirnames, filenames in os.walk(graph_objs_dir):
        dirnames.sort()
        for fname in sorted(filenames):
            if not (fname.startswith("_") and fname.endswith(".py")):
                continue
            if fname == "__init__.py":
                continue

            fpath = os.path.join(dirpath, fname)
            info = collect_class_info_from_file(fpath)
            if not info:
                continue

            class_name = info["class_name"]
            module_path = _relative_module_path(fpath, graph_objs_dir)
            parent_parts = module_path.split(".")[:-1] if "." in module_path else []
            if parent_parts:
                full_path = ".".join(parent_parts + [class_name])
            else:
                full_path = class_name

            info["module_path"] = module_path
            info["full_path"] = full_path
            by_full_path[full_path] = info
            by_class_name[class_name].append(info)

    return by_full_path, by_class_name


def collect_graph_objs_exports(init_path):
    """Parse graph_objs/__init__.py and extract class and module exports.

    Handles the relative_import pattern:
      __all__, __getattr__, __dir__ = relative_import(
          __name__,
          [".bar", ".box", ...],   # modules
          ["._bar.Bar", "._box.Box", ...],  # classes
      )
    """
    source = load_file(init_path)

    class_exports = set()
    module_exports = set()

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "relative_import":
                if len(node.args) >= 3:
                    modules_arg = node.args[1]
                    classes_arg = node.args[2]
                    if isinstance(modules_arg, (ast.List, ast.Tuple)):
                        for el in modules_arg.elts:
                            if isinstance(el, ast.Constant):
                                val = str(el.value)
                                if val.startswith("."):
                                    val = val[1:]
                                if val:
                                    module_exports.add(val)
                    if isinstance(classes_arg, (ast.List, ast.Tuple)):
                        for el in classes_arg.elts:
                            if isinstance(el, ast.Constant):
                                val = str(el.value)
                                parts = val.split(".")
                                if parts:
                                    class_name = parts[-1]
                                    if class_name:
                                        class_exports.add(class_name)

    return class_exports, module_exports


def collect_graph_objects_exports(init_path):
    """Parse graph_objects/__init__.py and extract class and module exports."""
    source = load_file(init_path)

    class_exports = set()
    module_exports = set()

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "relative_import":
                if len(node.args) >= 3:
                    modules_arg = node.args[1]
                    classes_arg = node.args[2]
                    if isinstance(modules_arg, (ast.List, ast.Tuple)):
                        for el in modules_arg.elts:
                            if isinstance(el, ast.Constant):
                                val = str(el.value)
                                parts = val.split(".")
                                if parts:
                                    mod_name = parts[-1]
                                    if mod_name and not mod_name[0].isupper():
                                        module_exports.add(mod_name)
                    if isinstance(classes_arg, (ast.List, ast.Tuple)):
                        for el in classes_arg.elts:
                            if isinstance(el, ast.Constant):
                                val = str(el.value)
                                parts = val.split(".")
                                if parts:
                                    class_name = parts[-1]
                                    if class_name and class_name[0].isupper():
                                        class_exports.add(class_name)

    return class_exports, module_exports


def collect_doc_go_attribute_refs(doc_dir):
    """Scan doc/python/*.md for go.<Class>.<attribute> references."""
    refs = defaultdict(set)
    if not os.path.isdir(doc_dir):
        return refs

    attr_pattern = re.compile(r"go\.([A-Z]\w*)\.([a-z_]\w*)")

    for fname in sorted(os.listdir(doc_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(doc_dir, fname)
        source = load_file(fpath)

        for match in attr_pattern.finditer(source):
            cls_name, attr_name = match.group(1), match.group(2)
            refs[cls_name].add(attr_name)

    return refs


def check_codegen_vs_validators(plotly_schema, validators_json):
    """Check 1: Codegen-recomputed property paths vs _validators.json."""
    errors = []

    trace_paths, layout_paths, frame_paths = collect_codegen_property_paths(
        plotly_schema
    )

    codegen_paths = trace_paths | layout_paths | frame_paths
    validator_keys = set(validators_json.keys()) - {"data"}

    missing_in_validators = codegen_paths - validator_keys
    for path in sorted(missing_in_validators):
        errors.append(
            ConsistencyError(
                "codegen-vs-validators",
                f"Codegen property '{path}' has no entry in _validators.json",
                suggestion="Re-run codegen: `python commands.py codegen`",
            )
        )

    extra_in_validators = validator_keys - codegen_paths
    for key in sorted(extra_in_validators):
        errors.append(
            ConsistencyError(
                "codegen-vs-validators",
                f"Validator key '{key}' has no corresponding codegen property",
                severity="warn",
                suggestion="Check if this is an orphaned validator entry or if schema preprocessing changed",
            )
        )

    return errors


def _validator_key_to_class_paths(val_key, data_class_str):
    """Convert a validator key + data_class_str to candidate full class paths.

    Handles special cases matching codegen's behavior in build_datatype_py():
      - layout.template.data.<trace> validators map to the top-level trace class
      - layout.template.layout validator maps to the top-level Layout class

    Examples:
      'waterfall' + 'Waterfall' -> ['Waterfall']
      'waterfall.marker' + 'Marker' -> ['waterfall.Marker']
      'layout.xaxis' + 'XAxis' -> ['layout.XAxis']
      'layout.template.data.bar' + 'Bar' -> ['Bar']
      'layout.template.layout' + 'Layout' -> ['Layout']
    """
    if val_key.startswith("layout.template.data."):
        return [data_class_str]

    if val_key == "layout.template.layout":
        return ["Layout"]

    if "." not in val_key:
        return [data_class_str]

    parts = val_key.split(".")
    parent_parts = parts[:-1]
    return [".".join(parent_parts + [data_class_str])]


def check_validators_vs_graph_objects(validators_json, graph_objs_dir):
    """Check 2: Every compound validator maps to a class whose property
    appears in the PARENT class's _valid_props.

    For example, validator 'waterfall.connector' has plotly_name='connector',
    and 'connector' must appear in Waterfall._valid_props (the parent class).

    Top-level validators (like 'waterfall' itself) have no parent, so we
    only verify the corresponding class exists.
    """
    errors = []

    by_full_path, by_class_name = collect_all_go_classes(graph_objs_dir)

    for val_key in sorted(validators_json.keys()):
        entry = validators_json[val_key]
        superclass = entry.get("superclass", "")
        if superclass not in ("CompoundValidator", "CompoundArrayValidator"):
            continue

        params = entry.get("params", {})
        data_class_str = params.get("data_class_str", "")
        if not data_class_str:
            continue

        plotly_name = params.get(
            "plotly_name",
            val_key.split(".")[-1] if "." in val_key else val_key,
        )

        candidate_paths = _validator_key_to_class_paths(val_key, data_class_str)
        matched = None
        for cand in candidate_paths:
            if cand in by_full_path:
                matched = by_full_path[cand]
                break

        if matched is None:
            if data_class_str in by_class_name:
                all_matches = by_class_name[data_class_str]
                if len(all_matches) == 1:
                    matched = all_matches[0]
                else:
                    errors.append(
                        ConsistencyError(
                            "validators-vs-graph_objects",
                            f"Validator '{val_key}' -> class '{data_class_str}' "
                            f"is ambiguous ({len(all_matches)} matches), none at "
                            f"expected path(s): {candidate_paths}",
                            suggestion=(
                                f"Available paths: "
                                f"{[m['full_path'] for m in all_matches]}"
                            ),
                        )
                    )
                    continue
            else:
                errors.append(
                    ConsistencyError(
                        "validators-vs-graph_objects",
                        f"Validator '{val_key}' references class '{data_class_str}' "
                        f"but no such class found (expected at one of: {candidate_paths})",
                        suggestion="Re-run codegen: `python commands.py codegen`",
                    )
                )
                continue

        if "." in val_key:
            parent_key = val_key.rsplit(".", 1)[0]
            parent_entry = validators_json.get(parent_key)

            if parent_entry:
                parent_params = parent_entry.get("params", {})
                parent_data_class_str = parent_params.get("data_class_str", "")

                parent_candidate_paths = _validator_key_to_class_paths(
                    parent_key, parent_data_class_str
                )
                parent_matched = None
                for pcand in parent_candidate_paths:
                    if pcand in by_full_path:
                        parent_matched = by_full_path[pcand]
                        break

                if parent_matched is None and parent_data_class_str in by_class_name:
                    pmatches = by_class_name[parent_data_class_str]
                    if len(pmatches) == 1:
                        parent_matched = pmatches[0]

                if parent_matched:
                    parent_props = parent_matched["valid_props"]
                    if plotly_name not in parent_props:
                        errors.append(
                            ConsistencyError(
                                "validators-vs-graph_objects",
                                f"Validator '{val_key}': property '{plotly_name}' "
                                f"not in parent class {parent_matched['full_path']}._valid_props",
                                suggestion=(
                                    f"Check {parent_matched['filepath']} — "
                                    f"_valid_props may be stale. "
                                    f"Re-run codegen: `python commands.py codegen`"
                                ),
                            )
                        )

    return errors


def check_graph_objs_exports(graph_objs_init, graph_objects_init):
    """Check 3: graph_objs and graph_objects exports should be consistent."""
    errors = []

    go_class_exports, go_module_exports = collect_graph_objs_exports(graph_objs_init)
    gos_class_exports, gos_module_exports = collect_graph_objects_exports(
        graph_objects_init
    )

    missing_in_objects = go_class_exports - gos_class_exports
    for cls in sorted(missing_in_objects):
        errors.append(
            ConsistencyError(
                "exports-sync",
                f"Class '{cls}' exported in graph_objs but missing from graph_objects",
                suggestion="Re-run codegen: `python commands.py codegen`",
            )
        )

    missing_in_objs = gos_class_exports - go_class_exports
    for cls in sorted(missing_in_objs):
        errors.append(
            ConsistencyError(
                "exports-sync",
                f"Class '{cls}' exported in graph_objects but missing from graph_objs",
                suggestion="Re-run codegen: `python commands.py codegen`",
            )
        )

    missing_mod_in_objects = go_module_exports - gos_module_exports
    for mod in sorted(missing_mod_in_objects):
        errors.append(
            ConsistencyError(
                "exports-sync",
                f"Module '{mod}' exported in graph_objs but missing from graph_objects",
                suggestion="Re-run codegen: `python commands.py codegen`",
            )
        )

    missing_mod_in_objs = gos_module_exports - go_module_exports
    for mod in sorted(missing_mod_in_objs):
        errors.append(
            ConsistencyError(
                "exports-sync",
                f"Module '{mod}' exported in graph_objects but missing from graph_objs",
                suggestion="Re-run codegen: `python commands.py codegen`",
            )
        )

    return errors


def check_trace_class_coverage(plotly_schema, graph_objs_dir):
    """Check 4: Every trace in schema should have a generated class file
    with matching _valid_props."""
    errors = []

    trace_info = collect_codegen_trace_info(plotly_schema)

    for trace_name, expected_props in sorted(trace_info.items()):
        expected_file = os.path.join(graph_objs_dir, f"_{trace_name}.py")
        if not os.path.isfile(expected_file):
            errors.append(
                ConsistencyError(
                    "trace-coverage",
                    f"Trace '{trace_name}' in schema but no graph_objs/_{trace_name}.py",
                    suggestion="Re-run codegen: `python commands.py codegen`",
                )
            )
            continue

        valid_props = collect_valid_props_from_file(expected_file)
        if valid_props is None:
            errors.append(
                ConsistencyError(
                    "trace-coverage",
                    f"Trace '{trace_name}' class file exists but has no _valid_props",
                    suggestion=f"Check {expected_file} — the class definition may be malformed",
                )
            )
            continue

        missing_props = expected_props - valid_props
        for prop in sorted(missing_props):
            errors.append(
                ConsistencyError(
                    "trace-coverage",
                    f"Trace '{trace_name}': schema property '{prop}' "
                    f"not in {trace_name.title().replace('_', '')}._valid_props",
                    suggestion=(
                        f"Property defined in schema but missing from generated class. "
                        f"Re-run codegen: `python commands.py codegen`"
                    ),
                )
            )

        extra_props = valid_props - expected_props
        for prop in sorted(extra_props):
            errors.append(
                ConsistencyError(
                    "trace-coverage",
                    f"Trace '{trace_name}': _valid_props has '{prop}' "
                    f"but not in schema properties",
                    severity="warn",
                    suggestion=(
                        f"Stale property in generated class. "
                        f"Re-run codegen: `python commands.py codegen`"
                    ),
                )
            )

    for fname in sorted(os.listdir(graph_objs_dir)):
        if fname.startswith("_") and fname.endswith(".py") and fname != "__init__.py":
            trace_name = fname[1:-3]
            if trace_name in (
                "figure",
                "figurewidget",
                "frame",
                "deprecations",
                "layout",
            ):
                continue
            if trace_name not in trace_info:
                errors.append(
                    ConsistencyError(
                        "trace-coverage",
                        f"graph_objs/_{trace_name}.py exists but "
                        f"'{trace_name}' not in schema traces",
                        severity="warn",
                        suggestion=(
                            f"Stale trace class file. If trace was removed from schema, "
                            f"delete the file manually and re-run codegen"
                        ),
                    )
                )

    return errors


def check_layout_valid_props(plotly_schema, graph_objs_dir):
    """Check 5: Layout._valid_props should cover all codegen layout properties."""
    errors = []

    layout_file = os.path.join(graph_objs_dir, "_layout.py")
    if not os.path.isfile(layout_file):
        errors.append(
            ConsistencyError(
                "layout-coverage",
                "graph_objs/_layout.py not found",
                suggestion="Re-run codegen: `python commands.py codegen`",
            )
        )
        return errors

    layout_valid_props = collect_valid_props_from_file(layout_file)
    if layout_valid_props is None:
        errors.append(
            ConsistencyError(
                "layout-coverage",
                "Could not parse _valid_props from graph_objs/_layout.py",
                suggestion="Check _layout.py — the class definition may be malformed",
            )
        )
        return errors

    codegen_layout_props = collect_codegen_layout_info(plotly_schema)

    missing_props = codegen_layout_props - layout_valid_props
    for prop in sorted(missing_props):
        errors.append(
            ConsistencyError(
                "layout-coverage",
                f"Codegen layout property '{prop}' not in Layout._valid_props",
                suggestion=(
                    f"Property defined in schema but missing from generated Layout class. "
                    f"Re-run codegen: `python commands.py codegen`"
                ),
            )
        )

    extra_props = layout_valid_props - codegen_layout_props
    for prop in sorted(extra_props):
        errors.append(
            ConsistencyError(
                "layout-coverage",
                f"Layout._valid_props has '{prop}' but not in codegen layout properties",
                severity="warn",
                suggestion=(
                    f"Stale property in Layout class. "
                    f"Re-run codegen: `python commands.py codegen`"
                ),
            )
        )

    return errors


def check_doc_attribute_refs(doc_dir, graph_objs_dir, plotly_schema):
    """Check 6: Doc examples go.Class.attribute should reference valid props.

    Note: Method names (like go.Figure.show) are excluded from this check
    since they don't appear in _valid_props. We only flag clear mistakes
    where the attribute looks like a data property (starts with lowercase
    letter) but doesn't exist in the class.
    """
    errors = []

    doc_refs = collect_doc_go_attribute_refs(doc_dir)
    if not doc_refs:
        return errors

    by_full_path, by_class_name = collect_all_go_classes(graph_objs_dir)

    _KNOWN_METHOD_NAMES = {
        "show",
        "update_layout",
        "update_traces",
        "add_trace",
        "add_traces",
        "update",
        "for_each_trace",
        "set_subplots",
        "add_hline",
        "add_vline",
        "add_hrect",
        "add_vrect",
        "to_dict",
        "to_json",
        "to_image",
        "write_html",
        "write_image",
        "write_json",
        "full_figure_for_development",
    }

    for cls_name, attr_refs in sorted(doc_refs.items()):
        matched = None
        if cls_name in by_class_name:
            matches = by_class_name[cls_name]
            for m in matches:
                if "." not in m["full_path"]:
                    matched = m
                    break
            if matched is None and matches:
                matched = matches[0]

        if matched is None:
            errors.append(
                ConsistencyError(
                    "doc-refs",
                    f"Doc references go.{cls_name} but class not found in graph_objects",
                    suggestion=(
                        f"Check that the class is properly exported. "
                        f"If renamed, update doc examples accordingly"
                    ),
                )
            )
            continue

        valid_props = matched["valid_props"]
        for attr in sorted(attr_refs):
            if attr in _KNOWN_METHOD_NAMES:
                continue
            if attr.startswith("add_") or attr.startswith("select_") or attr.startswith("update_") or attr.startswith("for_each_"):
                continue
            if attr not in valid_props:
                errors.append(
                    ConsistencyError(
                        "doc-refs",
                        f"Doc references go.{cls_name}.{attr} but '{attr}' "
                        f"not in {cls_name}._valid_props",
                        suggestion=(
                            f"Valid properties for {cls_name}: "
                            f"{sorted(list(valid_props))[:10]}..."
                            if len(valid_props) > 10
                            else f"Valid properties: {sorted(list(valid_props))}"
                        ),
                    )
                )

    return errors


def run_all_checks(verbose=False):
    """Run all consistency checks and return list of errors."""
    all_errors = []

    schema = load_json(SCHEMA_PATH)
    validators_json = load_json(VALIDATORS_PATH)

    _preprocess_schema(schema)

    if verbose:
        print("=" * 70)
        print("Schema Artifact Consistency Check")
        print("=" * 70)

    checks = [
        (
            "1. Codegen paths vs _validators.json",
            lambda: check_codegen_vs_validators(schema, validators_json),
        ),
        (
            "2. Validators vs graph_objects _valid_props",
            lambda: check_validators_vs_graph_objects(validators_json, GRAPH_OBJS_DIR),
        ),
        (
            "3. Export sync (graph_objs <-> graph_objects)",
            lambda: check_graph_objs_exports(GRAPH_OBJS_INIT, GRAPH_OBJECTS_INIT),
        ),
        (
            "4. Trace class coverage",
            lambda: check_trace_class_coverage(schema, GRAPH_OBJS_DIR),
        ),
        (
            "5. Layout property coverage",
            lambda: check_layout_valid_props(schema, GRAPH_OBJS_DIR),
        ),
        (
            "6. Doc attribute references",
            lambda: check_doc_attribute_refs(DOC_PYTHON_DIR, GRAPH_OBJS_DIR, schema),
        ),
    ]

    for check_name, check_fn in checks:
        if verbose:
            print(f"\n--- {check_name} ---")
        try:
            errors = check_fn()
        except Exception as e:
            import traceback

            traceback.print_exc()
            errors = [
                ConsistencyError(
                    check_name,
                    f"Check failed with exception: {e}",
                )
            ]
        all_errors.extend(errors)

        if verbose:
            if errors:
                for err in errors:
                    print(f"  {err}")
            else:
                print("  OK")

    error_count = sum(1 for e in all_errors if e.severity == "error")
    warn_count = sum(1 for e in all_errors if e.severity == "warn")

    if verbose:
        print("\n" + "=" * 70)
        print(f"Results: {error_count} errors, {warn_count} warnings")

        if error_count > 0:
            print("FAIL: Consistency check found errors.")
        elif warn_count > 0:
            print("PASS (with warnings): Consistency check passed with warnings.")
        else:
            print("PASS: All consistency checks passed.")

    return error_count, warn_count, all_errors


if __name__ == "__main__":
    error_count, _, _ = run_all_checks(verbose=True)
    sys.exit(1 if error_count > 0 else 0)

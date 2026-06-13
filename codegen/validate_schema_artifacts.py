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
    def __init__(self, check, message, severity="error"):
        self.check = check
        self.message = message
        self.severity = severity

    def __str__(self):
        tag = "ERROR" if self.severity == "error" else "WARN"
        return f"[{tag}] [{self.check}] {self.message}"


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


def collect_class_name_from_file(filepath):
    """Parse a Python file and extract the main class name."""
    try:
        source = load_file(filepath)
    except FileNotFoundError:
        return None

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ""
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name in (
                    "BaseTraceType",
                    "BaseLayoutType",
                    "BaseLayoutHierarchyType",
                    "BaseTraceHierarchyType",
                    "BaseFrameHierarchyType",
                ):
                    return node.name
    return None


def collect_all_go_classes(graph_objs_dir):
    """Walk graph_objs directory and collect class_name -> valid_props mapping."""
    result = {}

    for fname in sorted(os.listdir(graph_objs_dir)):
        if fname.startswith("_") and fname.endswith(".py") and fname != "__init__.py":
            fpath = os.path.join(graph_objs_dir, fname)
            class_name = collect_class_name_from_file(fpath)
            valid_props = collect_valid_props_from_file(fpath)
            if class_name and valid_props:
                result[class_name] = valid_props

    for subdir_name in sorted(os.listdir(graph_objs_dir)):
        subdir_path = os.path.join(graph_objs_dir, subdir_name)
        if os.path.isdir(subdir_path):
            for fname in sorted(os.listdir(subdir_path)):
                if fname.startswith("_") and fname.endswith(".py") and fname != "__init__.py":
                    fpath = os.path.join(subdir_path, fname)
                    class_name = collect_class_name_from_file(fpath)
                    valid_props = collect_valid_props_from_file(fpath)
                    if class_name and valid_props:
                        result[class_name] = valid_props

            for sub2_name in sorted(os.listdir(subdir_path)):
                sub2_path = os.path.join(subdir_path, sub2_name)
                if os.path.isdir(sub2_path):
                    for fname in sorted(os.listdir(sub2_path)):
                        if fname.startswith("_") and fname.endswith(".py") and fname != "__init__.py":
                            fpath = os.path.join(sub2_path, fname)
                            class_name = collect_class_name_from_file(fpath)
                            valid_props = collect_valid_props_from_file(fpath)
                            if class_name and valid_props:
                                result[class_name] = valid_props

    return result


def collect_graph_objs_exports(init_path):
    """Parse graph_objs/__init__.py and extract class and module exports."""
    source = load_file(init_path)

    class_exports = set()
    module_exports = set()

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and target.id == "__all__":
                            if isinstance(child.value, (ast.List, ast.Tuple)):
                                for el in child.value.elts:
                                    if isinstance(el, ast.Constant):
                                        class_exports.add(str(el.value))

    class_pattern = re.compile(r"from\s+\._(\w+)\s+import\s+(\w+)")
    module_pattern = re.compile(r"from\s+\.(\w+)\s+import\s+\1")

    for match in class_pattern.finditer(source):
        _, class_name = match.groups()
        class_exports.add(class_name)

    for match in module_pattern.finditer(source):
        mod_name = match.group(1)
        module_exports.add(mod_name)

    return class_exports, module_exports


def collect_graph_objects_exports(init_path):
    """Parse graph_objects/__init__.py and extract class and module exports."""
    source = load_file(init_path)

    class_exports = set()
    module_exports = set()

    class_pattern = re.compile(r'"\.\.graph_objs\.(\w+)"')
    for match in class_pattern.finditer(source):
        name = match.group(1)
        if name[0].isupper():
            class_exports.add(name)
        else:
            module_exports.add(name)

    return class_exports, module_exports


def collect_doc_go_attribute_refs(doc_dir):
    """Scan doc/python/*.md for go.<Class>.<attribute> references."""
    refs = defaultdict(set)
    if not os.path.isdir(doc_dir):
        return refs

    attr_pattern = re.compile(r"go\.([A-Z]\w*)\.([a-z]\w*)")

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
            )
        )

    extra_in_validators = validator_keys - codegen_paths
    for key in sorted(extra_in_validators):
        errors.append(
            ConsistencyError(
                "codegen-vs-validators",
                f"Validator key '{key}' has no corresponding codegen property",
                severity="warn",
            )
        )

    return errors


def check_validators_vs_graph_objects(validators_json, graph_objs_dir):
    """Check 2: Every compound validator's property should be in _valid_props."""
    errors = []

    all_go_props = collect_all_go_classes(graph_objs_dir)

    for val_key in sorted(validators_json.keys()):
        entry = validators_json[val_key]
        superclass = entry.get("superclass", "")
        if superclass != "CompoundValidator":
            continue

        params = entry.get("params", {})
        data_class_str = params.get("data_class_str", "")
        if not data_class_str:
            continue

        prop_name = params.get(
            "plotly_name",
            val_key.split(".")[-1] if "." in val_key else val_key,
        )

        if data_class_str in all_go_props:
            go_props = all_go_props[data_class_str]
            if prop_name not in go_props:
                errors.append(
                    ConsistencyError(
                        "validators-vs-graph_objects",
                        f"Validator '{val_key}' maps to class '{data_class_str}' "
                        f"but property '{prop_name}' not in {data_class_str}._valid_props",
                    )
                )
        else:
            errors.append(
                ConsistencyError(
                    "validators-vs-graph_objects",
                    f"Validator '{val_key}' references class '{data_class_str}' "
                    f"but no such class found in graph_objs",
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
            )
        )

    missing_in_objs = gos_class_exports - go_class_exports
    for cls in sorted(missing_in_objs):
        errors.append(
            ConsistencyError(
                "exports-sync",
                f"Class '{cls}' exported in graph_objects but missing from graph_objs",
            )
        )

    missing_mod_in_objects = go_module_exports - gos_module_exports
    for mod in sorted(missing_mod_in_objects):
        errors.append(
            ConsistencyError(
                "exports-sync",
                f"Module '{mod}' exported in graph_objs but missing from graph_objects",
            )
        )

    missing_mod_in_objs = gos_module_exports - go_module_exports
    for mod in sorted(missing_mod_in_objs):
        errors.append(
            ConsistencyError(
                "exports-sync",
                f"Module '{mod}' exported in graph_objects but missing from graph_objs",
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
                )
            )
            continue

        valid_props = collect_valid_props_from_file(expected_file)
        if valid_props is None:
            errors.append(
                ConsistencyError(
                    "trace-coverage",
                    f"Trace '{trace_name}' class file exists but has no _valid_props",
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
                    )
                )

    return errors


def check_layout_valid_props(plotly_schema, graph_objs_dir):
    """Check 5: Layout._valid_props should cover all codegen layout properties."""
    errors = []

    layout_file = os.path.join(graph_objs_dir, "_layout.py")
    if not os.path.isfile(layout_file):
        errors.append(
            ConsistencyError("layout-coverage", "graph_objs/_layout.py not found")
        )
        return errors

    layout_valid_props = collect_valid_props_from_file(layout_file)
    if layout_valid_props is None:
        errors.append(
            ConsistencyError(
                "layout-coverage",
                "Could not parse _valid_props from graph_objs/_layout.py",
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
            )
        )

    extra_props = layout_valid_props - codegen_layout_props
    for prop in sorted(extra_props):
        errors.append(
            ConsistencyError(
                "layout-coverage",
                f"Layout._valid_props has '{prop}' but not in codegen layout properties",
                severity="warn",
            )
        )

    return errors


def check_doc_attribute_refs(doc_dir, graph_objs_dir, plotly_schema):
    """Check 6: Doc examples go.Class.attribute should reference valid props."""
    errors = []

    doc_refs = collect_doc_go_attribute_refs(doc_dir)
    if not doc_refs:
        return errors

    all_go_props = collect_all_go_classes(graph_objs_dir)

    for cls_name, attr_refs in sorted(doc_refs.items()):
        if cls_name not in all_go_props:
            errors.append(
                ConsistencyError(
                    "doc-refs",
                    f"Doc references go.{cls_name} but class not found in graph_objects",
                )
            )
            continue

        valid_props = all_go_props[cls_name]
        for attr in sorted(attr_refs):
            if attr not in valid_props:
                errors.append(
                    ConsistencyError(
                        "doc-refs",
                        f"Doc references go.{cls_name}.{attr} but '{attr}' "
                        f"not in {cls_name}._valid_props",
                    )
                )

    return errors


def run_all_checks():
    """Run all consistency checks and return list of errors."""
    all_errors = []

    schema = load_json(SCHEMA_PATH)
    validators_json = load_json(VALIDATORS_PATH)

    _preprocess_schema(schema)

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

        if errors:
            for err in errors:
                print(f"  {err}")
        else:
            print("  OK")

    print("\n" + "=" * 70)
    error_count = sum(1 for e in all_errors if e.severity == "error")
    warn_count = sum(1 for e in all_errors if e.severity == "warn")
    print(f"Results: {error_count} errors, {warn_count} warnings")

    if error_count > 0:
        print("FAIL: Consistency check found errors.")
        return 1
    elif warn_count > 0:
        print("PASS (with warnings): Consistency check passed with warnings.")
        return 0
    else:
        print("PASS: All consistency checks passed.")
        return 0


if __name__ == "__main__":
    sys.exit(run_all_checks())

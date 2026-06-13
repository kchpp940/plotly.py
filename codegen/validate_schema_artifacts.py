"""
Schema artifact consistency checker for plotly.py

Validates that codegen outputs (validators, graph_objects, exports) and
documentation examples stay in sync with the plot-schema.json source of truth.

Architecture
------------
  *Configuration*            *Artifact Indices*              *Check Engine*
  ┌─────────────────┐      ┌──────────────────────┐       ┌────────────────────┐
  │ DEFAULT_CONFIG  │      │ SchemaArtifactIndex  │       │  ConsistencyCheck  │
  │  - checks       │      │  (plot-schema.json)  │       │  - load indices    │
  │  - doc rules    │      ├──────────────────────┤       │  - run checks      │
  │  - ignore lists │      │ValidatorArtifactIndex│       │  - format results  │
  └─────────────────┘      │ (_validators.json)   │       └────────────────────┘
                           ├──────────────────────┤
                           │GraphObjectArtifactIdx│
                           │  (graph_objs/*.py)   │
                           ├──────────────────────┤
                           │ DocReferenceIndex    │
                           │   (doc/python/*.md)  │
                           └──────────────────────┘

Each artifact index produces a structured, normalized view of its data
source. The ConsistencyCheck engine compares these indices according to
configurable rules.
"""

import ast
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


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


# =========================================================================
# CONFIGURATION
# =========================================================================


@dataclass
class DocReferenceRules:
    """Rules for validating documentation attribute references."""

    known_method_names: Set[str] = field(
        default_factory=lambda: {
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
    )
    method_prefix_ignores: Tuple[str, ...] = (
        "add_",
        "select_",
        "update_",
        "for_each_",
    )
    attribute_reference_pattern: str = r"go\.([A-Z]\w*)\.([a-z_]\w*)"


@dataclass
class ClassIndexingRules:
    """Rules for indexing graph_objs classes."""

    base_class_names: Set[str] = field(
        default_factory=lambda: {
            "BaseTraceType",
            "BaseLayoutType",
            "BaseLayoutHierarchyType",
            "BaseTraceHierarchyType",
            "BaseFrameHierarchyType",
            "BaseFigure",
        }
    )
    file_pattern: str = "_*.py"
    exclude_trace_files: Set[str] = field(
        default_factory=lambda: {
            "figure",
            "figurewidget",
            "frame",
            "deprecations",
            "layout",
        }
    )


@dataclass
class CheckSpec:
    """Configuration for a single consistency check."""

    enabled: bool = True
    severity_overrides: Dict[str, str] = field(default_factory=dict)
    ignore_patterns: Set[str] = field(default_factory=set)


@dataclass
class ValidatorRules:
    """Rules for validator key → class path mapping."""

    special_mappings: Dict[str, str] = field(default_factory=dict)
    template_prefix: str = "layout.template.data."
    template_layout_key: str = "layout.template.layout"
    compound_validator_superclasses: Set[str] = field(
        default_factory=lambda: {"CompoundValidator", "CompoundArrayValidator"}
    )


@dataclass
class ValidationConfig:
    """Top-level configuration for all consistency checks."""

    checks: Dict[str, CheckSpec] = field(
        default_factory=lambda: {
            "codegen-vs-validators": CheckSpec(),
            "validators-vs-graph_objects": CheckSpec(),
            "exports-sync": CheckSpec(),
            "trace-coverage": CheckSpec(),
            "layout-coverage": CheckSpec(),
            "doc-refs": CheckSpec(),
        }
    )
    doc_rules: DocReferenceRules = field(default_factory=DocReferenceRules)
    class_rules: ClassIndexingRules = field(default_factory=ClassIndexingRules)
    validator_rules: ValidatorRules = field(default_factory=ValidatorRules)
    default_severity: str = "error"
    default_suggestion: str = "Re-run codegen: `python commands.py codegen`"


DEFAULT_CONFIG = ValidationConfig()


# =========================================================================
# CONSISTENCY ERROR (output model)
# =========================================================================


@dataclass
class ConsistencyError:
    """Represents a single consistency finding."""

    check: str
    message: str
    severity: str = "error"
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        tag = "ERROR" if self.severity == "error" else "WARN"
        msg = f"[{tag}] [{self.check}] {self.message}"
        if self.suggestion:
            msg += f"\n        Suggestion: {self.suggestion}"
        return msg


# =========================================================================
# UTILITIES
# =========================================================================


def load_json(path: str) -> Any:
    with open(path, "r") as f:
        return json.load(f)


def load_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


# =========================================================================
# ARTIFICAT INDEX BASE
# =========================================================================


class BaseArtifactIndex:
    """Abstract base for structured artifact indices."""

    def __init__(self, config: ValidationConfig = DEFAULT_CONFIG):
        self.config = config
        self._built = False

    def build(self) -> None:
        """Build the index. Subclasses implement _build()."""
        self._build()
        self._built = True

    def _build(self) -> None:
        raise NotImplementedError

    def require_built(self) -> None:
        if not self._built:
            raise RuntimeError(f"{self.__class__.__name__} not built. Call build() first.")


# =========================================================================
# SCHEMA ARTIFACT INDEX
# =========================================================================


class SchemaArtifactIndex(BaseArtifactIndex):
    """Structured index of plot-schema.json.

    Attributes
    ----------
    raw_schema : dict
        The raw preprocessed schema dict.
    trace_property_paths : set[str]
        All trace property paths (e.g. 'waterfall.connector.line.color').
    layout_property_paths : set[str]
        All layout property paths.
    frame_property_paths : set[str]
        All frame property paths.
    all_property_paths : set[str]
        Union of trace+layout+frame paths.
    trace_properties : dict[str, set[str]]
        Mapping of trace_name → set of top-level property names.
    layout_properties : set[str]
        Set of top-level layout property names.
    """

    def __init__(
        self,
        schema_path: str = SCHEMA_PATH,
        config: ValidationConfig = DEFAULT_CONFIG,
    ):
        super().__init__(config)
        self.schema_path = schema_path
        self.raw_schema: Dict[str, Any] = {}
        self.trace_property_paths: Set[str] = set()
        self.layout_property_paths: Set[str] = set()
        self.frame_property_paths: Set[str] = set()
        self.all_property_paths: Set[str] = set()
        self.trace_properties: Dict[str, Set[str]] = {}
        self.layout_properties: Set[str] = set()

    @staticmethod
    def _preprocess_schema(plotly_schema: Dict[str, Any]) -> None:
        """Apply the same preprocessing that codegen uses."""
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

    def _build(self) -> None:
        from codegen.utils import (
            PlotlyNode,
            TraceNode,
            LayoutNode,
            FrameNode,
        )

        self.raw_schema = load_json(self.schema_path)
        self._preprocess_schema(self.raw_schema)

        all_trace_nodes = PlotlyNode.get_all_datatype_nodes(self.raw_schema, TraceNode)
        all_layout_nodes = PlotlyNode.get_all_datatype_nodes(self.raw_schema, LayoutNode)
        all_frame_nodes = PlotlyNode.get_all_datatype_nodes(self.raw_schema, FrameNode)

        for node in all_trace_nodes:
            if node.plotly_name and not node.is_array:
                key = ".".join(node.parent_path_parts + (node.name_property,))
                self.trace_property_paths.add(key)

        for node in all_layout_nodes:
            if node.plotly_name and not node.is_array:
                key = ".".join(node.parent_path_parts + (node.name_property,))
                self.layout_property_paths.add(key)

        for node in all_frame_nodes:
            if node.plotly_name and not node.is_array:
                key = ".".join(node.parent_path_parts + (node.name_property,))
                self.frame_property_paths.add(key)

        self.all_property_paths = (
            self.trace_property_paths
            | self.layout_property_paths
            | self.frame_property_paths
        )

        self._build_trace_properties(all_trace_nodes)
        self._build_layout_properties(self.raw_schema)

    def _build_trace_properties(self, all_trace_nodes) -> None:
        """Collect (trace_name → set of property_names) from codegen nodes."""
        for node in all_trace_nodes:
            if not node.is_array and len(node.node_path) <= 1:
                trace_name = node.plotly_name
                props = set()
                for child in node.child_datatypes:
                    props.add(child.name_property)
                for child in node.child_literals:
                    if child.plotly_name == "type":
                        props.add("type")
                self.trace_properties[trace_name] = props

    def _build_layout_properties(self, schema: Dict[str, Any]) -> None:
        """Collect top-level layout property names from codegen."""
        from codegen.utils import PlotlyNode, LayoutNode

        compound_layout_nodes = PlotlyNode.get_all_compound_datatype_nodes(
            schema, LayoutNode
        )
        layout_node = compound_layout_nodes[0]

        props = set()
        for child in layout_node.child_datatypes:
            props.add(child.name_property)
        for child in layout_node.child_literals:
            if child.plotly_name == "type":
                props.add("type")

        self.layout_properties = props


# =========================================================================
# VALIDATOR ARTIFACT INDEX
# =========================================================================


@dataclass
class ValidatorEntry:
    """Structured view of a single _validators.json entry."""

    key: str
    superclass: str
    data_class_str: str
    plotly_name: str
    raw_params: Dict[str, Any]
    is_compound: bool

    @property
    def parent_key(self) -> Optional[str]:
        if "." in self.key:
            return self.key.rsplit(".", 1)[0]
        return None


class ValidatorArtifactIndex(BaseArtifactIndex):
    """Structured index of _validators.json.

    Attributes
    ----------
    raw_validators : dict
        The raw _validators.json dict.
    entries : dict[str, ValidatorEntry]
        All validator entries keyed by validator key.
    compound_entries : dict[str, ValidatorEntry]
        Only compound/CompoundArray validators keyed by validator key.
    all_keys : set[str]
        Set of all validator keys (excluding the 'data' sentinel).
    """

    def __init__(
        self,
        validators_path: str = VALIDATORS_PATH,
        config: ValidationConfig = DEFAULT_CONFIG,
    ):
        super().__init__(config)
        self.validators_path = validators_path
        self.raw_validators: Dict[str, Any] = {}
        self.entries: Dict[str, ValidatorEntry] = {}
        self.compound_entries: Dict[str, ValidatorEntry] = {}
        self.all_keys: Set[str] = set()

    def _build(self) -> None:
        self.raw_validators = load_json(self.validators_path)
        compound_superclasses = self.config.validator_rules.compound_validator_superclasses

        for key, entry in self.raw_validators.items():
            if key == "data":
                continue

            superclass = entry.get("superclass", "")
            params = entry.get("params", {})
            data_class_str = params.get("data_class_str", "")
            plotly_name = params.get(
                "plotly_name",
                key.split(".")[-1] if "." in key else key,
            )
            is_compound = superclass in compound_superclasses

            ventry = ValidatorEntry(
                key=key,
                superclass=superclass,
                data_class_str=data_class_str,
                plotly_name=plotly_name,
                raw_params=params,
                is_compound=is_compound,
            )
            self.entries[key] = ventry
            if is_compound:
                self.compound_entries[key] = ventry

        self.all_keys = set(self.entries.keys())

    def validator_key_to_class_paths(
        self, val_key: str, data_class_str: str
    ) -> List[str]:
        """Convert a validator key + data_class_str to candidate full class paths.

        Matches codegen's behavior in build_datatype_py():
          - layout.template.data.<trace> validators map to the top-level trace class
          - layout.template.layout validator maps to the top-level Layout class
        """
        vrules = self.config.validator_rules
        if val_key.startswith(vrules.template_prefix):
            return [data_class_str]
        if val_key == vrules.template_layout_key:
            return ["Layout"]
        if val_key in vrules.special_mappings:
            return [vrules.special_mappings[val_key]]
        if "." not in val_key:
            return [data_class_str]
        parts = val_key.split(".")
        parent_parts = parts[:-1]
        return [".".join(parent_parts + [data_class_str])]


# =========================================================================
# GRAPH OBJECT ARTIFACT INDEX
# =========================================================================


@dataclass
class GOClassInfo:
    """Structured information about a generated graph_objs class."""

    class_name: str
    full_path: str
    module_path: str
    valid_props: Set[str]
    parent_path: str
    filepath: str

    @property
    def is_top_level(self) -> bool:
        return "." not in self.full_path


class GraphObjectArtifactIndex(BaseArtifactIndex):
    """Structured index of graph_objs generated code.

    Attributes
    ----------
    by_full_path : dict[str, GOClassInfo]
        Classes indexed by full dotted path (e.g. 'waterfall.marker.Marker').
    by_class_name : dict[str, list[GOClassInfo]]
        Classes indexed by bare class name (may have multiple matches).
    graph_objs_class_exports : set[str]
        Class names exported by graph_objs/__init__.py.
    graph_objs_module_exports : set[str]
        Module names exported by graph_objs/__init__.py.
    graph_objects_class_exports : set[str]
        Class names exported by graph_objects/__init__.py.
    graph_objects_module_exports : set[str]
        Module names exported by graph_objects/__init__.py.
    """

    def __init__(
        self,
        graph_objs_dir: str = GRAPH_OBJS_DIR,
        graph_objs_init: str = GRAPH_OBJS_INIT,
        graph_objects_init: str = GRAPH_OBJECTS_INIT,
        config: ValidationConfig = DEFAULT_CONFIG,
    ):
        super().__init__(config)
        self.graph_objs_dir = graph_objs_dir
        self.graph_objs_init = graph_objs_init
        self.graph_objects_init = graph_objects_init

        self.by_full_path: Dict[str, GOClassInfo] = {}
        self.by_class_name: Dict[str, List[GOClassInfo]] = defaultdict(list)
        self.graph_objs_class_exports: Set[str] = set()
        self.graph_objs_module_exports: Set[str] = set()
        self.graph_objects_class_exports: Set[str] = set()
        self.graph_objects_module_exports: Set[str] = set()

    def _build(self) -> None:
        self._build_class_index()
        self._build_exports()

    def _resolve_base_class_names(self, source: str) -> Set[str]:
        """Scan imports to find alias mappings for base datatype classes."""
        valid_bases = self.config.class_rules.base_class_names
        result = set()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "basedatatypes" in module:
                    for alias in node.names:
                        orig = alias.name
                        local = alias.asname or alias.name
                        if orig in valid_bases:
                            result.add(local)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    orig = alias.name
                    local = alias.asname or alias.name
                    if any(b in orig for b in valid_bases):
                        result.add(local)

        result.update(valid_bases)
        return result

    def _parse_class_from_file(self, filepath: str) -> Optional[GOClassInfo]:
        """Parse a single Python file and extract GO class info."""
        try:
            source = load_file(filepath)
        except FileNotFoundError:
            return None

        tree = ast.parse(source)
        valid_base_names = self._resolve_base_class_names(source)
        class_name: Optional[str] = None
        valid_props: Optional[Set[str]] = None
        parent_path: Optional[str] = None

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
                                if isinstance(target, ast.Name):
                                    if target.id == "_valid_props":
                                        if isinstance(item.value, ast.Set):
                                            elems = set()
                                            for el in item.value.elts:
                                                if isinstance(el, ast.Constant):
                                                    elems.add(str(el.value))
                                            valid_props = elems
                                    elif target.id == "_parent_path_str":
                                        if isinstance(item.value, ast.Constant):
                                            parent_path = str(item.value)
                    break

        if not class_name:
            return None

        module_path = self._relative_module_path(filepath)
        parent_parts = module_path.split(".")[:-1] if "." in module_path else []
        if parent_parts:
            full_path = ".".join(parent_parts + [class_name])
        else:
            full_path = class_name

        return GOClassInfo(
            class_name=class_name,
            full_path=full_path,
            module_path=module_path,
            valid_props=valid_props or set(),
            parent_path=parent_path or "",
            filepath=filepath,
        )

    def _relative_module_path(self, full_path: str) -> str:
        rel = os.path.relpath(full_path, self.graph_objs_dir)
        rel_no_ext = rel[:-3] if rel.endswith(".py") else rel
        parts = rel_no_ext.split(os.sep)
        parts = [p for p in parts if p not in ("", "__init__")]
        if parts and parts[-1].startswith("_"):
            parts[-1] = parts[-1][1:]
        return ".".join(parts)

    def _build_class_index(self) -> None:
        for dirpath, dirnames, filenames in os.walk(self.graph_objs_dir):
            dirnames.sort()
            for fname in sorted(filenames):
                if not (fname.startswith("_") and fname.endswith(".py")):
                    continue
                if fname == "__init__.py":
                    continue

                fpath = os.path.join(dirpath, fname)
                info = self._parse_class_from_file(fpath)
                if not info:
                    continue

                self.by_full_path[info.full_path] = info
                self.by_class_name[info.class_name].append(info)

    def _parse_relative_import_exports(
        self, init_path: str, filter_classes: bool = False
    ) -> Tuple[Set[str], Set[str]]:
        """Parse graph_objs/__init__.py-style relative_import() call."""
        source = load_file(init_path)
        class_exports: Set[str] = set()
        module_exports: Set[str] = set()

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
                                        name = parts[-1]
                                        if name:
                                            if filter_classes and not name[0].isupper():
                                                module_exports.add(name)
                                            elif not filter_classes:
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
                                        name = parts[-1]
                                        if name and (not filter_classes or name[0].isupper()):
                                            class_exports.add(name)

        return class_exports, module_exports

    def _build_exports(self) -> None:
        (
            self.graph_objs_class_exports,
            self.graph_objs_module_exports,
        ) = self._parse_relative_import_exports(self.graph_objs_init, filter_classes=False)

        (
            self.graph_objects_class_exports,
            self.graph_objects_module_exports,
        ) = self._parse_relative_import_exports(
            self.graph_objects_init, filter_classes=True
        )

    def find_top_level_class(self, class_name: str) -> Optional[GOClassInfo]:
        """Find the top-level (non-nested) class by name."""
        if class_name not in self.by_class_name:
            return None
        matches = self.by_class_name[class_name]
        for m in matches:
            if m.is_top_level:
                return m
        return matches[0] if matches else None

    def collect_valid_props_from_file(self, filepath: str) -> Optional[Set[str]]:
        """Convenience: extract _valid_props set from a single file."""
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


# =========================================================================
# DOC REFERENCE INDEX
# =========================================================================


@dataclass
class DocReference:
    """A single documented go.Class.attribute reference."""

    class_name: str
    attribute: str
    source_file: str


class DocReferenceIndex(BaseArtifactIndex):
    """Structured index of go.Class.attribute references in docs.

    Attributes
    ----------
    references : dict[str, set[str]]
        Mapping of class_name → set of referenced attribute names.
    all_references : list[DocReference]
        Flat list of all (class, attribute, file) tuples.
    """

    def __init__(
        self,
        doc_dir: str = DOC_PYTHON_DIR,
        config: ValidationConfig = DEFAULT_CONFIG,
    ):
        super().__init__(config)
        self.doc_dir = doc_dir
        self.references: Dict[str, Set[str]] = defaultdict(set)
        self.all_references: List[DocReference] = []

    def _build(self) -> None:
        if not os.path.isdir(self.doc_dir):
            return

        pattern = re.compile(self.config.doc_rules.attribute_reference_pattern)

        for fname in sorted(os.listdir(self.doc_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(self.doc_dir, fname)
            source = load_file(fpath)

            for match in pattern.finditer(source):
                cls_name, attr_name = match.group(1), match.group(2)
                self.references[cls_name].add(attr_name)
                self.all_references.append(
                    DocReference(
                        class_name=cls_name,
                        attribute=attr_name,
                        source_file=fpath,
                    )
                )

    def is_ignored_attribute(self, attr: str) -> bool:
        """Check if an attribute should be skipped based on doc rules."""
        rules = self.config.doc_rules
        if attr in rules.known_method_names:
            return True
        for prefix in rules.method_prefix_ignores:
            if attr.startswith(prefix):
                return True
        return False


# =========================================================================
# CONSISTENCY CHECK ENGINE
# =========================================================================


class ConsistencyCheck:
    """Engine that compares artifact indices according to configurable rules.

    Usage
    -----
        checker = ConsistencyCheck()
        checker.build_indices()
        errors = checker.run_all_checks()
    """

    def __init__(
        self,
        config: ValidationConfig = DEFAULT_CONFIG,
        schema_path: str = SCHEMA_PATH,
        validators_path: str = VALIDATORS_PATH,
        graph_objs_dir: str = GRAPH_OBJS_DIR,
        graph_objs_init: str = GRAPH_OBJS_INIT,
        graph_objects_init: str = GRAPH_OBJECTS_INIT,
        doc_dir: str = DOC_PYTHON_DIR,
    ):
        self.config = config
        self.schema_idx = SchemaArtifactIndex(schema_path, config)
        self.validator_idx = ValidatorArtifactIndex(validators_path, config)
        self.go_idx = GraphObjectArtifactIndex(
            graph_objs_dir, graph_objs_init, graph_objects_init, config
        )
        self.doc_idx = DocReferenceIndex(doc_dir, config)

    def build_indices(self) -> None:
        """Build all four artifact indices."""
        self.schema_idx.build()
        self.validator_idx.build()
        self.go_idx.build()
        self.doc_idx.build()

    def _apply_check_overrides(self, check_name: str, errors: List[ConsistencyError]) -> List[ConsistencyError]:
        """Apply severity overrides and ignore patterns from config."""
        spec = self.config.checks.get(check_name)
        if not spec or not spec.enabled:
            return []

        result = []
        for err in errors:
            ignored = False
            for pat in spec.ignore_patterns:
                if re.search(pat, err.message):
                    ignored = True
                    break
            if ignored:
                continue

            if err.message in spec.severity_overrides:
                err.severity = spec.severity_overrides[err.message]
            result.append(err)
        return result

    # ----- Individual checks -----

    def check_codegen_vs_validators(self) -> List[ConsistencyError]:
        """Check 1: Codegen-recomputed property paths vs _validators.json."""
        check_name = "codegen-vs-validators"
        errors: List[ConsistencyError] = []

        codegen_paths = self.schema_idx.all_property_paths
        validator_keys = self.validator_idx.all_keys

        missing_in_validators = codegen_paths - validator_keys
        for path in sorted(missing_in_validators):
            errors.append(
                ConsistencyError(
                    check_name,
                    f"Codegen property '{path}' has no entry in _validators.json",
                    suggestion=self.config.default_suggestion,
                )
            )

        extra_in_validators = validator_keys - codegen_paths
        for key in sorted(extra_in_validators):
            errors.append(
                ConsistencyError(
                    check_name,
                    f"Validator key '{key}' has no corresponding codegen property",
                    severity="warn",
                    suggestion=(
                        "Check if this is an orphaned validator entry or if "
                        "schema preprocessing changed"
                    ),
                )
            )

        return self._apply_check_overrides(check_name, errors)

    def check_validators_vs_graph_objects(self) -> List[ConsistencyError]:
        """Check 2: Every compound validator's property appears in the
        PARENT class's _valid_props."""
        check_name = "validators-vs-graph_objects"
        errors: List[ConsistencyError] = []

        by_full_path = self.go_idx.by_full_path
        by_class_name = self.go_idx.by_class_name
        v_idx = self.validator_idx

        for val_key in sorted(v_idx.compound_entries.keys()):
            ventry = v_idx.compound_entries[val_key]
            data_class_str = ventry.data_class_str
            if not data_class_str:
                continue

            plotly_name = ventry.plotly_name
            candidate_paths = v_idx.validator_key_to_class_paths(val_key, data_class_str)
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
                                check_name,
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
                            check_name,
                            f"Validator '{val_key}' references class '{data_class_str}' "
                            f"but no such class found (expected at one of: {candidate_paths})",
                            suggestion=self.config.default_suggestion,
                        )
                    )
                    continue

            if "." in val_key:
                parent_key = ventry.parent_key
                parent_ventry = v_idx.entries.get(parent_key) if parent_key else None

                if parent_ventry:
                    parent_data_class_str = parent_ventry.data_class_str
                    parent_candidate_paths = v_idx.validator_key_to_class_paths(
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
                        parent_props = parent_matched.valid_props
                        if plotly_name not in parent_props:
                            errors.append(
                                ConsistencyError(
                                    check_name,
                                    f"Validator '{val_key}': property '{plotly_name}' "
                                    f"not in parent class {parent_matched.full_path}._valid_props",
                                    suggestion=(
                                        f"Check {parent_matched.filepath} — "
                                        f"_valid_props may be stale. "
                                        f"{self.config.default_suggestion}"
                                    ),
                                )
                            )

        return self._apply_check_overrides(check_name, errors)

    def check_graph_objs_exports(self) -> List[ConsistencyError]:
        """Check 3: graph_objs and graph_objects exports should be consistent."""
        check_name = "exports-sync"
        errors: List[ConsistencyError] = []

        go_class = self.go_idx.graph_objs_class_exports
        gos_class = self.go_idx.graph_objects_class_exports
        go_mod = self.go_idx.graph_objs_module_exports
        gos_mod = self.go_idx.graph_objects_module_exports

        for cls in sorted(go_class - gos_class):
            errors.append(
                ConsistencyError(
                    check_name,
                    f"Class '{cls}' exported in graph_objs but missing from graph_objects",
                    suggestion=self.config.default_suggestion,
                )
            )

        for cls in sorted(gos_class - go_class):
            errors.append(
                ConsistencyError(
                    check_name,
                    f"Class '{cls}' exported in graph_objects but missing from graph_objs",
                    suggestion=self.config.default_suggestion,
                )
            )

        for mod in sorted(go_mod - gos_mod):
            errors.append(
                ConsistencyError(
                    check_name,
                    f"Module '{mod}' exported in graph_objs but missing from graph_objects",
                    suggestion=self.config.default_suggestion,
                )
            )

        for mod in sorted(gos_mod - go_mod):
            errors.append(
                ConsistencyError(
                    check_name,
                    f"Module '{mod}' exported in graph_objects but missing from graph_objs",
                    suggestion=self.config.default_suggestion,
                )
            )

        return self._apply_check_overrides(check_name, errors)

    def check_trace_class_coverage(self) -> List[ConsistencyError]:
        """Check 4: Every trace in schema should have a generated class file."""
        check_name = "trace-coverage"
        errors: List[ConsistencyError] = []
        exclude_files = self.config.class_rules.exclude_trace_files

        for trace_name, expected_props in sorted(self.schema_idx.trace_properties.items()):
            expected_file = os.path.join(self.go_idx.graph_objs_dir, f"_{trace_name}.py")
            if not os.path.isfile(expected_file):
                errors.append(
                    ConsistencyError(
                        check_name,
                        f"Trace '{trace_name}' in schema but no graph_objs/_{trace_name}.py",
                        suggestion=self.config.default_suggestion,
                    )
                )
                continue

            valid_props = self.go_idx.collect_valid_props_from_file(expected_file)
            if valid_props is None:
                errors.append(
                    ConsistencyError(
                        check_name,
                        f"Trace '{trace_name}' class file exists but has no _valid_props",
                        suggestion=f"Check {expected_file} — the class definition may be malformed",
                    )
                )
                continue

            missing_props = expected_props - valid_props
            for prop in sorted(missing_props):
                errors.append(
                    ConsistencyError(
                        check_name,
                        f"Trace '{trace_name}': schema property '{prop}' "
                        f"not in {trace_name.title().replace('_', '')}._valid_props",
                        suggestion=(
                            f"Property defined in schema but missing from generated class. "
                            f"{self.config.default_suggestion}"
                        ),
                    )
                )

            extra_props = valid_props - expected_props
            for prop in sorted(extra_props):
                errors.append(
                    ConsistencyError(
                        check_name,
                        f"Trace '{trace_name}': _valid_props has '{prop}' "
                        f"but not in schema properties",
                        severity="warn",
                        suggestion=(
                            f"Stale property in generated class. "
                            f"{self.config.default_suggestion}"
                        ),
                    )
                )

        for fname in sorted(os.listdir(self.go_idx.graph_objs_dir)):
            if fname.startswith("_") and fname.endswith(".py") and fname != "__init__.py":
                trace_name = fname[1:-3]
                if trace_name in exclude_files:
                    continue
                if trace_name not in self.schema_idx.trace_properties:
                    errors.append(
                        ConsistencyError(
                            check_name,
                            f"graph_objs/_{trace_name}.py exists but "
                            f"'{trace_name}' not in schema traces",
                            severity="warn",
                            suggestion=(
                                "Stale trace class file. If trace was removed from schema, "
                                "delete the file manually and re-run codegen"
                            ),
                        )
                    )

        return self._apply_check_overrides(check_name, errors)

    def check_layout_valid_props(self) -> List[ConsistencyError]:
        """Check 5: Layout._valid_props should cover all codegen layout properties."""
        check_name = "layout-coverage"
        errors: List[ConsistencyError] = []

        layout_file = os.path.join(self.go_idx.graph_objs_dir, "_layout.py")
        if not os.path.isfile(layout_file):
            errors.append(
                ConsistencyError(
                    check_name,
                    "graph_objs/_layout.py not found",
                    suggestion=self.config.default_suggestion,
                )
            )
            return self._apply_check_overrides(check_name, errors)

        layout_valid_props = self.go_idx.collect_valid_props_from_file(layout_file)
        if layout_valid_props is None:
            errors.append(
                ConsistencyError(
                    check_name,
                    "Could not parse _valid_props from graph_objs/_layout.py",
                    suggestion="Check _layout.py — the class definition may be malformed",
                )
            )
            return self._apply_check_overrides(check_name, errors)

        codegen_layout_props = self.schema_idx.layout_properties

        for prop in sorted(codegen_layout_props - layout_valid_props):
            errors.append(
                ConsistencyError(
                    check_name,
                    f"Codegen layout property '{prop}' not in Layout._valid_props",
                    suggestion=(
                        f"Property defined in schema but missing from generated Layout class. "
                        f"{self.config.default_suggestion}"
                    ),
                )
            )

        for prop in sorted(layout_valid_props - codegen_layout_props):
            errors.append(
                ConsistencyError(
                    check_name,
                    f"Layout._valid_props has '{prop}' but not in codegen layout properties",
                    severity="warn",
                    suggestion=(
                        f"Stale property in Layout class. "
                        f"{self.config.default_suggestion}"
                    ),
                )
            )

        return self._apply_check_overrides(check_name, errors)

    def check_doc_attribute_refs(self) -> List[ConsistencyError]:
        """Check 6: Doc examples go.Class.attribute should reference valid props."""
        check_name = "doc-refs"
        errors: List[ConsistencyError] = []

        doc_refs = self.doc_idx.references
        if not doc_refs:
            return self._apply_check_overrides(check_name, errors)

        for cls_name, attr_refs in sorted(doc_refs.items()):
            matched = self.go_idx.find_top_level_class(cls_name)

            if matched is None:
                errors.append(
                    ConsistencyError(
                        check_name,
                        f"Doc references go.{cls_name} but class not found in graph_objects",
                        suggestion=(
                            "Check that the class is properly exported. "
                            "If renamed, update doc examples accordingly"
                        ),
                    )
                )
                continue

            valid_props = matched.valid_props
            for attr in sorted(attr_refs):
                if self.doc_idx.is_ignored_attribute(attr):
                    continue
                if attr not in valid_props:
                    errors.append(
                        ConsistencyError(
                            check_name,
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

        return self._apply_check_overrides(check_name, errors)

    # ----- Runner -----

    def get_check_runners(self) -> List[Tuple[str, Callable[[], List[ConsistencyError]]]]:
        """Return ordered list of (display_name, check_fn) tuples."""
        return [
            ("1. Codegen paths vs _validators.json", self.check_codegen_vs_validators),
            ("2. Validators vs graph_objects _valid_props", self.check_validators_vs_graph_objects),
            ("3. Export sync (graph_objs <-> graph_objects)", self.check_graph_objs_exports),
            ("4. Trace class coverage", self.check_trace_class_coverage),
            ("5. Layout property coverage", self.check_layout_valid_props),
            ("6. Doc attribute references", self.check_doc_attribute_refs),
        ]

    def run_all_checks(
        self, verbose: bool = False
    ) -> Tuple[int, int, List[ConsistencyError]]:
        """Run all enabled checks and return (error_count, warn_count, all_errors).

        Maintains backward compatibility with the old run_all_checks() API.
        """
        all_errors: List[ConsistencyError] = []

        if verbose:
            print("=" * 70)
            print("Schema Artifact Consistency Check")
            print("=" * 70)

        for check_name, check_fn in self.get_check_runners():
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


# =========================================================================
# BACKWARD-COMPATIBLE CLI ENTRY POINT
# =========================================================================


def run_all_checks(
    verbose: bool = False, config: Optional[ValidationConfig] = None
) -> Tuple[int, int, List[ConsistencyError]]:
    """Backward-compatible wrapper: build indices and run all checks.

    This matches the signature of the previous module-level run_all_checks()
    so that callers in commands.py and codegen/__init__.py keep working.
    """
    checker = ConsistencyCheck(config=config or DEFAULT_CONFIG)
    checker.build_indices()
    return checker.run_all_checks(verbose=verbose)


if __name__ == "__main__":
    error_count, _, _ = run_all_checks(verbose=True)
    sys.exit(1 if error_count > 0 else 0)

"""
Packaging manifest validator for plotly.py

Validates that all required artifacts are present and consistent BEFORE
building sdist/wheel packages. Catches missing generated files, stale
resources, inconsistent versions, and incomplete type hints distribution.

Checks performed:
  1. Core package structure: __init__.py files in plotly, _plotly_utils, subpackages
  2. Schema data: codegen/resources/plot-schema.json exists and is non-empty
  3. Validators: plotly/validators/_validators.json exists, non-empty, well-formed
  4. Graph objects: __init__.py exports, key trace/layout files present
  5. Plotly.js resources: plotly.min.js, widgetbundle.js, templates, datasets
  6. JupyterLab extension: labextension static assets, install.json
  7. Type hints: py.typed marker file, key .pyi stubs (if used)
  8. Version consistency: pyproject.toml, labextension, plotlyjs_version.py
  9. Build inclusion: verify hatch include/exclude covers all critical paths
 10. Resource freshness: warn if plotly.min.js is 0-byte or extremely old

Exit code is non-zero if any CRITICAL checks fail.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"

PLOTLY_PKG = PROJECT_ROOT / "plotly"
PLOTLY_UTILS = PROJECT_ROOT / "_plotly_utils"
VALIDATORS_DIR = PLOTLY_PKG / "validators"
GRAPH_OBJS_DIR = PLOTLY_PKG / "graph_objs"
GRAPH_OBJECTS_DIR = PLOTLY_PKG / "graph_objects"
PACKAGE_DATA_DIR = PLOTLY_PKG / "package_data"
LABEXTENSION_DIR = PLOTLY_PKG / "labextension"
SCHEMA_DIR = PROJECT_ROOT / "codegen" / "resources"
DOC_PYTHON_DIR = PROJECT_ROOT / "doc" / "python"
JS_DIR = PROJECT_ROOT / "js"


@dataclass
class CheckResult:
    name: str
    severity: str
    message: str
    detail: str = ""

    def is_error(self) -> bool:
        return self.severity == "ERROR"

    def is_warn(self) -> bool:
        return self.severity == "WARN"

    def __str__(self) -> str:
        base = f"[{self.severity:5s}] [{self.name}] {self.message}"
        if self.detail:
            base += f"\n         └─ {self.detail}"
        return base


def _err(name: str, msg: str, detail: str = "") -> CheckResult:
    return CheckResult(name, "ERROR", msg, detail)


def _warn(name: str, msg: str, detail: str = "") -> CheckResult:
    return CheckResult(name, "WARN", msg, detail)


def _ok(name: str, msg: str) -> CheckResult:
    return CheckResult(name, "OK", msg)


def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _file_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def _file_hash(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ---------------------------------------------------------------------------
# Check 1: Core package structure
# ---------------------------------------------------------------------------

def check_core_package_structure() -> list[CheckResult]:
    results: list[CheckResult] = []

    required_inits = [
        PLOTLY_PKG / "__init__.py",
        PLOTLY_UTILS / "__init__.py",
        PLOTLY_PKG / "io" / "__init__.py",
        PLOTLY_PKG / "offline" / "__init__.py",
        PLOTLY_PKG / "express" / "__init__.py",
        PLOTLY_PKG / "colors" / "__init__.py",
        PLOTLY_PKG / "figure_factory" / "__init__.py",
        PLOTLY_PKG / "api" / "__init__.py",
        PLOTLY_PKG / "data" / "__init__.py",
        VALIDATORS_DIR.parent / "__init__.py",  # plotly/__init__.py already checked
        GRAPH_OBJS_DIR / "__init__.py",
        GRAPH_OBJECTS_DIR / "__init__.py",
        PLOTLY_UTILS / "colors" / "__init__.py",
    ]

    missing = [str(p.relative_to(PROJECT_ROOT)) for p in required_inits if not p.is_file()]
    if missing:
        results.append(_err(
            "core-structure",
            f"Missing {len(missing)} required __init__.py files",
            ", ".join(missing),
        ))
    else:
        results.append(_ok("core-structure", f"All {len(required_inits)} core __init__.py files present"))

    plotly_init_size = (PLOTLY_PKG / "__init__.py").stat().st_size
    if plotly_init_size < 1000:
        results.append(_warn(
            "core-structure",
            f"plotly/__init__.py is suspiciously small ({plotly_init_size} bytes)",
        ))

    return results


# ---------------------------------------------------------------------------
# Check 2: Schema data
# ---------------------------------------------------------------------------

def check_schema() -> list[CheckResult]:
    results: list[CheckResult] = []
    schema_path = SCHEMA_DIR / "plot-schema.json"

    if not schema_path.is_file():
        results.append(_err("schema", "plot-schema.json not found", str(schema_path)))
        return results

    size = schema_path.stat().st_size
    if size == 0:
        results.append(_err("schema", "plot-schema.json is 0 bytes"))
        return results
    if size < 500_000:
        results.append(_warn(
            "schema",
            f"plot-schema.json is smaller than expected ({size/1024:.0f} KB)",
            "Schema was not properly generated or downloaded",
        ))

    try:
        schema = _read_json(schema_path)
    except json.JSONDecodeError as e:
        results.append(_err("schema", f"plot-schema.json is not valid JSON: {e}"))
        return results

    required_keys = ["traces", "layout"]
    missing = [k for k in required_keys if k not in schema]
    if missing:
        results.append(_err(
            "schema",
            f"plot-schema.json missing top-level keys: {missing}",
        ))
    else:
        n_traces = len(schema["traces"])
        results.append(_ok(
            "schema",
            f"plot-schema.json valid, {n_traces} traces, {size/1024:.0f} KB",
        ))

    return results


# ---------------------------------------------------------------------------
# Check 3: Validators
# ---------------------------------------------------------------------------

def check_validators() -> list[CheckResult]:
    results: list[CheckResult] = []
    validators_path = VALIDATORS_DIR / "_validators.json"

    if not validators_path.is_file():
        results.append(_err("validators", "_validators.json not found", str(validators_path)))
        return results

    size = validators_path.stat().st_size
    if size == 0:
        results.append(_err("validators", "_validators.json is 0 bytes"))
        return results

    try:
        validators = _read_json(validators_path)
    except json.JSONDecodeError as e:
        results.append(_err("validators", f"_validators.json is not valid JSON: {e}"))
        return results

    n_keys = len(validators)
    if n_keys < 100:
        results.append(_warn(
            "validators",
            f"_validators.json has only {n_keys} entries (expected thousands)",
        ))
    else:
        results.append(_ok(
            "validators",
            f"_validators.json valid, {n_keys} validator entries, {size/1024:.0f} KB",
        ))

    compound_count = sum(
        1 for v in validators.values()
        if isinstance(v, dict) and v.get("superclass") == "CompoundValidator"
    )
    if compound_count < 10:
        results.append(_warn(
            "validators",
            f"Only {compound_count} CompoundValidator entries found",
            "Codegen may not have run properly",
        ))
    else:
        results.append(_ok("validators", f"{compound_count} CompoundValidator entries present"))

    return results


# ---------------------------------------------------------------------------
# Check 4: Graph objects
# ---------------------------------------------------------------------------

REQUIRED_TRACE_FILES = [
    "_scatter.py", "_bar.py", "_box.py", "_pie.py", "_heatmap.py",
    "_histogram.py", "_contour.py", "_surface.py", "_layout.py",
    "_figure.py", "_frame.py",
]


def _collect_init_exports(init_path: Path) -> tuple[set[str], set[str]]:
    source = _read_text(init_path)
    class_exports: set[str] = set()
    module_exports: set[str] = set()

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

    class_pat = re.compile(r"from\s+\._(\w+)\s+import\s+(\w+)")
    module_pat = re.compile(r"from\s+\.(\w+)\s+import\s+\1")
    for m in class_pat.finditer(source):
        class_exports.add(m.group(2))
    for m in module_pat.finditer(source):
        module_exports.add(m.group(1))

    rel_class_pat = re.compile(r'"\.\.graph_objs\.([A-Z]\w*)"')
    rel_module_pat = re.compile(r'"\.\.graph_objs\.([a-z]\w*)"')
    for m in rel_class_pat.finditer(source):
        class_exports.add(m.group(1))
    for m in rel_module_pat.finditer(source):
        module_exports.add(m.group(1))

    type_check_class_pat = re.compile(r"from\s+\.\.graph_objs\s+import\s+([A-Z]\w+)")
    type_check_module_pat = re.compile(r"from\s+\.\.graph_objs\s+import\s+([a-z]\w+)")
    for m in type_check_class_pat.finditer(source):
        class_exports.add(m.group(1))
    for m in type_check_module_pat.finditer(source):
        module_exports.add(m.group(1))

    return class_exports, module_exports


def check_graph_objects() -> list[CheckResult]:
    results: list[CheckResult] = []

    go_init = GRAPH_OBJS_DIR / "__init__.py"
    gos_init = GRAPH_OBJECTS_DIR / "__init__.py"

    for fname in REQUIRED_TRACE_FILES:
        fpath = GRAPH_OBJS_DIR / fname
        if not fpath.is_file():
            results.append(_err(
                "graph-objects",
                f"Missing required graph_objs file: {fname}",
            ))

    go_classes, go_modules = _collect_init_exports(go_init)
    gos_classes, gos_modules = _collect_init_exports(gos_init)

    if len(go_classes) < 30:
        results.append(_warn(
            "graph-objects",
            f"graph_objs/__init__.py exports only {len(go_classes)} classes (expected ~50+)",
        ))
    else:
        results.append(_ok(
            "graph-objects",
            f"graph_objs/__init__.py exports {len(go_classes)} classes, {len(go_modules)} modules",
        ))

    missing_classes = go_classes - gos_classes
    if missing_classes:
        results.append(_err(
            "graph-objects",
            f"{len(missing_classes)} classes in graph_objs but missing from graph_objects",
            ", ".join(sorted(missing_classes)[:10]),
        ))
    else:
        results.append(_ok("graph-objects", "graph_objs ↔ graph_objects class exports in sync"))

    missing_modules = go_modules - gos_modules
    if missing_modules:
        results.append(_err(
            "graph-objects",
            f"{len(missing_modules)} modules in graph_objs but missing from graph_objects",
            ", ".join(sorted(missing_modules)[:10]),
        ))
    else:
        results.append(_ok("graph-objects", "graph_objs ↔ graph_objects module exports in sync"))

    subdirs = [p for p in GRAPH_OBJS_DIR.iterdir() if p.is_dir() and p.name != "__pycache__"]
    if len(subdirs) < 10:
        results.append(_warn(
            "graph-objects",
            f"Only {len(subdirs)} subdirectories in graph_objs (expected ~50+)",
        ))
    else:
        results.append(_ok(
            "graph-objects",
            f"{len(subdirs)} hierarchy subdirectories present in graph_objs",
        ))

    return results


# ---------------------------------------------------------------------------
# Check 5: Plotly.js resources
# ---------------------------------------------------------------------------

EXPECTED_TEMPLATES = [
    "ggplot2.json", "gridon.json", "plotly.json", "plotly_dark.json",
    "plotly_white.json", "presentation.json", "seaborn.json",
    "simple_white.json", "xgridoff.json", "ygridoff.json",
]

EXPECTED_DATASETS = [
    "carshare.csv.gz", "election.csv.gz", "election.geojson.gz",
    "experiment.csv.gz", "gapminder.csv.gz", "iris.csv.gz",
    "medals.csv.gz", "stocks.csv.gz", "tips.csv.gz", "wind.csv.gz",
]


def check_plotlyjs_resources() -> list[CheckResult]:
    results: list[CheckResult] = []

    plotly_min_js = PACKAGE_DATA_DIR / "plotly.min.js"
    if not plotly_min_js.is_file():
        results.append(_err(
            "plotlyjs",
            "plotly.min.js not found — plotly.js bundle is required",
            str(plotly_min_js.relative_to(PROJECT_ROOT)),
        ))
    else:
        size = plotly_min_js.stat().st_size
        if size == 0:
            results.append(_err("plotlyjs", "plotly.min.js is 0 bytes"))
        elif size < 1_000_000:
            results.append(_warn(
                "plotlyjs",
                f"plotly.min.js is smaller than expected ({size/1024:.0f} KB)",
                "Bundle may be a stub or failed to download",
            ))
        else:
            results.append(_ok(
                "plotlyjs",
                f"plotly.min.js present, {size/1024/1024:.2f} MB, sha256:{_file_hash(plotly_min_js)}",
            ))

    widgetbundle = PACKAGE_DATA_DIR / "widgetbundle.js"
    if not widgetbundle.is_file():
        results.append(_warn(
            "plotlyjs",
            "widgetbundle.js not found — FigureWidget will not work in Jupyter",
            "Run `python commands.py codegen` or `npm run build` in js/",
        ))
    elif widgetbundle.stat().st_size == 0:
        results.append(_warn("plotlyjs", "widgetbundle.js is 0 bytes"))
    else:
        results.append(_ok(
            "plotlyjs",
            f"widgetbundle.js present, {widgetbundle.stat().st_size/1024:.0f} KB",
        ))

    templates_dir = PACKAGE_DATA_DIR / "templates"
    if not templates_dir.is_dir():
        results.append(_err("plotlyjs", "templates/ directory missing"))
    else:
        actual_templates = set(p.name for p in templates_dir.glob("*.json"))
        missing = [t for t in EXPECTED_TEMPLATES if t not in actual_templates]
        extra = [t for t in actual_templates if t not in EXPECTED_TEMPLATES]
        if missing:
            results.append(_err(
                "plotlyjs",
                f"Missing {len(missing)} expected template files",
                ", ".join(missing),
            ))
        if extra:
            results.append(_warn(
                "plotlyjs",
                f"Found {len(extra)} unexpected template files",
                ", ".join(extra),
            ))
        if not missing:
            results.append(_ok(
                "plotlyjs",
                f"All {len(EXPECTED_TEMPLATES)} template JSON files present",
            ))

    datasets_dir = PACKAGE_DATA_DIR / "datasets"
    if not datasets_dir.is_dir():
        results.append(_warn("plotlyjs", "datasets/ directory missing — px.data will fail"))
    else:
        actual_datasets = set(p.name for p in datasets_dir.iterdir() if p.is_file())
        missing = [d for d in EXPECTED_DATASETS if d not in actual_datasets]
        if missing:
            results.append(_warn(
                "plotlyjs",
                f"Missing {len(missing)} expected dataset files",
                ", ".join(missing),
            ))
        else:
            results.append(_ok(
                "plotlyjs",
                f"All {len(EXPECTED_DATASETS)} built-in datasets present",
            ))

    return results


# ---------------------------------------------------------------------------
# Check 6: JupyterLab extension
# ---------------------------------------------------------------------------

def check_labextension() -> list[CheckResult]:
    results: list[CheckResult] = []

    if not LABEXTENSION_DIR.is_dir():
        results.append(_err(
            "labextension",
            "plotly/labextension/ directory missing",
            "Run `npm run build` in js/ to build the extension",
        ))
        return results

    lab_pkg = LABEXTENSION_DIR / "package.json"
    if not lab_pkg.is_file():
        results.append(_err("labextension", "labextension/package.json missing"))
    else:
        try:
            pkg = _read_json(lab_pkg)
            jl = pkg.get("jupyterlab", {})
            build = jl.get("_build", {})
            load = build.get("load", "")
            if not load:
                results.append(_warn(
                    "labextension",
                    "jupyterlab._build.load missing in package.json",
                    "Extension may not load correctly",
                ))
            else:
                load_path = LABEXTENSION_DIR / load
                if not load_path.is_file():
                    results.append(_err(
                        "labextension",
                        f"_build.load target not found: {load}",
                        "Labextension build is stale — rerun npm build",
                    ))
                else:
                    results.append(_ok(
                        "labextension",
                        f"Labextension package.json valid, load={load}",
                    ))
        except json.JSONDecodeError as e:
            results.append(_err("labextension", f"package.json invalid: {e}"))

    static_dir = LABEXTENSION_DIR / "static"
    if not static_dir.is_dir():
        results.append(_err("labextension", "labextension/static/ directory missing"))
    else:
        js_files = list(static_dir.glob("*.js"))
        if not js_files:
            results.append(_err(
                "labextension",
                "No .js files in labextension/static/",
                "Extension build did not produce static assets",
            ))
        else:
            remote = [f for f in js_files if f.name.startswith("remoteEntry")]
            style = static_dir / "style.js"
            if not remote:
                results.append(_warn(
                    "labextension",
                    "No remoteEntry.*.js file in static/",
                ))
            if not style.is_file():
                results.append(_warn("labextension", "style.js missing from static/"))

            total_js = sum(f.stat().st_size for f in js_files)
            results.append(_ok(
                "labextension",
                f"{len(js_files)} static JS files, {total_js/1024:.0f} KB total",
            ))

    install_json = JS_DIR / "install.json"
    if not install_json.is_file():
        results.append(_err("labextension", "js/install.json missing for Jupyter extension"))
    else:
        try:
            inst = _read_json(install_json)
            if inst.get("packageName") != "plotly":
                results.append(_warn(
                    "labextension",
                    f"Unexpected packageName in install.json: {inst.get('packageName')}",
                ))
            else:
                results.append(_ok("labextension", "js/install.json present and valid"))
        except json.JSONDecodeError as e:
            results.append(_err("labextension", f"install.json invalid: {e}"))

    return results


# ---------------------------------------------------------------------------
# Check 7: Type hints (py.typed + .pyi stubs)
# ---------------------------------------------------------------------------

def check_type_hints() -> list[CheckResult]:
    results: list[CheckResult] = []

    py_typed = PLOTLY_PKG / "py.typed"
    if not py_typed.is_file():
        results.append(_err(
            "type-hints",
            "plotly/py.typed missing — PEP 561 type hint marker required",
            "Plotly has inline type annotations and must ship py.typed so type "
            "checkers can discover them. Create empty plotly/py.typed to enable "
            "PEP 561 support. Hatch's /plotly* include glob will pick it up.",
        ))
    else:
        if py_typed.stat().st_size > 100:
            results.append(_warn(
                "type-hints",
                "py.typed should normally be empty (or minimal marker content)",
            ))
        results.append(_ok("type-hints", "plotly/py.typed marker present (PEP 561)"))

    utils_typed = PLOTLY_UTILS / "py.typed"
    if not utils_typed.is_file():
        results.append(_err(
            "type-hints",
            "_plotly_utils/py.typed missing",
            "_plotly_utils is a separate package namespace. Since _plotly_utils "
            "has inline type annotations, it also needs py.typed for PEP 561 "
            "compliance. Hatch's /_plotly* include glob will pick it up.",
        ))
    else:
        results.append(_ok("type-hints", "_plotly_utils/py.typed marker present"))

    pyi_files = list(PLOTLY_PKG.rglob("*.pyi"))
    if pyi_files:
        results.append(_ok(
            "type-hints",
            f"Found {len(pyi_files)} .pyi stub files in plotly/",
        ))
    else:
        results.append(_warn(
            "type-hints",
            "No .pyi stub files — using inline type annotations only",
            "All public APIs should have inline type hints if no stub files exist. "
            "hatch's /plotly* glob will include any .pyi files under plotly/.",
        ))

    return results


# ---------------------------------------------------------------------------
# Check 8: Version consistency
# ---------------------------------------------------------------------------

def _extract_pyproject_version() -> str:
    content = _read_text(PYPROJECT_TOML)
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return m.group(1) if m else ""


def check_version_consistency() -> list[CheckResult]:
    results: list[CheckResult] = []

    pyproject_ver = _extract_pyproject_version()
    if not pyproject_ver:
        results.append(_err("version", "Could not extract version from pyproject.toml"))
        return results
    results.append(_ok("version", f"pyproject.toml version: {pyproject_ver}"))

    lab_pkg_path = LABEXTENSION_DIR / "package.json"
    if lab_pkg_path.is_file():
        try:
            lab_ver = _read_json(lab_pkg_path).get("version", "")
            if lab_ver != pyproject_ver:
                results.append(_err(
                    "version",
                    f"Labextension version mismatch",
                    f"package.json={lab_ver} vs pyproject.toml={pyproject_ver}",
                ))
            else:
                results.append(_ok("version", "labextension/package.json version matches pyproject.toml"))
        except Exception:
            pass

    js_pkg_path = JS_DIR / "package.json"
    if js_pkg_path.is_file():
        try:
            js_ver = _read_json(js_pkg_path).get("version", "")
            if js_ver and js_ver != pyproject_ver:
                results.append(_err(
                    "version",
                    f"js/package.json version mismatch",
                    f"js/package.json={js_ver} vs pyproject.toml={pyproject_ver}",
                ))
            elif js_ver:
                results.append(_ok("version", "js/package.json version matches pyproject.toml"))
        except Exception:
            pass

    pjv_path = PLOTLY_PKG / "offline" / "_plotlyjs_version.py"
    if pjv_path.is_file():
        content = _read_text(pjv_path)
        m = re.search(r'__plotlyjs_version__\s*=\s*"([^"]+)"', content)
        if m:
            plotlyjs_ver = m.group(1)
            if not plotlyjs_ver:
                results.append(_warn(
                    "version",
                    "_plotlyjs_version.py has empty version string",
                ))
            else:
                results.append(_ok(
                    "version",
                    f"_plotlyjs_version.py declares plotly.js: {plotlyjs_ver}",
                ))
        else:
            results.append(_warn("version", "Could not parse _plotlyjs_version.py"))
    else:
        results.append(_err("version", "_plotlyjs_version.py missing"))

    citation_path = PROJECT_ROOT / "CITATION.cff"
    if citation_path.is_file():
        content = _read_text(citation_path)
        m = re.search(r'^\s*version\s*:\s*(\S+)', content, re.MULTILINE)
        if m and m.group(1) != pyproject_ver:
            results.append(_warn(
                "version",
                f"CITATION.cff version {m.group(1)} != pyproject.toml {pyproject_ver}",
            ))

    return results


# ---------------------------------------------------------------------------
# Check 9: Hatch build inclusion coverage
# ---------------------------------------------------------------------------

def _parse_hatch_config() -> tuple[list[str], list[str]]:
    content = _read_text(PYPROJECT_TOML)
    includes: list[str] = []
    excludes: list[str] = []

    in_include = False
    in_exclude = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("include") and "=" in stripped:
            in_include = True
            in_exclude = False
            rest = stripped.split("=", 1)[1].strip()
            if rest.startswith("["):
                inner = rest.strip("[]")
                for item in re.findall(r'"([^"]+)"', inner):
                    includes.append(item)
                if not rest.endswith("]"):
                    continue
                in_include = False
            continue
        if stripped.startswith("exclude") and "=" in stripped and not in_include:
            in_exclude = True
            in_include = False
            rest = stripped.split("=", 1)[1].strip()
            if rest.startswith("["):
                inner = rest.strip("[]")
                for item in re.findall(r'"([^"]+)"', inner):
                    excludes.append(item)
                in_exclude = False
            continue
        if in_include:
            for item in re.findall(r'"([^"]+)"', stripped):
                includes.append(item)
            if stripped.endswith("]"):
                in_include = False
        if in_exclude:
            for item in re.findall(r'"([^"]+)"', stripped):
                excludes.append(item)
            if stripped.endswith("]"):
                in_exclude = False

    return includes, excludes


def check_hatch_inclusion() -> list[CheckResult]:
    results: list[CheckResult] = []

    includes, excludes = _parse_hatch_config()

    if not includes:
        results.append(_warn(
            "hatch-config",
            "No [tool.hatch.build] include patterns found — using default",
        ))
    else:
        results.append(_ok(
            "hatch-config",
            f"Hatch include patterns: {', '.join(includes)}",
        ))

    critical_paths = {
        "/plotly*": PLOTLY_PKG,
        "/_plotly*": PLOTLY_UTILS,
        "js/install.json": JS_DIR / "install.json",
    }
    for pattern, path in critical_paths.items():
        if pattern in includes:
            continue
        if pattern.startswith("/"):
            base = pattern.lstrip("/*").split("*")[0].rstrip("*")
            matched = any(
                inc.lstrip("/*").startswith(base.rstrip("/*")) or
                base.startswith(inc.lstrip("/*").rstrip("/*"))
                for inc in includes if inc.startswith("/")
            )
            if not matched:
                results.append(_warn(
                    "hatch-config",
                    f"Critical path '{pattern}' not explicitly in hatch includes",
                ))
        else:
            if pattern not in includes:
                results.append(_warn(
                    "hatch-config",
                    f"Critical file '{pattern}' not in hatch includes",
                ))

    if "js" in excludes:
        results.append(_ok(
            "hatch-config",
            "js/ correctly excluded from wheel (top-level namespace collision)",
        ))

    shared_data_count = _read_text(PYPROJECT_TOML).count("[tool.hatch.build.targets.wheel.shared-data]")
    if shared_data_count:
        results.append(_ok("hatch-config", "Wheel shared-data section present (labextension install)"))

    if "/plotly*" in includes:
        results.append(_ok(
            "hatch-config",
            "Glob '/plotly*' will include plotly/py.typed and plotly/**/*.pyi (if they exist)",
        ))
    if "/_plotly*" in includes:
        results.append(_ok(
            "hatch-config",
            "Glob '/_plotly*' will include _plotly_utils/py.typed and _plotly_utils/**/*.pyi (if they exist)",
        ))

    pyproject_content = _read_text(PYPROJECT_TOML)
    if "[tool.hatch.build.targets.wheel]" in pyproject_content and "packages" not in pyproject_content:
        results.append(_ok(
            "hatch-config",
            "Using default packages discovery — plotly/ and _plotly_utils/ will be recognized",
        ))

    return results


# ---------------------------------------------------------------------------
# Check 10: Resource freshness
# ---------------------------------------------------------------------------

def check_resource_freshness() -> list[CheckResult]:
    results: list[CheckResult] = []

    plotly_min_js = PACKAGE_DATA_DIR / "plotly.min.js"
    validators_json = VALIDATORS_DIR / "_validators.json"
    schema_json = SCHEMA_DIR / "plot-schema.json"

    if plotly_min_js.is_file() and validators_json.is_file():
        mtime_delta = validators_json.stat().st_mtime - plotly_min_js.stat().st_mtime
        if abs(mtime_delta) > 30 * 24 * 3600:
            age_days = abs(mtime_delta) / 86400
            older = "validators" if mtime_delta > 0 else "plotly.min.js"
            results.append(_warn(
                "freshness",
                f"{older} is ~{age_days:.0f} days newer than the other",
                "Resources may be out of sync — rerun codegen or update bundle",
            ))

    for p in [validators_json, schema_json]:
        if p.is_file():
            age_days = (datetime.now().timestamp() - p.stat().st_mtime) / 86400
            if age_days > 180:
                results.append(_warn(
                    "freshness",
                    f"{p.relative_to(PROJECT_ROOT)} is {age_days:.0f} days old",
                    "Consider regenerating from latest plotly.js",
                ))

    return results


# ---------------------------------------------------------------------------
# Check 11: Doc examples
# ---------------------------------------------------------------------------

def check_doc_examples() -> list[CheckResult]:
    results: list[CheckResult] = []

    if not DOC_PYTHON_DIR.is_dir():
        results.append(_warn(
            "doc-examples",
            "doc/python/ directory missing — doc examples not available for packaging",
        ))
        return results

    md_files = list(DOC_PYTHON_DIR.glob("*.md"))
    if len(md_files) < 50:
        results.append(_warn(
            "doc-examples",
            f"Only {len(md_files)} .md files in doc/python/ (expected ~150+)",
            "Doc examples may be incomplete",
        ))
    else:
        counter: Counter = Counter()
        for md in md_files:
            try:
                content = _read_text(md)
                if "import plotly" in content:
                    counter["import_plotly"] += 1
                if "plotly.express" in content or "px." in content:
                    counter["uses_px"] += 1
                if "go.Figure" in content or "graph_objects" in content:
                    counter["uses_go"] += 1
            except Exception:
                pass
        results.append(_ok(
            "doc-examples",
            f"{len(md_files)} doc .md files: {counter.get('import_plotly', 0)} with imports, "
            f"{counter.get('uses_px', 0)} use px, {counter.get('uses_go', 0)} use go",
        ))

    return results


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    ("Core package structure", check_core_package_structure),
    ("Schema data (plot-schema.json)", check_schema),
    ("Validators (_validators.json)", check_validators),
    ("Graph objects completeness", check_graph_objects),
    ("Plotly.js resources", check_plotlyjs_resources),
    ("JupyterLab extension assets", check_labextension),
    ("Type hints (PEP 561 py.typed)", check_type_hints),
    ("Version consistency", check_version_consistency),
    ("Hatch build inclusion", check_hatch_inclusion),
    ("Resource freshness", check_resource_freshness),
    ("Doc examples presence", check_doc_examples),
]


def run_all_checks(verbose: bool = True) -> int:
    all_results: list[CheckResult] = []

    if verbose:
        print("=" * 78)
        print("  Plotly.py Packaging Manifest Validator")
        print(f"  Project root: {PROJECT_ROOT}")
        print(f"  Run at:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 78)

    for check_name, check_fn in ALL_CHECKS:
        if verbose:
            print(f"\n▶ {check_name}")
        try:
            results = check_fn()
        except Exception as e:
            import traceback
            traceback.print_exc()
            results = [_err(check_name.split(" ")[0].lower(), f"Check crashed: {e}")]

        all_results.extend(results)
        if verbose:
            for r in results:
                prefix = {"OK": "  ✓ ", "WARN": "  ⚠ ", "ERROR": "  ✗ "}.get(r.severity, "  ? ")
                lines = str(r).splitlines()
                print(f"{prefix}{lines[0]}")
                for line in lines[1:]:
                    print(f"    {line}")

    if verbose:
        print("\n" + "=" * 78)

    errors = [r for r in all_results if r.is_error()]
    warnings = [r for r in all_results if r.is_warn()]
    oks = [r for r in all_results if r.severity == "OK"]

    if verbose:
        print(f"  Summary: {len(errors)} ERROR  |  {len(warnings)} WARN  |  {len(oks)} OK")
        print("=" * 78)

    if errors:
        if verbose:
            print("\n❌ BUILD BLOCKED — the following errors must be resolved:")
            for e in errors:
                prefix = "   - "
                lines = str(e).splitlines()
                print(f"{prefix}{lines[0]}")
                for line in lines[1:]:
                    print(f"     {line}")
        return 1

    if warnings and verbose:
        print("\n⚠️  Warnings (non-blocking, review recommended):")
        for w in warnings:
            prefix = "   - "
            lines = str(w).splitlines()
            print(f"{prefix}{lines[0]}")
            for line in lines[1:]:
                print(f"     {line}")

    if verbose:
        print("\n✅ Packaging manifest validation PASSED — safe to build sdist/wheel.")
    return 0


def main() -> int:
    import argparse

    global ALL_CHECKS

    parser = argparse.ArgumentParser(
        description="Validate plotly.py packaging manifest before building sdist/wheel"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress per-check output, only print final summary and exit code",
    )
    check_choices = [name.split(" ")[0].lower().replace("(", "").replace(")", "") for name, _ in ALL_CHECKS]
    parser.add_argument(
        "--check",
        choices=check_choices,
        help="Run only a single check by name prefix",
    )
    args = parser.parse_args()

    if args.check:
        for idx, (name, fn) in enumerate(ALL_CHECKS):
            prefix = name.split(" ")[0].lower().replace("(", "").replace(")", "")
            if prefix == args.check:
                ALL_CHECKS = [(name, fn)]
                break

    return run_all_checks(verbose=not args.quiet)


if __name__ == "__main__":
    sys.exit(main())

"""
Post-build artifact validator for plotly.py

Opens the built .whl and .tar.gz files in the dist/ directory and verifies
that all critical artifacts are actually present in the final packages.
This catches issues where the source tree has files but hatch's
include/exclude rules accidentally omit them from the distribution.

Works by extracting each archive to a temp dir and checking for the
presence of expected paths. Also verifies wheel metadata (METADATA,
WHEEL, RECORD) and sdist PKG-INFO.

Usage:
    python codegen/validate_dist_artifacts.py                # auto-detect dist/
    python codegen/validate_dist_artifacts.py dist/          # specify dist dir
    python codegen/validate_dist_artifacts.py dist/plotly-6.8.0-py3-none-any.whl
    python codegen/validate_dist_artifacts.py dist/plotly-6.8.0.tar.gz
    python codegen/validate_dist_artifacts.py -q             # quiet mode
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from tarfile import TarFile

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


@dataclass
class ExtractedPackage:
    archive_path: Path
    pkg_type: str  # "wheel" or "sdist"
    extract_dir: Path
    file_list: list[str] = field(default_factory=list)

    def contains(self, pattern: str) -> bool:
        for f in self.file_list:
            if fnmatch.fnmatch(f, pattern):
                return True
        return False

    def contains_any(self, patterns: list[str]) -> list[str]:
        found = []
        for p in patterns:
            if self.contains(p):
                found.append(p)
        return found

    def find_all(self, pattern: str) -> list[str]:
        return [f for f in self.file_list if fnmatch.fnmatch(f, pattern)]


def _extract_wheel(whl_path: Path, tmpdir: Path) -> ExtractedPackage:
    extract_dir = tmpdir / "wheel"
    extract_dir.mkdir()

    file_list: list[str] = []
    with zipfile.ZipFile(whl_path, "r") as zf:
        zf.extractall(extract_dir)
        for info in zf.infolist():
            if not info.is_dir():
                file_list.append(info.filename)

    return ExtractedPackage(
        archive_path=whl_path,
        pkg_type="wheel",
        extract_dir=extract_dir,
        file_list=sorted(file_list),
    )


def _extract_sdist(tar_path: Path, tmpdir: Path) -> ExtractedPackage:
    extract_dir = tmpdir / "sdist"
    extract_dir.mkdir()

    file_list: list[str] = []
    with TarFile.open(tar_path, "r:*") as tf:
        tf.extractall(extract_dir)
        for member in tf.getmembers():
            if member.isfile():
                file_list.append(member.name)

    return ExtractedPackage(
        archive_path=tar_path,
        pkg_type="sdist",
        extract_dir=extract_dir,
        file_list=sorted(file_list),
    )


def _find_archives(dist_path: Path) -> list[Path]:
    if dist_path.is_file():
        return [dist_path]
    if dist_path.is_dir():
        archives = []
        for ext in ("*.whl", "*.tar.gz"):
            archives.extend(sorted(dist_path.glob(ext)))
        return archives
    return []


# ---------------------------------------------------------------------------
# Expected file patterns
# ---------------------------------------------------------------------------

WHEEL_REQUIRED_FILES = [
    ("plotly/__init__.py", "Top-level plotly package __init__"),
    ("_plotly_utils/__init__.py", "_plotly_utils package __init__"),
    ("plotly/validators/_validators.json", "Validators JSON data"),
    ("plotly/graph_objs/__init__.py", "graph_objs __init__ exports"),
    ("plotly/graph_objects/__init__.py", "graph_objects __init__ exports"),
    ("plotly/package_data/plotly.min.js", "plotly.js bundle"),
    ("plotly/package_data/widgetbundle.js", "FigureWidget bundle"),
    ("plotly/package_data/templates/plotly.json", "Plotly template"),
    ("plotly/package_data/templates/ggplot2.json", "ggplot2 template"),
    ("plotly/package_data/datasets/gapminder.csv.gz", "Gapminder dataset"),
    ("plotly/package_data/datasets/iris.csv.gz", "Iris dataset"),
    ("plotly/io/__init__.py", "plotly.io package"),
    ("plotly/offline/__init__.py", "plotly.offline package"),
    ("plotly/express/__init__.py", "plotly.express package"),
    ("plotly/figure_factory/__init__.py", "plotly.figure_factory package"),
    ("plotly/labextension/package.json", "Labextension package.json"),
    ("plotly/labextension/static/*.js", "Labextension static JS assets"),
    ("plotly/offline/_plotlyjs_version.py", "Plotly.js version file"),
    ("plotly/serializers.py", "Core serializers module"),
    ("plotly/graph_objs/_scatter.py", "Scatter trace class"),
    ("plotly/graph_objs/_bar.py", "Bar trace class"),
    ("plotly/graph_objs/_layout.py", "Layout class"),
    ("plotly/graph_objs/_figure.py", "Figure class"),
]

WHEEL_OPTIONAL_FILES = [
    ("plotly/py.typed", "PEP 561 type hint marker"),
    ("_plotly_utils/py.typed", "PEP 561 type hint marker for _plotly_utils"),
    ("plotly/**/*.pyi", "Type stub files"),
    ("plotly/matplotlylib/__init__.py", "matplotlylib package (optional)"),
]

SDIST_REQUIRED_FILES = [
    ("*/pyproject.toml", "pyproject.toml build config"),
    ("*/hatch_build.py", "Hatch build hooks"),
    ("*/README.md", "README"),
    ("*/LICENSE.txt", "License"),
    ("*/plotly/__init__.py", "Top-level plotly package __init__"),
    ("*/_plotly_utils/__init__.py", "_plotly_utils package __init__"),
    ("*/plotly/validators/_validators.json", "Validators JSON data"),
    ("*/plotly/graph_objs/__init__.py", "graph_objs __init__"),
    ("*/plotly/graph_objects/__init__.py", "graph_objects __init__"),
    ("*/plotly/package_data/plotly.min.js", "plotly.js bundle"),
    ("*/plotly/package_data/widgetbundle.js", "FigureWidget bundle"),
    ("*/plotly/package_data/templates/plotly.json", "Plotly template"),
    ("*/plotly/package_data/datasets/gapminder.csv.gz", "Gapminder dataset"),
    ("*/codegen/resources/plot-schema.json", "Source plot-schema.json"),
    ("*/js/install.json", "Jupyter install.json for extension"),
    ("*/plotly/labextension/package.json", "Labextension package.json"),
    ("*/plotly/labextension/static/*.js", "Labextension static JS assets"),
    ("*/codegen/validate_packaging_manifest.py", "Packaging validator"),
]

WHEEL_METADATA_REQUIRED = [
    ("*.dist-info/METADATA", "Wheel METADATA"),
    ("*.dist-info/WHEEL", "WHEEL metadata"),
    ("*.dist-info/RECORD", "RECORD manifest"),
    ("*.dist-info/entry_points.txt", "Entry points (optional)"),
]

SDIST_METADATA_REQUIRED = [
    ("*/PKG-INFO", "PKG-INFO metadata"),
    ("*/pyproject.toml", "pyproject.toml"),
]

# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

def check_required_files(pkg: ExtractedPackage) -> list[CheckResult]:
    results: list[CheckResult] = []

    if pkg.pkg_type == "wheel":
        required = WHEEL_REQUIRED_FILES
        optional = WHEEL_OPTIONAL_FILES
    else:
        required = SDIST_REQUIRED_FILES
        optional = []

    for pattern, description in required:
        if not pkg.contains(pattern):
            results.append(_err(
                "required-files",
                f"Missing required file: {pattern}",
                description,
            ))
        else:
            matches = pkg.find_all(pattern)
            if len(matches) == 1:
                size = (pkg.extract_dir / matches[0]).stat().st_size
                if size == 0 and "js" not in pattern:
                    results.append(_warn(
                        "required-files",
                        f"File is 0 bytes: {matches[0]}",
                    ))
                elif size == 0:
                    results.append(_err(
                        "required-files",
                        f"Critical JS file is 0 bytes: {matches[0]}",
                    ))
                else:
                    results.append(_ok(
                        "required-files",
                        f"{pattern} present ({size/1024:.1f} KB)",
                    ))
            else:
                results.append(_ok(
                    "required-files",
                    f"{pattern} present ({len(matches)} matches)",
                ))

    for pattern, description in optional:
        if not pkg.contains(pattern):
            matches_count = len(pkg.find_all(pattern))
            results.append(_warn(
                "optional-files",
                f"Optional file not present: {pattern}",
                f"{description}. This is fine if the feature is not needed.",
            ))
        else:
            matches = pkg.find_all(pattern)
            results.append(_ok(
                "optional-files",
                f"{pattern} present ({len(matches)} matches)",
            ))

    return results


def check_metadata(pkg: ExtractedPackage) -> list[CheckResult]:
    results: list[CheckResult] = []

    metadata_files = WHEEL_METADATA_REQUIRED if pkg.pkg_type == "wheel" else SDIST_METADATA_REQUIRED

    for pattern, description in metadata_files:
        if not pkg.contains(pattern):
            if "entry_points" in pattern:
                results.append(_warn(
                    "metadata",
                    f"Optional metadata missing: {pattern}",
                ))
            else:
                results.append(_err(
                    "metadata",
                    f"Missing required metadata: {pattern}",
                    description,
                ))
        else:
            matches = pkg.find_all(pattern)
            if matches:
                fpath = pkg.extract_dir / matches[0]
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    if pattern.endswith("METADATA") or pattern.endswith("PKG-INFO"):
                        ver_match = re.search(r'^Version:\s*(\S+)', content, re.MULTILINE)
                        if ver_match:
                            results.append(_ok(
                                "metadata",
                                f"{pattern} present, version={ver_match.group(1)}",
                            ))
                        else:
                            results.append(_warn(
                                "metadata",
                                f"{pattern} present but couldn't extract version",
                            ))
                    else:
                        results.append(_ok(
                            "metadata",
                            f"{pattern} present ({fpath.stat().st_size} bytes)",
                        ))
                except Exception as e:
                    results.append(_warn(
                        "metadata",
                        f"Could not read {pattern}: {e}",
                    ))

    if pkg.pkg_type == "wheel":
        data_files = pkg.find_all("*.data/**/*")
        if data_files:
            results.append(_ok(
                "metadata",
                f"Wheel .data directory present with {len(data_files)} files",
                ", ".join(data_files[:5]) + ("..." if len(data_files) > 5 else ""),
            ))
        else:
            results.append(_warn(
                "metadata",
                "No .data directory in wheel",
                "JupyterLab extension assets are installed via shared-data, "
                "so this is expected — they'll be placed in share/jupyter/ on install.",
            ))

    return results


def check_version_consistency(pkg: ExtractedPackage) -> list[CheckResult]:
    results: list[CheckResult] = []
    versions: dict[str, str] = {}

    try:
        if pkg.pkg_type == "wheel":
            metadata_files = pkg.find_all("*.dist-info/METADATA")
        else:
            metadata_files = pkg.find_all("*/PKG-INFO")

        for mf in metadata_files:
            content = (pkg.extract_dir / mf).read_text(encoding="utf-8", errors="replace")
            m = re.search(r'^Version:\s*(\S+)', content, re.MULTILINE)
            if m:
                versions[mf] = m.group(1)

        pyplotlyjs = pkg.find_all("*/_plotlyjs_version.py")
        for pf in pyplotlyjs:
            content = (pkg.extract_dir / pf).read_text(encoding="utf-8", errors="replace")
            m = re.search(r'__plotlyjs_version__\s*=\s*"([^"]+)"', content)
            if m:
                versions["plotly.js version"] = m.group(1)

        lab_pkg_json = pkg.find_all("*/labextension/package.json")
        for lf in lab_pkg_json:
            try:
                data = json.loads((pkg.extract_dir / lf).read_text(encoding="utf-8"))
                v = data.get("version", "")
                if v:
                    versions[lf] = v
            except Exception:
                pass

        if len(set(v for k, v in versions.items() if "plotly.js" not in k)) > 1:
            results.append(_err(
                "version-consistency",
                "Version mismatch across package files",
                "; ".join(f"{k}={v}" for k, v in versions.items()),
            ))
        elif versions:
            results.append(_ok(
                "version-consistency",
                f"Versions consistent: {', '.join(f'{k}={v}' for k, v in versions.items())}",
            ))
        else:
            results.append(_warn("version-consistency", "Could not extract version info"))

    except Exception as e:
        results.append(_err("version-consistency", f"Version check failed: {e}"))

    return results


def check_anti_pollution(pkg: ExtractedPackage) -> list[CheckResult]:
    results: list[CheckResult] = []

    forbidden_patterns = [
        ("__pycache__/", "Python bytecode cache"),
        ("*.pyc", "Python bytecode"),
        (".DS_Store", "macOS metadata"),
        (".git/", "Git repository data"),
        ("node_modules/", "npm dependencies"),
        ("*.egg-info/", "Egg metadata"),
    ]

    if pkg.pkg_type == "wheel":
        forbidden_patterns.append(("js/", "Top-level js/ directory (namespace conflict)"))

    for pattern, description in forbidden_patterns:
        matches = pkg.find_all(f"*{pattern}*")
        if matches:
            results.append(_err(
                "anti-pollution",
                f"Forbidden pattern '{pattern}' found: {len(matches)} files",
                description,
            ))
        else:
            results.append(_ok("anti-pollution", f"No {description} in package"))

    return results


def check_labextension_assets(pkg: ExtractedPackage) -> list[CheckResult]:
    results: list[CheckResult] = []

    static_js = pkg.find_all("*/labextension/static/*.js")
    if not static_js:
        results.append(_err(
            "labextension",
            "No labextension static JS files found",
        ))
    else:
        total_size = sum((pkg.extract_dir / f).stat().st_size for f in static_js)
        remote_entry = [f for f in static_js if "remoteEntry" in f]
        if not remote_entry:
            results.append(_warn(
                "labextension",
                "No remoteEntry.*.js in labextension/static/",
            ))
        results.append(_ok(
            "labextension",
            f"Found {len(static_js)} labextension static JS files, {total_size/1024:.0f} KB total",
        ))

    lab_pkg = pkg.find_all("*/labextension/package.json")
    if not lab_pkg:
        results.append(_err("labextension", "labextension/package.json missing"))
    else:
        try:
            data = json.loads((pkg.extract_dir / lab_pkg[0]).read_text(encoding="utf-8"))
            jl = data.get("jupyterlab", {})
            build = jl.get("_build", {})
            if not build.get("load"):
                results.append(_warn(
                    "labextension",
                    "jupyterlab._build.load not set in package.json",
                ))
            else:
                load_path = build.get("load")
                load_pattern = f"*/labextension/{load_path}"
                if not pkg.contains(load_pattern):
                    results.append(_err(
                        "labextension",
                        f"_build.load target not found: {load_path}",
                    ))
                else:
                    results.append(_ok(
                        "labextension",
                        f"jupyterlab._build.load valid: {load_path}",
                    ))
        except Exception as e:
            results.append(_warn("labextension", f"Could not parse package.json: {e}"))

    if pkg.pkg_type == "sdist":
        install_json = pkg.find_all("*/js/install.json")
        if not install_json:
            results.append(_err(
                "labextension",
                "js/install.json missing from sdist",
            ))
        else:
            try:
                data = json.loads((pkg.extract_dir / install_json[0]).read_text(encoding="utf-8"))
                if data.get("packageName") == "plotly":
                    results.append(_ok("labextension", "js/install.json valid"))
                else:
                    results.append(_warn(
                        "labextension",
                        f"Unexpected packageName in install.json: {data.get('packageName')}",
                    ))
            except Exception as e:
                results.append(_warn("labextension", f"Could not parse install.json: {e}"))

    return results


def check_type_hints_inclusion(pkg: ExtractedPackage) -> list[CheckResult]:
    results: list[CheckResult] = []

    py_typed = pkg.find_all("*/py.typed")
    pyi_files = pkg.find_all("*/*.pyi")

    if py_typed:
        for pf in py_typed:
            results.append(_ok(
                "type-hints",
                f"py.typed marker included: {pf}",
            ))
    else:
        results.append(_warn(
            "type-hints",
            "No py.typed marker in package",
            "Type hints will not be distributed (PEP 561). "
            "Add plotly/py.typed to the source tree to include it.",
        ))

    if pyi_files:
        results.append(_ok(
            "type-hints",
            f"{len(pyi_files)} .pyi stub files included",
        ))
    else:
        results.append(_warn(
            "type-hints",
            "No .pyi stub files in package — relying on inline annotations",
        ))

    return results


def check_template_coverage(pkg: ExtractedPackage) -> list[CheckResult]:
    results: list[CheckResult] = []
    expected_templates = [
        "ggplot2.json", "gridon.json", "plotly.json", "plotly_dark.json",
        "plotly_white.json", "presentation.json", "seaborn.json",
        "simple_white.json", "xgridoff.json", "ygridoff.json",
    ]

    prefix = "*/package_data/templates/" if pkg.pkg_type == "sdist" else "plotly/package_data/templates/"
    missing = []
    for t in expected_templates:
        pattern = prefix + t
        if not pkg.contains(pattern):
            missing.append(t)

    if missing:
        results.append(_err(
            "templates",
            f"Missing {len(missing)} template files",
            ", ".join(missing),
        ))
    else:
        results.append(_ok(
            "templates",
            f"All {len(expected_templates)} template JSON files present",
        ))

    return results


def check_dataset_coverage(pkg: ExtractedPackage) -> list[CheckResult]:
    results: list[CheckResult] = []
    expected_datasets = [
        "carshare.csv.gz", "election.csv.gz", "election.geojson.gz",
        "experiment.csv.gz", "gapminder.csv.gz", "iris.csv.gz",
        "medals.csv.gz", "stocks.csv.gz", "tips.csv.gz", "wind.csv.gz",
    ]

    prefix = "*/package_data/datasets/" if pkg.pkg_type == "sdist" else "plotly/package_data/datasets/"
    missing = []
    for d in expected_datasets:
        pattern = prefix + d
        if not pkg.contains(pattern):
            missing.append(d)

    if missing:
        results.append(_warn(
            "datasets",
            f"Missing {len(missing)} dataset files",
            ", ".join(missing),
        ))
    else:
        results.append(_ok(
            "datasets",
            f"All {len(expected_datasets)} built-in datasets present",
        ))

    return results


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def validate_archive(archive_path: Path, verbose: bool = True) -> tuple[int, list[CheckResult]]:
    all_results: list[CheckResult] = []

    if not archive_path.is_file():
        all_results.append(_err("archive", f"Archive not found: {archive_path}"))
        return 1, all_results

    suffix = archive_path.suffixes
    if archive_path.suffix == ".whl":
        pkg_type = "wheel"
    elif len(suffix) >= 2 and suffix[-2] == ".tar" and suffix[-1] == ".gz":
        pkg_type = "sdist"
    else:
        all_results.append(_err(
            "archive",
            f"Unknown archive type: {archive_path.name}",
            "Expected .whl or .tar.gz",
        ))
        return 1, all_results

    if verbose:
        print(f"\n{'=' * 78}")
        print(f"  Validating {pkg_type.upper()}: {archive_path.name}")
        print(f"  Size: {archive_path.stat().st_size / 1024 / 1024:.2f} MB")
        print("=" * 78)

    with tempfile.TemporaryDirectory(prefix="plotly_pkg_check_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        try:
            if pkg_type == "wheel":
                pkg = _extract_wheel(archive_path, tmpdir)
            else:
                pkg = _extract_sdist(archive_path, tmpdir)
        except Exception as e:
            all_results.append(_err(
                "extract",
                f"Failed to extract {archive_path.name}: {e}",
            ))
            return 1, all_results

        if verbose:
            print(f"  Total files in {pkg_type}: {len(pkg.file_list)}")

        checks = [
            ("Required files", check_required_files),
            ("Metadata", check_metadata),
            ("Version consistency", check_version_consistency),
            ("Anti-pollution (no cache/bytecode)", check_anti_pollution),
            ("Labextension assets", check_labextension_assets),
            ("Type hints inclusion", check_type_hints_inclusion),
            ("Template coverage", check_template_coverage),
            ("Dataset coverage", check_dataset_coverage),
        ]

        for check_name, check_fn in checks:
            if verbose:
                print(f"\n▶ {check_name}")
            try:
                results = check_fn(pkg)
            except Exception as e:
                import traceback
                traceback.print_exc()
                results = [_err(check_name.lower().split(" ")[0], f"Check crashed: {e}")]

            all_results.extend(results)
            if verbose:
                for r in results:
                    prefix = {"OK": "  ✓ ", "WARN": "  ⚠ ", "ERROR": "  ✗ "}.get(r.severity, "  ? ")
                    lines = str(r).splitlines()
                    print(f"{prefix}{lines[0]}")
                    for line in lines[1:]:
                        print(f"    {line}")

    errors = [r for r in all_results if r.is_error()]
    warnings = [r for r in all_results if r.is_warn()]

    if verbose:
        print("\n" + "=" * 78)
        print(f"  Summary: {len(errors)} ERROR  |  {len(warnings)} WARN  |  "
              f"{len(all_results) - len(errors) - len(warnings)} OK")
        print("=" * 78)

    exit_code = 1 if errors else 0
    return exit_code, all_results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate built plotly.py wheel/sdist archives in dist/"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="dist",
        help="Path to dist/ directory or a specific .whl/.tar.gz file (default: dist/)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress per-check output, only print final summary and exit code",
    )
    args = parser.parse_args()

    dist_path = Path(args.path).resolve()
    archives = _find_archives(dist_path)

    if not archives:
        print(f"❌ No .whl or .tar.gz files found at {dist_path}")
        print("   Build packages first: `python -m build --sdist --wheel -o dist`")
        return 1

    if not args.quiet:
        print("=" * 78)
        print("  Plotly.py Post-Build Distribution Validator")
        print(f"  Project root: {PROJECT_ROOT}")
        print(f"  Run at:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Archives:     {', '.join(a.name for a in archives)}")
        print("=" * 78)

    total_exit = 0
    all_errors: list[str] = []

    for archive in archives:
        exit_code, results = validate_archive(archive, verbose=not args.quiet)
        total_exit = max(total_exit, exit_code)
        if exit_code != 0:
            errors = [str(r) for r in results if r.is_error()]
            all_errors.extend(f"{archive.name}: {e}" for e in errors)

    if not args.quiet:
        if total_exit == 0:
            print("\n✅ All distribution archives validated successfully.")
            print("   Key artifacts verified inside the built packages.")
        else:
            print("\n❌ Distribution validation FAILED — the following issues must be fixed:")
            for e in all_errors:
                prefix = "   - "
                lines = e.splitlines()
                print(f"{prefix}{lines[0]}")
                for line in lines[1:]:
                    print(f"     {line}")

    return total_exit


if __name__ == "__main__":
    sys.exit(main())

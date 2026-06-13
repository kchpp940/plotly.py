"""
Hatch build hooks for plotly.py

Runs the packaging manifest validator before building sdist/wheel,
blocking the build if critical artifacts are missing or inconsistent.

Only runs validate_packaging_manifest.py (stable, passable checks).
The schema artifact validator (validate_schema_artifacts.py) is kept
as a separate manual command since it has known issues and would
block the release build.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VALIDATOR_SCRIPT = PROJECT_ROOT / "codegen" / "validate_packaging_manifest.py"

SKIP_PACKAGING_CHECK = os.environ.get("PLOTLY_SKIP_PACKAGING_CHECK", "").lower() in (
    "1", "true", "yes", "on"
)


def _run_validator(script_path: Path, label: str) -> None:
    if SKIP_PACKAGING_CHECK:
        print(f"[hatch-hook] Skipping {label} check (PLOTLY_SKIP_PACKAGING_CHECK=1)")
        return

    if script_path.is_file():
        cmd = [sys.executable, str(script_path)]
        print(f"[hatch-hook] Running {label} validator...")
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            raise SystemExit(
                f"\n[hatch-hook] ❌ {label} validation FAILED "
                f"(exit code {result.returncode}).\n"
                f"[hatch-hook] Fix the issues above, or set "
                f"PLOTLY_SKIP_PACKAGING_CHECK=1 "
                f"to bypass (not recommended for release builds)."
            )
        print(f"[hatch-hook] ✅ {label} validation passed.")
    else:
        print(f"[hatch-hook] ⚠️  {label} validator script not found at {script_path}, skipping.")


def build_sdist(directory: str) -> str | None:
    """Hook called before building the source distribution."""
    print("\n" + "=" * 60)
    print("[hatch-hook] Pre-build: Packaging manifest check (sdist)")
    print("=" * 60)
    _run_validator(VALIDATOR_SCRIPT, "packaging-manifest")
    print()
    return None


def build_wheel(wheel_directory: str, directory: str) -> str | None:
    """Hook called before building the wheel."""
    print("\n" + "=" * 60)
    print("[hatch-hook] Pre-build: Packaging manifest check (wheel)")
    print("=" * 60)
    _run_validator(VALIDATOR_SCRIPT, "packaging-manifest")
    print()
    return None

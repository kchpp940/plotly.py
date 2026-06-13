import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lint_error_messages import DEFAULT_TARGET_FILES, scan_files


def test_no_raw_multiline_error_strings():
    repo_root = SCRIPTS_DIR.parent
    target_paths = [repo_root / f for f in DEFAULT_TARGET_FILES]
    violations = scan_files(target_paths)

    if violations:
        msg_lines = [
            f"Found {len(violations)} raw multi-line error string violation(s):"
        ]
        for v in violations:
            msg_lines.append(v.format())
        pytest.fail("\n".join(msg_lines))

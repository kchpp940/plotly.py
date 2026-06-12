"""Verify the dependency registry stays in sync with pyproject.toml extras.

This test acts as a build-time guard: if someone adds a new optional
dependency to ``[project.optional-dependencies]`` but forgets to register
it (or its min_version / extra name) in :mod:`_plotly_utils.dependencies`,
this test will fail.

Run with::

    pytest tests/test_core/test_optional_imports/test_pyproject_consistency.py
"""

import os

import pytest

from plotly.optional_imports import check_pyproject_consistency


_PYPROJECT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "..",
    "pyproject.toml",
)
_PYPROJECT_PATH = os.path.normpath(_PYPROJECT_PATH)


@pytest.fixture(scope="module")
def consistency_issues():
    """Run the consistency check once and share results across test cases."""
    return check_pyproject_consistency(
        pyproject_path=_PYPROJECT_PATH,
        ignore_extras=["dev", "dev_build", "dev_optional", "dev_pandas1", "dev_pandas2", "dev_pandas3"],
        ignore_packages=["plotly"],
    )


def test_no_mismatch_min_version(consistency_issues):
    """Every registered min_version must agree with pyproject.toml."""
    assert not consistency_issues["mismatch_min_version"], (
        "min_version drift between registry and pyproject.toml:\n  - "
        + "\n  - ".join(consistency_issues["mismatch_min_version"])
    )


def test_no_dep_extra_missing(consistency_issues):
    """Every dep.extra must point to a real extra in pyproject.toml."""
    assert not consistency_issues["dep_extra_missing"], (
        "Registered dependencies reference nonexistent extras:\n  - "
        + "\n  - ".join(consistency_issues["dep_extra_missing"])
    )


def test_no_capability_missing_dep(consistency_issues):
    """Every capability must reference a registered dependency."""
    assert not consistency_issues["capability_missing_dep"], (
        "Capabilities reference unregistered dependencies:\n  - "
        + "\n  - ".join(consistency_issues["capability_missing_dep"])
    )


def test_no_unregistered_user_facing_packages(consistency_issues):
    """Every package in user-facing extras must have a Dependency registration."""
    assert not consistency_issues["unregistered_package"], (
        "Packages in user-facing extras have no Dependency registration:\n  - "
        + "\n  - ".join(consistency_issues["unregistered_package"])
    )


def test_no_error_level_issues(consistency_issues):
    """Sanity check – no error-level issues at all."""
    assert not consistency_issues.get("error", []), (
        "Dependency consistency errors:\n  - "
        + "\n  - ".join(consistency_issues["error"])
    )

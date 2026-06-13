"""
Regression tests for schema artifact consistency checker.

Tests the layered architecture:
  - SchemaArtifactIndex
  - ValidatorArtifactIndex
  - GraphObjectArtifactIndex
  - DocReferenceIndex
  - ConsistencyCheck engine
  - Configuration system (enable/disable checks, ignore patterns, severity overrides)
  - Error injection scenarios
  - CLI exit codes
"""

import json
import os
import subprocess
import sys

import pytest

from codegen.validate_schema_artifacts import (
    ConsistencyCheck,
    ValidationConfig,
    CheckSpec,
    SchemaArtifactIndex,
    ValidatorArtifactIndex,
    GraphObjectArtifactIndex,
    DocReferenceIndex,
    ValidatorEntry,
    GOClassInfo,
    DocReference,
    DEFAULT_CONFIG,
    run_all_checks,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VALIDATORS_PATH = os.path.join(PROJECT_ROOT, "plotly", "validators", "_validators.json")
SCATTER_CLASS_PATH = os.path.join(PROJECT_ROOT, "plotly", "graph_objs", "_scatter.py")
COMMANDS_PATH = os.path.join(PROJECT_ROOT, "commands.py")


@pytest.fixture
def clean_checker():
    """Provide a ConsistencyCheck instance with all indices built."""
    checker = ConsistencyCheck()
    checker.build_indices()
    return checker


# =====================================================================
# Index construction tests
# =====================================================================


class TestSchemaArtifactIndex:
    def test_build_trace_property_paths(self, clean_checker):
        assert len(clean_checker.schema_idx.trace_property_paths) > 0
        assert "scatter.x" in clean_checker.schema_idx.trace_property_paths
        assert "scatter.marker.color" in clean_checker.schema_idx.trace_property_paths

    def test_build_layout_property_paths(self, clean_checker):
        assert len(clean_checker.schema_idx.layout_property_paths) > 0
        assert "layout.xaxis" in clean_checker.schema_idx.layout_property_paths
        assert "layout.template" in clean_checker.schema_idx.layout_property_paths

    def test_build_trace_properties(self, clean_checker):
        assert "scatter" in clean_checker.schema_idx.trace_properties
        scatter_props = clean_checker.schema_idx.trace_properties["scatter"]
        assert len(scatter_props) > 0
        assert "x" in scatter_props or "xaxis" in scatter_props

    def test_build_layout_properties(self, clean_checker):
        assert len(clean_checker.schema_idx.layout_properties) > 0
        assert "xaxis" in clean_checker.schema_idx.layout_properties
        assert "yaxis" in clean_checker.schema_idx.layout_properties


class TestValidatorArtifactIndex:
    def test_build_entries(self, clean_checker):
        assert len(clean_checker.validator_idx.entries) > 10000
        assert "data" not in clean_checker.validator_idx.all_keys

    def test_compound_entries(self, clean_checker):
        assert len(clean_checker.validator_idx.compound_entries) > 1000
        assert all(v.is_compound for v in clean_checker.validator_idx.compound_entries.values())

    def test_validator_entry_dataclass(self, clean_checker):
        entry = list(clean_checker.validator_idx.entries.values())[0]
        assert isinstance(entry, ValidatorEntry)
        assert hasattr(entry, "key")
        assert hasattr(entry, "superclass")
        assert hasattr(entry, "is_compound")
        assert hasattr(entry, "parent_key")

    def test_validator_entry_parent_key(self, clean_checker):
        entry = clean_checker.validator_idx.entries["scatter.marker"]
        assert entry.parent_key == "scatter"

    def test_validator_key_to_class_paths_template(self, clean_checker):
        v_idx = clean_checker.validator_idx
        assert v_idx.validator_key_to_class_paths("layout.template.data.scatter", "Scatter") == ["Scatter"]
        assert v_idx.validator_key_to_class_paths("layout.template.layout", "Layout") == ["Layout"]
        assert v_idx.validator_key_to_class_paths("waterfall.marker", "Marker") == ["waterfall.Marker"]


class TestGraphObjectArtifactIndex:
    def test_build_class_index(self, clean_checker):
        assert len(clean_checker.go_idx.by_full_path) > 1000
        assert "Bar" in clean_checker.go_idx.by_full_path
        assert "Scatter" in clean_checker.go_idx.by_full_path

    def test_go_class_info_dataclass(self, clean_checker):
        info = clean_checker.go_idx.by_full_path["Scatter"]
        assert isinstance(info, GOClassInfo)
        assert info.class_name == "Scatter"
        assert info.full_path == "Scatter"
        assert info.is_top_level is True
        assert len(info.valid_props) > 0

    def test_nested_class_path(self, clean_checker):
        assert "scatter.Marker" in clean_checker.go_idx.by_full_path
        nested = clean_checker.go_idx.by_full_path["scatter.Marker"]
        assert nested.is_top_level is False
        assert nested.full_path == "scatter.Marker"

    def test_exports(self, clean_checker):
        assert len(clean_checker.go_idx.graph_objs_class_exports) > 50
        assert len(clean_checker.go_idx.graph_objects_class_exports) > 50
        assert "Scatter" in clean_checker.go_idx.graph_objs_class_exports
        assert "Scatter" in clean_checker.go_idx.graph_objects_class_exports

    def test_find_top_level_class(self, clean_checker):
        found = clean_checker.go_idx.find_top_level_class("Scatter")
        assert found is not None
        assert found.class_name == "Scatter"
        assert found.is_top_level is True


class TestDocReferenceIndex:
    def test_build_references(self, clean_checker):
        refs = clean_checker.doc_idx.references
        assert isinstance(refs, dict)

    def test_doc_reference_dataclass(self, clean_checker):
        if clean_checker.doc_idx.all_references:
            ref = clean_checker.doc_idx.all_references[0]
            assert isinstance(ref, DocReference)
            assert hasattr(ref, "class_name")
            assert hasattr(ref, "attribute")
            assert hasattr(ref, "source_file")

    def test_is_ignored_attribute(self, clean_checker):
        idx = clean_checker.doc_idx
        assert idx.is_ignored_attribute("show") is True
        assert idx.is_ignored_attribute("add_trace") is True
        assert idx.is_ignored_attribute("for_each_trace") is True
        assert idx.is_ignored_attribute("update_layout") is True
        assert idx.is_ignored_attribute("xaxis") is False
        assert idx.is_ignored_attribute("marker") is False


# =====================================================================
# Configuration system tests
# =====================================================================


class TestConfiguration:
    def test_disable_check(self):
        cfg = ValidationConfig()
        cfg.checks["doc-refs"] = CheckSpec(enabled=False)
        checker = ConsistencyCheck(config=cfg)
        checker.build_indices()
        err, warn, all_errs = checker.run_all_checks(verbose=False)
        doc_refs_errs = [e for e in all_errs if e.check == "doc-refs"]
        assert len(doc_refs_errs) == 0

    def test_ignore_pattern(self):
        cfg = ValidationConfig()
        cfg.checks["codegen-vs-validators"] = CheckSpec(
            enabled=True,
            ignore_patterns={r"Codegen property 'scatter"},
        )
        checker = ConsistencyCheck(config=cfg)
        checker.build_indices()
        err, warn, all_errs = checker.run_all_checks(verbose=False)
        codegen_errs = [e for e in all_errs if e.check == "codegen-vs-validators"]
        assert all("Codegen property 'scatter" not in str(e) for e in codegen_errs)

    def test_default_config(self):
        assert DEFAULT_CONFIG.doc_rules is not None
        assert DEFAULT_CONFIG.class_rules is not None
        assert DEFAULT_CONFIG.validator_rules is not None
        assert "codegen-vs-validators" in DEFAULT_CONFIG.checks
        assert DEFAULT_CONFIG.checks["codegen-vs-validators"].enabled is True


# =====================================================================
# Error injection tests (using temp file modifications)
# =====================================================================


class TestErrorInjection:
    @pytest.fixture
    def temp_validators_backup(self):
        with open(VALIDATORS_PATH, "r") as f:
            original = f.read()
        yield
        with open(VALIDATORS_PATH, "w") as f:
            f.write(original)

    @pytest.fixture
    def temp_scatter_backup(self):
        with open(SCATTER_CLASS_PATH, "r") as f:
            original = f.read()
        yield
        with open(SCATTER_CLASS_PATH, "w") as f:
            f.write(original)

    def test_missing_validator_entry(self, temp_validators_backup):
        with open(VALIDATORS_PATH, "r") as f:
            data = json.load(f)
        removed = data.pop("scatter.yaxis", None)
        assert removed is not None
        with open(VALIDATORS_PATH, "w") as f:
            json.dump(data, f, indent=4)

        err, warn, all_errs = run_all_checks(verbose=False)
        assert err >= 1
        matching = [e for e in all_errs if "scatter.yaxis" in e.message and e.check == "codegen-vs-validators"]
        assert len(matching) >= 1

    def test_missing_valid_props_entry(self, temp_scatter_backup):
        with open(SCATTER_CLASS_PATH, "r") as f:
            content = f.read()
        modified = content.replace('"mode",', "")
        assert modified != content
        with open(SCATTER_CLASS_PATH, "w") as f:
            f.write(modified)

        err, warn, all_errs = run_all_checks(verbose=False)
        assert err >= 1
        matching = [e for e in all_errs if "mode" in e.message and e.check == "trace-coverage"]
        assert len(matching) >= 1

    def test_clean_state_zero_errors(self):
        err, warn, _ = run_all_checks(verbose=False)
        assert err == 0
        assert warn == 0


# =====================================================================
# CLI exit code tests
# =====================================================================


class TestCLIExitCodes:
    def test_cli_success_exit_zero(self):
        result = subprocess.run(
            [sys.executable, COMMANDS_PATH, "validateschema"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_cli_help(self):
        result = subprocess.run(
            [sys.executable, COMMANDS_PATH, "validateschema", "--help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "validateschema" in result.stdout
        assert "--strict" in result.stdout

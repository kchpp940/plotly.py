"""
Schema and codegen consistency tests.

These tests validate that codegen outputs (validators, graph_objects, exports)
stay in sync with the plot-schema.json source of truth.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


def test_codegen_vs_validators():
    from codegen.validate_schema_artifacts import (
        SCHEMA_PATH,
        VALIDATORS_PATH,
        load_json,
        _preprocess_schema,
        check_codegen_vs_validators,
    )

    schema = load_json(SCHEMA_PATH)
    validators_json = load_json(VALIDATORS_PATH)
    _preprocess_schema(schema)

    errors = check_codegen_vs_validators(schema, validators_json)
    error_count = sum(1 for e in errors if e.severity == "error")
    assert error_count == 0, "\n".join(str(e) for e in errors if e.severity == "error")


def test_validators_vs_graph_objects():
    from codegen.validate_schema_artifacts import (
        VALIDATORS_PATH,
        GRAPH_OBJS_DIR,
        load_json,
        check_validators_vs_graph_objects,
    )

    validators_json = load_json(VALIDATORS_PATH)
    errors = check_validators_vs_graph_objects(validators_json, GRAPH_OBJS_DIR)
    error_count = sum(1 for e in errors if e.severity == "error")
    assert error_count == 0, "\n".join(str(e) for e in errors if e.severity == "error")


def test_graph_objs_exports():
    from codegen.validate_schema_artifacts import (
        GRAPH_OBJS_INIT,
        GRAPH_OBJECTS_INIT,
        check_graph_objs_exports,
    )

    errors = check_graph_objs_exports(GRAPH_OBJS_INIT, GRAPH_OBJECTS_INIT)
    error_count = sum(1 for e in errors if e.severity == "error")
    assert error_count == 0, "\n".join(str(e) for e in errors if e.severity == "error")


def test_trace_class_coverage():
    from codegen.validate_schema_artifacts import (
        SCHEMA_PATH,
        GRAPH_OBJS_DIR,
        load_json,
        _preprocess_schema,
        check_trace_class_coverage,
    )

    schema = load_json(SCHEMA_PATH)
    _preprocess_schema(schema)

    errors = check_trace_class_coverage(schema, GRAPH_OBJS_DIR)
    error_count = sum(1 for e in errors if e.severity == "error")
    assert error_count == 0, "\n".join(str(e) for e in errors if e.severity == "error")


def test_layout_valid_props():
    from codegen.validate_schema_artifacts import (
        SCHEMA_PATH,
        GRAPH_OBJS_DIR,
        load_json,
        _preprocess_schema,
        check_layout_valid_props,
    )

    schema = load_json(SCHEMA_PATH)
    _preprocess_schema(schema)

    errors = check_layout_valid_props(schema, GRAPH_OBJS_DIR)
    error_count = sum(1 for e in errors if e.severity == "error")
    assert error_count == 0, "\n".join(str(e) for e in errors if e.severity == "error")


def test_doc_attribute_refs():
    from codegen.validate_schema_artifacts import (
        SCHEMA_PATH,
        GRAPH_OBJS_DIR,
        DOC_PYTHON_DIR,
        load_json,
        _preprocess_schema,
        check_doc_attribute_refs,
    )

    schema = load_json(SCHEMA_PATH)
    _preprocess_schema(schema)

    errors = check_doc_attribute_refs(DOC_PYTHON_DIR, GRAPH_OBJS_DIR, schema)
    error_count = sum(1 for e in errors if e.severity == "error")
    assert error_count == 0, "\n".join(str(e) for e in errors if e.severity == "error")

import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

SMOKE_TEST_FILES = {
    "tests/test_core/test_graph_objs/test_constructor.py",
    "tests/test_core/test_graph_objs/test_figure.py",
    "tests/test_core/test_subplots/test_make_subplots.py",
    "tests/test_io/test_to_from_json.py",
    "tests/test_plotly_utils/validators/test_string_validator.py",
}


def _relative_path(path):
    return os.path.relpath(path, PROJECT_ROOT)


def pytest_collection_modifyitems(config, items):
    for item in items:
        filepath = item.fspath.strpath
        rel_path = _relative_path(filepath)
        markers = []

        if rel_path.startswith("tests/test_core/"):
            markers.append("core")
            if rel_path in SMOKE_TEST_FILES:
                markers.append("smoke")

        elif rel_path.startswith("tests/test_io/"):
            markers.append("core")

        elif rel_path.startswith("tests/test_plotly_utils/"):
            markers.append("core")

        elif rel_path.startswith("tests/test_optional/"):
            markers.append("optional")

            if rel_path.startswith("tests/test_optional/test_px/"):
                markers.append("express")

            if rel_path.startswith("tests/test_optional/test_kaleido/"):
                markers.append("image_export")

            if rel_path.startswith("tests/test_optional/test_matplotlylib/"):
                markers.append("matplotlib")

        elif rel_path.startswith("test_init/"):
            if "test_dependencies_not_imported" not in rel_path:
                markers.append("core")

        for marker in markers:
            item.add_marker(marker)

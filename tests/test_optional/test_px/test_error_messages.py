import re
import sys

import pandas as pd
import pytest

import plotly.express as px
from _plotly_utils.error_messages import (
    ErrorCode,
    ErrorMessage,
    build_error_message,
    disable_snapshot_mode,
    enable_snapshot_mode,
    is_snapshot_mode,
)


class TestExpressInvalidValueError:
    def teardown_method(self):
        if is_snapshot_mode():
            disable_snapshot_mode()

    def test_invalid_column_error_code_and_type(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="nonexistent_column", y="b")

        msg = exc_info.value.args[0]
        assert isinstance(msg, ErrorMessage)
        assert isinstance(msg, str)

        assert hasattr(msg, "error_code")
        assert msg.error_code in {
            ErrorCode.INVALID_VALUE.value,
            ErrorCode.INVALID_PARAM.value,
        }

    def test_invalid_column_error_content_in_snapshot_mode(self):
        df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": [4, 5, 6]})
        enable_snapshot_mode()
        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="not_a_real_column", y="col_b")

        msg_str = str(exc_info.value.args[0])
        assert "Column not found" in msg_str
        assert "not_a_real_column" in msg_str

    def test_invalid_column_error_path_metadata(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="does_not_exist", y="y")

        msg = exc_info.value.args[0]
        assert hasattr(msg, "error_path")
        assert msg.error_path is not None
        assert "x" in msg.error_path


class TestExpressTrendlineDependencyError:
    def teardown_method(self):
        if is_snapshot_mode():
            disable_snapshot_mode()

    def test_trendline_missing_statsmodels_dependency(self, monkeypatch):
        import plotly.express.trendline_functions as trend_mod

        original_sm = sys.modules.get("statsmodels")
        original_sm_api = sys.modules.get("statsmodels.api")

        monkeypatch.setitem(sys.modules, "statsmodels", None)
        monkeypatch.setitem(sys.modules, "statsmodels.api", None)

        import importlib

        importlib.reload(trend_mod)

        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [2, 4, 5, 4, 6]})
        with pytest.raises((ImportError, ModuleNotFoundError, Exception)):
            px.scatter(df, x="x", y="y", trendline="ols")

        if original_sm is not None:
            sys.modules["statsmodels"] = original_sm
        if original_sm_api is not None:
            sys.modules["statsmodels.api"] = original_sm_api
        importlib.reload(trend_mod)

    def test_dependency_error_message_structure(self):
        msg = build_error_message(
            ErrorCode.DEPENDENCY_MISSING,
            "statsmodels is required for trendline computation.",
            install_hint="pip install statsmodels",
        )

        assert msg.error_code == "E001"
        assert msg.install_hint == "pip install statsmodels"
        assert "statsmodels" in msg.install_hint
        assert isinstance(msg, ErrorMessage)
        assert isinstance(msg, str)
        assert str(msg) == "statsmodels is required for trendline computation."


class TestExpressInvalidFacetAndParams:
    def teardown_method(self):
        if is_snapshot_mode():
            disable_snapshot_mode()

    def test_invalid_trendline_error_code(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="a", y="b", trendline="totally_invalid_trendline")

        msg = exc_info.value.args[0]
        assert isinstance(msg, ErrorMessage)
        assert msg.error_code == ErrorCode.INVALID_PARAM.value
        assert msg.error_code == "E004"

    def test_invalid_trendline_structured_metadata(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        enable_snapshot_mode()
        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="a", y="b", trendline="bad_value")

        msg = exc_info.value.args[0]
        assert hasattr(msg, "error_path")
        assert msg.error_path is not None
        assert "trendline" in msg.error_path

        msg_str = str(msg)
        assert "Invalid value" in msg_str
        assert "totally_invalid_trendline" not in msg_str
        assert "bad_value" in msg_str

    def test_ecdfnorm_invalid_value_metadata(self):
        df = pd.DataFrame({"val": [1.1, 2.2, 3.3]})
        with pytest.raises(ValueError) as exc_info:
            px.ecdf(df, x="val", ecdfnorm="bogus_norm")

        msg = exc_info.value.args[0]
        assert isinstance(msg, ErrorMessage)
        assert msg.error_code == ErrorCode.INVALID_PARAM.value
        assert msg.error_path is not None
        assert "ecdfnorm" in msg.error_path


class TestSnapshotModeExpressErrors:
    def teardown_method(self):
        if is_snapshot_mode():
            disable_snapshot_mode()

    def test_snapshot_mode_enables_code_prefix(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})

        enable_snapshot_mode()
        assert is_snapshot_mode() is True

        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="missing_col", y="y")

        msg_str = str(exc_info.value.args[0])
        assert re.search(r"\[E\d{3}\]", msg_str) is not None

    def test_snapshot_mode_disables_code_prefix(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})

        if is_snapshot_mode():
            disable_snapshot_mode()
        assert is_snapshot_mode() is False

        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="missing_col", y="y")

        msg_str = str(exc_info.value.args[0])
        assert re.search(r"\[E\d{3}\]", msg_str) is None

    def test_snapshot_toggle_consistency(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        enable_snapshot_mode()
        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="a", y="b", trendline="bad_trendline_type")
        msg_with_prefix = str(exc_info.value.args[0])
        assert "[E004]" in msg_with_prefix

        disable_snapshot_mode()
        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="a", y="b", trendline="bad_trendline_type")
        msg_without_prefix = str(exc_info.value.args[0])
        assert "[E004]" not in msg_without_prefix

        enable_snapshot_mode()
        with pytest.raises(ValueError) as exc_info:
            px.scatter(df, x="a", y="b", trendline="bad_trendline_type")
        msg_again_with_prefix = str(exc_info.value.args[0])
        assert "[E004]" in msg_again_with_prefix

        disable_snapshot_mode()
        assert is_snapshot_mode() is False

    def test_snapshot_mode_preserves_structured_attributes(self):
        enable_snapshot_mode()

        msg = build_error_message(
            ErrorCode.INVALID_VALUE,
            "Something went wrong.",
            path=["field_a", "nested_b"],
            install_hint="pip install fix-it",
        )

        assert "[E002]" in str(msg)
        assert msg.error_code == "E002"
        assert msg.install_hint == "pip install fix-it"
        assert msg.error_path == ["field_a", "nested_b"]

        disable_snapshot_mode()


class TestErrorMessageBackwardCompatibility:
    def test_assert_in_operator_on_fragment(self):
        msg = build_error_message(
            ErrorCode.INVALID_PARAM,
            "Column 'bad_col' not found in the data frame. Expected one of: a, b, c",
            path=["x"],
        )

        assert "bad_col" in msg
        assert "not found" in msg
        assert "EXPECTED_ONE_OF_XYZ" not in msg

    def test_re_match_against_message(self):
        msg = build_error_message(
            ErrorCode.LENGTH_MISMATCH,
            "All arguments should have the same length. Length of x is 5 but length of y is 10.",
            path=["x", "y"],
        )

        pattern = r"same length"
        assert re.search(pattern, msg) is not None

        match = re.search(r"Length of x is (\d+)", msg)
        assert match is not None
        assert int(match.group(1)) == 5

    def test_value_error_args_contains_error_message(self):
        msg = build_error_message(
            ErrorCode.INVALID_VALUE,
            "The value 42 is not valid for this field.",
            path=["some_field"],
        )

        err = ValueError(msg)
        assert err.args[0] is msg
        assert isinstance(err.args[0], ErrorMessage)
        assert isinstance(err.args[0], str)
        assert str(err) == "The value 42 is not valid for this field."

    def test_error_message_str_equality_no_prefix(self):
        if is_snapshot_mode():
            disable_snapshot_mode()

        raw_msg = "This is the exact original error message."
        msg = build_error_message(ErrorCode.DEPRECATION, raw_msg)

        assert str(msg) == raw_msg

    def test_concatenation_and_formatting_works_like_str(self):
        msg = build_error_message(ErrorCode.CONFIG_ERROR, "Config key missing")

        concatenated = msg + " (extra)"
        assert isinstance(concatenated, str)
        assert concatenated == "Config key missing (extra)"

        formatted = "Prefix: {}".format(msg)
        assert formatted == "Prefix: Config key missing"

        upper = msg.upper()
        assert upper == "CONFIG KEY MISSING"

    def test_error_code_never_in_default_string_output(self):
        if is_snapshot_mode():
            disable_snapshot_mode()

        msg = build_error_message(ErrorCode.NOT_ALLOWED, "Operation not permitted")
        msg_str = str(msg)

        assert "[E015]" not in msg_str
        assert "E015" not in msg_str or msg.error_code == "E015"

    def test_all_error_code_values_are_formatted(self):
        for code in ErrorCode:
            assert code.value.startswith("E")
            assert len(code.value) == 4
            assert code.value[1:].isdigit()

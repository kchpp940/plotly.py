import pytest
import unittest.mock as mock

from _plotly_utils.basevalidators import (
    EnumeratedValidator,
    LiteralValidator,
)
from _plotly_utils.error_messages import (
    enable_snapshot_mode,
    disable_snapshot_mode,
    is_snapshot_mode,
)

import plotly.io as pio
from plotly.io._json import JsonConfig


@pytest.fixture(autouse=True)
def ensure_default_mode():
    disable_snapshot_mode()
    yield
    disable_snapshot_mode()


@pytest.fixture()
def enumerated_validator():
    values = ["first", "second", "third", 4]
    return EnumeratedValidator("prop", "parent", values, array_ok=False)


@pytest.fixture()
def enumerated_validator_aok():
    values = ["first", "second", "third", 4]
    return EnumeratedValidator("prop", "parent", values, array_ok=True)


@pytest.fixture()
def literal_validator():
    return LiteralValidator("prop", "parent", "scatter")


class TestValidatorInvalidValueExactFormat:
    def test_enumerated_invalid_value_starts_with_correct_text(
        self, enumerated_validator
    ):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator.validate_coerce("bogus_value")

        err_msg = str(exc_info.value.args[0])

        assert err_msg.startswith(
            "\n    Invalid value of type 'builtins.str' received "
            "for the 'prop' property of parent\n"
        )

    def test_enumerated_invalid_value_contains_received_value(
        self, enumerated_validator
    ):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator.validate_coerce(12345)

        err_msg = str(exc_info.value.args[0])

        assert "        Received value: 12345\n\n" in err_msg

    def test_enumerated_invalid_value_ends_with_enumeration_desc(
        self, enumerated_validator
    ):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator.validate_coerce("bogus")

        err_msg = str(exc_info.value.args[0])

        assert "The 'prop' property is an enumeration" in err_msg

    def test_no_error_code_prefix_in_default_mode(self, enumerated_validator):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator.validate_coerce("bogus")

        err_msg = str(exc_info.value.args[0])

        assert not err_msg.startswith("[E002]")
        assert "[E002]" not in err_msg[:20]

    def test_error_code_attribute_exists(self, enumerated_validator):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator.validate_coerce("bogus")

        error_obj = exc_info.value.args[0]
        assert hasattr(error_obj, "error_code")
        assert error_obj.error_code == "E002"


class TestValidatorInvalidElementsExactFormat:
    def test_invalid_elements_starts_with_correct_text(
        self, enumerated_validator_aok
    ):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator_aok.validate_coerce(["bogus", "values"])

        err_msg = str(exc_info.value.args[0])

        assert err_msg.startswith(
            "\n    Invalid element(s) received for the 'prop' property of parent\n"
        )

    def test_invalid_elements_contains_invalid_list(
        self, enumerated_validator_aok
    ):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator_aok.validate_coerce([True, False])

        err_msg = str(exc_info.value.args[0])

        assert "        Invalid elements include: [" in err_msg
        assert "True" in err_msg or "False" in err_msg

    def test_invalid_elements_ends_with_description(
        self, enumerated_validator_aok
    ):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator_aok.validate_coerce(["bogus"])

        err_msg = str(exc_info.value.args[0])

        assert "The 'prop' property is an enumeration" in err_msg

    def test_no_error_code_prefix_in_invalid_elements(
        self, enumerated_validator_aok
    ):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator_aok.validate_coerce(["bogus"])

        err_msg = str(exc_info.value.args[0])

        assert not err_msg.startswith("[E003]")
        assert "[E003]" not in err_msg[:20]

    def test_error_code_attribute_invalid_elements(
        self, enumerated_validator_aok
    ):
        with pytest.raises(ValueError) as exc_info:
            enumerated_validator_aok.validate_coerce(["bogus"])

        error_obj = exc_info.value.args[0]
        assert hasattr(error_obj, "error_code")
        assert error_obj.error_code == "E003"


class TestLiteralValidatorReadOnlyExactFormat:
    def test_readonly_message_exact_format(self, literal_validator):
        with pytest.raises(ValueError) as exc_info:
            literal_validator.validate_coerce("bogus_type")

        err_msg = str(exc_info.value.args[0])

        assert err_msg == "\n    The 'prop' property of parent is read-only"

    def test_readonly_no_error_code_prefix(self, literal_validator):
        with pytest.raises(ValueError) as exc_info:
            literal_validator.validate_coerce("bogus")

        err_msg = str(exc_info.value.args[0])

        assert not err_msg.startswith("[E009]")
        assert "[E009]" not in err_msg

    def test_readonly_error_code_attribute(self, literal_validator):
        with pytest.raises(ValueError) as exc_info:
            literal_validator.validate_coerce("bogus")

        error_obj = exc_info.value.args[0]
        assert hasattr(error_obj, "error_code")
        assert error_obj.error_code == "E009"


class TestRendererInvalidNameExactFormat:
    def test_invalid_renderer_starts_with_correct_text(self):
        with pytest.raises(ValueError) as exc_info:
            pio.renderers.default = "bogus_renderer_name"

        err_msg = str(exc_info.value.args[0])

        assert err_msg.startswith("\nInvalid named renderer(s) received:")

    def test_invalid_renderer_contains_bogus_name(self):
        with pytest.raises(ValueError) as exc_info:
            pio.renderers.default = "bogus_renderer_name"

        err_msg = str(exc_info.value.args[0])

        assert "bogus_renderer_name" in err_msg

    def test_invalid_renderer_no_error_code_prefix(self):
        with pytest.raises(ValueError) as exc_info:
            pio.renderers.default = "bogus_renderer_name"

        err_msg = str(exc_info.value.args[0])

        assert not err_msg.startswith("[E006]")
        assert "[E006]" not in err_msg[:20]

    def test_invalid_renderer_error_code_attribute(self):
        with pytest.raises(ValueError) as exc_info:
            pio.renderers.default = "bogus_renderer_name"

        error_obj = exc_info.value.args[0]
        assert hasattr(error_obj, "error_code")
        assert error_obj.error_code == "E006"


class TestJsonInvalidEngineExactFormat:
    @pytest.fixture(autouse=True)
    def restore_json_engine(self):
        original_engine = pio.json.config.default_engine
        yield
        pio.json.config.default_engine = original_engine

    def test_invalid_engine_contains_supported_text(self):
        with pytest.raises(ValueError) as exc_info:
            pio.json.config.default_engine = "nonexistent_engine"

        err_msg = str(exc_info.value.args[0])

        assert "Supported JSON engines include" in err_msg

    def test_invalid_engine_no_error_code_prefix(self):
        with pytest.raises(ValueError) as exc_info:
            pio.json.config.default_engine = "nonexistent_engine"

        err_msg = str(exc_info.value.args[0])

        assert not err_msg.startswith("[E007]")

    def test_invalid_engine_error_code_attribute(self):
        with pytest.raises(ValueError) as exc_info:
            pio.json.config.default_engine = "nonexistent_engine"

        error_obj = exc_info.value.args[0]
        assert hasattr(error_obj, "error_code")
        assert error_obj.error_code == "E007"


class TestOrjsonMissingDependencyExactFormat:
    def test_orjson_missing_exact_message(self):
        with mock.patch(
            "plotly.io._json.get_module",
            side_effect=lambda name, *args, **kwargs: (
                None if name == "orjson" else mock.MagicMock()
            ),
        ):
            with pytest.raises(ValueError) as exc_info:
                JsonConfig.validate_orjson()

        err_msg = str(exc_info.value.args[0])

        assert err_msg == "The orjson engine requires the orjson package"

    def test_orjson_missing_no_error_code_prefix(self):
        with mock.patch(
            "plotly.io._json.get_module",
            side_effect=lambda name, *args, **kwargs: (
                None if name == "orjson" else mock.MagicMock()
            ),
        ):
            with pytest.raises(ValueError) as exc_info:
                JsonConfig.validate_orjson()

        err_msg = str(exc_info.value.args[0])

        assert not err_msg.startswith("[E001]")
        assert "[E001]" not in err_msg

    def test_orjson_missing_error_code_attribute(self):
        with mock.patch(
            "plotly.io._json.get_module",
            side_effect=lambda name, *args, **kwargs: (
                None if name == "orjson" else mock.MagicMock()
            ),
        ):
            with pytest.raises(ValueError) as exc_info:
                JsonConfig.validate_orjson()

        error_obj = exc_info.value.args[0]
        assert hasattr(error_obj, "error_code")
        assert error_obj.error_code == "E001"


class TestBackwardCompatSnapshotModeToggle:
    def test_default_mode_lacks_prefix(self, enumerated_validator):
        assert is_snapshot_mode() is False

        with pytest.raises(ValueError) as exc_info:
            enumerated_validator.validate_coerce("bogus")

        err_msg = str(exc_info.value.args[0])
        assert not err_msg.startswith("[E002]")
        assert "[E002]" not in err_msg[:20]

    def test_snapshot_mode_adds_prefix(self, enumerated_validator):
        enable_snapshot_mode()
        assert is_snapshot_mode() is True

        try:
            with pytest.raises(ValueError) as exc_info:
                enumerated_validator.validate_coerce("bogus")

            err_msg = str(exc_info.value.args[0])
            assert err_msg.startswith("[E002]")
            assert "Invalid value of type" in err_msg
        finally:
            disable_snapshot_mode()

    def test_disable_snapshot_removes_prefix_again(self, enumerated_validator):
        enable_snapshot_mode()
        disable_snapshot_mode()
        assert is_snapshot_mode() is False

        with pytest.raises(ValueError) as exc_info:
            enumerated_validator.validate_coerce("bogus")

        err_msg = str(exc_info.value.args[0])
        assert not err_msg.startswith("[E002]")
        assert "[E002]" not in err_msg[:20]

    def test_snapshot_mode_renderer_error(self):
        enable_snapshot_mode()
        try:
            with pytest.raises(ValueError) as exc_info:
                pio.renderers.default = "bogus_renderer"

            err_msg = str(exc_info.value.args[0])
            assert err_msg.startswith("[E006]")
        finally:
            disable_snapshot_mode()

    def test_snapshot_mode_orjson_error(self):
        enable_snapshot_mode()
        try:
            with mock.patch(
                "plotly.io._json.get_module",
                side_effect=lambda name, *args, **kwargs: (
                    None if name == "orjson" else mock.MagicMock()
                ),
            ):
                with pytest.raises(ValueError) as exc_info:
                    JsonConfig.validate_orjson()

            err_msg = str(exc_info.value.args[0])
            assert err_msg.startswith("[E001]")
            assert "pip install orjson" in err_msg
        finally:
            disable_snapshot_mode()

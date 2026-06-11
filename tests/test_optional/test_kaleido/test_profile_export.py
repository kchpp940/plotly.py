import pytest
from unittest.mock import patch

import plotly.graph_objects as go
import plotly.io as pio
from plotly.io._defaults import defaults, _VALID_PROFILE_KEYS
from plotly.io._utils import resolve_export_kwargs


fig = {"data": [], "layout": {"title": {"text": "figure title"}}}


class TestResolveExportKwargs:
    def test_no_profile_no_explicit_returns_none(self):
        result = resolve_export_kwargs()
        assert result["format"] is None
        assert result["width"] is None
        assert result["height"] is None
        assert result["scale"] is None
        assert result["validate"] is None
        assert result["engine"] is None

    def test_profile_overrides_none(self):
        result = resolve_export_kwargs(profile="web")
        assert result["format"] == "png"
        assert result["width"] == 800
        assert result["height"] == 600
        assert result["scale"] == 1

    def test_explicit_overrides_profile(self):
        result = resolve_export_kwargs(profile="web", width=1200, format="svg")
        assert result["width"] == 1200
        assert result["format"] == "svg"
        assert result["height"] == 600  # from profile

    def test_print_profile(self):
        result = resolve_export_kwargs(profile="print")
        assert result["format"] == "pdf"
        assert result["scale"] == 2

    def test_retina_profile(self):
        result = resolve_export_kwargs(profile="retina")
        assert result["format"] == "png"
        assert result["scale"] == 2

    def test_thumbnail_profile(self):
        result = resolve_export_kwargs(profile="thumbnail")
        assert result["width"] == 200
        assert result["height"] == 150


class TestGetProfile:
    def test_valid_profile(self):
        profile = defaults.get_profile("web")
        assert profile["format"] == "png"
        assert profile["width"] == 800

    def test_invalid_profile_raises(self):
        with pytest.raises(ValueError, match="not found"):
            defaults.get_profile("nonexistent")

    def test_non_string_profile_name_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            defaults.get_profile(123)

    def test_profile_returns_copy(self):
        p1 = defaults.get_profile("web")
        p1["width"] = 9999
        p2 = defaults.get_profile("web")
        assert p2["width"] != 9999


class TestProfilesConfig:
    def test_builtin_profiles_exist(self):
        assert "web" in defaults.profiles
        assert "print" in defaults.profiles
        assert "retina" in defaults.profiles
        assert "thumbnail" in defaults.profiles

    def test_add_custom_profile(self):
        defaults.profiles["custom_test"] = {"format": "svg", "width": 400, "height": 300}
        profile = defaults.get_profile("custom_test")
        assert profile["format"] == "svg"
        assert profile["width"] == 400
        del defaults.profiles["custom_test"]

    def test_profile_with_invalid_keys_raises(self):
        defaults.profiles["bad_profile"] = {"format": "png", "invalid_key": 42}
        with pytest.raises(ValueError, match="invalid keys"):
            defaults.get_profile("bad_profile")
        del defaults.profiles["bad_profile"]

    def test_valid_profile_keys(self):
        assert _VALID_PROFILE_KEYS == {"format", "width", "height", "scale", "validate", "engine"}

    def test_profile_with_validate_key(self):
        defaults.profiles["no_validate"] = {"validate": False, "format": "svg"}
        result = resolve_export_kwargs(profile="no_validate")
        assert result["validate"] is False
        assert result["format"] == "svg"
        del defaults.profiles["no_validate"]

    def test_explicit_validate_overrides_profile(self):
        defaults.profiles["no_validate"] = {"validate": False}
        result = resolve_export_kwargs(profile="no_validate", validate=True)
        assert result["validate"] is True
        del defaults.profiles["no_validate"]


class TestToImageWithProfile:
    def test_to_image_with_profile(self):
        test_fig = go.Figure(fig)
        test_image_bytes = b"mock image data"

        with patch(
            "plotly.io._kaleido.kaleido.calc_fig_sync",
            return_value=test_image_bytes,
        ) as mock_calc:
            pio.to_image(test_fig, profile="retina", validate=False)
            mock_calc.assert_called_once()
            _, kwargs = mock_calc.call_args
            assert kwargs["opts"]["scale"] == 2

    def test_to_image_explicit_overrides_profile(self):
        test_fig = go.Figure(fig)
        test_image_bytes = b"mock image data"

        with patch(
            "plotly.io._kaleido.kaleido.calc_fig_sync",
            return_value=test_image_bytes,
        ) as mock_calc:
            pio.to_image(test_fig, profile="retina", scale=3, validate=False)
            mock_calc.assert_called_once()
            _, kwargs = mock_calc.call_args
            assert kwargs["opts"]["scale"] == 3

    def test_to_image_invalid_profile_raises(self):
        test_fig = go.Figure(fig)
        with pytest.raises(ValueError, match="not found"):
            pio.to_image(test_fig, profile="nonexistent", validate=False)

    def test_to_image_profile_format(self):
        test_fig = go.Figure(fig)
        test_image_bytes = b"mock image data"

        with patch(
            "plotly.io._kaleido.kaleido.calc_fig_sync",
            return_value=test_image_bytes,
        ) as mock_calc:
            pio.to_image(test_fig, profile="print", validate=False)
            mock_calc.assert_called_once()
            _, kwargs = mock_calc.call_args
            assert kwargs["opts"]["format"] == "pdf"


class TestWriteImageWithProfile:
    def test_write_image_passes_profile(self):
        test_fig = go.Figure(fig)
        test_image_bytes = b"mock image data"

        with patch(
            "plotly.io._kaleido.to_image",
            return_value=test_image_bytes,
        ) as mock_to_image, patch("pathlib.Path.write_bytes"):
            pio.write_image(test_fig, "test.png", profile="retina", validate=False)
            mock_to_image.assert_called_once()
            call_kwargs = mock_to_image.call_args[1]
            assert call_kwargs["profile"] == "retina"


class TestFigMethods:
    def test_fig_to_image_with_profile(self):
        test_fig = go.Figure(fig)
        test_image_bytes = b"mock image data"

        with patch(
            "plotly.io._kaleido.kaleido.calc_fig_sync",
            return_value=test_image_bytes,
        ) as mock_calc:
            test_fig.to_image(profile="thumbnail", validate=False)
            mock_calc.assert_called_once()
            _, kwargs = mock_calc.call_args
            assert kwargs["opts"]["width"] == 200
            assert kwargs["opts"]["height"] == 150

    def test_fig_write_image_with_profile(self):
        test_fig = go.Figure(fig)
        test_image_bytes = b"mock image data"

        with patch(
            "plotly.io._kaleido.to_image",
            return_value=test_image_bytes,
        ) as mock_to_image, patch("pathlib.Path.write_bytes"):
            test_fig.write_image("test.png", profile="print", validate=False)
            mock_to_image.assert_called_once()
            call_kwargs = mock_to_image.call_args[1]
            assert call_kwargs["profile"] == "print"

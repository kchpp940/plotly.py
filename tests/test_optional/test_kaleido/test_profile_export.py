import pytest
from unittest.mock import patch
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
from plotly.io._defaults import defaults, _VALID_PROFILE_KEYS
from plotly.io._utils import ImageExportOptions


fig = {"data": [], "layout": {"title": {"text": "figure title"}}}


class TestImageExportOptions:
    def test_no_profile_no_explicit_uses_defaults(self):
        opts = ImageExportOptions(fig=fig).resolve()
        assert opts.format == defaults.default_format
        assert opts.width == defaults.default_width
        assert opts.height == defaults.default_height
        assert opts.scale == defaults.default_scale
        assert opts.validate is True
        assert opts.engine == "auto"

    def test_profile_applies_values(self):
        opts = ImageExportOptions(fig=fig, profile="web").resolve()
        assert opts.format == "png"
        assert opts.width == 800
        assert opts.height == 600
        assert opts.scale == 1

    def test_explicit_overrides_profile(self):
        opts = ImageExportOptions(fig=fig, profile="web", width=1200, format="svg").resolve()
        assert opts.width == 1200
        assert opts.format == "svg"
        assert opts.height == 600  # from profile

    def test_print_profile(self):
        opts = ImageExportOptions(fig=fig, profile="print").resolve()
        assert opts.format == "pdf"
        assert opts.scale == 2

    def test_retina_profile(self):
        opts = ImageExportOptions(fig=fig, profile="retina").resolve()
        assert opts.format == "png"
        assert opts.scale == 2

    def test_thumbnail_profile(self):
        opts = ImageExportOptions(fig=fig, profile="thumbnail").resolve()
        assert opts.width == 200
        assert opts.height == 150

    def test_layout_width_height_overrides_defaults(self):
        fig_with_size = {
            "data": [],
            "layout": {"width": 800, "height": 600},
        }
        opts = ImageExportOptions(fig=fig_with_size).resolve()
        assert opts.width == 800
        assert opts.height == 600

    def test_layout_width_height_overrides_profile(self):
        fig_with_size = {
            "data": [],
            "layout": {"width": 999, "height": 888},
        }
        opts = ImageExportOptions(fig=fig_with_size, profile="web").resolve()
        # profile.width=800 should win over layout.width=999? Let's check priority.
        # ImageExportOptions priority: explicit > profile > layout > template > defaults
        # So profile should override layout.
        assert opts.width == 800
        assert opts.height == 600

    def test_explicit_overrides_layout(self):
        fig_with_size = {
            "data": [],
            "layout": {"width": 800, "height": 600},
        }
        opts = ImageExportOptions(fig=fig_with_size, width=1000).resolve()
        assert opts.width == 1000

    def test_format_inference_from_file_extension(self):
        opts = ImageExportOptions(fig=fig, file="out.svg").resolve()
        assert opts.format == "svg"

    def test_explicit_format_overrides_file_extension(self):
        opts = ImageExportOptions(fig=fig, file="out.png", format="svg").resolve()
        assert opts.format == "svg"

    def test_profile_format_overrides_default_but_not_file_extension(self):
        # profile says pdf, but file has .svg extension
        opts = ImageExportOptions(fig=fig, profile="print", file="out.svg").resolve()
        # file extension wins over profile format
        assert opts.format == "svg"

    def test_path_set_from_file(self):
        opts = ImageExportOptions(fig=fig, file="dir/out.png").resolve()
        assert opts.path == Path("dir/out.png")

    def test_opts_property(self):
        opts = ImageExportOptions(fig=fig, profile="retina").resolve()
        assert opts.opts == dict(
            format="png",
            width=700,
            height=500,
            scale=2,
        )

    def test_fig_dict_coerced(self):
        opts = ImageExportOptions(fig=go.Figure(fig), validate=False).resolve()
        assert isinstance(opts.fig_dict, dict)
        assert "layout" in opts.fig_dict

    def test_invalid_profile_name_raises(self):
        with pytest.raises(ValueError, match="not found"):
            ImageExportOptions(fig=fig, profile="nonexistent").resolve()


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
        opts = ImageExportOptions(fig=fig, profile="no_validate").resolve()
        assert opts.validate is False
        assert opts.format == "svg"
        del defaults.profiles["no_validate"]

    def test_explicit_validate_overrides_profile(self):
        defaults.profiles["no_validate"] = {"validate": False}
        opts = ImageExportOptions(fig=fig, profile="no_validate", validate=True).resolve()
        assert opts.validate is True
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


class TestWriteImagesWithProfile:
    def test_write_images_with_single_profile(self):
        test_fig = go.Figure(fig)
        test_image_bytes = b"mock"

        with patch(
            "plotly.io._kaleido.kaleido.write_fig_from_object_sync",
            return_value=None,
        ) as mock_write:
            pio.write_images(
                [test_fig, test_fig],
                ["a.png", "b.png"],
                profile="retina",
            )
            mock_write.assert_called_once()
            args, _ = mock_write.call_args
            specs = args[0]
            for spec in specs:
                assert spec["opts"]["scale"] == 2

    def test_write_images_with_mixed_profiles(self):
        test_fig = go.Figure(fig)

        with patch(
            "plotly.io._kaleido.kaleido.write_fig_from_object_sync",
            return_value=None,
        ) as mock_write:
            pio.write_images(
                [test_fig, test_fig],
                ["a.png", "b.png"],
                profile=["retina", "thumbnail"],
            )
            mock_write.assert_called_once()
            args, _ = mock_write.call_args
            specs = args[0]
            assert specs[0]["opts"]["scale"] == 2
            assert specs[0]["opts"]["width"] == 700
            assert specs[1]["opts"]["width"] == 200
            assert specs[1]["opts"]["height"] == 150

    def test_write_images_explicit_overrides_profile(self):
        test_fig = go.Figure(fig)

        with patch(
            "plotly.io._kaleido.kaleido.write_fig_from_object_sync",
            return_value=None,
        ) as mock_write:
            pio.write_images(
                [test_fig, test_fig],
                ["a.png", "b.png"],
                profile=["retina", "thumbnail"],
                scale=5,
            )
            mock_write.assert_called_once()
            args, _ = mock_write.call_args
            specs = args[0]
            # explicit scale=5 overrides both profiles
            assert specs[0]["opts"]["scale"] == 5
            assert specs[1]["opts"]["scale"] == 5

    def test_write_images_format_from_extension(self):
        test_fig = go.Figure(fig)

        with patch(
            "plotly.io._kaleido.kaleido.write_fig_from_object_sync",
            return_value=None,
        ) as mock_write:
            pio.write_images(
                [test_fig, test_fig],
                ["a.svg", "b.pdf"],
                validate=False,
            )
            mock_write.assert_called_once()
            args, _ = mock_write.call_args
            specs = args[0]
            assert specs[0]["opts"]["format"] == "svg"
            assert specs[1]["opts"]["format"] == "pdf"

    def test_write_images_invalid_profile_raises(self):
        test_fig = go.Figure(fig)
        with pytest.raises(ValueError, match="not found"):
            pio.write_images(
                [test_fig],
                ["a.png"],
                profile="nonexistent",
            )

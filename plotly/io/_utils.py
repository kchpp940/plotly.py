from pathlib import Path
from typing import List, Union

import plotly
import plotly.graph_objs as go
from plotly.offline import get_plotlyjs_version


def as_path_object(file: Union[str, Path]) -> Union[Path, None]:
    if isinstance(file, str):
        return Path(file)
    elif isinstance(file, Path):
        return file
    return None


def infer_format(path: Union[Path, None], format: Union[str, None]) -> Union[str, None]:
    if path is not None and format is None:
        ext = path.suffix
        if ext:
            format = ext.lstrip(".")
        else:
            raise ValueError(
                f"""
Cannot infer image type from output path '{path}'.
Please specify the type using the format parameter, or add a file extension.
For example:

    >>> import plotly.io as pio
    >>> pio.write_image(fig, file_path, format='png')
"""
            )
    return format


class ImageExportOptions:
    """
    Unified resolver for image export parameters.

    Resolution priority (highest first):
      1. Explicit parameter (format/width/height/scale/validate/engine)
      2. Named profile value (from plotly.io.defaults.profiles)
      3. File extension inference (for format, only if file is provided)
      4. Figure layout.width / layout.height (from fig_dict)
      5. Figure template.layout.width / template.layout.height (from fig_dict)
      6. Global defaults (plotly.io.defaults.default_*)
    """

    def __init__(
        self,
        fig,
        format=None,
        width=None,
        height=None,
        scale=None,
        validate=None,
        engine=None,
        profile=None,
        file=None,
    ):
        self.fig = fig
        self._format = format
        self._width = width
        self._height = height
        self._scale = scale
        self._validate = validate
        self._engine = engine
        self._profile = profile
        self._file = file

        self._fig_dict = None
        self._path = None
        self._resolved = False

    def resolve(self):
        if self._resolved:
            return self
        from plotly.io._defaults import defaults

        # 3. format inference from file extension: extension > profile > defaults
        # but explicit format (self._format) wins over everything
        fmt = self._format
        if self._file is not None:
            self._path = as_path_object(self._file)
            # infer_format only modifies fmt if it's None
            if fmt is None:
                fmt = infer_format(self._path, fmt)

        # 1. + 2. profile + explicit args (for everything except format where extension was handled)
        if self._profile is not None:
            profile_dict = defaults.get_profile(self._profile)
        else:
            profile_dict = {}

        # For format: explicit > extension > profile > defaults
        # fmt already has explicit or extension. If still None, check profile.
        if fmt is None:
            fmt = profile_dict.get("format")

        width = self._width if self._width is not None else profile_dict.get("width")
        height = self._height if self._height is not None else profile_dict.get("height")
        scale = self._scale if self._scale is not None else profile_dict.get("scale")
        # For validate: explicit (non-None) > profile > True
        validate = self._validate if self._validate is not None else profile_dict.get("validate")
        if validate is None:
            validate = True
        # For engine: explicit (non-None) > profile > "auto"
        engine = self._engine if self._engine is not None else profile_dict.get("engine")
        if engine is None:
            engine = "auto"

        # fig_dict (with validation)
        self._fig_dict = validate_coerce_fig_to_dict(self.fig, validate)

        # 4. + 5. + 6. width: explicit > profile > layout > template.layout > defaults
        if width is None:
            width = (
                self._fig_dict.get("layout", {}).get("width")
                or self._fig_dict.get("layout", {})
                .get("template", {})
                .get("layout", {})
                .get("width")
                or defaults.default_width
            )
        # same for height
        if height is None:
            height = (
                self._fig_dict.get("layout", {}).get("height")
                or self._fig_dict.get("layout", {})
                .get("template", {})
                .get("layout", {})
                .get("height")
                or defaults.default_height
            )
        # format/scale own defaults
        if fmt is None:
            fmt = defaults.default_format
        if scale is None:
            scale = defaults.default_scale

        self.format = fmt
        self.width = width
        self.height = height
        self.scale = scale
        self.validate = validate
        self.engine = engine
        self.path = self._path
        self.fig_dict = self._fig_dict
        self._resolved = True
        return self

    @property
    def opts(self):
        self.resolve()
        return dict(
            format=self.format,
            width=self.width,
            height=self.height,
            scale=self.scale,
        )


def validate_coerce_fig_to_dict(fig, validate):
    from plotly.basedatatypes import BaseFigure

    if isinstance(fig, BaseFigure):
        fig_dict = fig.to_dict()
    elif isinstance(fig, dict):
        if validate:
            # This will raise an exception if fig is not a valid plotly figure
            fig_dict = plotly.graph_objs.Figure(fig).to_plotly_json()
        else:
            fig_dict = fig
    elif hasattr(fig, "to_plotly_json"):
        fig_dict = fig.to_plotly_json()
    else:
        raise ValueError(
            """
The fig parameter must be a dict or Figure.
    Received value of type {typ}: {v}""".format(typ=type(fig), v=fig)
        )
    return fig_dict


def validate_coerce_output_type(output_type):
    if output_type == "Figure" or output_type == go.Figure:
        cls = go.Figure
    elif output_type == "FigureWidget" or (
        hasattr(go, "FigureWidget") and output_type == go.FigureWidget
    ):
        cls = go.FigureWidget
    else:
        raise ValueError(
            """
Invalid output type: {output_type}
    Must be one of: 'Figure', 'FigureWidget'"""
        )
    return cls


def broadcast_args_to_dicts(**kwargs: dict) -> List[dict]:
    """
    Given one or more keyword arguments which may be either a single value or a list of values,
    return a list of keyword dictionaries by broadcasting the single valuesacross all the dicts.
    If more than one item in the input is a list, all lists must be the same length.

    Parameters
    ----------
    **kwargs: dict
        The keyword arguments

    Returns
    -------
    list of dicts
        A list of dictionaries

    Raises
    ------
    ValueError
        If any of the input lists are not the same length
    """
    # Check that all list arguments have the same length,
    # and find out what that length is
    # If there are no list arguments, length is 1
    list_lengths = [len(v) for v in tuple(kwargs.values()) if isinstance(v, list)]
    if list_lengths and len(set(list_lengths)) > 1:
        raise ValueError("All list arguments must have the same length.")
    list_length = list_lengths[0] if list_lengths else 1

    # Expand all arguments to lists of the same length
    expanded_kwargs = {
        k: [v] * list_length if not isinstance(v, list) else v
        for k, v in kwargs.items()
    }
    # Reshape into a list of dictionaries
    # Each dictionary represents the keyword arguments for a single function call
    list_of_kwargs = [
        {k: v[i] for k, v in expanded_kwargs.items()} for i in range(list_length)
    ]

    return list_of_kwargs


def plotly_cdn_url(cdn_ver=get_plotlyjs_version()):
    """Return a valid plotly CDN url."""
    return "https://cdn.plot.ly/plotly-{cdn_ver}.min.js".format(
        cdn_ver=cdn_ver,
    )

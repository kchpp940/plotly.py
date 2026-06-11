from typing import List

import plotly
import plotly.graph_objs as go
from plotly.offline import get_plotlyjs_version


def resolve_export_kwargs(
    profile=None,
    format=None,
    width=None,
    height=None,
    scale=None,
    validate=None,
    engine=None,
):
    from plotly.io._defaults import defaults

    if profile is not None:
        profile_dict = defaults.get_profile(profile)
    else:
        profile_dict = {}

    resolved_format = format if format is not None else profile_dict.get("format")
    resolved_width = width if width is not None else profile_dict.get("width")
    resolved_height = height if height is not None else profile_dict.get("height")
    resolved_scale = scale if scale is not None else profile_dict.get("scale")
    resolved_validate = validate if validate is not None else profile_dict.get("validate")
    resolved_engine = engine if engine is not None else profile_dict.get("engine")

    return dict(
        format=resolved_format,
        width=resolved_width,
        height=resolved_height,
        scale=resolved_scale,
        validate=resolved_validate,
        engine=resolved_engine,
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

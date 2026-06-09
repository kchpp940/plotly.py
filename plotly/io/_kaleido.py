import os
import json
from pathlib import Path
from typing import Union, List, NamedTuple, Optional
import importlib.metadata as importlib_metadata
from packaging.version import Version
import warnings

import plotly
from plotly.io._utils import (
    validate_coerce_fig_to_dict,
    broadcast_args_to_dicts,
    validate_coerce_format,
)
from plotly.io._defaults import defaults

ENGINE_SUPPORT_TIMELINE = "September 2025"
ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS = True

PLOTLY_GET_CHROME_ERROR_MSG = """

Kaleido requires Google Chrome to be installed.

Either download and install Chrome yourself following Google's instructions for your operating system,
or install it from your terminal by running:

    $ plotly_get_chrome

"""

KALEIDO_DEPRECATION_MSG = f"""
Support for Kaleido versions less than 1.0.0 is deprecated and will be removed after {ENGINE_SUPPORT_TIMELINE}.
Please upgrade Kaleido to version 1.0.0 or greater (`pip install 'kaleido>=1.0.0'` or `pip install 'plotly[kaleido]'`).
"""
ORCA_DEPRECATION_MSG = f"""
Support for the Orca engine is deprecated and will be removed after {ENGINE_SUPPORT_TIMELINE}.
Please install Kaleido (`pip install 'kaleido>=1.0.0'` or `pip install 'plotly[kaleido]'`) to use the Kaleido engine.
"""
ENGINE_PARAM_DEPRECATION_MSG = f"""
Support for the 'engine' argument is deprecated and will be removed after {ENGINE_SUPPORT_TIMELINE}.
Kaleido will be the only supported engine at that time.
"""

_KALEIDO_AVAILABLE = None
_KALEIDO_MAJOR = None


def kaleido_scope_default_warning_func(x):
    return f"""
Use of plotly.io.kaleido.scope.{x} is deprecated and support will be removed after {ENGINE_SUPPORT_TIMELINE}.
Please use plotly.io.defaults.{x} instead.
"""


def bad_attribute_error_msg_func(x):
    return f"""
Attribute plotly.io.defaults.{x} is not valid.
Also, use of plotly.io.kaleido.scope.* is deprecated and support will be removed after {ENGINE_SUPPORT_TIMELINE}.
Please use plotly.io.defaults.* instead.
"""


def kaleido_available() -> bool:
    """
    Returns True if any version of Kaleido is installed, otherwise False.
    """
    global _KALEIDO_AVAILABLE
    global _KALEIDO_MAJOR
    if _KALEIDO_AVAILABLE is not None:
        return _KALEIDO_AVAILABLE
    try:
        import kaleido  # noqa: F401

        _KALEIDO_AVAILABLE = True
    except ImportError:
        _KALEIDO_AVAILABLE = False
    return _KALEIDO_AVAILABLE


def kaleido_major() -> int:
    """
    Returns the major version number of Kaleido if it is installed,
    otherwise raises a ValueError.
    """
    global _KALEIDO_MAJOR
    if _KALEIDO_MAJOR is not None:
        return _KALEIDO_MAJOR
    if not kaleido_available():
        raise ValueError("Kaleido is not installed.")
    else:
        _KALEIDO_MAJOR = Version(importlib_metadata.version("kaleido")).major
    return _KALEIDO_MAJOR


KALEIDO_NOT_INSTALLED_MSG = """
The Kaleido package is required for this operation,
which can be installed using pip:

    $ pip install --upgrade kaleido
"""

KALEIDO_V1_REQUIRED_MSG = """
This operation requires Kaleido version 1.0.0 or greater.
Install it using `pip install 'kaleido>=1.0.0'` or `pip install 'plotly[kaleido]'`.
"""


def _require_kaleido(operation: str = "This operation") -> None:
    """
    Check that Kaleido is installed, raising a unified ValueError if not.

    Parameters
    ----------
    operation: str
        A short description of the operation being performed, used in the error message.
    """
    if not kaleido_available():
        raise ValueError(
            f"""
{operation} requires the Kaleido package,
which can be installed using pip:

    $ pip install --upgrade kaleido
"""
        )


def _require_kaleido_v1(operation: str = "This operation") -> None:
    """
    Check that Kaleido v1.0.0+ is installed, raising a unified ValueError if not.

    Parameters
    ----------
    operation: str
        A short description of the operation being performed, used in the error message.
    """
    if not kaleido_available():
        raise ValueError(
            f"""
{operation} requires the Kaleido package,
which can be installed using pip:

    $ pip install --upgrade kaleido
"""
        )
    if kaleido_major() < 1:
        raise ValueError(
            f"""
{operation} requires Kaleido version 1.0.0 or greater.
Install it using `pip install 'kaleido>=1.0.0'` or `pip install 'plotly[kaleido]'`.
"""
        )


try:
    if kaleido_available() and kaleido_major() < 1:
        # Kaleido v0
        import kaleido
        from kaleido.scopes.plotly import PlotlyScope

        # Show a deprecation warning if the old method of setting defaults is used
        class PlotlyScopeWrapper(PlotlyScope):
            def __setattr__(self, name, value):
                if name in defaults.__dict__:
                    if ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
                        warnings.warn(
                            kaleido_scope_default_warning_func(name),
                            DeprecationWarning,
                            stacklevel=2,
                        )
                super().__setattr__(name, value)

            def __getattr__(self, name):
                if hasattr(defaults, name):
                    if ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
                        warnings.warn(
                            kaleido_scope_default_warning_func(name),
                            DeprecationWarning,
                            stacklevel=2,
                        )
                return super().__getattr__(name)

        # Ensure the new method of setting defaults is backwards compatible with Kaleido v0
        # DefaultsBackwardsCompatible sets the attributes on `scope` object at the same time
        # as they are set on the `defaults` object
        class DefaultsBackwardsCompatible(defaults.__class__):
            def __init__(self, scope):
                self._scope = scope
                super().__init__()

            def __setattr__(self, name, value):
                if not name == "_scope":
                    if (
                        hasattr(self._scope, name)
                        and getattr(self._scope, name) != value
                    ):
                        setattr(self._scope, name, value)
                super().__setattr__(name, value)

        scope = PlotlyScopeWrapper()
        defaults = DefaultsBackwardsCompatible(scope)
        # Compute absolute path to the 'plotly/package_data/' directory
        root_dir = os.path.dirname(os.path.abspath(plotly.__file__))
        package_dir = os.path.join(root_dir, "package_data")
        scope.plotlyjs = os.path.join(package_dir, "plotly.min.js")
        if scope.mathjax is None:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", message=r".*scope\.mathjax.*", category=DeprecationWarning
                )
                scope.mathjax = (
                    "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js"
                )
    else:
        # Kaleido v1
        import kaleido

        # Show a deprecation warning if the old method of setting defaults is used
        class DefaultsWrapper:
            def __getattr__(self, name):
                if hasattr(defaults, name):
                    if ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
                        warnings.warn(
                            kaleido_scope_default_warning_func(name),
                            DeprecationWarning,
                            stacklevel=2,
                        )
                    return getattr(defaults, name)
                else:
                    raise AttributeError(bad_attribute_error_msg_func(name))

            def __setattr__(self, name, value):
                if hasattr(defaults, name):
                    if ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
                        warnings.warn(
                            kaleido_scope_default_warning_func(name),
                            DeprecationWarning,
                            stacklevel=2,
                        )
                    setattr(defaults, name, value)
                else:
                    raise AttributeError(bad_attribute_error_msg_func(name))

        scope = DefaultsWrapper()

except ImportError:
    PlotlyScope = None
    scope = None


def _validate_engine_param(engine: Union[str, None]) -> str:
    """
    Stage 1: Validate and normalize the engine parameter WITHOUT checking
    external dependencies or emitting warnings. This ensures pure argument
    validation errors surface before any dependency checks.

    Parameters
    ----------
    engine: str or None
        The engine argument passed by the user

    Returns
    -------
    str
        Normalized engine name: 'auto', 'kaleido', or 'orca'

    Raises
    ------
    ValueError
        If the engine value is not in the allowed set.
    """
    if engine is None:
        return "auto"

    if not isinstance(engine, str) or engine not in {"auto", "kaleido", "orca"}:
        raise ValueError(f"Invalid image export engine specified: {repr(engine)}")

    return engine


def _resolve_engine_and_warn(
    engine: str, original_engine: Union[str, None], stacklevel: int = 2
) -> str:
    """
    Stage 2: Resolve 'auto' to a concrete engine and emit all deprecation
    warnings. This should be called AFTER format and other pure argument
    validation has completed.

    Parameters
    ----------
    engine: str
        Normalized engine name from _validate_engine_param
    original_engine: str or None
        The original engine argument as passed by the user (before normalization),
        used to determine if the engine parameter was explicitly provided.
    stacklevel: int
        Stack level for warnings (passed through to warnings.warn)

    Returns
    -------
    str
        The resolved concrete engine name: 'kaleido' or 'orca'
    """
    if original_engine is not None and ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
        warnings.warn(
            ENGINE_PARAM_DEPRECATION_MSG, DeprecationWarning, stacklevel=stacklevel
        )

    if engine == "auto":
        if kaleido_available():
            engine = "kaleido"
        else:
            from ._orca import validate_executable

            try:
                validate_executable()
                engine = "orca"
            except Exception:
                engine = "kaleido"

    if engine == "orca" and ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
        warnings.warn(ORCA_DEPRECATION_MSG, DeprecationWarning, stacklevel=stacklevel)

    if (
        engine == "kaleido"
        and kaleido_available()
        and kaleido_major() < 1
        and ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS
    ):
        warnings.warn(KALEIDO_DEPRECATION_MSG, DeprecationWarning, stacklevel=stacklevel)

    return engine


def _resolve_image_defaults(
    fig_dict: dict,
    format: Union[str, None],
    width: Union[int, None],
    height: Union[int, None],
    scale: Union[int, float, None],
) -> tuple:
    """
    Apply default values for image export parameters in a unified way.

    Parameters
    ----------
    fig_dict: dict
        The figure dictionary (used for layout width/height fallback)
    format: str or None
    width: int or None
    height: int or None
    scale: int, float, or None

    Returns
    -------
    tuple
        (format, width, height, scale) with all defaults applied
    """
    format = validate_coerce_format(format)
    if format is None:
        format = defaults.default_format

    width = (
        width
        or fig_dict.get("layout", {}).get("width")
        or fig_dict.get("layout", {})
        .get("template", {})
        .get("layout", {})
        .get("width")
        or defaults.default_width
    )
    height = (
        height
        or fig_dict.get("layout", {}).get("height")
        or fig_dict.get("layout", {})
        .get("template", {})
        .get("layout", {})
        .get("height")
        or defaults.default_height
    )
    if scale is None:
        scale = defaults.default_scale

    return format, width, height, scale


def as_path_object(file: Union[str, Path]) -> Union[Path, None]:
    """
    Cast the `file` argument, which may be either a string or a Path object,
    to a Path object.
    If `file` is neither a string nor a Path object, None will be returned.
    """
    if isinstance(file, str):
        # Use the standard Path constructor to make a pathlib object.
        path = Path(file)
    elif isinstance(file, Path):
        # `file` is already a Path object.
        path = file
    else:
        # We could not make a Path object out of file. Either `file` is an open file
        # descriptor with a `write()` method or it's an invalid object.
        path = None
    return path


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
    return validate_coerce_format(format)


def resolve_format(
    path: Union[Path, None] = None, format: Union[str, None] = None
) -> str:
    """
    Fully resolve and validate the image format in a unified order, BEFORE
    any engine warnings or dependency checks are emitted.

    Resolution order (each step is validated via validate_coerce_format):
      1. Explicit `format` argument if provided
      2. File extension inference from `path` if available and format is None
      3. Fallback to defaults.default_format

    Parameters
    ----------
    path: Path or None
        Optional output file path, used for extension inference.
    format: str or None
        Explicit format argument.

    Returns
    -------
    str
        The fully resolved, validated, and normalized format string
        (e.g. 'jpeg', not 'jpg' or '.JPG').

    Raises
    ------
    ValueError
        If any step of the resolution produces an invalid format value,
        including if defaults.default_format is misconfigured.
    """
    if format is not None or (path is not None and path.suffix):
        return infer_format(path, format)

    try:
        fmt = validate_coerce_format(defaults.default_format)
    except ValueError as e:
        raise ValueError(
            f"""
Invalid default image format configured in plotly.io.defaults.default_format: {repr(defaults.default_format)}.
Please set it to one of the supported formats: 'png', 'jpeg', 'jpg', 'webp', 'svg', 'pdf', 'eps'.
"""
        ) from e

    if fmt is None:
        raise ValueError(
            f"""
Invalid default image format configured in plotly.io.defaults.default_format: {repr(defaults.default_format)}.
Please set it to one of the supported formats: 'png', 'jpeg', 'jpg', 'webp', 'svg', 'pdf', 'eps'.
"""
        )
    return fmt


class ImageExportOptions(NamedTuple):
    """
    Container for fully or partially resolved image export options.
    This is passed between write_image -> to_image and write_images to
    avoid duplicate parsing, validation, and warnings.

    Fields:
        format:  Always resolved and validated (never None).
        width:   May be None if fig_dict was not available during resolution;
                 layout/template fallback happens later in to_image.
        height:  Same as width.
        scale:   May be None; default applied in _resolve_image_defaults.
    """
    format: str
    width: Optional[int] = None
    height: Optional[int] = None
    scale: Optional[Union[int, float]] = None


def resolve_export_options(
    fig_dict: Optional[dict],
    path: Optional[Path] = None,
    format: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale: Optional[Union[int, float]] = None,
) -> ImageExportOptions:
    """
    Resolve image export options into an ImageExportOptions object.

    Resolution is done in two layers:
      1. format: Always fully resolved (explicit arg -> extension -> default_format)
         and validated. This happens BEFORE any engine warnings or dependency checks.
      2. width/height/scale: If fig_dict is provided, layout/template fallback is
         applied now; otherwise values are preserved as-is and resolved later.

    Parameters
    ----------
    fig_dict: dict or None
        The figure dictionary for layout/template fallback. None if not yet available.
    path: Path or None
        Optional output path for extension inference.
    format: str or None
        Explicit format argument.
    width: int or None
    height: int or None
    scale: int, float, or None

    Returns
    -------
    ImageExportOptions
        Resolved options object. format is always a validated string.
    """
    fmt = resolve_format(path, format)

    if fig_dict is not None:
        _, resolved_width, resolved_height, resolved_scale = _resolve_image_defaults(
            fig_dict, fmt, width, height, scale
        )
        return ImageExportOptions(
            format=fmt,
            width=resolved_width,
            height=resolved_height,
            scale=resolved_scale,
        )

    return ImageExportOptions(
        format=fmt,
        width=width,
        height=height,
        scale=scale,
    )


def to_image(
    fig: Union[dict, plotly.graph_objects.Figure],
    format: Union[str, None] = None,
    width: Union[int, None] = None,
    height: Union[int, None] = None,
    scale: Union[int, float, None] = None,
    validate: bool = True,
    # Deprecated
    engine: Union[str, None] = None,
    # Internal: pre-resolved options to avoid duplicate parsing
    _options: Optional[ImageExportOptions] = None,
) -> bytes:
    """
    Convert a figure to a static image bytes string

    Parameters
    ----------
    fig:
        Figure object or dict representing a figure

    format: str or None
        The desired image format. One of
            - 'png'
            - 'jpg' or 'jpeg'
            - 'webp'
            - 'svg'
            - 'pdf'
            - 'eps' (deprecated) (Requires the poppler library to be installed and on the PATH)

        If not specified, will default to:
            - `plotly.io.defaults.default_format` if engine is "kaleido"
            - `plotly.io.orca.config.default_format` if engine is "orca" (deprecated)

    width: int or None
        The width of the exported image in layout pixels. If the `scale`
        property is 1.0, this will also be the width of the exported image
        in physical pixels.

        If not specified, will default to:
            - `plotly.io.defaults.default_width` if engine is "kaleido"
            - `plotly.io.orca.config.default_width` if engine is "orca" (deprecated)

    height: int or None
        The height of the exported image in layout pixels. If the `scale`
        property is 1.0, this will also be the height of the exported image
        in physical pixels.

        If not specified, will default to:
            - `plotly.io.defaults.default_height` if engine is "kaleido"
            - `plotly.io.orca.config.default_height` if engine is "orca" (deprecated)

    scale: int or float or None
        The scale factor to use when exporting the figure. A scale factor
        larger than 1.0 will increase the image resolution with respect
        to the figure's layout pixel dimensions. Whereas as scale factor of
        less than 1.0 will decrease the image resolution.

        If not specified, will default to:
            - `plotly.io.defaults.default_scale` if engine is "kaleido"
            - `plotly.io.orca.config.default_scale` if engine is "orca" (deprecated)

    validate: bool
        True if the figure should be validated before being converted to
        an image, False otherwise.

    engine (deprecated): str
        Image export engine to use. This parameter is deprecated and Orca engine support will be
        dropped in the next major Plotly version. Until then, the following values are supported:
          - "kaleido": Use Kaleido for image export
          - "orca": Use Orca for image export
          - "auto" (default): Use Kaleido if installed, otherwise use Orca

    Returns
    -------
    bytes
        The image data
    """

    original_engine = engine

    engine = _validate_engine_param(engine)

    if _options is not None:
        format = _options.format
        if _options.width is not None:
            width = _options.width
        if _options.height is not None:
            height = _options.height
        if _options.scale is not None:
            scale = _options.scale
    else:
        format = resolve_format(None, format)

    engine = _resolve_engine_and_warn(engine, original_engine, stacklevel=2)

    if engine == "orca":
        from ._orca import to_image as to_image_orca

        return to_image_orca(
            fig,
            format=format,
            width=width,
            height=height,
            scale=scale,
            validate=validate,
        )

    _require_kaleido('Image export using the "kaleido" engine')

    fig_dict = validate_coerce_fig_to_dict(fig, validate)

    if _options is None or _options.width is None or _options.height is None:
        _, width, height, scale = _resolve_image_defaults(
            fig_dict, format, width, height, scale
        )

    if kaleido_major() > 0:
        if format == "eps":
            raise ValueError(
                f"""
EPS export is not supported by Kaleido v1. Please use SVG or PDF instead.
You can also downgrade to Kaleido v0, but support for Kaleido v0 will be removed after {ENGINE_SUPPORT_TIMELINE}.
To downgrade to Kaleido v0, run:
    $ pip install 'kaleido<1.0.0'
"""
            )
        from kaleido.errors import ChromeNotFoundError

        try:
            kopts = {}
            if defaults.plotlyjs:
                kopts["plotlyjs"] = defaults.plotlyjs
            if defaults.mathjax:
                kopts["mathjax"] = defaults.mathjax
            if defaults.headers:
                kopts["headers"] = defaults.headers

            img_bytes = kaleido.calc_fig_sync(
                fig_dict,
                opts=dict(
                    format=format,
                    width=width,
                    height=height,
                    scale=scale,
                ),
                topojson=defaults.topojson,
                kopts=kopts,
            )
        except ChromeNotFoundError:
            raise RuntimeError(PLOTLY_GET_CHROME_ERROR_MSG)

    else:
        img_bytes = scope.transform(
            fig_dict, format=format, width=width, height=height, scale=scale
        )

    return img_bytes


def write_image(
    fig: Union[dict, plotly.graph_objects.Figure],
    file: Union[str, Path],
    format: Union[str, None] = None,
    scale: Union[int, float, None] = None,
    width: Union[int, None] = None,
    height: Union[int, None] = None,
    validate: bool = True,
    # Deprecated
    engine: Union[str, None] = None,
):
    """
    Convert a figure to a static image and write it to a file or writeable
    object

    Parameters
    ----------
    fig:
        Figure object or dict representing a figure

    file: str or writeable
        A string representing a local file path or a writeable object
        (e.g. a pathlib.Path object or an open file descriptor)

    format: str or None
        The desired image format. One of
          - 'png'
          - 'jpg' or 'jpeg'
          - 'webp'
          - 'svg'
          - 'pdf'
          - 'eps' (deprecated) (Requires the poppler library to be installed and on the PATH)

        If not specified and `file` is a string then this will default to the
        file extension. If not specified and `file` is not a string then this
        will default to:
            - `plotly.io.defaults.default_format` if engine is "kaleido"
            - `plotly.io.orca.config.default_format` if engine is "orca" (deprecated)

    width: int or None
        The width of the exported image in layout pixels. If the `scale`
        property is 1.0, this will also be the width of the exported image
        in physical pixels.

        If not specified, will default to:
            - `plotly.io.defaults.default_width` if engine is "kaleido"
            - `plotly.io.orca.config.default_width` if engine is "orca" (deprecated)

    height: int or None
        The height of the exported image in layout pixels. If the `scale`
        property is 1.0, this will also be the height of the exported image
        in physical pixels.

        If not specified, will default to:
            - `plotly.io.defaults.default_height` if engine is "kaleido"
            - `plotly.io.orca.config.default_height` if engine is "orca" (deprecated)

    scale: int or float or None
        The scale factor to use when exporting the figure. A scale factor
        larger than 1.0 will increase the image resolution with respect
        to the figure's layout pixel dimensions. Whereas as scale factor of
        less than 1.0 will decrease the image resolution.

        If not specified, will default to:
            - `plotly.io.defaults.default_scale` if engine is "kaleido"
            - `plotly.io.orca.config.default_scale` if engine is "orca" (deprecated)

    validate: bool
        True if the figure should be validated before being converted to
        an image, False otherwise.

    engine (deprecated): str
        Image export engine to use. This parameter is deprecated and Orca engine support will be
        dropped in the next major Plotly version. Until then, the following values are supported:
          - "kaleido": Use Kaleido for image export
          - "orca": Use Orca for image export
          - "auto" (default): Use Kaleido if installed, otherwise use Orca

    Returns
    -------
    None
    """
    path = as_path_object(file)

    options = resolve_export_options(
        fig_dict=None,
        path=path,
        format=format,
        width=width,
        height=height,
        scale=scale,
    )

    img_data = to_image(
        fig,
        validate=validate,
        engine=engine,
        _options=options,
    )

    # Open file
    if path is None:
        # We previously failed to make sense of `file` as a pathlib object.
        # Attempt to write to `file` as an open file descriptor.
        try:
            file.write(img_data)
            return
        except AttributeError:
            pass
        raise ValueError(
            f"""
The 'file' argument '{file}' is not a string, pathlib.Path object, or file descriptor.
"""
        )
    else:
        # We previously succeeded in interpreting `file` as a pathlib object.
        # Now we can use `write_bytes()`.
        path.write_bytes(img_data)


def write_images(
    fig: Union[
        List[Union[dict, plotly.graph_objects.Figure]],
        Union[dict, plotly.graph_objects.Figure],
    ],
    file: Union[List[Union[str, Path]], Union[str, Path]],
    format: Union[List[Union[str, None]], Union[str, None]] = None,
    scale: Union[List[Union[int, float, None]], Union[int, float, None]] = None,
    width: Union[List[Union[int, None]], Union[int, None]] = None,
    height: Union[List[Union[int, None]], Union[int, None]] = None,
    validate: Union[List[bool], bool] = True,
) -> None:
    """
    Write multiple images to files or writeable objects. This is much faster than
    calling write_image() multiple times. This function can only be used with the Kaleido
    engine, v1.0.0 or greater.

    This function accepts the same arguments as write_image() (minus the `engine` argument),
    except that any of the arguments may be either a single value or an iterable of values.
    If multiple arguments are iterable, they must all have the same length.

    Parameters
    ----------
    fig:
        List of figure objects or dicts representing a figure.
        Also accepts a single figure or dict representing a figure.

    file: str, pathlib.Path, or list of (str or pathlib.Path)
        List of str or pathlib.Path objects representing local file paths to write to.
        Can also be a single str or pathlib.Path object if fig argument is
        a single figure or dict representing a figure.

    format: str, None, or list of (str or None)
        The image format to use for exported images.
        Supported formats are:
          - 'png'
          - 'jpg' or 'jpeg'
          - 'webp'
          - 'svg'
          - 'pdf'

        Use a list to specify formats for each figure or dict in the list
        provided to the `fig` argument.
        Specify format as a `str` to apply the same format to all exported images.
        If not specified, and the corresponding `file` argument has a file extension, then `format` will default to the
        file extension. Otherwise, will default to `plotly.io.defaults.default_format`.

    width: int, None, or list of (int or None)
        The width of the exported image in layout pixels. If the `scale`
        property is 1.0, this will also be the width of the exported image
        in physical pixels.

        Use a list to specify widths for each figure or dict in the list
        provided to the `fig` argument.
        Specify width as an `int` to apply the same width to all exported images.
        If not specified, will default to `plotly.io.defaults.default_width`.

    height: int, None, or list of (int or None)
        The height of the exported image in layout pixels. If the `scale`
        property is 1.0, this will also be the height of the exported image
        in physical pixels.

        Use a list to specify heights for each figure or dict in the list
        provided to the `fig` argument.
        Specify height as an `int` to apply the same height to all exported images.
        If not specified, will default to `plotly.io.defaults.default_height`.

    scale: int, float, None, or list of (int, float, or None)
        The scale factor to use when exporting the figure. A scale factor
        larger than 1.0 will increase the image resolution with respect
        to the figure's layout pixel dimensions. Whereas as scale factor of
        less than 1.0 will decrease the image resolution.

        Use a list to specify scale for each figure or dict in the list
        provided to the `fig` argument.
        Specify scale as an `int` or `float` to apply the same scale to all exported images.
        If not specified, will default to `plotly.io.defaults.default_scale`.

    validate: bool or list of bool
        True if the figure should be validated before being converted to
        an image, False otherwise.

        Use a list to specify validation setting for each figure in the list
        provided to the `fig` argument.
        Specify validate as a boolean to apply the same validation setting to all figures.

    Returns
    -------
    None
    """

    arg_dicts = broadcast_args_to_dicts(
        fig=fig,
        file=file,
        format=format,
        scale=scale,
        width=width,
        height=height,
        validate=validate,
    )

    for d in arg_dicts:
        d["fig"] = validate_coerce_fig_to_dict(d["fig"], d["validate"])
        d["file"] = as_path_object(d["file"])

    kaleido_specs = []
    for d in arg_dicts:
        options = resolve_export_options(
            fig_dict=d["fig"],
            path=d["file"],
            format=d["format"],
            width=d["width"],
            height=d["height"],
            scale=d["scale"],
        )
        if options.format == "eps":
            raise ValueError(
                f"""
EPS export is not supported by Kaleido v1. Please use SVG or PDF instead.
You can also downgrade to Kaleido v0, but support for Kaleido v0 will be removed after {ENGINE_SUPPORT_TIMELINE}.
To downgrade to Kaleido v0, run:
    $ pip install 'kaleido<1.0.0'
"""
            )
        kaleido_specs.append(
            dict(
                fig=d["fig"],
                path=d["file"],
                opts=dict(
                    format=options.format,
                    width=options.width,
                    height=options.height,
                    scale=options.scale,
                ),
                topojson=defaults.topojson,
            )
        )

    _require_kaleido_v1("The `write_images()` function")

    from kaleido.errors import ChromeNotFoundError

    try:
        kopts = {}
        if defaults.plotlyjs:
            kopts["plotlyjs"] = defaults.plotlyjs
        if defaults.mathjax:
            kopts["mathjax"] = defaults.mathjax
        if defaults.headers:
            kopts["headers"] = defaults.headers
        kaleido.write_fig_from_object_sync(
            kaleido_specs,
            kopts=kopts,
        )
    except ChromeNotFoundError:
        raise RuntimeError(PLOTLY_GET_CHROME_ERROR_MSG)


def full_figure_for_development(
    fig: Union[dict, plotly.graph_objects.Figure],
    warn: bool = True,
    as_dict: bool = False,
) -> Union[plotly.graph_objects.Figure, dict]:
    """
    Compute default values for all attributes not specified in the input figure and
    returns the output as a "full" figure. This function calls Plotly.js via Kaleido
    to populate unspecified attributes. This function is intended for interactive use
    during development to learn more about how Plotly.js computes default values and is
    not generally necessary or recommended for production use.

    Parameters
    ----------
    fig:
        Figure object or dict representing a figure

    warn: bool
        If False, suppress warnings about not using this in production.

    as_dict: bool
        If True, output is a dict with some keys that go.Figure can't parse.
        If False, output is a go.Figure with unparseable keys skipped.

    Returns
    -------
    plotly.graph_objects.Figure or dict
        The full figure
    """

    _require_kaleido("Full figure generation")

    if warn:
        warnings.warn(
            "full_figure_for_development is not recommended or necessary for "
            "production use in most circumstances. \n"
            "To suppress this warning, set warn=False"
        )

    if kaleido_available() and kaleido_major() > 0:
        # Kaleido v1
        bytes = kaleido.calc_fig_sync(
            fig,
            opts=dict(format="json"),
        )
        fig = json.loads(bytes.decode("utf-8"))
    else:
        # Kaleido v0
        if ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
            warnings.warn(KALEIDO_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
        fig = json.loads(scope.transform(fig, format="json").decode("utf-8"))

    if as_dict:
        return fig
    else:
        import plotly.graph_objects as go

        return go.Figure(fig, skip_invalid=True)


def plotly_get_chrome() -> None:
    """
    Install Google Chrome for Kaleido (Required for Plotly image export).
    This function is a command-line wrapper for `plotly.io.get_chrome()`.

    When running from the command line, use the command `plotly_get_chrome`;
    when calling from Python code, use `plotly.io.get_chrome()`.
    """

    usage = """
Usage: plotly_get_chrome [-y] [--path PATH]

Installs Google Chrome for Plotly image export.

Options:
  -y  Skip confirmation prompt
  --path PATH  Specify the path to install Chrome. Must be a path to an existing directory.
  --help  Show this message and exit.
"""

    _require_kaleido_v1("This command")

    # Handle command line arguments
    import sys

    cli_args = sys.argv

    # Handle "-y" flag
    cli_yes = "-y" in cli_args
    if cli_yes:
        cli_args.remove("-y")

    # Handle "--path" flag
    chrome_install_path = None
    if "--path" in cli_args:
        path_index = cli_args.index("--path") + 1
        if path_index < len(cli_args):
            chrome_install_path = cli_args[path_index]
            cli_args.remove("--path")
            cli_args.remove(chrome_install_path)
            chrome_install_path = Path(chrome_install_path)

    # If any arguments remain, command syntax was incorrect -- print usage and exit
    if len(cli_args) > 1:
        print(usage)
        sys.exit(1)

    if not cli_yes:
        print(
            f"""
Plotly will install a copy of Google Chrome to be used for generating static images of plots.
Chrome will be installed at: {chrome_install_path}"""
        )
        response = input("Do you want to proceed? [y/n] ")
        if not response or response[0].lower() != "y":
            print("Cancelled")
            return
    print("Installing Chrome for Plotly...")
    exe_path = get_chrome(chrome_install_path)
    print("Chrome installed successfully.")
    print(f"The Chrome executable is now located at: {exe_path}")


def get_chrome(path: Union[str, Path, None] = None) -> Path:
    """
    Get the path to the Chrome executable for Kaleido.
    This function is used by the `plotly_get_chrome` command line utility.

    Parameters
    ----------
    path: str or Path or None
        The path to the directory where Chrome should be installed.
        If None, the default download path will be used.
    """
    _require_kaleido_v1("This command")

    # Use default download path if no path was specified
    if path:
        user_specified_path = True
        chrome_install_path = Path(path)  # Ensure it's a Path object
    else:
        user_specified_path = False
        from choreographer.cli.defaults import default_download_path

        chrome_install_path = default_download_path

    # If install path was chosen by user, make sure there is an existing directory
    # located at chrome_install_path; otherwise fail
    if user_specified_path:
        if not chrome_install_path.exists():
            raise ValueError(
                f"""
The specified install path '{chrome_install_path}' does not exist.
Please specify a path to an existing directory using the --path argument,
or omit the --path argument to use the default download path.
"""
            )
        # Make sure the path is a directory
        if not chrome_install_path.is_dir():
            raise ValueError(
                f"""
The specified install path '{chrome_install_path}' already exists but is not a directory.
Please specify a path to an existing directory using the --path argument,
or omit the --path argument to use the default download path.
"""
            )

    return kaleido.get_chrome_sync(path=chrome_install_path)


__all__ = ["to_image", "write_image", "scope", "full_figure_for_development"]

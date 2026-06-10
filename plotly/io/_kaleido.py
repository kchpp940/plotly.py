import os
import json
from pathlib import Path
from typing import Union, List
import importlib.metadata as importlib_metadata
from packaging.version import Version
import warnings

import plotly
from plotly.io._utils import validate_coerce_fig_to_dict, broadcast_args_to_dicts
from plotly.io._defaults import defaults

ENGINE_SUPPORT_TIMELINE = "September 2025"
ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS = True

# Valid image format constants
# ----------------------------
valid_formats = ("png", "jpeg", "webp", "svg", "pdf", "eps")
format_conversions = {fmt: fmt for fmt in valid_formats}
format_conversions.update({"jpg": "jpeg"})

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

KALEIDO_NOT_INSTALLED_MSG = """
Image export using the "kaleido" engine requires the Kaleido package,
which can be installed using pip:

    $ pip install --upgrade kaleido
"""

KALEIDO_V1_REQUIRED_MSG = f"""
This operation requires Kaleido version 1.0.0 or greater.
Please upgrade Kaleido (`pip install 'kaleido>=1.0.0'` or `pip install 'plotly[kaleido]'`).
"""

EPS_NOT_SUPPORTED_V1_MSG = f"""
EPS export is not supported by Kaleido v1. Please use SVG or PDF instead.
You can also downgrade to Kaleido v0, but support for Kaleido v0 will be removed after {ENGINE_SUPPORT_TIMELINE}.
To downgrade to Kaleido v0, run:
    $ pip install 'kaleido<1.0.0'
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


def raise_format_value_error(val):
    raise ValueError(
        """
Invalid value of type {typ} receive as an image format specification.
    Received value: {v}

An image format must be specified as one of the following string values:
    {valid_formats}""".format(
            typ=type(val), v=val, valid_formats=sorted(format_conversions.keys())
        )
    )


def validate_coerce_format(fmt):
    """
    Validate / coerce a user specified image format, and raise an informative
    exception if format is invalid.

    Parameters
    ----------
    fmt
        A value that may or may not be a valid image format string.

    Returns
    -------
    str or None
        A valid image format string as supported by Kaleido. This may not
        be identical to the input image designation. For example,
        the resulting string will always be lower case and  'jpg' is
        converted to 'jpeg'.

        If the input format value is None, then no exception is raised and
        None is returned.

    Raises
    ------
    ValueError
        if the input `fmt` cannot be interpreted as a valid image format.
    """
    if fmt is None:
        return None

    if not isinstance(fmt, str) or not fmt:
        raise_format_value_error(fmt)

    fmt = fmt.lower()

    if fmt[0] == ".":
        fmt = fmt[1:]

    if fmt not in format_conversions:
        raise_format_value_error(fmt)

    return format_conversions[fmt]


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
    return format


class _ImageExportOptions:
    """
    Internal container for resolved image export options.
    Created by _resolve_export_options() to ensure format/defaults
    are parsed exactly once, even when passing between write_image → to_image.
    """

    __slots__ = (
        "format",        # Final resolved format (str, never None, validated)
        "scale",         # Final resolved scale (float/int, never None)
        "engine",        # Resolved engine (str, "kaleido" or "orca")
        "engine_original", # Original engine value (None if not specified by user)
        "width",         # User-provided width (None means use layout/defaults)
        "height",        # User-provided height (None means use layout/defaults)
        "validate",      # Whether to validate the figure
        "_validated",    # Internal flag to prevent re-validation
    )

    def __init__(
        self,
        format,
        scale,
        engine,
        engine_original,
        width,
        height,
        validate,
    ):
        self.format = format
        self.scale = scale
        self.engine = engine
        self.engine_original = engine_original
        self.width = width
        self.height = height
        self.validate = validate
        self._validated = True


def _resolve_export_options(
    format=None,
    scale=None,
    width=None,
    height=None,
    validate=True,
    engine=None,
    file_path=None,
):
    """
    Resolve and validate ALL image export options in a single pass.

    This is the ONE source of truth for format/defaults resolution.
    All entry points (to_image, write_image, write_images) should use this
    to avoid duplicate parsing, inconsistent defaults, or wrong error order.

    Error chain order (all pure local, no side effects):
      1. Format: explicit arg → infer from file extension → defaults.default_format
         (all through validate_coerce_format)
      2. Scale: explicit arg → defaults.default_scale
      3. Engine: None → "auto" → resolve to "kaleido" or "orca"

    Parameters
    ----------
    format, scale, width, height, validate, engine:
        The user-provided arguments
    file_path: Path or None
        For write_image, the file path used to infer format from extension

    Returns
    -------
    _ImageExportOptions
        Fully resolved and validated options. Use .format, .scale, etc.
    """
    # Step 1: Resolve and validate FINAL format (explicit arg > file ext > defaults)
    if format is not None:
        fmt_raw = validate_coerce_format(format)
    elif file_path is not None:
        fmt_inferred = infer_format(file_path, None)
        fmt_raw = validate_coerce_format(fmt_inferred)
    else:
        fmt_raw = None
    resolved_format = fmt_raw or validate_coerce_format(defaults.default_format)

    # Step 2: Resolve scale
    resolved_scale = scale or defaults.default_scale

    # Step 3: Resolve engine (save original for deprecation warnings)
    engine_original = engine
    if engine is None:
        engine = "auto"

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

    if engine not in {"kaleido", "orca"}:
        raise ValueError(f"Invalid image export engine specified: {repr(engine)}")

    return _ImageExportOptions(
        format=resolved_format,
        scale=resolved_scale,
        engine=engine,
        engine_original=engine_original,
        width=width,
        height=height,
        validate=validate,
    )


def _ensure_kaleido_available():
    """
    Check that Kaleido is installed, raise a consistent ValueError if not.
    """
    if not kaleido_available():
        raise ValueError(KALEIDO_NOT_INSTALLED_MSG)


def _ensure_kaleido_v1():
    """
    Check that Kaleido v1+ is installed, raise a consistent ValueError if not.
    """
    _ensure_kaleido_available()
    if kaleido_major() < 1:
        raise ValueError(KALEIDO_V1_REQUIRED_MSG)


def _handle_deprecation_warnings(engine, stacklevel=2):
    """
    Emit deprecation warnings for engine parameter and orca/kaleido_v0 usage.

    Parameters
    ----------
    engine: str or None
        The engine parameter value
    stacklevel: int
        Stack level for warnings, relative to the caller of this function.
        Default 2 means the warning points to the caller of the function
        that called _handle_deprecation_warnings.
    """
    # +1 for this helper function itself
    level = stacklevel + 1

    if engine is not None and ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
        warnings.warn(
            ENGINE_PARAM_DEPRECATION_MSG, DeprecationWarning, stacklevel=level
        )

    if ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
        if (
            engine in {None, "auto", "kaleido"}
            and kaleido_available()
            and kaleido_major() < 1
        ):
            warnings.warn(
                KALEIDO_DEPRECATION_MSG, DeprecationWarning, stacklevel=level
            )

    if engine == "orca" and ENABLE_KALEIDO_V0_DEPRECATION_WARNINGS:
        warnings.warn(ORCA_DEPRECATION_MSG, DeprecationWarning, stacklevel=level)


def _resolve_image_dimensions(fig_dict, width, height):
    """
    Resolve width/height with cascading fallback:
    explicit arg > layout.width/height > template.layout.width/height > defaults
    """
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
    return width, height


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


def to_image(
    fig: Union[dict, plotly.graph_objects.Figure],
    format: Union[str, None] = None,
    width: Union[int, None] = None,
    height: Union[int, None] = None,
    scale: Union[int, float, None] = None,
    validate: bool = True,
    # Deprecated
    engine: Union[str, None] = None,
    # Internal use
    _skip_deprecation_warnings: bool = False,
    _deprecation_stacklevel: int = 2,
    _export_options: Union["_ImageExportOptions", None] = None,
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
    # ------------------------------------------------------------------
    # Error chain order (from most-local/deterministic to external deps):
    #   1. Resolve options via _resolve_export_options  (format+scale+engine, all validated)
    #   2. Orca delegation                              (if orca, orca handles warnings)
    #   3. Deprecation warnings                         (only after format/defaults OK)
    #   4. Kaleido installation check                   (external dep #1)
    #   5. Figure conversion + dim defaults             (local)
    #   6. v0/v1 branch + EPS check                     (local)
    #   7. Chrome detection (via Kaleido call)          (external dep #2)
    # ------------------------------------------------------------------

    # Step 1: Resolve options. Use pre-resolved options if provided (by write_image)
    # to avoid duplicate parsing and ensure consistent defaults.
    if _export_options is None:
        opts = _resolve_export_options(
            format=format,
            scale=scale,
            width=width,
            height=height,
            validate=validate,
            engine=engine,
        )
    else:
        opts = _export_options

    # Step 2: If Orca, delegate immediately (orca handles its own warnings)
    if opts.engine == "orca":
        from ._orca import to_image as to_image_orca

        return to_image_orca(
            fig,
            format=format,
            width=opts.width,
            height=opts.height,
            scale=opts.scale,
            validate=opts.validate,
        )

    # Step 3: Emit deprecation warnings (only after format is fully validated,
    # and only if caller hasn't already handled them)
    if not _skip_deprecation_warnings:
        _handle_deprecation_warnings(opts.engine_original, stacklevel=_deprecation_stacklevel)

    # Step 4: Check Kaleido availability
    _ensure_kaleido_available()

    # Step 5: Convert figure to dict and resolve width/height with cascading fallback
    fig_dict = validate_coerce_fig_to_dict(fig, opts.validate)
    resolved_width, resolved_height = _resolve_image_dimensions(
        fig_dict, opts.width, opts.height
    )

    # Step 6-7: Request image bytes (v0/v1 branching + Chrome detection)
    # opts.format is already fully resolved (never None, already validated)
    # so v0/v1 branches just use it directly — no further format manipulation.
    if kaleido_major() > 0:
        # Kaleido v1 - check EPS support before invoking
        if opts.format == "eps":
            raise ValueError(EPS_NOT_SUPPORTED_V1_MSG)

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
                    format=opts.format,
                    width=resolved_width,
                    height=resolved_height,
                    scale=opts.scale,
                ),
                topojson=defaults.topojson,
                kopts=kopts,
            )
        except ChromeNotFoundError:
            raise RuntimeError(PLOTLY_GET_CHROME_ERROR_MSG)
    else:
        # Kaleido v0
        img_bytes = scope.transform(
            fig_dict,
            format=opts.format,
            width=resolved_width,
            height=resolved_height,
            scale=opts.scale,
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
    # Internal use
    _skip_deprecation_warnings: bool = False,
    _deprecation_stacklevel: int = 2,
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
    # ------------------------------------------------------------------
    # Error chain order (same as to_image):
    #   1. Resolve options via _resolve_export_options  (format+scale+engine, all validated)
    #   2. Orca delegation                              (if orca, orca handles warnings)
    #   3. Deprecation warnings                         (only after format/defaults OK)
    #   4. Call to_image with _export_options           (avoids duplicate parsing)
    # ------------------------------------------------------------------

    # Resolve path for file writing AND format inference
    path = as_path_object(file)

    # Step 1: Resolve ALL options in one pass.
    # This handles format cascade (explicit > file ext > defaults), scale, and engine.
    opts = _resolve_export_options(
        format=format,
        scale=scale,
        width=width,
        height=height,
        validate=validate,
        engine=engine,
        file_path=path,
    )

    # Step 2: If Orca, delegate immediately (orca handles its own warnings)
    if opts.engine == "orca":
        from ._orca import write_image as write_image_orca

        return write_image_orca(
            fig,
            file=file,
            format=format,
            width=opts.width,
            height=opts.height,
            scale=opts.scale,
            validate=opts.validate,
        )

    # Step 3: Emit deprecation warnings (only after format is fully validated,
    # and only if caller hasn't already handled them)
    if not _skip_deprecation_warnings:
        _handle_deprecation_warnings(opts.engine_original, stacklevel=_deprecation_stacklevel)

    # Step 4: Request image bytes via to_image. Pass _export_options so to_image
    # doesn't re-parse format/defaults/engine — single source of truth.
    img_data = to_image(
        fig,
        _export_options=opts,
        _skip_deprecation_warnings=True,
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
    # Step 1: Broadcast arguments (pure local, no external deps)
    arg_dicts = broadcast_args_to_dicts(
        fig=fig,
        file=file,
        format=format,
        scale=scale,
        width=width,
        height=height,
        validate=validate,
    )

    # Step 2: Resolve ALL format and scale defaults FIRST (pure local).
    # Uses the same validation cascade as _resolve_export_options:
    #   format: explicit > file ext > defaults.default_format
    #   scale: explicit > defaults.default_scale
    # Both are resolved before any Kaleido/Chrome checks for consistent error order.
    for d in arg_dicts:
        d["file"] = as_path_object(d["file"])
        fmt_raw = validate_coerce_format(
            infer_format(d["file"], d["format"])
        )
        d["format"] = fmt_raw or validate_coerce_format(defaults.default_format)
        d["scale"] = d["scale"] or defaults.default_scale

    # Step 3: Check Kaleido v1 availability (all options are resolved now)
    _ensure_kaleido_v1()

    # Step 4: Convert figures to dicts and resolve dimensions
    for d in arg_dicts:
        d["fig"] = validate_coerce_fig_to_dict(d["fig"], d["validate"])
        d["width"], d["height"] = _resolve_image_dimensions(
            d["fig"], d["width"], d["height"]
        )

    # Step 5: Reshape for Kaleido (format/scale already resolved, no more defaults)
    kaleido_specs = [
        dict(
            fig=d["fig"],
            path=d["file"],
            opts=dict(
                format=d["format"],
                width=d["width"],
                height=d["height"],
                scale=d["scale"],
            ),
            topojson=defaults.topojson,
        )
        for d in arg_dicts
    ]

    # Step 6: Call Kaleido (Chrome detection is the last check)
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
    # Check Kaleido availability with consistent error message
    _ensure_kaleido_available()

    if warn:
        warnings.warn(
            "full_figure_for_development is not recommended or necessary for "
            "production use in most circumstances. \n"
            "To suppress this warning, set warn=False"
        )

    if kaleido_major() > 0:
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
    import sys

    usage = """
Usage: plotly_get_chrome [-y] [--path PATH]

Installs Google Chrome for Plotly image export.

Options:
  -y  Skip confirmation prompt
  --path PATH  Specify the path to install Chrome. Must be a path to an existing directory.
  --help  Show this message and exit.
"""

    # Parse arguments first (so --help works even without Kaleido)
    cli_args = sys.argv.copy()

    # Handle --help first
    if "--help" in cli_args or "-h" in cli_args:
        print(usage)
        sys.exit(0)

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
        else:
            print(usage, file=sys.stderr)
            sys.exit(1)

    # If any arguments remain, command syntax was incorrect -- print usage and exit
    if len(cli_args) > 1:
        print(usage, file=sys.stderr)
        sys.exit(1)

    # Check Kaleido v1 availability (after arg parsing, with CLI-friendly error)
    try:
        _ensure_kaleido_v1()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Confirmation prompt
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

    # Install Chrome
    print("Installing Chrome for Plotly...")
    try:
        exe_path = get_chrome(chrome_install_path)
    except Exception as e:
        print(f"Error installing Chrome: {e}", file=sys.stderr)
        sys.exit(1)

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
    # Check Kaleido v1 availability with consistent error message
    _ensure_kaleido_v1()

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

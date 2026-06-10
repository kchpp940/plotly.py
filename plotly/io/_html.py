import uuid
from pathlib import Path, PurePath
import webbrowser
import hashlib
import base64
import os

from _plotly_utils.optional_imports import get_module
from plotly.io._utils import validate_coerce_fig_to_dict, plotly_cdn_url
from plotly.offline.offline import _get_jconfig, get_plotlyjs

_json = get_module("json")


def _coerce_to_path(file):
    """
    Coerce a file path specification to a pathlib.Path object.

    Parameters
    ----------
    file : str, pathlib.Path, or file-like
        A string representing a local file path, a pathlib.Path object, or
        a file-like object with a `write()` method.

    Returns
    -------
    pathlib.Path or None
        Returns a pathlib.Path if `file` can be interpreted as a file path,
        otherwise returns None (for file-like objects without a filesystem path).
    """
    if isinstance(file, str):
        return Path(file)
    elif isinstance(file, PurePath):
        return Path(file)
    else:
        return None


def _ensure_output_directory(path):
    """
    Ensure the parent directory for the given output path exists.

    Parameters
    ----------
    path : pathlib.Path
        The output file path whose parent directory should be created.

    Raises
    ------
    OSError
        If the directory cannot be created.
    """
    parent = path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def _ensure_plotlyjs_bundle(
    html_path,
    include_plotlyjs,
    full_html=True,
    bundle_dir=None,
):
    """
    Ensure the plotly.js bundle is present for HTML output with
    include_plotlyjs='directory'.

    This function handles:
    - Creating the output directory if needed
    - Copying plotly.min.js to the appropriate location

    This is an internal helper called only by entry points that write to
    disk (write_html, offline.plot with output_type='file', IFrameRenderer,
    SphinxGalleryOrcaRenderer). It should NOT be called by to_html or
    notebook renderers, which have no filesystem output path and therefore
    no responsibility for bundle copying.

    Parameters
    ----------
    html_path : pathlib.Path or None
        Path to the HTML file being written. If None, no filesystem operations
        are performed.
    include_plotlyjs : str or bool
        The include_plotlyjs parameter value. Bundle operations are only
        performed when this is 'directory'.
    full_html : bool (default True)
        Whether writing a full HTML document. Bundle operations are only
        performed when full_html is True.
    bundle_dir : pathlib.Path or None (default None)
        If provided, the plotly.min.js bundle will be copied to this directory
        rather than to the HTML file's parent directory. This is useful when
        multiple HTML files in subdirectories share a single bundle at a
        common ancestor directory.
    """
    if include_plotlyjs != "directory":
        return

    if not full_html:
        return

    if html_path is None:
        return

    try:
        html_abs = html_path.resolve()
        _ensure_output_directory(html_abs)

        if bundle_dir is not None:
            bundle_dir_abs = Path(bundle_dir).resolve()
            _ensure_output_directory(bundle_dir_abs / "dummy")
        else:
            bundle_dir_abs = html_abs.parent

        bundle_path = bundle_dir_abs / "plotly.min.js"
        if not bundle_path.exists():
            bundle_path.write_text(get_plotlyjs(), encoding="utf-8")
    except Exception as e:
        raise ValueError(
            "Failed to prepare plotly.js bundle for output path '{}': {}".format(
                str(html_path), str(e)
            )
        )


def _generate_sri_hash(content):
    """Generate SHA256 hash for SRI (Subresource Integrity)"""
    if isinstance(content, str):
        content = content.encode("utf-8")
    sha256_hash = hashlib.sha256(content).digest()
    return "sha256-" + base64.b64encode(sha256_hash).decode("utf-8")


# Build script to set global PlotlyConfig object. This must execute before
# plotly.js is loaded.
_window_plotly_config = """\
<script>\
window.PlotlyConfig = {MathJaxConfig: 'local'};\
</script>"""

_mathjax_config = """\
<script>\
if (window.MathJax && window.MathJax.Hub && window.MathJax.Hub.Config) {window.MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}\
</script>"""


def to_html(
    fig,
    config=None,
    auto_play=True,
    include_plotlyjs=True,
    include_mathjax=False,
    post_script=None,
    full_html=True,
    animation_opts=None,
    default_width="100%",
    default_height="100%",
    validate=True,
    div_id=None,
):
    """
    Convert a figure to an HTML string representation.

    Parameters
    ----------
    fig:
        Figure object or dict representing a figure
    config: dict or None (default None)
        Plotly.js figure config options
    auto_play: bool (default=True)
        Whether to automatically start the animation sequence on page load
        if the figure contains frames. Has no effect if the figure does not
        contain frames.
    include_plotlyjs: bool or string (default True)
        Specifies how the plotly.js library is included/loaded in the output
        div string.

        If True, a script tag containing the plotly.js source code (~3MB)
        is included in the output.  HTML files generated with this option are
        fully self-contained and can be used offline.

        If 'cdn', a script tag that references the plotly.js CDN is included
        in the output. The url used is versioned to match the bundled plotly.js.
        HTML files generated with this option are about 3MB smaller than those
        generated with include_plotlyjs=True, but they require an active
        internet connection in order to load the plotly.js library.

        If 'directory', a script tag is included that references an external
        plotly.min.js bundle that is assumed to reside in the same
        directory as the HTML file.

        If a string that ends in '.js', a script tag is included that
        references the specified path. This approach can be used to point
        the resulting HTML file to an alternative CDN or local bundle.

        If False, no script tag referencing plotly.js is included. This is
        useful when the resulting div string will be placed inside an HTML
        document that already loads plotly.js. This option is not advised
        when full_html=True as it will result in a non-functional html file.
    include_mathjax: bool or string (default False)
        Specifies how the MathJax.js library is included in the output html
        div string.  MathJax is required in order to display labels
        with LaTeX typesetting.

        If False, no script tag referencing MathJax.js will be included in the
        output.

        If 'cdn', a script tag that references a MathJax CDN location will be
        included in the output.  HTML div strings generated with this option
        will be able to display LaTeX typesetting as long as internet access
        is available.

        If a string that ends in '.js', a script tag is included that
        references the specified path. This approach can be used to point the
        resulting HTML div string to an alternative CDN.
    post_script: str or list or None (default None)
        JavaScript snippet(s) to be included in the resulting div just after
        plot creation.  The string(s) may include '{plot_id}' placeholders
        that will then be replaced by the `id` of the div element that the
        plotly.js figure is associated with.  One application for this script
        is to install custom plotly.js event handlers.
    full_html: bool (default True)
        If True, produce a string containing a complete HTML document
        starting with an <html> tag.  If False, produce a string containing
        a single <div> element.
    animation_opts: dict or None (default None)
        dict of custom animation parameters to be passed to the function
        Plotly.animate in Plotly.js. See
        https://github.com/plotly/plotly.js/blob/master/src/plots/animation_attributes.js
        for available options. Has no effect if the figure does not contain
        frames, or auto_play is False.
    default_width, default_height: number or str (default '100%')
        The default figure width/height to use if the provided figure does not
        specify its own layout.width/layout.height property.  May be
        specified in pixels as an integer (e.g. 500), or as a css width style
        string (e.g. '500px', '100%').
    validate: bool (default True)
        True if the figure should be validated before being converted to
        JSON, False otherwise.
    div_id: str (default None)
        If provided, this is the value of the id attribute of the div tag. If None, the
        id attribute is a UUID.

    Returns
    -------
    str
        Representation of figure as an HTML div string
    """
    from plotly.io.json import to_json_plotly

    # ## Validate figure ##
    fig_dict = validate_coerce_fig_to_dict(fig, validate)

    # ## Generate div id ##
    plotdivid = div_id or str(uuid.uuid4())

    # ## Serialize figure ##
    jdata = to_json_plotly(fig_dict.get("data", []))
    jlayout = to_json_plotly(fig_dict.get("layout", {}))

    if fig_dict.get("frames", None):
        jframes = to_json_plotly(fig_dict.get("frames", []))
    else:
        jframes = None

    # ## Serialize figure config ##
    config = _get_jconfig(config)

    # Set responsive
    config.setdefault("responsive", True)

    # Get div width/height
    layout_dict = fig_dict.get("layout", {})
    template_dict = fig_dict.get("layout", {}).get("template", {}).get("layout", {})

    div_width = layout_dict.get("width", template_dict.get("width", default_width))
    div_height = layout_dict.get("height", template_dict.get("height", default_height))

    # Add 'px' suffix to numeric widths
    try:
        float(div_width)
    except (ValueError, TypeError):
        pass
    else:
        div_width = str(div_width) + "px"

    try:
        float(div_height)
    except (ValueError, TypeError):
        pass
    else:
        div_height = str(div_height) + "px"

    # ## Get platform URL ##
    if config.get("showLink", False) or config.get("showSendToCloud", False):
        # Figure is going to include a Chart Studio link or send-to-cloud button,
        # So we need to configure the PLOTLYENV.BASE_URL property
        base_url_line = """
                    window.PLOTLYENV.BASE_URL='{plotly_platform_url}';\
""".format(plotly_platform_url=config.get("plotlyServerURL", "https://plot.ly"))
    else:
        # Figure is not going to include a Chart Studio link or send-to-cloud button,
        # In this case we don't want https://plot.ly to show up anywhere in the HTML
        # output
        config.pop("plotlyServerURL", None)
        config.pop("linkText", None)
        config.pop("showLink", None)
        base_url_line = ""

    # ## Build script body ##
    # This is the part that actually calls Plotly.js

    # build post script snippet(s)
    then_post_script = ""
    if post_script:
        if not isinstance(post_script, (list, tuple)):
            post_script = [post_script]
        for ps in post_script:
            then_post_script += """.then(function(){{
                            {post_script}
                        }})""".format(post_script=ps.replace("{plot_id}", plotdivid))

    then_addframes = ""
    then_animate = ""
    if jframes:
        then_addframes = """.then(function(){{
                            Plotly.addFrames('{id}', {frames});
                        }})""".format(id=plotdivid, frames=jframes)

        if auto_play:
            if animation_opts:
                animation_opts_arg = ", " + _json.dumps(animation_opts)
            else:
                animation_opts_arg = ""
            then_animate = """.then(function(){{
                            Plotly.animate('{id}', null{animation_opts});
                        }})""".format(id=plotdivid, animation_opts=animation_opts_arg)

    # Serialize config dict to JSON
    jconfig = _json.dumps(config)

    script = """\
                if (document.getElementById("{id}")) {{\
                    Plotly.newPlot(\
                        "{id}",\
                        {data},\
                        {layout},\
                        {config}\
                    ){then_addframes}{then_animate}{then_post_script}\
                }}""".format(
        id=plotdivid,
        data=jdata,
        layout=jlayout,
        config=jconfig,
        then_addframes=then_addframes,
        then_animate=then_animate,
        then_post_script=then_post_script,
    )

    # ## Handle loading/initializing plotly.js ##
    include_plotlyjs_orig = include_plotlyjs
    if isinstance(include_plotlyjs, str):
        include_plotlyjs = include_plotlyjs.lower()

    # Init and load
    load_plotlyjs = ""

    if include_plotlyjs == "cdn":
        # Generate SRI hash from the bundled plotly.js content
        plotlyjs_content = get_plotlyjs()
        sri_hash = _generate_sri_hash(plotlyjs_content)

        load_plotlyjs = """\
        {win_config}
        <script charset="utf-8" src="{cdn_url}" integrity="{integrity}" crossorigin="anonymous"></script>\
    """.format(
            win_config=_window_plotly_config,
            cdn_url=plotly_cdn_url(),
            integrity=sri_hash,
        )

    elif include_plotlyjs == "directory":
        load_plotlyjs = """\
        {win_config}
        <script charset="utf-8" src="plotly.min.js"></script>\
    """.format(win_config=_window_plotly_config)

    elif isinstance(include_plotlyjs, str) and include_plotlyjs.endswith(".js"):
        load_plotlyjs = """\
        {win_config}
        <script charset="utf-8" src="{url}"></script>\
    """.format(win_config=_window_plotly_config, url=include_plotlyjs_orig)

    elif include_plotlyjs:
        load_plotlyjs = """\
        {win_config}
        <script>{plotlyjs}</script>\
    """.format(win_config=_window_plotly_config, plotlyjs=get_plotlyjs())

    # ## Handle loading/initializing MathJax ##
    include_mathjax_orig = include_mathjax
    if isinstance(include_mathjax, str):
        include_mathjax = include_mathjax.lower()

    mathjax_template = """\
    <script src="{url}?config=TeX-AMS-MML_SVG"></script>"""

    if include_mathjax == "cdn":
        mathjax_script = (
            mathjax_template.format(
                url=("https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js")
            )
            + _mathjax_config
        )

    elif isinstance(include_mathjax, str) and include_mathjax.endswith(".js"):
        mathjax_script = (
            mathjax_template.format(url=include_mathjax_orig) + _mathjax_config
        )
    elif not include_mathjax:
        mathjax_script = ""
    else:
        raise ValueError(
            """\
Invalid value of type {typ} received as the include_mathjax argument
    Received value: {val}

include_mathjax may be specified as False, 'cdn', or a string ending with '.js'
    """.format(typ=type(include_mathjax), val=repr(include_mathjax))
        )

    plotly_html_div = """\
<div style="height:{height}; width:{width};">\
        {mathjax_script}\
        {load_plotlyjs}\
            <div id="{id}" class="plotly-graph-div" \
style="height:100%; width:100%;"></div>\
            <script>\
                window.PLOTLYENV=window.PLOTLYENV || {{}};{base_url_line}\
                {script};\
            </script>\
        </div>""".format(
        mathjax_script=mathjax_script,
        load_plotlyjs=load_plotlyjs,
        id=plotdivid,
        width=div_width,
        height=div_height,
        base_url_line=base_url_line,
        script=script,
    ).strip()

    if full_html:
        return """\
<html>
<head><meta charset="utf-8" /></head>
<body>
    {div}
</body>
</html>""".format(div=plotly_html_div)
    else:
        return plotly_html_div


def write_html(
    fig,
    file,
    config=None,
    auto_play=True,
    include_plotlyjs=True,
    include_mathjax=False,
    post_script=None,
    full_html=True,
    animation_opts=None,
    validate=True,
    default_width="100%",
    default_height="100%",
    auto_open=False,
    div_id=None,
):
    """
    Write a figure to an HTML file representation

    Parameters
    ----------
    fig:
        Figure object or dict representing a figure
    file: str or writeable
        A string representing a local file path or a writeable object
        (e.g. a pathlib.Path object or an open file descriptor)
    config: dict or None (default None)
        Plotly.js figure config options
    auto_play: bool (default=True)
        Whether to automatically start the animation sequence on page load
        if the figure contains frames. Has no effect if the figure does not
        contain frames.
    include_plotlyjs: bool or string (default True)
        Specifies how the plotly.js library is included/loaded in the output
        div string.

        If True, a script tag containing the plotly.js source code (~3MB)
        is included in the output.  HTML files generated with this option are
        fully self-contained and can be used offline.

        If 'cdn', a script tag that references the plotly.js CDN is included
        in the output. The url used is versioned to match the bundled plotly.js.
        HTML files generated with this option are about 3MB smaller than those
        generated with include_plotlyjs=True, but they require an active
        internet connection in order to load the plotly.js library.

        If 'directory', a script tag is included that references an external
        plotly.min.js bundle that is assumed to reside in the same
        directory as the HTML file.  If `file` is a string to a local file
        path and `full_html` is True, then the plotly.min.js bundle is copied
        into the directory of the resulting HTML file. If a file named
        plotly.min.js already exists in the output directory then this file
        is left unmodified and no copy is performed. HTML files generated
        with this option can be used offline, but they require a copy of
        the plotly.min.js bundle in the same directory. This option is
        useful when many figures will be saved as HTML files in the same
        directory because the plotly.js source code will be included only
        once per output directory, rather than once per output file.

        If a string that ends in '.js', a script tag is included that
        references the specified path. This approach can be used to point
        the resulting HTML file to an alternative CDN or local bundle.

        If False, no script tag referencing plotly.js is included. This is
        useful when the resulting div string will be placed inside an HTML
        document that already loads plotly.js.  This option is not advised
        when full_html=True as it will result in a non-functional html file.

    include_mathjax: bool or string (default False)
        Specifies how the MathJax.js library is included in the output html
        div string.  MathJax is required in order to display labels
        with LaTeX typesetting.

        If False, no script tag referencing MathJax.js will be included in the
        output.

        If 'cdn', a script tag that references a MathJax CDN location will be
        included in the output.  HTML div strings generated with this option
        will be able to display LaTeX typesetting as long as internet access
        is available.

        If a string that ends in '.js', a script tag is included that
        references the specified path. This approach can be used to point the
        resulting HTML div string to an alternative CDN.
    post_script: str or list or None (default None)
        JavaScript snippet(s) to be included in the resulting div just after
        plot creation.  The string(s) may include '{plot_id}' placeholders
        that will then be replaced by the `id` of the div element that the
        plotly.js figure is associated with.  One application for this script
        is to install custom plotly.js event handlers.
    full_html: bool (default True)
        If True, produce a string containing a complete HTML document
        starting with an <html> tag.  If False, produce a string containing
        a single <div> element.
    animation_opts: dict or None (default None)
        dict of custom animation parameters to be passed to the function
        Plotly.animate in Plotly.js. See
        https://github.com/plotly/plotly.js/blob/master/src/plots/animation_attributes.js
        for available options. Has no effect if the figure does not contain
        frames, or auto_play is False.
    default_width, default_height: number or str (default '100%')
        The default figure width/height to use if the provided figure does not
        specify its own layout.width/layout.height property.  May be
        specified in pixels as an integer (e.g. 500), or as a css width style
        string (e.g. '500px', '100%').
    validate: bool (default True)
        True if the figure should be validated before being converted to
        JSON, False otherwise.
    auto_open: bool (default True)
        If True, open the saved file in a web browser after saving.
        This argument only applies if `full_html` is True.
    div_id: str (default None)
        If provided, this is the value of the id attribute of the div tag. If None, the
        id attribute is a UUID.

    Returns
    -------
    None
    """

    # Coerce file to path if possible
    path = _coerce_to_path(file)

    # Ensure plotly.js bundle is present (directory creation + bundle copy)
    _ensure_plotlyjs_bundle(
        html_path=path,
        include_plotlyjs=include_plotlyjs,
        full_html=full_html,
    )

    # Build HTML string
    html_str = to_html(
        fig,
        config=config,
        auto_play=auto_play,
        include_plotlyjs=include_plotlyjs,
        include_mathjax=include_mathjax,
        post_script=post_script,
        full_html=full_html,
        animation_opts=animation_opts,
        default_width=default_width,
        default_height=default_height,
        validate=validate,
        div_id=div_id,
    )

    # Write HTML string
    if path is not None:
        _ensure_output_directory(path)
        path.write_text(html_str, "utf-8")
    else:
        file.write(html_str)

    # Handle auto_open
    if path is not None and full_html and auto_open:
        url = path.absolute().as_uri()
        webbrowser.open(url)

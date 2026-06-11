import uuid
from pathlib import Path
import webbrowser

from _plotly_utils.optional_imports import get_module
from plotly.io._utils import validate_coerce_fig_to_dict
from plotly.offline.offline import _get_jconfig
from plotly.io._resource_policy import (
    ResourcePolicySet,
    ResourcePolicyContext,
    _resolve_resource_context,
    _finalize_resource_context,
)

_json = get_module("json")


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
    resource_policy=None,
    resource_context=None,
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
    resource_policy : ResourcePolicySet or None (default None)
        A ResourcePolicySet object specifying how to include plotly.js,
        MathJax, CSS, and meta tags. If provided, this overrides
        include_plotlyjs and include_mathjax parameters.
    resource_context : ResourcePolicyContext or None (default None)
        A ResourcePolicyContext object. If provided, this takes highest
        priority and overrides both resource_policy and the legacy
        include_plotlyjs/include_mathjax parameters.

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

    # ## Build resource context ##
    # For to_html (no file output), we don't know output_path yet
    ctx = _resolve_resource_context(
        resource_context=resource_context,
        resource_policy=resource_policy,
        include_plotlyjs=include_plotlyjs,
        include_mathjax=include_mathjax,
        include_meta_charset=False,
    )

    # ## Generate resource HTML ##
    # For div output, resources go inside the div
    # For full_html output, resources go in <head>
    if full_html:
        head_html = ctx.get_head_html()
        if ctx.meta is None:
            head_html = '<meta charset="utf-8" />\n' + head_html
        resources_in_div = ""
    else:
        head_html = ""
        raw_resources = ctx.get_head_html()
        if raw_resources:
            resource_lines = raw_resources.split("\n")
            indented_lines = ["        " + line for line in resource_lines]
            resources_in_div = "\n".join(indented_lines)
        else:
            resources_in_div = ""

    plotly_html_div = """\
<div style="height:{height}; width:{width};">\
        \
        {resources_in_div}\
            <div id="{id}" class="plotly-graph-div" \
style="height:100%; width:100%;"></div>\
            <script>\
                window.PLOTLYENV=window.PLOTLYENV || {{}};{base_url_line}\
                {script};\
            </script>\
        </div>""".format(
        resources_in_div=resources_in_div,
        id=plotdivid,
        width=div_width,
        height=div_height,
        base_url_line=base_url_line,
        script=script,
    ).strip()

    if full_html:
        return """\
<html>
<head>
{head}
</head>
<body>
    {div}
</body>
</html>""".format(head=head_html, div=plotly_html_div)
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
    resource_policy=None,
    resource_context=None,
    overwrite_resources=False,
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
    resource_policy : ResourcePolicySet or None (default None)
        A ResourcePolicySet object specifying how to include plotly.js,
        MathJax, CSS, and meta tags. If provided, this overrides
        include_plotlyjs and include_mathjax parameters.
    resource_context : ResourcePolicyContext or None (default None)
        A ResourcePolicyContext object. If provided, this takes highest
        priority and overrides both resource_policy and the legacy
        include_plotlyjs/include_mathjax parameters.
    overwrite_resources : bool (default False)
        If True, overwrite existing resource files when copying to the
        output directory. If False, skip copying if the file already exists.

    Returns
    -------
    None
    """
    # Check if file is a string/Path (has a path)
    if isinstance(file, str):
        path = Path(file)
    elif isinstance(file, Path):
        path = file
    else:
        path = None

    # Build resource context
    ctx = _resolve_resource_context(
        resource_context=resource_context,
        resource_policy=resource_policy,
        include_plotlyjs=include_plotlyjs,
        include_mathjax=include_mathjax,
        output_path=path,
        overwrite=overwrite_resources,
        include_meta_charset=True,
    )

    # Build HTML string
    html_str = to_html(
        fig,
        config=config,
        auto_play=auto_play,
        post_script=post_script,
        full_html=full_html,
        animation_opts=animation_opts,
        default_width=default_width,
        default_height=default_height,
        validate=validate,
        div_id=div_id,
        resource_context=ctx,
    )

    # Write HTML string
    if path is not None:
        path.write_text(html_str, "utf-8")
    else:
        file.write(html_str)

    # Execute resource copies, manifest writes, and missing warnings
    if path is not None and full_html:
        _finalize_resource_context(ctx)

    # Handle auto_open
    if path is not None and full_html and auto_open:
        url = path.absolute().as_uri()
        webbrowser.open(url)

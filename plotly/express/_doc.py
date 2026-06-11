import inspect
from textwrap import TextWrapper
from ._params import PARAMS

try:
    getfullargspec = inspect.getfullargspec
except AttributeError:  # python 2
    getfullargspec = inspect.getargspec


colref_type = "str or int or Series or array-like"
colref_desc = "Either a name of a column in `data_frame`, or a pandas Series or array_like object."
colref_list_type = "list of str or int, or Series or array-like"
colref_list_desc = (
    "Either names of columns in `data_frame`, or pandas Series, or array_like objects"
)

_docs_overrides = dict(
    histfunc=[
        "str (default `'count'` if no arguments are provided, else `'sum'`)",
        "One of `'count'`, `'sum'`, `'avg'`, `'min'`, or `'max'`.",
        "Function used to aggregate values for summarization (note: can be normalized with `histnorm`).",
    ],
    histnorm=[
        "str (default `None`)",
        "One of `'percent'`, `'probability'`, `'density'`, or `'probability density'`",
        "If `None`, the output of `histfunc` is used as is.",
        "If `'probability'`, the output of `histfunc` for a given bin is divided by the sum of the output of `histfunc` for all bins.",
        "If `'percent'`, the output of `histfunc` for a given bin is divided by the sum of the output of `histfunc` for all bins and multiplied by 100.",
        "If `'density'`, the output of `histfunc` for a given bin is divided by the size of the bin.",
        "If `'probability density'`, the output of `histfunc` for a given bin is normalized such that it corresponds to the probability that a random event whose distribution is described by the output of `histfunc` will fall into that bin.",
    ],
    barnorm=[
        "str (default `None`)",
        "One of `'fraction'` or `'percent'`.",
        "If `'fraction'`, the value of each bar is divided by the sum of all values at that location coordinate.",
        "`'percent'` is the same but multiplied by 100 to show percentages.",
        "`None` will stack up all values at each location coordinate.",
    ],
    groupnorm=[
        "str (default `None`)",
        "One of `'fraction'` or `'percent'`.",
        "If `'fraction'`, the value of each point is divided by the sum of all values at that location coordinate.",
        "`'percent'` is the same but multiplied by 100 to show percentages.",
        "`None` will stack up all values at each location coordinate.",
    ],
    barmode=[
        "str (default `'relative'`)",
        "One of `'group'`, `'overlay'` or `'relative'`",
        "In `'relative'` mode, bars are stacked above zero for positive values and below zero for negative values.",
        "In `'overlay'` mode, bars are drawn on top of one another.",
        "In `'group'` mode, bars are placed beside each other.",
    ],
    boxmode=[
        "str (default `'group'`)",
        "One of `'group'` or `'overlay'`",
        "In `'overlay'` mode, boxes are on drawn top of one another.",
        "In `'group'` mode, boxes are placed beside each other.",
    ],
    violinmode=[
        "str (default `'group'`)",
        "One of `'group'` or `'overlay'`",
        "In `'overlay'` mode, violins are on drawn top of one another.",
        "In `'group'` mode, violins are placed beside each other.",
    ],
    stripmode=[
        "str (default `'group'`)",
        "One of `'group'` or `'overlay'`",
        "In `'overlay'` mode, strips are on drawn top of one another.",
        "In `'group'` mode, strips are placed beside each other.",
    ],
)


def make_docstring(fn, override_dict=None, append_dict=None):
    """Build a docstring for a plotly.express chart-type function.

    The parameter documentation is resolved, in order of decreasing precedence:
      1. ``override_dict[param]`` – per-call override
      2. ``_docs_overrides[param]`` – project-wide hand-written overrides
      3. ``PARAMS.build_docs_dict(chart_name)[param]`` – chart-specific registry
      4. A sentinel ``"(missing from registry)"`` entry when none of the above match

    ``chart_name`` is taken from the decorated function's ``__name__`` (i.e. the
    public ``px.scatter`` / ``px.line`` / ... names).
    """
    override_dict = {} if override_dict is None else override_dict
    append_dict = {} if append_dict is None else append_dict
    chart_name = fn.__name__

    # ---- Build chart-specific docs dict: registry -> global overrides
    chart_docs = PARAMS.build_docs_dict(chart_name)
    chart_docs.update(_docs_overrides)

    tw = TextWrapper(
        width=75,
        initial_indent="    ",
        subsequent_indent="    ",
        break_on_hyphens=False,
    )
    result = (fn.__doc__ or "") + "\nParameters\n----------\n"
    for param in getfullargspec(fn)[0]:
        if override_dict.get(param):
            param_doc = list(override_dict[param])
        else:
            param_doc = list(chart_docs.get(param, ["(missing from registry)", ""]))
            if append_dict.get(param):
                param_doc += append_dict[param]
        param_desc_list = param_doc[1:]
        param_has_doc = param in chart_docs or param in override_dict
        param_desc = (
            tw.fill(" ".join(param_desc_list or ""))
            if param_has_doc
            else tw.fill("(documentation missing from registry)")
        )

        param_type = param_doc[0] if param_doc else "(unknown)"
        result += "%s: %s\n%s\n" % (param, param_type, param_desc)
    result += "\nReturns\n-------\n"
    result += "    plotly.graph_objects.Figure"
    return result


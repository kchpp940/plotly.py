import plotly.express as px
import plotly.graph_objects as go
import narwhals.stable.v1 as nw
import numpy as np
import pandas as pd
from plotly.express._core import build_dataframe, _is_col_list
from pandas.testing import assert_frame_equal
import pytest
import warnings


def test_is_col_list(constructor):
    df_input = nw.from_native(constructor(dict(a=[1, 2], b=[1, 2])))
    native_namespace = nw.get_native_namespace(df_input)
    columns = df_input.columns
    df_input = df_input.to_native()
    is_pd_like = nw.dependencies.is_pandas_like_dataframe(df_input)
    assert _is_col_list(columns, ["a"], is_pd_like, native_namespace)
    assert _is_col_list(columns, ["a", "b"], is_pd_like, native_namespace)
    assert _is_col_list(columns, [[3, 4]], is_pd_like, native_namespace)
    assert _is_col_list(columns, [[3, 4], [3, 4]], is_pd_like, native_namespace)
    assert not _is_col_list(columns, pytest, is_pd_like, native_namespace)
    assert not _is_col_list(columns, False, is_pd_like, native_namespace)
    assert not _is_col_list(columns, ["a", 1], is_pd_like, native_namespace)
    assert not _is_col_list(columns, "a", is_pd_like, native_namespace)
    assert not _is_col_list(columns, 1, is_pd_like, native_namespace)
    assert not _is_col_list(columns, ["a", "b", "c"], is_pd_like, native_namespace)
    assert not _is_col_list(columns, [1, 2], is_pd_like, native_namespace)


def test_is_col_list_pandas():
    df_input = pd.DataFrame([[1, 2], [1, 2]])
    is_pd_like = True
    native_namespace = pd
    columns = list(df_input.columns)
    assert _is_col_list(columns, [0], is_pd_like, native_namespace)
    assert _is_col_list(columns, [0, 1], is_pd_like, native_namespace)
    assert _is_col_list(columns, [[3, 4]], is_pd_like, native_namespace)
    assert _is_col_list(columns, [[3, 4], [3, 4]], is_pd_like, native_namespace)
    assert not _is_col_list(columns, pytest, is_pd_like, native_namespace)
    assert not _is_col_list(columns, False, is_pd_like, native_namespace)
    assert not _is_col_list(columns, ["a", 1], is_pd_like, native_namespace)
    assert not _is_col_list(columns, "a", is_pd_like, native_namespace)
    assert not _is_col_list(columns, 1, is_pd_like, native_namespace)
    assert not _is_col_list(columns, [0, 1, 2], is_pd_like, native_namespace)
    assert not _is_col_list(columns, ["a", "b"], is_pd_like, native_namespace)

    df_input = None
    is_pd_like = False
    native_namespace = None
    assert _is_col_list(df_input, [[3, 4]], is_pd_like, native_namespace)
    assert _is_col_list(df_input, [[3, 4], [3, 4]], is_pd_like, native_namespace)
    assert not _is_col_list(df_input, [0], is_pd_like, native_namespace)
    assert not _is_col_list(df_input, [0, 1], is_pd_like, native_namespace)
    assert not _is_col_list(df_input, pytest, is_pd_like, native_namespace)
    assert not _is_col_list(df_input, False, is_pd_like, native_namespace)
    assert not _is_col_list(df_input, ["a", 1], is_pd_like, native_namespace)
    assert not _is_col_list(df_input, "a", is_pd_like, native_namespace)
    assert not _is_col_list(df_input, 1, is_pd_like, native_namespace)
    assert not _is_col_list(df_input, [0, 1, 2], is_pd_like, native_namespace)
    assert not _is_col_list(df_input, ["a", "b"], is_pd_like, native_namespace)


@pytest.mark.parametrize(
    "px_fn",
    [px.scatter, px.line, px.area, px.bar, px.violin, px.box, px.strip]
    + [px.histogram, px.funnel, px.density_contour, px.density_heatmap],
)
@pytest.mark.parametrize("orientation", [None, "v", "h"])
@pytest.mark.parametrize("style", ["implicit", "explicit"])
def test_wide_mode_external(px_fn, orientation, style):
    # here we test this feature "black box" style by calling actual PX functions and
    # inspecting the figure... this is important but clunky, and is mostly a smoke test
    # allowing us to do more "white box" testing below

    if px_fn != px.funnel:
        x, y = ("y", "x") if orientation == "h" else ("x", "y")
    else:
        x, y = ("y", "x") if orientation != "v" else ("x", "y")
    xaxis, yaxis = x + "axis", y + "axis"

    df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6], c=[7, 8, 9]), index=[11, 12, 13])
    if style == "implicit":
        fig = px_fn(df, orientation=orientation)

    if px_fn in [px.scatter, px.line, px.area, px.bar, px.funnel, px.density_contour]:
        if style == "explicit":
            fig = px_fn(**{"data_frame": df, y: list(df.columns), x: df.index})
        assert len(fig.data) == 3
        assert list(fig.data[0][x]) == [11, 12, 13]
        assert list(fig.data[0][y]) == [1, 2, 3]
        assert list(fig.data[1][x]) == [11, 12, 13]
        assert list(fig.data[1][y]) == [4, 5, 6]
        assert fig.layout[xaxis].title.text == "index"
        assert fig.layout[yaxis].title.text == "value"
        assert fig.layout.legend.title.text == "variable"
    if px_fn in [px.density_heatmap]:
        if style == "explicit":
            fig = px_fn(**{"data_frame": df, y: list(df.columns), x: df.index})
        assert len(fig.data) == 1
        assert list(fig.data[0][x]) == [11, 12, 13, 11, 12, 13, 11, 12, 13]
        assert list(fig.data[0][y]) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
        assert fig.layout[xaxis].title.text == "index"
        assert fig.layout[yaxis].title.text == "value"
    if px_fn in [px.violin, px.box, px.strip]:
        if style == "explicit":
            fig = px_fn(**{"data_frame": df, y: list(df.columns)})
        assert len(fig.data) == 1
        assert list(fig.data[0][x]) == ["a"] * 3 + ["b"] * 3 + ["c"] * 3
        assert list(fig.data[0][y]) == list(range(1, 10))
        assert fig.layout[yaxis].title.text == "value"
        assert fig.layout[xaxis].title.text == "variable"
    if px_fn in [px.histogram]:
        if style == "explicit":
            fig = px_fn(**{"data_frame": df, x: list(df.columns)})
        assert len(fig.data) == 3
        assert list(fig.data[1][x]) == [4, 5, 6]
        assert fig.layout.legend.title.text == "variable"
        assert fig.layout[xaxis].title.text == "value"


def test_wide_mode_labels_external():
    # here we prove that the _uglylabels_ can be renamed using the usual labels kwarg
    df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6], c=[7, 8, 9]), index=[11, 12, 13])
    fig = px.bar(df)
    assert fig.layout.xaxis.title.text == "index"
    assert fig.layout.yaxis.title.text == "value"
    assert fig.layout.legend.title.text == "variable"
    labels = dict(index="my index", value="my value", variable="my column")
    fig = px.bar(df, labels=labels)
    assert fig.layout.xaxis.title.text == "my index"
    assert fig.layout.yaxis.title.text == "my value"
    assert fig.layout.legend.title.text == "my column"
    df.index.name = "my index"
    df.columns.name = "my column"
    fig = px.bar(df)
    assert fig.layout.xaxis.title.text == "my index"
    assert fig.layout.yaxis.title.text == "value"
    assert fig.layout.legend.title.text == "my column"


# here we do basic exhaustive testing of the various graph_object permutations
# via build_dataframe directly, which leads to more compact test code:
# we pass in args (which includes df) and look at how build_dataframe mutates
# both args and the df, and assume that since the rest of the downstream PX
# machinery has no wide-mode-specific code, and the tests above pass, that this is
# enough to prove things work
@pytest.mark.parametrize(
    "trace_type,x,y,color",
    [
        (go.Scatter, "index", "value", "variable"),
        (go.Histogram2dContour, "index", "value", "variable"),
        (go.Histogram2d, "index", "value", None),
        (go.Bar, "index", "value", "variable"),
        (go.Funnel, "index", "value", "variable"),
        (go.Box, "variable", "value", None),
        (go.Violin, "variable", "value", None),
        (go.Histogram, "value", None, "variable"),
    ],
)
@pytest.mark.parametrize("orientation", [None, "v", "h"])
def test_wide_mode_internal(trace_type, x, y, color, orientation):
    df_in = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6]), index=[11, 12, 13])
    args_in = dict(data_frame=df_in, color=None, orientation=orientation)
    args_out = build_dataframe(args_in, trace_type)
    df_out = args_out.pop("data_frame")
    expected = dict(
        variable=["a", "a", "a", "b", "b", "b"],
        value=[1, 2, 3, 4, 5, 6],
    )
    if x == "index":
        expected["index"] = [11, 12, 13, 11, 12, 13]
    assert_frame_equal(
        df_out.to_pandas(),
        pd.DataFrame(expected)[df_out.columns],
    )
    if trace_type in [go.Histogram2dContour, go.Histogram2d]:
        if orientation is None or orientation == "v":
            assert args_out == dict(x=x, y=y, color=color)
        else:
            assert args_out == dict(x=y, y=x, color=color)
    else:
        if (orientation is None and trace_type != go.Funnel) or orientation == "v":
            assert args_out == dict(x=x, y=y, color=color, orientation="v")
        else:
            assert args_out == dict(x=y, y=x, color=color, orientation="h")


cases = []
for transpose in [True, False]:
    for tt in [go.Scatter, go.Bar, go.Funnel, go.Histogram2dContour, go.Histogram2d]:
        color = None if tt == go.Histogram2d else "variable"
        df_in = dict(a=[1, 2], b=[3, 4])
        args = dict(x=None, y=["a", "b"], color=None, orientation=None)
        df_exp = dict(
            variable=["a", "a", "b", "b"],
            value=[1, 2, 3, 4],
            index=[0, 1, 0, 1],
        )
        cases.append((tt, df_in, args, "index", "value", color, df_exp, transpose))

        df_in = dict(a=[1, 2], b=[3, 4], c=[5, 6])
        args = dict(x="c", y=["a", "b"], color=None, orientation=None)
        df_exp = dict(
            variable=["a", "a", "b", "b"],
            value=[1, 2, 3, 4],
            c=[5, 6, 5, 6],
        )
        cases.append((tt, df_in, args, "c", "value", color, df_exp, transpose))

        args = dict(x=None, y=[[1, 2], [3, 4]], color=None, orientation=None)
        df_exp = dict(
            variable=[
                "wide_variable_0",
                "wide_variable_0",
                "wide_variable_1",
                "wide_variable_1",
            ],
            value=[1, 2, 3, 4],
            index=[0, 1, 0, 1],
        )
        cases.append((tt, None, args, "index", "value", color, df_exp, transpose))

    for tt in [go.Bar]:  # bar categorical exception
        df_in = dict(a=["q", "r"], b=["s", "t"])
        args = dict(x=None, y=["a", "b"], color=None, orientation=None)
        df_exp = dict(
            variable=["a", "a", "b", "b"],
            value=["q", "r", "s", "t"],
            index=[0, 1, 0, 1],
            count=[1, 1, 1, 1],
        )
        cases.append((tt, df_in, args, "value", "count", "variable", df_exp, transpose))

    for tt in [go.Violin, go.Box]:
        df_in = dict(a=[1, 2], b=[3, 4])
        args = dict(x=None, y=["a", "b"], color=None, orientation=None)
        df_exp = dict(
            variable=["a", "a", "b", "b"],
            value=[1, 2, 3, 4],
        )
        cases.append((tt, df_in, args, "variable", "value", None, df_exp, transpose))

        df_in = dict(a=[1, 2], b=[3, 4], c=[5, 6])
        args = dict(x="c", y=["a", "b"], color=None, orientation=None)
        df_exp = dict(
            variable=["a", "a", "b", "b"],
            value=[1, 2, 3, 4],
            c=[5, 6, 5, 6],
        )
        cases.append((tt, df_in, args, "c", "value", None, df_exp, transpose))

        args = dict(x=None, y=[[1, 2], [3, 4]], color=None, orientation=None)
        df_exp = dict(
            variable=[
                "wide_variable_0",
                "wide_variable_0",
                "wide_variable_1",
                "wide_variable_1",
            ],
            value=[1, 2, 3, 4],
        )
        cases.append((tt, None, args, "variable", "value", None, df_exp, transpose))

    for tt in [go.Histogram]:
        df_in = dict(a=[1, 2], b=[3, 4])
        args = dict(x=None, y=["a", "b"], color=None, orientation=None)
        df_exp = dict(
            variable=["a", "a", "b", "b"],
            value=[1, 2, 3, 4],
        )
        cases.append((tt, df_in, args, None, "value", "variable", df_exp, transpose))

        df_in = dict(a=[1, 2], b=[3, 4], c=[5, 6])
        args = dict(x="c", y=["a", "b"], color=None, orientation=None)
        df_exp = dict(
            variable=["a", "a", "b", "b"],
            value=[1, 2, 3, 4],
            c=[5, 6, 5, 6],
        )
        cases.append((tt, df_in, args, "c", "value", "variable", df_exp, transpose))

        args = dict(x=None, y=[[1, 2], [3, 4]], color=None, orientation=None)
        df_exp = dict(
            variable=[
                "wide_variable_0",
                "wide_variable_0",
                "wide_variable_1",
                "wide_variable_1",
            ],
            value=[1, 2, 3, 4],
        )
        cases.append((tt, None, args, None, "value", "variable", df_exp, transpose))


@pytest.mark.parametrize("tt,df_in,args_in,x,y,color,df_out_exp,transpose", cases)
def test_wide_x_or_y(tt, df_in, args_in, x, y, color, df_out_exp, transpose):
    if transpose:
        args_in["y"], args_in["x"] = args_in["x"], args_in["y"]
    args_in["data_frame"] = df_in
    args_out = build_dataframe(args_in, tt)
    df_out = args_out.pop("data_frame")
    assert_frame_equal(df_out.to_native(), pd.DataFrame(df_out_exp)[df_out.columns])
    if transpose:
        args_exp = dict(x=y, y=x, color=color)
    else:
        args_exp = dict(x=x, y=y, color=color)
    if tt not in [go.Histogram2dContour, go.Histogram2d]:
        orientation_exp = args_in["orientation"]
        if (args_in["x"] is None) != (args_in["y"] is None) and tt != go.Histogram:
            orientation_exp = "h" if transpose else "v"
        args_exp["orientation"] = orientation_exp
    assert args_out == args_exp


@pytest.mark.parametrize("orientation", [None, "v", "h"])
def test_wide_mode_internal_bar_exception(orientation):
    df_in = pd.DataFrame(dict(a=["q", "r", "s"], b=["t", "u", "v"]), index=[11, 12, 13])
    args_in = dict(data_frame=df_in, color=None, orientation=orientation)
    args_out = build_dataframe(args_in, go.Bar)
    df_out = args_out.pop("data_frame")
    assert_frame_equal(
        df_out.to_native(),
        pd.DataFrame(
            dict(
                index=[11, 12, 13, 11, 12, 13],
                variable=["a", "a", "a", "b", "b", "b"],
                value=["q", "r", "s", "t", "u", "v"],
                count=[1, 1, 1, 1, 1, 1],
            )
        )[df_out.columns],
    )
    if orientation is None or orientation == "v":
        assert args_out == dict(x="value", y="count", color="variable", orientation="v")
    else:
        assert args_out == dict(x="count", y="value", color="variable", orientation="h")


# given all of the above tests, and given that the melt() code is not sensitive
# to the trace type, we can do all sorts of special-case testing just by focusing
# on build_dataframe(args, go.Scatter) for various values of args, and looking at
# how args and df get mutated
special_cases = []


def append_special_case(df_in, args_in, args_expect, df_expect):
    special_cases.append((df_in, args_in, args_expect, df_expect))


# input is single bare array: column comes out as string "0"
append_special_case(
    df_in=[1, 2, 3],
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(x="index", y="value", color="variable", orientation="v"),
    df_expect=pd.DataFrame(
        dict(index=[0, 1, 2], value=[1, 2, 3], variable=["0", "0", "0"])
    ),
)

# input is single bare Series: column comes out as string "0"
append_special_case(
    df_in=pd.Series([1, 2, 3]),
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(x="index", y="value", color="variable", orientation="v"),
    df_expect=pd.DataFrame(
        dict(index=[0, 1, 2], value=[1, 2, 3], variable=["0", "0", "0"])
    ),
)

# input is a Series from a DF: we pick up the name and index values automatically
df = pd.DataFrame(dict(my_col=[1, 2, 3]), index=["a", "b", "c"])
append_special_case(
    df_in=df["my_col"],
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(x="index", y="value", color="variable", orientation="v"),
    df_expect=pd.DataFrame(
        dict(
            index=["a", "b", "c"],
            value=[1, 2, 3],
            variable=["my_col", "my_col", "my_col"],
        )
    ),
)

# input is an index from a DF: treated like a Series basically
df = pd.DataFrame(dict(my_col=[1, 2, 3]), index=["a", "b", "c"])
df.index.name = "my_index"
append_special_case(
    df_in=df.index,
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(x="index", y="value", color="variable", orientation="v"),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 2],
            value=["a", "b", "c"],
            variable=["my_index", "my_index", "my_index"],
        )
    ),
)

# input is a data frame with named row and col indices: we grab those
df = pd.DataFrame(dict(my_col=[1, 2, 3]), index=["a", "b", "c"])
df.index.name = "my_index"
df.columns.name = "my_col_name"
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(x="my_index", y="value", color="my_col_name", orientation="v"),
    df_expect=pd.DataFrame(
        dict(
            my_index=["a", "b", "c"],
            value=[1, 2, 3],
            my_col_name=["my_col", "my_col", "my_col"],
        )
    ),
)

# input is array of arrays: treated as rows, columns come out as string "0", "1"
append_special_case(
    df_in=[[1, 2], [4, 5]],
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(x="index", y="value", color="variable", orientation="v"),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 4, 2, 5],
            variable=["0", "0", "1", "1"],
        )
    ),
)

# partial-melting by assigning symbol: we pick up that column and don't melt it
append_special_case(
    df_in=pd.DataFrame(dict(a=[1, 2], b=[3, 4], symbol_col=["q", "r"])),
    args_in=dict(x=None, y=None, color=None, symbol="symbol_col"),
    args_expect=dict(
        x="index",
        y="value",
        color="variable",
        symbol="symbol_col",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            variable=["a", "a", "b", "b"],
            symbol_col=["q", "r", "q", "r"],
        )
    ),
)

# partial-melting by assigning the same column twice: we pick it up once
append_special_case(
    df_in=pd.DataFrame(dict(a=[1, 2], b=[3, 4], symbol_col=["q", "r"])),
    args_in=dict(
        x=None,
        y=None,
        color=None,
        symbol="symbol_col",
        custom_data=["symbol_col"],
    ),
    args_expect=dict(
        x="index",
        y="value",
        color="variable",
        symbol="symbol_col",
        custom_data=["symbol_col"],
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            variable=["a", "a", "b", "b"],
            symbol_col=["q", "r", "q", "r"],
        )
    ),
)

# partial-melting by assigning more than one column: we pick them both up
append_special_case(
    df_in=pd.DataFrame(
        dict(a=[1, 2], b=[3, 4], symbol_col=["q", "r"], data_col=["i", "j"])
    ),
    args_in=dict(
        x=None,
        y=None,
        color=None,
        symbol="symbol_col",
        custom_data=["data_col"],
    ),
    args_expect=dict(
        x="index",
        y="value",
        color="variable",
        symbol="symbol_col",
        custom_data=["data_col"],
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            variable=["a", "a", "b", "b"],
            symbol_col=["q", "r", "q", "r"],
            data_col=["i", "j", "i", "j"],
        )
    ),
)

# partial-melting by assigning symbol to a bare array: we pick it up with the attr name
append_special_case(
    df_in=pd.DataFrame(dict(a=[1, 2], b=[3, 4])),
    args_in=dict(x=None, y=None, color=None, symbol=["q", "r"]),
    args_expect=dict(
        x="index", y="value", color="variable", symbol="symbol", orientation="v"
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            variable=["a", "a", "b", "b"],
            symbol=["q", "r", "q", "r"],
        )
    ),
)

# assigning color to variable explicitly: just works
append_special_case(
    df_in=pd.DataFrame(dict(a=[1, 2], b=[3, 4])),
    args_in=dict(x=None, y=None, color="variable"),
    args_expect=dict(x="index", y="value", color="variable", orientation="v"),
    df_expect=pd.DataFrame(
        dict(index=[0, 1, 0, 1], value=[1, 2, 3, 4], variable=["a", "a", "b", "b"])
    ),
)

# assigning color to a different column: variable drops out of args
append_special_case(
    df_in=pd.DataFrame(dict(a=[1, 2], b=[3, 4], color_col=["q", "r"])),
    args_in=dict(x=None, y=None, color="color_col"),
    args_expect=dict(x="index", y="value", color="color_col", orientation="v"),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            variable=["a", "a", "b", "b"],
            color_col=["q", "r", "q", "r"],
        )
    ),
)

# assigning variable to something else: just works
append_special_case(
    df_in=pd.DataFrame(dict(a=[1, 2], b=[3, 4])),
    args_in=dict(x=None, y=None, color=None, symbol="variable"),
    args_expect=dict(
        x="index", y="value", color="variable", symbol="variable", orientation="v"
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            variable=["a", "a", "b", "b"],
        )
    ),
)

# swapping symbol and color: just works
append_special_case(
    df_in=pd.DataFrame(dict(a=[1, 2], b=[3, 4], color_col=["q", "r"])),
    args_in=dict(x=None, y=None, color="color_col", symbol="variable"),
    args_expect=dict(
        x="index",
        y="value",
        color="color_col",
        symbol="variable",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            variable=["a", "a", "b", "b"],
            color_col=["q", "r", "q", "r"],
        )
    ),
)

# a DF with a named column index: have to use that instead of variable
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]))
df.columns.name = "my_col_name"
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None, facet_row="my_col_name"),
    args_expect=dict(
        x="index",
        y="value",
        color="my_col_name",
        facet_row="my_col_name",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            my_col_name=["a", "a", "b", "b"],
        )
    ),
)

# passing the DF index into some other attr: works
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]))
df.columns.name = "my_col_name"
df.index.name = "my_index_name"
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None, hover_name=df.index),
    args_expect=dict(
        x="my_index_name",
        y="value",
        color="my_col_name",
        hover_name="my_index_name",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            my_index_name=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            my_col_name=["a", "a", "b", "b"],
        )
    ),
)

# assigning value to something: works
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]))
df.columns.name = "my_col_name"
df.index.name = "my_index_name"
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None, hover_name="value"),
    args_expect=dict(
        x="my_index_name",
        y="value",
        color="my_col_name",
        hover_name="value",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            my_index_name=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            my_col_name=["a", "a", "b", "b"],
        )
    ),
)

# assigning a px.Constant: works
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]))
df.columns.name = "my_col_name"
df.index.name = "my_index_name"
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None, symbol=px.Constant(1)),
    args_expect=dict(
        x="my_index_name",
        y="value",
        color="my_col_name",
        symbol="symbol",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            my_index_name=[0, 1, 0, 1],
            value=[1, 2, 3, 4],
            my_col_name=["a", "a", "b", "b"],
            symbol=[1, 1, 1, 1],
        )
    ),
)

# df has columns named after every special string
df = pd.DataFrame(dict(index=[1, 2], value=[3, 4], variable=[5, 6]), index=[7, 8])
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(
        x="_index",
        y="_value",
        color="_variable",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            _index=[7, 8, 7, 8, 7, 8],
            _value=[1, 2, 3, 4, 5, 6],
            _variable=["index", "index", "value", "value", "variable", "variable"],
        )
    ),
)

# df has columns with name collisions with indexes
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]), index=[7, 8])
df.index.name = "a"
df.columns.name = "b"
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(
        x="index",
        y="value",
        color="variable",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[7, 8, 7, 8],
            value=[1, 2, 3, 4],
            variable=["a", "a", "b", "b"],
        )
    ),
)

# everything is called value, OMG
df = pd.DataFrame(dict(b=[1, 2], value=[3, 4]), index=[7, 8])
df.index.name = "value"
df.columns.name = "value"
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None),
    args_expect=dict(
        x="index",
        y="_value",
        color="variable",
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(
            index=[7, 8, 7, 8],
            _value=[1, 2, 3, 4],
            variable=["b", "b", "value", "value"],
        )
    ),
)

# y = columns
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]), index=[7, 8])
df.index.name = "c"
df.columns.name = "d"
append_special_case(
    df_in=df,
    args_in=dict(x=df.index, y=df.columns, color=None),
    args_expect=dict(x="c", y="value", color="d"),
    df_expect=pd.DataFrame(
        dict(c=[7, 8, 7, 8], d=["a", "a", "b", "b"], value=[1, 2, 3, 4])
    ),
)

# y = columns subset
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]), index=[7, 8])
df.index.name = "c"
df.columns.name = "d"
append_special_case(
    df_in=df,
    args_in=dict(x=df.index, y=df.columns[:1], color=None),
    args_expect=dict(x="c", y="value", color="variable"),
    df_expect=pd.DataFrame(dict(c=[7, 8], variable=["a", "a"], value=[1, 2])),
)

# list-like hover_data
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]), index=[7, 8])
df.index.name = "c"
df.columns.name = "d"
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=None, hover_data=dict(new=[5, 6])),
    args_expect=dict(
        x="c",
        y="value",
        color="d",
        orientation="v",
        hover_data=dict(new=(True, [5, 6])),
    ),
    df_expect=pd.DataFrame(
        dict(
            c=[7, 8, 7, 8], d=["a", "a", "b", "b"], new=[5, 6, 5, 6], value=[1, 2, 3, 4]
        )
    ),
)

# NO_COLOR
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]))
append_special_case(
    df_in=df,
    args_in=dict(x=None, y=None, color=px.NO_COLOR),
    args_expect=dict(
        x="index",
        y="value",
        color=None,
        orientation="v",
    ),
    df_expect=pd.DataFrame(
        dict(variable=["a", "a", "b", "b"], index=[0, 1, 0, 1], value=[1, 2, 3, 4])
    ),
)


@pytest.mark.parametrize("df_in, args_in, args_expect, df_expect", special_cases)
def test_wide_mode_internal_special_cases(df_in, args_in, args_expect, df_expect):
    args_in["data_frame"] = df_in
    args_out = build_dataframe(args_in, go.Scatter)
    df_out = args_out.pop("data_frame")

    assert args_out == args_expect
    assert_frame_equal(
        df_out.to_pandas(),
        df_expect[df_out.columns],
    )


def test_multi_index():
    df = pd.DataFrame([[1, 2, 3, 4], [3, 4, 5, 6], [1, 2, 3, 4], [3, 4, 5, 6]])
    df.index = [["a", "a", "b", "b"], ["c", "d", "c", "d"]]
    with pytest.raises(TypeError) as err_msg:
        px.scatter(df)
    assert "pandas MultiIndex is not supported by plotly express" in str(err_msg.value)

    df = pd.DataFrame([[1, 2, 3, 4], [3, 4, 5, 6], [1, 2, 3, 4], [3, 4, 5, 6]])
    df.columns = [["e", "e", "f", "f"], ["g", "h", "g", "h"]]
    with pytest.raises(TypeError) as err_msg:
        px.scatter(df)
    assert "pandas MultiIndex is not supported by plotly express" in str(err_msg.value)


@pytest.mark.parametrize("df", [px.data.stocks(), dict(a=[1, 2], b=["1", "2"])])
def test_mixed_input_error(df):
    with pytest.raises(ValueError) as err_msg:
        px.line(df)
    assert (
        "Plotly Express cannot process wide-form data with columns of different type"
        in str(err_msg.value)
    )


def test_mixed_number_input(constructor):
    df = constructor(dict(a=[1, 2], b=[1.1, 2.1]))
    fig = px.line(df)
    assert len(fig.data) == 2


def test_line_group(constructor):
    df = constructor(
        {
            "who": ["a", "a", "b", "b"],
            "x": [0, 1, 0, 1],
            "score": [1.0, 2, 3, 4],
            "miss": [3.2, 2.5, 1.3, 1.5],
        }
    )
    fig = px.line(df, x="x", y=["miss", "score"])
    assert len(fig.data) == 2
    fig = px.line(df, x="x", y=["miss", "score"], color="who")
    assert len(fig.data) == 4
    fig = px.scatter(df, x="x", y=["miss", "score"], color="who")
    assert len(fig.data) == 2


def test_no_pd_perf_warning():
    n_cols = 1000
    n_rows = 1000

    columns = list(f"col_{c}" for c in range(n_cols))
    index = list(f"i_{r}" for r in range(n_rows))

    df = pd.DataFrame(
        np.random.uniform(size=(n_rows, n_cols)), index=index, columns=columns
    )

    with warnings.catch_warnings(record=True) as warn_list:
        _ = px.bar(
            df,
            x=df.index,
            y=df.columns[:-2],
            labels=df.columns[:-2],
        )
    performance_warnings = [
        warn
        for warn in warn_list
        if issubclass(warn.category, pd.errors.PerformanceWarning)
    ]
    assert len(performance_warnings) == 0, "PerformanceWarning(s) raised!"


def test_wide_mode_duplicate_columns_pandas():
    """Test that pandas DataFrames with duplicate column names work in wide mode.

    Regression test for duplicate column handling: columns should be de-duplicated
    internally but original names preserved for display (trace names, hovertemplate).
    """
    df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=["a", "a", "b"])

    # Test px.line
    fig = px.line(df, y=["a", "a", "b"])
    assert len(fig.data) == 3, f"Expected 3 traces, got {len(fig.data)}"
    trace_names = [t.name for t in fig.data]
    assert trace_names == ["a", "a", "b"], f"Expected ['a', 'a', 'b'], got {trace_names}"
    # Verify data is correctly separated
    assert list(fig.data[0].y) == [1, 4]
    assert list(fig.data[1].y) == [2, 5]
    assert list(fig.data[2].y) == [3, 6]
    # Verify no internal names leak into hovertemplate
    for t in fig.data:
        assert "wide_variable" not in str(t.hovertemplate)
        assert "wide_cross" not in str(t.hovertemplate)
        # Verify hovertemplate uses original names (not a_1 etc.)
        assert "a_1" not in str(t.hovertemplate)

    # Test px.bar
    fig_bar = px.bar(df, y=["a", "a", "b"])
    assert len(fig_bar.data) == 3
    assert [t.name for t in fig_bar.data] == ["a", "a", "b"]

    # Test px.area
    fig_area = px.area(df, y=["a", "a", "b"])
    assert len(fig_area.data) == 3
    assert [t.name for t in fig_area.data] == ["a", "a", "b"]


def test_wide_mode_labels_and_duplicate_columns():
    """Test that labels work correctly with duplicate column names."""
    df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=["a", "a", "b"])

    fig = px.line(
        df, y=["a", "a", "b"],
        labels={"variable": "MySeries", "value": "MyValue", "a": "LabelA"}
    )
    assert fig.layout.legend.title.text == "MySeries"
    assert fig.layout.yaxis.title.text == "MyValue"
    trace_names = [t.name for t in fig.data]
    # Trace names still show original column names (a, a, b), not labels
    assert trace_names == ["a", "a", "b"]
    # Hovertemplate should show "MySeries" as the key label
    for t in fig.data:
        assert "MySeries=" in str(t.hovertemplate)
        assert "MyValue=" in str(t.hovertemplate)
        # Internal names should not appear
        assert "wide_variable" not in str(t.hovertemplate)
        assert "wide_cross" not in str(t.hovertemplate)


def test_wide_mode_named_index():
    """Test that named pandas Index is correctly used as axis title."""
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    df.index.name = "time_idx"

    # Test px.line with implicit x (index)
    fig = px.line(df)
    assert fig.layout.xaxis.title.text == "time_idx"
    assert fig.layout.yaxis.title.text == "value"
    assert fig.layout.legend.title.text == "variable"
    assert len(fig.data) == 2
    assert [t.name for t in fig.data] == ["a", "b"]

    # Test with labels override
    fig2 = px.line(df, labels={"variable": "Series", "value": "Amount"})
    assert fig2.layout.legend.title.text == "Series"
    assert fig2.layout.yaxis.title.text == "Amount"
    for t in fig2.data:
        assert "time_idx=%{x}" in str(t.hovertemplate)


@pytest.mark.parametrize("px_fn", [px.line, px.area, px.bar])
def test_wide_mode_polars_consistency(px_fn):
    """Test that pandas and polars backends produce consistent output in wide mode.

    Tests axis titles, legend titles, trace names, and hovertemplate consistency.
    """
    try:
        import polars as pl
    except ImportError:
        pytest.skip("polars not installed")

    # pandas input
    df_pd = pd.DataFrame({"x": [1, 2, 3], "y1": [4, 5, 6], "y2": [7, 8, 9]})
    fig_pd = px_fn(
        df_pd, x="x", y=["y1", "y2"],
        labels={"variable": "Series", "value": "Value"}
    )

    # polars input (Narwhals backend)
    df_pl = pl.DataFrame({"x": [1, 2, 3], "y1": [4, 5, 6], "y2": [7, 8, 9]})
    fig_pl = px_fn(
        df_pl, x="x", y=["y1", "y2"],
        labels={"variable": "Series", "value": "Value"}
    )

    # Compare axis titles
    assert fig_pd.layout.xaxis.title.text == fig_pl.layout.xaxis.title.text
    assert fig_pd.layout.yaxis.title.text == fig_pl.layout.yaxis.title.text

    # Compare legend titles
    pd_legend_title = fig_pd.layout.legend.title.text if fig_pd.layout.legend.title else None
    pl_legend_title = fig_pl.layout.legend.title.text if fig_pl.layout.legend.title else None
    assert pd_legend_title == pl_legend_title

    # Compare number of traces
    assert len(fig_pd.data) == len(fig_pl.data)

    # Compare trace names
    pd_trace_names = [t.name for t in fig_pd.data]
    pl_trace_names = [t.name for t in fig_pl.data]
    assert pd_trace_names == pl_trace_names

    # Check no internal names leak in either
    for fig in [fig_pd, fig_pl]:
        for t in fig.data:
            ht = str(t.hovertemplate)
            assert "wide_variable" not in ht, f"Internal name leak: {ht}"
            assert "wide_cross" not in ht, f"Internal name leak: {ht}"


def test_wide_mode_no_internal_name_leaks():
    """Regression test: ensure wide_variable and wide_cross never appear in output.

    Tests px.line, px.area, and px.bar with various wide-form configurations.
    """
    test_configs = [
        # (px_fn, df_kwargs, call_kwargs)
        (px.line, {"data": {"a": [1, 2, 3], "b": [4, 5, 6]}}, {}),
        (px.area, {"data": {"a": [1, 2, 3], "b": [4, 5, 6]}}, {}),
        (px.bar, {"data": {"a": [1, 2, 3], "b": [4, 5, 6]}}, {}),
        (px.line, {"data": {"x": [1, 2, 3], "y1": [4, 5, 6], "y2": [7, 8, 9]}}, {"x": "x", "y": ["y1", "y2"]}),
        (px.area, {"data": {"x": [1, 2, 3], "y1": [4, 5, 6], "y2": [7, 8, 9]}}, {"x": "x", "y": ["y1", "y2"]}),
        (px.bar, {"data": {"cat": ["A", "B"], "v1": [1, 2], "v2": [3, 4]}}, {"x": "cat", "y": ["v1", "v2"]}),
    ]

    for px_fn, df_kwargs, call_kwargs in test_configs:
        df = pd.DataFrame(**df_kwargs)
        fig = px_fn(df, **call_kwargs)
        for trace in fig.data:
            ht = str(trace.hovertemplate) if trace.hovertemplate else ""
            assert "wide_variable" not in ht, (
                f"{px_fn.__name__}: internal name 'wide_variable' leaked into "
                f"hovertemplate: {ht}"
            )
            assert "wide_cross" not in ht, (
                f"{px_fn.__name__}: internal name 'wide_cross' leaked into "
                f"hovertemplate: {ht}"
            )


import plotly.express as px
import narwhals.stable.v1 as nw
import numpy as np
import pandas as pd
import pytest
from collections import OrderedDict  # an OrderedDict is needed for Python 2


def test_skip_hover(backend):
    df = px.data.iris(return_type=backend)
    fig = px.scatter(
        df,
        x="petal_length",
        y="petal_width",
        size="species_id",
        hover_data={"petal_length": None, "petal_width": None},
    )
    assert fig.data[0].hovertemplate == "species_id=%{marker.size}<extra></extra>"


def test_hover_data_string_column(backend):
    df = px.data.tips(return_type=backend)
    fig = px.scatter(
        df,
        x="tip",
        y="total_bill",
        hover_data="sex",
    )
    assert "sex" in fig.data[0].hovertemplate


def test_composite_hover(backend):
    df = px.data.tips(return_type=backend)
    hover_dict = OrderedDict(
        {"day": False, "time": False, "sex": True, "total_bill": ":.1f"}
    )
    fig = px.scatter(
        df,
        x="tip",
        y="total_bill",
        color="day",
        facet_row="time",
        hover_data=hover_dict,
    )
    for el in ["tip", "total_bill", "sex"]:
        assert el in fig.data[0].hovertemplate
    for el in ["day", "time"]:
        assert el not in fig.data[0].hovertemplate
    assert ":.1f" in fig.data[0].hovertemplate


def test_newdatain_hover_data():
    hover_dicts = [
        {"comment": ["a", "b", "c"]},
        {"comment": (1.234, 45.3455, 5666.234)},
        {"comment": [1.234, 45.3455, 5666.234]},
        {"comment": np.array([1.234, 45.3455, 5666.234])},
        {"comment": pd.Series([1.234, 45.3455, 5666.234])},
    ]
    for hover_dict in hover_dicts:
        fig = px.scatter(x=[1, 2, 3], y=[3, 4, 5], hover_data=hover_dict)
        assert (
            fig.data[0].hovertemplate
            == "x=%{x}<br>y=%{y}<br>comment=%{customdata[0]}<extra></extra>"
        )
    fig = px.scatter(
        x=[1, 2, 3], y=[3, 4, 5], hover_data={"comment": (True, ["a", "b", "c"])}
    )
    assert (
        fig.data[0].hovertemplate
        == "x=%{x}<br>y=%{y}<br>comment=%{customdata[0]}<extra></extra>"
    )
    hover_dicts = [
        {"comment": (":.1f", (1.234, 45.3455, 5666.234))},
        {"comment": (":.1f", [1.234, 45.3455, 5666.234])},
        {"comment": (":.1f", np.array([1.234, 45.3455, 5666.234]))},
        {"comment": (":.1f", pd.Series([1.234, 45.3455, 5666.234]))},
    ]
    for hover_dict in hover_dicts:
        fig = px.scatter(
            x=[1, 2, 3],
            y=[3, 4, 5],
            hover_data=hover_dict,
        )
        assert (
            fig.data[0].hovertemplate
            == "x=%{x}<br>y=%{y}<br>comment=%{customdata[0]:.1f}<extra></extra>"
        )


def test_formatted_hover_and_labels(backend):
    df = px.data.tips(return_type=backend)
    fig = px.scatter(
        df,
        x="tip",
        y="total_bill",
        hover_data={"total_bill": ":.1f"},
        labels={"total_bill": "Total bill"},
    )
    assert ":.1f" in fig.data[0].hovertemplate


def test_fail_wrong_column():
    # Testing for each of bare string, list, and basic dictionary
    for hover_data_value in ["d", ["d"], {"d": True}]:
        with pytest.raises(ValueError) as err_msg:
            px.scatter(
                {"a": [1, 2], "b": [3, 4], "c": [2, 1]},
                x="a",
                y="b",
                hover_data=hover_data_value,
            )
        assert (
            "Value of 'hover_data_0' is not the name of a column in 'data_frame'."
            in str(err_msg.value)
        )
    # Testing other dictionary possibilities below
    with pytest.raises(ValueError) as err_msg:
        px.scatter(
            {"a": [1, 2], "b": [3, 4], "c": [2, 1]},
            x="a",
            y="b",
            hover_data={"d": ":.1f"},
        )
    assert (
        "Value of 'hover_data_0' is not the name of a column in 'data_frame'."
        in str(err_msg.value)
    )
    with pytest.raises(ValueError) as err_msg:
        px.scatter(
            {"a": [1, 2], "b": [3, 4], "c": [2, 1]},
            x="a",
            y="b",
            hover_data={"d": [3, 4, 5]},  # d is too long
        )
    assert (
        "All arguments should have the same length. The length of hover_data key `d` is 3"
        in str(err_msg.value)
    )
    with pytest.raises(ValueError) as err_msg:
        px.scatter(
            {"a": [1, 2], "b": [3, 4], "c": [2, 1]},
            x="a",
            y="b",
            hover_data={"d": (True, [3, 4, 5])},  # d is too long
        )
    assert (
        "All arguments should have the same length. The length of hover_data key `d` is 3"
        in str(err_msg.value)
    )
    with pytest.raises(ValueError) as err_msg:
        px.scatter(
            {"a": [1, 2], "b": [3, 4], "c": [2, 1]},
            x="a",
            y="b",
            hover_data={"c": [3, 4]},
        )
    assert (
        "Ambiguous input: values for 'c' appear both in hover_data and data_frame"
        in str(err_msg.value)
    )
    with pytest.raises(ValueError) as err_msg:
        px.scatter(
            {"a": [1, 2], "b": [3, 4], "c": [2, 1]},
            x="a",
            y="b",
            hover_data={"c": (True, [3, 4])},
        )
    assert (
        "Ambiguous input: values for 'c' appear both in hover_data and data_frame"
        in str(err_msg.value)
    )


def test_sunburst_hoverdict_color(backend):
    df = px.data.gapminder(year=2007, return_type=backend)
    fig = px.sunburst(
        df,
        path=["continent", "country"],
        values="pop",
        color="lifeExp",
        hover_data={"pop": ":,"},
    )
    assert "color" in fig.data[0].hovertemplate


def test_date_in_hover(constructor):
    df = nw.from_native(
        constructor({"date": ["2015-04-04 19:31:30+0100"], "value": [3]})
    ).with_columns(date=nw.col("date").str.to_datetime(format="%Y-%m-%d %H:%M:%S%z"))
    fig = px.scatter(df.to_native(), x="value", y="value", hover_data=["date"])

    # Check that what gets displayed is the local datetime
    assert nw.to_py_scalar(fig.data[0].customdata[0][0]) == nw.to_py_scalar(
        df.item(row=0, column="date")
    ).replace(tzinfo=None)


@pytest.mark.parametrize("px_fn", [px.line, px.area, px.bar])
def test_wide_form_hover_data_list_custom_data_list(px_fn):
    """Regression test: hover_data (list) and custom_data (list) work together in wide-form.

    Both hover_data and custom_data columns should be preserved after melt,
    and customdata should contain all unique columns from both.
    """
    df = pd.DataFrame({
        "x": [1, 2, 3],
        "y1": [4, 5, 6],
        "y2": [7, 8, 9],
        "h1": [10, 11, 12],
        "h2": [100, 200, 300],
    })

    fig = px_fn(df, x="x", y=["y1", "y2"], hover_data=["h1", "h2"], custom_data=["h1"])

    # Two traces for y1 and y2
    assert len(fig.data) == 2
    for trace in fig.data:
        # customdata should have 2 columns: h1, h2 (h1 appears in both but deduplicated)
        assert trace.customdata is not None
        n_cols = len(trace.customdata[0]) if len(trace.customdata) > 0 else 0
        assert n_cols == 2, f"Expected 2 customdata columns, got {n_cols}"
        # h1 values
        assert [row[0] for row in trace.customdata] == [10, 11, 12]
        # h2 values
        assert [row[1] for row in trace.customdata] == [100, 200, 300]
        # hovertemplate should reference both columns
        ht = str(trace.hovertemplate)
        assert "h1=%{customdata[0]}" in ht
        assert "h2=%{customdata[1]}" in ht
        # No internal name leaks
        assert "wide_variable" not in ht
        assert "wide_cross" not in ht


@pytest.mark.parametrize("px_fn", [px.line, px.area, px.bar])
def test_wide_form_hover_data_dict_custom_data_list(px_fn):
    """Regression test: hover_data (dict) and custom_data (list) work together in wide-form.

    hover_data dict with format specifiers should be applied correctly, and
    all columns should be preserved in customdata.
    """
    df = pd.DataFrame({
        "x": [1, 2, 3],
        "y1": [4.5, 5.5, 6.5],
        "y2": [7.5, 8.5, 9.5],
        "h1": [10, 11, 12],
        "h2": [100.123, 200.456, 300.789],
    })

    fig = px_fn(
        df, x="x", y=["y1", "y2"],
        hover_data={"h1": True, "h2": ":,.2f"},
        custom_data=["h1"]
    )

    assert len(fig.data) == 2
    for trace in fig.data:
        # customdata should have 2 columns: h1, h2
        assert trace.customdata is not None
        n_cols = len(trace.customdata[0]) if len(trace.customdata) > 0 else 0
        assert n_cols == 2, f"Expected 2 customdata columns, got {n_cols}"
        # hovertemplate should reference both columns with formatting applied to h2
        ht = str(trace.hovertemplate)
        assert "h1=%{customdata[0]}" in ht
        assert "h2=%{customdata[1]:,.2f}" in ht
        # No internal name leaks
        assert "wide_variable" not in ht
        assert "wide_cross" not in ht


@pytest.mark.parametrize("px_fn", [px.line, px.area, px.bar])
def test_wide_form_hover_data_labels(px_fn):
    """Regression test: labels work correctly with hover_data in wide-form mode."""
    df = pd.DataFrame({
        "x": [1, 2, 3],
        "y1": [4, 5, 6],
        "y2": [7, 8, 9],
        "extra": [10, 11, 12],
    })

    fig = px_fn(
        df, x="x", y=["y1", "y2"],
        labels={
            "x": "Custom X",
            "y1": "First Series",
            "variable": "The Series",
            "value": "The Value",
            "extra": "Extra Info",
        },
        hover_data={"extra": True},
    )

    # Axis titles should use labels
    assert fig.layout.xaxis.title.text == "Custom X"
    assert fig.layout.yaxis.title.text == "The Value"
    assert fig.layout.legend.title.text == "The Series"

    for trace in fig.data:
        ht = str(trace.hovertemplate)
        # hovertemplate should use custom labels
        assert "The Series=" in ht
        assert "The Value=" in ht
        assert "Extra Info=%{customdata[0]}" in ht
        # No internal name leaks
        assert "wide_variable" not in ht
        assert "wide_cross" not in ht


def test_wide_form_hover_and_custom_no_field_overlap():
    """Regression test: hover_data and custom_data should not overwrite each other.

    When both are used in wide-form, the unpivot (melt) should preserve all columns
    and temporary melt fields should never overwrite user-provided columns.
    """
    df = pd.DataFrame({
        "x": [1, 2, 3],
        "y1": [4, 5, 6],
        "y2": [7, 8, 9],
        "variable": [10, 20, 30],  # Column with same name as melt field
        "value": [100, 200, 300],     # Column with same name as melt field
    })

    # This should not crash, and user's 'variable' and 'value' columns should be preserved
    fig = px.line(
        df, x="x", y=["y1", "y2"],
        hover_data=["variable", "value"],
    )

    assert len(fig.data) == 2
    for trace in fig.data:
        ht = str(trace.hovertemplate)
        # User's 'variable' and 'value' columns should appear in customdata
        # (they are distinct from the melt variable/value fields)
        assert "variable=%{customdata" in ht or "%{customdata" in ht
        # No internal name leaks
        assert "wide_variable" not in ht
        assert "wide_cross" not in ht


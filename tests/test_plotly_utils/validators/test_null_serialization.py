import json
import tempfile
import os
import math
import pytest

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from _plotly_utils.basevalidators import (
    copy_to_readonly_numpy_array,
    to_scalar_or_list,
    is_null_value,
    _clean_null_scalar,
    _clean_array_nulls,
    DataArrayValidator,
)
from _plotly_utils.utils import PlotlyJSONEncoder


# =============================================================================
# Section 1: Unit tests for helper functions
# =============================================================================
class TestNullHelpers:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, True),
            (pd.NA, True),
            (pd.NaT, True),
            (np.ma.core.masked, True),
            (np.datetime64("NaT"), True),
            (np.datetime64("NaT", "us"), True),
            (float("nan"), True),
            (np.float64("nan"), True),
            (0, False),
            (0.0, False),
            ("", False),
            (False, False),
            (pd.Timestamp("2021-01-01"), False),
            (np.datetime64("2021-01-01"), False),
            (1, False),
            ("hello", False),
        ],
    )
    def test_is_null_value(self, value, expected):
        assert is_null_value(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, None),
            (pd.NA, None),
            (pd.NaT, None),
            (np.ma.core.masked, None),
            (np.datetime64("NaT"), None),
            (float("nan"), None),
            (1, 1),
            ("hello", "hello"),
            (pd.Timestamp("2021-01-01"), pd.Timestamp("2021-01-01")),
        ],
    )
    def test_clean_null_scalar(self, value, expected):
        result = _clean_null_scalar(value)
        if expected is None or (isinstance(expected, float) and math.isnan(expected)):
            if result is None:
                return
            assert math.isnan(result)
        else:
            assert result == expected

    def test_clean_array_nulls_object_with_pd_NA(self):
        arr = np.array([1, pd.NA, 3, pd.NA, 5], dtype=object)
        cleaned = _clean_array_nulls(arr)
        assert cleaned.dtype == object
        assert cleaned[1] is None
        assert cleaned[3] is None
        assert cleaned[0] == 1
        assert cleaned[2] == 3

    def test_clean_array_nulls_object_with_pd_NaT(self):
        arr = np.array(
            [pd.Timestamp("2021-01-01"), pd.NaT, pd.Timestamp("2021-01-03")],
            dtype=object,
        )
        cleaned = _clean_array_nulls(arr)
        assert cleaned.dtype == object
        assert cleaned[1] is None

    def test_clean_array_nulls_datetime64(self):
        arr = np.array(
            ["2021-01-01", "NaT", "2021-01-03"], dtype="datetime64[us]"
        )
        cleaned = _clean_array_nulls(arr)
        assert cleaned.dtype == object
        assert cleaned[1] is None
        assert cleaned[0].year == 2021

    def test_clean_array_nulls_float_nan_unchanged(self):
        arr = np.array([1.0, np.nan, 3.0])
        cleaned = _clean_array_nulls(arr)
        assert cleaned is arr
        assert np.isnan(cleaned[1])


# =============================================================================
# Section 2: copy_to_readonly_numpy_array tests
# =============================================================================
class TestCopyToReadonlyNullHandling:
    def test_int64_nullable_series(self):
        s = pd.Series([1, pd.NA, 3, pd.NA, 5], dtype="Int64")
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype.kind == "f"
        assert not result.flags["WRITEABLE"]
        assert np.isnan(result[1])
        assert np.isnan(result[3])

    def test_float64_nullable_series(self):
        s = pd.Series([1.0, pd.NA, 3.0], dtype="Float64")
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype.kind == "f"
        assert np.isnan(result[1])

    def test_string_nullable_series(self):
        s = pd.Series(["a", pd.NA, "c"], dtype="string")
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype == object
        assert result[1] is None
        assert result[0] == "a"
        assert result[2] == "c"

    def test_boolean_nullable_series(self):
        s = pd.Series([True, pd.NA, False], dtype="boolean")
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype == object
        assert result[1] is None
        assert result[0] is True
        assert result[2] is False

    def test_datetime_with_nat(self):
        s = pd.Series(
            pd.to_datetime(["2021-01-01", pd.NaT, "2021-01-03"])
        )
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype == object
        assert result[1] is None

    def test_np_masked_array_int(self):
        arr = np.ma.array([1, 2, 3], mask=[False, True, False])
        result = copy_to_readonly_numpy_array(arr)
        assert result.dtype.kind == "f"
        assert np.isnan(result[1])

    def test_np_masked_array_float(self):
        data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        masked = np.ma.masked_where(data == 5.0, data)
        result = copy_to_readonly_numpy_array(masked)
        assert result.dtype.kind == "f"
        assert np.isnan(result[1, 1])

    def test_object_array_pd_na(self):
        arr = np.array([1, pd.NA, 3], dtype=object)
        result = copy_to_readonly_numpy_array(arr)
        assert result.dtype == object
        assert result[1] is None
        assert result[0] == 1


# =============================================================================
# Section 3: to_scalar_or_list tests
# =============================================================================
class TestToScalarOrListNulls:
    def test_list_of_nullable_series_for_table(self):
        cells_values = [
            pd.Series([1, pd.NA, 3], dtype="Int64"),
            pd.Series(["a", None, "c"], dtype="string"),
            pd.Series(pd.to_datetime(["2021-01-01", pd.NaT, "2021-01-03"])),
        ]
        result = to_scalar_or_list(cells_values)

        assert isinstance(result, list)
        assert len(result) == 3

        assert isinstance(result[0][0], (int, float))
        assert result[0][0] == 1
        assert result[0][1] is None or (isinstance(result[0][1], float) and math.isnan(result[0][1]))

        assert result[1][0] == "a"
        assert result[1][1] is None

        assert result[2][0].year == 2021
        assert result[2][1] is None

    def test_object_array_preserves_types(self):
        arr = np.array([1, pd.NA, 3], dtype=object)
        result = to_scalar_or_list(arr)
        assert result[0] == 1
        assert result[1] is None
        assert result[2] == 3


# =============================================================================
# Section 4: PlotlyJSONEncoder tests
# =============================================================================
class TestPlotlyJSONEncoderNulls:
    def test_pd_na_in_list(self):
        data = [1, pd.NA, 3]
        s = json.dumps(data, cls=PlotlyJSONEncoder)
        result = json.loads(s)
        assert result == [1, None, 3]

    def test_pd_nat_in_list(self):
        data = [pd.Timestamp("2021-01-01"), pd.NaT]
        s = json.dumps(data, cls=PlotlyJSONEncoder)
        result = json.loads(s)
        assert result[0].startswith("2021-01-01")
        assert result[1] is None

    def test_np_masked_singleton(self):
        data = [1, np.ma.core.masked, 3]
        s = json.dumps(data, cls=PlotlyJSONEncoder)
        result = json.loads(s)
        assert result == [1, None, 3]

    def test_datetime64_nat(self):
        data = [np.datetime64("2021-01-01"), np.datetime64("NaT")]
        s = json.dumps(data, cls=PlotlyJSONEncoder)
        result = json.loads(s)
        assert "2021-01-01" in result[0]
        assert result[1] is None

    def test_datetime64_array_with_nat(self):
        arr = np.array(
            ["2021-01-01", "NaT", "2021-01-03"], dtype="datetime64[us]"
        )
        s = json.dumps(arr, cls=PlotlyJSONEncoder)
        result = json.loads(s)
        assert "2021-01-01" in result[0]
        assert result[1] is None
        assert "2021-01-03" in result[2]


# =============================================================================
# Section 5: Full Figure / end-to-end tests
# =============================================================================
class TestScatterNullsEndToEnd:
    def test_scatter_int64_nullable_series_json_roundtrip(self):
        s = pd.Series([1, pd.NA, 3, pd.NA, 5], dtype="Int64")
        fig = go.Figure(go.Scatter(x=s, y=s, mode="markers"))

        json_str = fig.to_json(engine="json")
        parsed = json.loads(json_str)

        x = parsed["data"][0]["x"]
        if isinstance(x, dict):
            import base64

            x_arr = np.frombuffer(
                base64.b64decode(x["bdata"]), dtype=x["dtype"]
            )
            assert np.isnan(x_arr[1])
            assert np.isnan(x_arr[3])
        else:
            assert x[1] is None
            assert x[3] is None

    def test_scatter_datetime_nat_json_roundtrip(self):
        dates = pd.to_datetime(
            ["2021-01-01", pd.NaT, "2021-01-03", pd.NaT, "2021-01-05"]
        )
        fig = go.Figure(go.Scatter(x=dates, y=[1, 2, 3, 4, 5]))

        json_str = fig.to_json(engine="json")
        parsed = json.loads(json_str)

        x = parsed["data"][0]["x"]
        assert "2021-01-01" in x[0]
        assert x[1] is None
        assert "2021-01-03" in x[2]
        assert x[3] is None

    def test_scatter_datetime_nat_write_json(self):
        dates = pd.to_datetime(["2021-01-01", pd.NaT, "2021-01-03"])
        fig = go.Figure(go.Scatter(x=dates, y=[1, 2, 3]))
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            fname = f.name
        try:
            fig.write_json(fname)
            with open(fname) as f:
                loaded = json.load(f)
            x = loaded["data"][0]["x"]
            assert "2021-01-01" in x[0]
            assert x[1] is None
            assert "2021-01-03" in x[2]
        finally:
            os.unlink(fname)

    @pytest.mark.parametrize("engine", ["json", pytest.param(
        "orjson", marks=pytest.mark.skipif(
            __import__("importlib").util.find_spec("orjson") is None,
            reason="orjson not installed",
        )
    )])
    def test_scatter_nulls_both_engines(self, engine):
        dates = pd.to_datetime(
            ["2021-01-01", pd.NaT, "2021-01-03"]
        )
        fig = go.Figure(go.Scatter(x=dates, y=[1, 2, 3]))
        json_str = fig.to_json(engine=engine)
        parsed = json.loads(json_str)
        x = parsed["data"][0]["x"]
        assert "2021-01-01" in x[0]
        assert x[1] is None


class TestHeatmapNullsEndToEnd:
    def test_heatmap_np_masked_array(self):
        data = np.array(
            [[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=float
        )
        masked = np.ma.masked_where(data == 5, data)
        fig = go.Figure(go.Heatmap(z=masked))

        json_str = fig.to_json(engine="json")
        parsed = json.loads(json_str)
        z = parsed["data"][0]["z"]

        if isinstance(z, dict):
            import base64

            z_arr = np.frombuffer(
                base64.b64decode(z["bdata"]), dtype=z["dtype"]
            ).reshape(3, 3)
            assert np.isnan(z_arr[1, 1])
        else:
            assert z[1][1] is None or (
                isinstance(z[1][1], float) and math.isnan(z[1][1])
            )


class TestTableNullsEndToEnd:
    def test_table_mixed_nullable_series(self):
        cells_values = [
            pd.Series([1, pd.NA, 3], dtype="Int64"),
            pd.Series(["a", None, "c"], dtype="string"),
            pd.Series(
                pd.to_datetime(["2021-01-01", pd.NaT, "2021-01-03"])
            ),
        ]
        fig = go.Figure(
            go.Table(
                header=dict(values=["A", "B", "C"]),
                cells=dict(values=cells_values),
            )
        )

        json_str = fig.to_json(engine="json")
        parsed = json.loads(json_str)
        vals = parsed["data"][0]["cells"]["values"]

        col0 = vals[0]
        assert isinstance(col0[0], (int, float))
        assert col0[0] == 1
        assert col0[1] is None
        assert col0[2] == 3
        assert col0[1] != "None"

        col1 = vals[1]
        assert col1[0] == "a"
        assert col1[1] is None
        assert col1[2] == "c"
        assert col1[0] != "'a'"

        col2 = vals[2]
        assert "2021-01-01" in col2[0]
        assert col2[1] is None
        assert "2021-01-03" in col2[2]

    def test_table_nulls_write_json(self):
        cells_values = [
            pd.Series([1, pd.NA, 3], dtype="Int64"),
        ]
        fig = go.Figure(
            go.Table(
                header=dict(values=["A"]),
                cells=dict(values=cells_values),
            )
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            fname = f.name
        try:
            fig.write_json(fname)
            with open(fname) as f:
                loaded = json.load(f)
            vals = loaded["data"][0]["cells"]["values"]
            assert vals[0][1] is None
        finally:
            os.unlink(fname)


# =============================================================================
# Section 6: Ensure normal (non-null) values are preserved
# =============================================================================
class TestNormalValuesPreserved:
    def test_normal_int_list(self):
        result = copy_to_readonly_numpy_array([1, 2, 3])
        assert result.dtype.kind in ("i", "u")
        assert list(result) == [1, 2, 3]

    def test_normal_float_list(self):
        result = copy_to_readonly_numpy_array([1.0, 2.0, 3.0])
        assert result.dtype.kind == "f"

    def test_normal_scatter_roundtrip(self):
        fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        parsed = json.loads(fig.to_json())
        assert parsed["data"][0]["x"] == [1, 2, 3]
        assert parsed["data"][0]["y"] == [4, 5, 6]

    def test_normal_dates_roundtrip(self):
        dates = pd.to_datetime(["2021-01-01", "2021-01-02", "2021-01-03"])
        fig = go.Figure(go.Scatter(x=dates, y=[1, 2, 3]))
        parsed = json.loads(fig.to_json())
        x = parsed["data"][0]["x"]
        assert "2021-01-01" in x[0]
        assert "2021-01-02" in x[1]
        assert "2021-01-03" in x[2]

    def test_normal_strings_table(self):
        cells_values = [
            pd.Series([1, 2, 3], dtype="Int64"),
            pd.Series(["a", "b", "c"], dtype="string"),
        ]
        fig = go.Figure(
            go.Table(
                header=dict(values=["A", "B"]),
                cells=dict(values=cells_values),
            )
        )
        parsed = json.loads(fig.to_json())
        vals = parsed["data"][0]["cells"]["values"]
        assert vals[0] == [1, 2, 3]
        assert vals[1] == ["a", "b", "c"]

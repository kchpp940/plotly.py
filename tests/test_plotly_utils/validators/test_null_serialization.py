import json
import tempfile
import os
import math
import pytest

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from _plotly_utils.basevalidators import (
    clean_nulls,
    copy_to_readonly_numpy_array,
    to_scalar_or_list,
    is_null_value,
    _clean_null_scalar,
    _clean_array_nulls,
    DataArrayValidator,
)
from _plotly_utils.utils import PlotlyJSONEncoder
import plotly.io as pio


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

    def test_clean_array_nulls_float_nan_to_object_none(self):
        arr = np.array([1.0, np.nan, 3.0])
        cleaned = _clean_array_nulls(arr)
        assert cleaned.dtype == object
        assert cleaned[1] is None
        assert cleaned[0] == 1.0
        assert cleaned[2] == 3.0
        assert isinstance(cleaned[0], float)
        assert isinstance(cleaned[2], float)

    def test_clean_array_nulls_float_no_nan_unchanged(self):
        arr = np.array([1.0, 2.0, 3.0])
        cleaned = _clean_array_nulls(arr)
        assert cleaned is arr

    def test_clean_array_nulls_int_no_nan_unchanged(self):
        arr = np.array([1, 2, 3])
        cleaned = _clean_array_nulls(arr)
        assert cleaned is arr
        assert cleaned.dtype.kind in ("i", "u")


# =============================================================================
# Section 2: copy_to_readonly_numpy_array tests
# =============================================================================
class TestCopyToReadonlyNullHandling:
    def test_int64_nullable_series(self):
        s = pd.Series([1, pd.NA, 3, pd.NA, 5], dtype="Int64")
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype == object
        assert not result.flags["WRITEABLE"]
        assert result[1] is None
        assert result[3] is None
        assert isinstance(result[0], int)
        assert isinstance(result[2], int)
        assert result[0] == 1
        assert result[2] == 3

    def test_float64_nullable_series(self):
        s = pd.Series([1.0, pd.NA, 3.0], dtype="Float64")
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype == object
        assert result[1] is None
        assert isinstance(result[0], float)
        assert isinstance(result[2], float)
        assert result[0] == 1.0
        assert result[2] == 3.0

    def test_string_nullable_series(self):
        s = pd.Series(["a", pd.NA, "c"], dtype="string")
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype == object
        assert result[1] is None
        assert result[0] == "a"
        assert result[2] == "c"
        assert isinstance(result[0], str)

    def test_boolean_nullable_series(self):
        s = pd.Series([True, pd.NA, False], dtype="boolean")
        result = copy_to_readonly_numpy_array(s)
        assert result.dtype == object
        assert result[1] is None
        assert result[0] is True
        assert result[2] is False
        assert isinstance(result[0], bool)
        assert isinstance(result[2], bool)

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
        assert result.dtype == object
        assert result[1] is None
        assert isinstance(result[0], int)
        assert isinstance(result[2], int)
        assert result[0] == 1
        assert result[2] == 3

    def test_np_masked_array_float(self):
        data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        masked = np.ma.masked_where(data == 5.0, data)
        result = copy_to_readonly_numpy_array(masked)
        assert result.dtype == object
        assert result.shape == (2, 3)
        assert result[1, 1] is None
        assert isinstance(result[0, 0], float)
        assert isinstance(result[1, 0], float)
        assert result[0, 0] == 1.0
        assert result[1, 0] == 4.0

    def test_np_masked_array_2d_shape_preserved(self):
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=float)
        masked = np.ma.masked_where(data % 3 == 0, data)
        result = copy_to_readonly_numpy_array(masked)
        assert result.dtype == object
        assert result.shape == (3, 3)
        assert result[0, 2] is None
        assert result[1, 2] is None
        assert result[2, 2] is None
        assert isinstance(result[0, 0], float)
        assert result[0, 0] == 1.0

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

        assert isinstance(result[0][0], int), "Int64 non-null must be int"
        assert result[0][0] == 1
        assert result[0][1] is None
        assert result[0][2] == 3

        assert isinstance(result[1][0], str), "string non-null must be str"
        assert result[1][0] == "a"
        assert result[1][1] is None

        assert result[2][0].year == 2021
        assert result[2][1] is None

    def test_scalar_or_list_float64_nullable(self):
        s = pd.Series([1.5, pd.NA, 3.5], dtype="Float64")
        result = to_scalar_or_list(s)
        assert isinstance(result[0], float), "Float64 non-null must be float"
        assert result[0] == 1.5
        assert result[1] is None
        assert result[2] == 3.5

    def test_scalar_or_list_boolean_nullable(self):
        s = pd.Series([True, pd.NA, False], dtype="boolean")
        result = to_scalar_or_list(s)
        assert isinstance(result[0], bool), "boolean non-null must be bool"
        assert result[0] is True
        assert result[1] is None
        assert result[2] is False

    def test_scalar_or_list_masked_array(self):
        ma = np.ma.array([10, 20, 30], mask=[False, True, False])
        result = to_scalar_or_list(ma)
        assert isinstance(result[0], int), "MaskedArray int non-null must be int"
        assert result[0] == 10
        assert result[1] is None
        assert result[2] == 30

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
        assert isinstance(x, list), "Array with nulls must not be b64 encoded"
        assert x[1] is None
        assert x[3] is None
        assert isinstance(x[0], int), "Int64 non-null must be JSON int, not float"
        assert isinstance(x[2], int)
        assert x[0] == 1
        assert x[2] == 3

    def test_scatter_float64_nullable_series_json_roundtrip(self):
        s = pd.Series([1.5, pd.NA, 3.5], dtype="Float64")
        fig = go.Figure(go.Scatter(x=s, y=s, mode="markers"))

        json_str = fig.to_json(engine="json")
        parsed = json.loads(json_str)

        x = parsed["data"][0]["x"]
        assert isinstance(x, list), "Array with nulls must not be b64 encoded"
        assert x[1] is None
        assert isinstance(x[0], float), "Float64 non-null must be JSON float"
        assert isinstance(x[2], float)
        assert x[0] == 1.5
        assert x[2] == 3.5

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

        assert isinstance(z, list), "Array with masked values must not be b64 encoded"
        assert len(z) == 3
        assert len(z[0]) == 3
        assert z[1][1] is None
        assert isinstance(z[0][0], float), "Non-null values must preserve float type"
        assert isinstance(z[0][1], float)
        assert z[0][0] == 1.0
        assert z[0][1] == 2.0


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
        assert isinstance(col0[0], int), "Int64 non-null must be int"
        assert col0[0] == 1
        assert col0[1] is None
        assert col0[2] == 3

        col1 = vals[1]
        assert isinstance(col1[0], str), "string non-null must be str"
        assert col1[0] == "a"
        assert col1[1] is None
        assert col1[2] == "c"

        col2 = vals[2]
        assert "2021-01-01" in col2[0]
        assert col2[1] is None
        assert "2021-01-03" in col2[2]

    def test_table_float64_nullable_series(self):
        cells_values = [
            pd.Series([1.5, pd.NA, 3.5], dtype="Float64"),
        ]
        fig = go.Figure(
            go.Table(
                header=dict(values=["Y"]),
                cells=dict(values=cells_values),
            )
        )

        json_str = fig.to_json(engine="json")
        parsed = json.loads(json_str)
        vals = parsed["data"][0]["cells"]["values"]

        assert isinstance(vals[0][0], float), "Float64 non-null must be float"
        assert vals[0][0] == 1.5
        assert vals[0][1] is None
        assert vals[0][2] == 3.5

    def test_table_boolean_nullable_series(self):
        cells_values = [
            pd.Series([True, pd.NA, False], dtype="boolean"),
        ]
        fig = go.Figure(
            go.Table(
                header=dict(values=["B"]),
                cells=dict(values=cells_values),
            )
        )

        json_str = fig.to_json(engine="json")
        parsed = json.loads(json_str)
        vals = parsed["data"][0]["cells"]["values"]

        assert isinstance(vals[0][0], bool), "boolean non-null must be bool"
        assert vals[0][0] is True
        assert vals[0][1] is None
        assert vals[0][2] is False

    def test_table_masked_array(self):
        ma = np.ma.array([10, 20, 30], mask=[False, True, False])
        fig = go.Figure(
            go.Table(
                header=dict(values=["X"]),
                cells=dict(values=[ma]),
            )
        )

        json_str = fig.to_json(engine="json")
        parsed = json.loads(json_str)
        vals = parsed["data"][0]["cells"]["values"]

        assert isinstance(vals[0][0], int), "MaskedArray int non-null must be int"
        assert vals[0][0] == 10
        assert vals[0][1] is None
        assert vals[0][2] == 30

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


# =============================================================================
# Section 7: Unit tests for unified clean_nulls() public API
# =============================================================================
class TestUnifiedCleanNullsAPI:
    def test_clean_nulls_python_scalars(self):
        assert clean_nulls(None) is None
        assert clean_nulls(42) == 42 and isinstance(clean_nulls(42), int)
        assert clean_nulls(3.14) == 3.14 and isinstance(clean_nulls(3.14), float)
        assert clean_nulls(float("nan")) is None
        assert clean_nulls(True) is True
        assert clean_nulls(False) is False
        assert clean_nulls("hello") == "hello"

    def test_clean_nulls_numpy_scalars(self):
        assert clean_nulls(np.int64(42)) == 42 and isinstance(clean_nulls(np.int64(42)), int)
        assert clean_nulls(np.float64(np.nan)) is None
        assert clean_nulls(np.datetime64("NaT")) is None

    def test_clean_nulls_pd_na_sentinels(self):
        assert clean_nulls(pd.NA) is None
        assert clean_nulls(pd.NaT) is None
        assert clean_nulls(np.ma.core.masked) is None

    def test_clean_nulls_container_recursive(self):
        nested = {"a": [1, float("nan"), {"b": pd.NA}], "c": (True, float("inf"))}
        result = clean_nulls(nested)
        assert result["a"][1] is None
        assert result["a"][2]["b"] is None
        assert result["c"][0] is True
        assert isinstance(result["c"], list)  # tuple -> list

    def test_clean_nulls_pandas_extension_series(self):
        s_int = pd.Series([1, pd.NA, 3], dtype="Int64")
        r = clean_nulls(s_int)
        assert r == [1, None, 3]
        assert isinstance(r[0], int) and isinstance(r[2], int)

        s_float = pd.Series([1.5, pd.NA, 3.5], dtype="Float64")
        r2 = clean_nulls(s_float)
        assert isinstance(r2[0], float) and r2[1] is None

        s_bool = pd.Series([True, pd.NA, False], dtype="boolean")
        assert clean_nulls(s_bool) == [True, None, False]

        s_str = pd.Series(["a", pd.NA, "c"], dtype="string")
        assert clean_nulls(s_str) == ["a", None, "c"]

    def test_clean_nulls_masked_array_1d(self):
        ma = np.ma.array([10, 20, 30], mask=[False, True, False])
        r = clean_nulls(ma)
        assert r == [10, None, 30]
        assert isinstance(r[0], int)

    def test_clean_nulls_masked_array_2d_shape(self):
        data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        ma = np.ma.masked_where(data % 3 == 0, data)
        r = clean_nulls(ma)
        assert len(r) == 2 and len(r[0]) == 3
        assert r[0][2] is None
        assert r[1][2] is None
        assert isinstance(r[0][0], float)

    def test_clean_nulls_numpy_array_2d_nan(self):
        arr = np.array([[1.0, np.nan, 3.0], [np.nan, 5.0, np.nan]])
        r = clean_nulls(arr)
        assert r == [[1.0, None, 3.0], [None, 5.0, None]]
        assert isinstance(r[0][0], float)

    def test_clean_nulls_datetime64_with_nat(self):
        arr = np.array(["2021-01-01", "NaT", "2021-01-03"], dtype="datetime64[us]")
        r = clean_nulls(arr)
        assert r[1] is None
        assert hasattr(r[0], "isoformat")  # native datetime

    def test_clean_nulls_nested_table_input(self):
        cells = [
            pd.Series([1, pd.NA, 3], dtype="Int64"),
            np.ma.array([10, 20, 30], mask=[False, True, False]),
            pd.Series([1.5, pd.NA, 3.5], dtype="Float64"),
            pd.Series(["a", pd.NA, "c"], dtype="string"),
            {"meta": pd.NA, "flags": [True, pd.NA, False]},
        ]
        r = clean_nulls(cells)
        # Int64 column
        assert r[0] == [1, None, 3] and isinstance(r[0][0], int)
        # MaskedArray column
        assert r[1] == [10, None, 30] and isinstance(r[1][0], int)
        # Float64 column
        assert isinstance(r[2][0], float) and r[2][1] is None
        # string column
        assert r[3] == ["a", None, "c"]
        # nested dict
        assert r[4]["meta"] is None
        assert r[4]["flags"][1] is None

    def test_clean_nulls_preserves_structure(self):
        """Original outer container structure must be preserved."""
        nested_3d = np.array([[[1, np.nan], [3, 4]], [[5, 6], [np.nan, 8]]], dtype=float)
        r = clean_nulls(nested_3d)
        assert len(r) == 2
        assert len(r[0]) == 2
        assert len(r[0][0]) == 2
        assert r[0][0][1] is None
        assert r[1][1][0] is None

    def test_clean_nulls_json_serializable(self):
        """clean_nulls output must be directly JSON-encodable."""
        input_data = [
            pd.Series([1, pd.NA, 3], dtype="Int64"),
            pd.Series(pd.to_datetime(["2021-01-01", pd.NaT, "2021-01-03"])),
            np.ma.array([10, 20, 30], mask=[False, True, False]),
            {"nested": [float("nan"), pd.NA, "ok"]},
        ]
        cleaned = clean_nulls(input_data)
        # datetimes in cleaned[1] are Python datetimes - format for JSON
        class DTEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, "isoformat"):
                    return obj.isoformat()
                return super().default(obj)
        json_str = json.dumps(cleaned, cls=DTEncoder)
        parsed = json.loads(json_str)
        assert parsed[0][1] is None
        assert parsed[1][1] is None
        assert parsed[2][1] is None
        assert parsed[3]["nested"][0] is None
        assert parsed[3]["nested"][1] is None


# =============================================================================
# Section 8: Verify all three serialization paths use unified clean_nulls
# =============================================================================
class TestThreePathsReuseCleanNulls:
    def build_figure(self):
        return go.Figure(
            data=[
                go.Scatter(
                    x=pd.Series([1, pd.NA, 3, pd.NA, 5], dtype="Int64"),
                    y=pd.Series([1.5, pd.NA, 3.5, None, 5.5], dtype="Float64"),
                    mode="markers",
                ),
                go.Table(
                    header=dict(values=["Int", "Float", "Bool", "Str", "MA"]),
                    cells=dict(values=[
                        pd.Series([1, pd.NA, 3], dtype="Int64"),
                        pd.Series([1.5, pd.NA, 3.5], dtype="Float64"),
                        pd.Series([True, pd.NA, False], dtype="boolean"),
                        pd.Series(["a", pd.NA, "c"], dtype="string"),
                        np.ma.array([10, 20, 30], mask=[False, True, False]),
                    ]),
                ),
                go.Heatmap(z=np.array([[1.0, np.nan], [np.nan, 4.0]])),
            ]
        )

    def test_path1_json_engine(self):
        """engine='json' uses PlotlyJSONEncoder -> clean_nulls."""
        fig = self.build_figure()
        p = json.loads(fig.to_json(engine="json"))

        sc_x = p["data"][0]["x"]
        assert isinstance(sc_x[0], int) and sc_x[1] is None

        tc = p["data"][1]["cells"]["values"]
        assert isinstance(tc[0][0], int) and tc[0][1] is None     # Int64
        assert isinstance(tc[1][0], float) and tc[1][1] is None   # Float64
        assert tc[2][1] is None and isinstance(tc[2][0], bool)     # boolean
        assert tc[3][1] is None and isinstance(tc[3][0], str)      # string
        assert isinstance(tc[4][0], int) and tc[4][1] is None      # MaskedArray

        hm = p["data"][2]["z"]
        assert hm[0][1] is None and hm[1][0] is None

    def test_path2_orjson_engine(self):
        """engine='orjson' uses clean_to_json_compatible -> clean_nulls."""
        pytest.importorskip("orjson")
        fig = self.build_figure()
        p = json.loads(fig.to_json(engine="orjson"))

        sc_x = p["data"][0]["x"]
        assert isinstance(sc_x[0], int) and sc_x[1] is None

        tc = p["data"][1]["cells"]["values"]
        assert isinstance(tc[0][0], int) and tc[0][1] is None
        assert isinstance(tc[4][0], int) and tc[4][1] is None

        hm = p["data"][2]["z"]
        assert hm[0][1] is None and hm[1][0] is None

    def test_path3_write_json_roundtrip(self):
        """write_json / read_json round-trip must preserve null semantics."""
        fig = self.build_figure()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            fname = f.name
        try:
            fig.write_json(fname, engine="json")
            loaded = pio.read_json(fname)
            lp = json.loads(loaded.to_json())
            tc = lp["data"][1]["cells"]["values"]
            assert isinstance(tc[0][0], int) and tc[0][1] is None
            assert isinstance(tc[4][0], int) and tc[4][1] is None
            assert lp["data"][2]["z"][0][1] is None
        finally:
            os.unlink(fname)

    def test_all_paths_consistent_output(self):
        """json and orjson engines must produce semantically identical output."""
        fig = self.build_figure()
        p_json = json.loads(fig.to_json(engine="json"))

        try:
            import orjson  # noqa
            p_orj = json.loads(fig.to_json(engine="orjson"))
            # Structure and null positions must match exactly
            assert p_json["data"][0]["x"] == p_orj["data"][0]["x"]
            assert p_json["data"][0]["y"] == p_orj["data"][0]["y"]
            assert p_json["data"][1]["cells"]["values"] == p_orj["data"][1]["cells"]["values"]
            assert p_json["data"][2]["z"] == p_orj["data"][2]["z"]
        except ImportError:
            pytest.skip("orjson not installed")

import pytest

from _plotly_utils.error_messages import (
    ErrorCode,
    ErrorMessage,
    enable_snapshot_mode,
    disable_snapshot_mode,
    is_snapshot_mode,
    format_path,
    format_prop_path,
    format_install_hint,
    build_error_message,
)


# ============================================================
# Part 1: format functions
# ============================================================

# format_path
def test_format_path_empty_list():
    assert format_path([]) == ""


def test_format_path_list_of_strings():
    assert format_path(["a", "b", "c"]) == "['a']['b']['c']"


def test_format_path_mixed_list():
    assert format_path(["a", 2, "b", 0]) == "['a'][2]['b'][0]"


# format_prop_path
def test_format_prop_path_without_inds():
    result = format_prop_path("xaxis", "layout")
    assert result == ("xaxis", "layout")


def test_format_prop_path_with_inds():
    result = format_prop_path("xaxis", "layout", inds=[0, 2])
    assert result == ("xaxis[0][2]", "layout")


# format_install_hint
def test_format_install_hint_basic_package():
    assert format_install_hint("pandas") == "pip install pandas"


def test_format_install_hint_with_pip_extras():
    assert format_install_hint("plotly", pip_extras="kaleido") == "pip install 'plotly[kaleido]'"


# ============================================================
# Part 2: snapshot mode toggle
# ============================================================

def test_snapshot_mode_toggle():
    disable_snapshot_mode()
    assert is_snapshot_mode() is False

    enable_snapshot_mode()
    assert is_snapshot_mode() is True

    disable_snapshot_mode()
    assert is_snapshot_mode() is False


# ============================================================
# Part 3: build_error_message default mode
# ============================================================

@pytest.fixture(autouse=True)
def _reset_snapshot_mode():
    disable_snapshot_mode()
    yield
    disable_snapshot_mode()


def test_build_default_mode_basic():
    output = build_error_message(ErrorCode.INVALID_VALUE, "Bad value")
    assert output == "Bad value"


def test_build_default_mode_no_code_prefix():
    output = build_error_message(ErrorCode.INVALID_VALUE, "Bad value")
    assert not str(output).startswith("[E")


def test_build_default_mode_no_install_hint_in_output():
    install_hint = format_install_hint("plotly", pip_extras="kaleido")
    output = build_error_message(
        ErrorCode.DEPENDENCY_MISSING,
        "Missing package",
        install_hint=install_hint,
    )
    assert install_hint not in str(output)


def test_build_default_mode_no_path_in_output():
    path = ["layout", "xaxis", 0, "title"]
    output = build_error_message(
        ErrorCode.INVALID_VALUE,
        "Bad value",
        path=path,
    )
    path_str = format_path(path)
    assert path_str not in str(output)
    assert "Path to error" not in str(output)


def test_build_default_mode_no_detail_in_output():
    detail = "Some detailed information"
    output = build_error_message(
        ErrorCode.INVALID_VALUE,
        "Bad value",
        detail=detail,
    )
    assert detail not in str(output)


def test_build_default_mode_is_str_subclass():
    output = build_error_message(ErrorCode.INVALID_VALUE, "Bad value")
    assert isinstance(output, str)
    assert isinstance(output, ErrorMessage)


def test_build_default_mode_metadata_attributes():
    install_hint = "pip install pandas"
    path = ["a", "b", 2]
    output = build_error_message(
        ErrorCode.DEPENDENCY_MISSING,
        "Missing package",
        path=path,
        install_hint=install_hint,
    )
    assert output.error_code == "E001"
    assert output.install_hint == install_hint
    assert output.error_path == path


# ============================================================
# Part 4: build_error_message snapshot mode
# ============================================================

@pytest.fixture(autouse=True)
def _enable_snapshot_mode_for_section(request):
    if "snapshot" in request.node.name:
        enable_snapshot_mode()
        yield
        disable_snapshot_mode()
    else:
        yield


def test_build_snapshot_mode_code_prefix():
    enable_snapshot_mode()
    try:
        output = build_error_message(ErrorCode.INVALID_VALUE, "Bad value")
        assert str(output).startswith("[E002] ")
    finally:
        disable_snapshot_mode()


def test_build_snapshot_mode_includes_install_hint():
    enable_snapshot_mode()
    try:
        install_hint = format_install_hint("plotly", pip_extras="kaleido")
        output = build_error_message(
            ErrorCode.DEPENDENCY_MISSING,
            "Missing package",
            install_hint=install_hint,
        )
        assert install_hint in str(output)
        assert "Install:" in str(output)
    finally:
        disable_snapshot_mode()


def test_build_snapshot_mode_includes_path():
    enable_snapshot_mode()
    try:
        path = ["layout", "xaxis", 0, "title"]
        output = build_error_message(
            ErrorCode.INVALID_VALUE,
            "Bad value",
            path=path,
        )
        assert "Path to error:" in str(output)
        path_str = format_path(path)
        assert path_str in str(output)
    finally:
        disable_snapshot_mode()


def test_build_snapshot_mode_includes_detail():
    enable_snapshot_mode()
    try:
        detail = "Some detailed information"
        output = build_error_message(
            ErrorCode.INVALID_VALUE,
            "Bad value",
            detail=detail,
        )
        assert detail in str(output)
    finally:
        disable_snapshot_mode()


def test_build_snapshot_mode_metadata_attributes():
    enable_snapshot_mode()
    try:
        install_hint = "pip install pandas"
        path = ["a", "b", 2]
        output = build_error_message(
            ErrorCode.DEPENDENCY_MISSING,
            "Missing package",
            path=path,
            install_hint=install_hint,
        )
        assert output.error_code == "E001"
        assert output.install_hint == install_hint
        assert output.error_path == path
    finally:
        disable_snapshot_mode()


# ============================================================
# Part 5: ErrorMessage str compatibility
# ============================================================

def test_error_message_str_eq():
    msg = ErrorMessage("same text", code="E001")
    assert msg == "same text"
    assert "same text" == msg
    assert not (msg == "different text")


def test_error_message_formatting():
    msg = ErrorMessage("same text", code="E001")
    assert "%s" % msg == "same text"
    assert format(msg) == "same text"
    assert f"{msg}" == "same text"


def test_error_message_concat():
    msg = ErrorMessage("hello", code="E001")
    assert msg + " extra" == "hello extra"
    assert "prefix " + msg == "prefix hello"


def test_error_message_in_valueerror():
    original = "original message"
    msg = ErrorMessage(original, code="E001")
    exc = ValueError(msg)
    assert str(exc.args[0]) == original
    assert str(exc) == original

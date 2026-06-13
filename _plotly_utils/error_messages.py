from enum import Enum


class ErrorCode(Enum):
    DEPENDENCY_MISSING = "E001"
    INVALID_VALUE = "E002"
    INVALID_ELEMENT = "E003"
    INVALID_PARAM = "E004"
    INVALID_FORMAT = "E005"
    INVALID_RENDERER = "E006"
    INVALID_ENGINE = "E007"
    INVALID_TYPE = "E008"
    READ_ONLY_PROPERTY = "E009"
    DEPRECATION = "E010"
    CONFIG_ERROR = "E011"
    LENGTH_MISMATCH = "E012"
    AMBIGUOUS_INPUT = "E013"
    DATA_CONVERSION = "E014"
    NOT_ALLOWED = "E015"


def format_path(path):
    if not path:
        return ""
    return "[" + "][".join(repr(k) for k in path) + "]"


def format_prop_path(plotly_name, parent_name, inds=None):
    name = plotly_name
    if inds:
        for i in inds:
            name += "[" + str(i) + "]"
    return name, parent_name


def format_install_hint(package, pip_extras=None):
    if pip_extras:
        return f"pip install '{package}[{pip_extras}]'"
    return f"pip install {package}"


def build_error_message(code, message, path=None, install_hint=None, detail=None):
    parts = []
    code_str = code.value if isinstance(code, ErrorCode) else str(code)

    header = f"[{code_str}] {message}"
    parts.append(header)

    if path:
        path_str = format_path(path) if isinstance(path, (list, tuple)) else str(path)
        parts.append(f"\nPath to error: {path_str}")

    if detail:
        parts.append(f"\n{detail}")

    if install_hint:
        parts.append(f"\nInstall: {install_hint}")

    return "\n".join(parts)

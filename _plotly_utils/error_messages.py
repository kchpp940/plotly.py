from enum import Enum


_SNAPSHOT_MODE = False


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


class ErrorMessage(str):
    _error_code = None
    _install_hint = None
    _path = None

    def __new__(cls, value, code=None, install_hint=None, path=None):
        instance = super().__new__(cls, value)
        instance._error_code = code
        instance._install_hint = install_hint
        instance._path = path
        return instance

    @property
    def error_code(self):
        return self._error_code

    @property
    def install_hint(self):
        return self._install_hint

    @property
    def error_path(self):
        return self._path


def enable_snapshot_mode():
    global _SNAPSHOT_MODE
    _SNAPSHOT_MODE = True


def disable_snapshot_mode():
    global _SNAPSHOT_MODE
    _SNAPSHOT_MODE = False


def is_snapshot_mode():
    return _SNAPSHOT_MODE


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
        return "pip install '{package}[{pip_extras}]'".format(
            package=package, pip_extras=pip_extras
        )
    return "pip install {package}".format(package=package)


def build_error_message(code, message, path=None, install_hint=None, detail=None):
    code_str = code.value if isinstance(code, ErrorCode) else str(code)

    if _SNAPSHOT_MODE:
        parts = []
        header = "[{code_str}] {message}".format(code_str=code_str, message=message)
        parts.append(header)

        if path:
            path_str = format_path(path) if isinstance(path, (list, tuple)) else str(path)
            parts.append("\nPath to error: {path_str}".format(path_str=path_str))

        if detail:
            parts.append("\n{detail}".format(detail=detail))

        if install_hint:
            parts.append("\nInstall: {install_hint}".format(install_hint=install_hint))

        message_text = "\n".join(parts)
    else:
        message_text = message

    return ErrorMessage(
        message_text, code=code_str, install_hint=install_hint, path=path
    )

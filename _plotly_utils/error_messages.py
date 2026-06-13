"""Structured error message infrastructure for Plotly.py.

This module provides a backward-compatible system for building error messages
that carry machine-readable metadata (error codes, install hints, structured
paths) without changing the user-visible string output in production.

Core Concepts
=============

Two Output Modes
----------------

1. DEFAULT MODE (production)
   ``build_error_message`` returns ONLY the ``message`` argument as-is. The
   error code, install hint, path, and detail are NOT visible in the string
   representation. They are only accessible via the ``ErrorMessage``
   attributes: ``.error_code``, ``.install_hint``, ``.error_path``. This
   guarantees 100% backward compatibility with existing error messages so
   that user code performing substring checks or regex matches against
   exceptions continues to work.

2. SNAPSHOT MODE (tests/docs only)
   When ``enable_snapshot_mode()`` is active, ``build_error_message``
   prefixes the output with ``"[E###]"`` and appends ``Install:`` and
   ``Path to error:`` sections. This mode MUST NEVER be enabled at import
   time or in production code paths. Enable it only temporarily in specific
   tests or doc-generation scripts and always disable it in a ``finally``
   block::

       enable_snapshot_mode()
       try:
           ... generate / verify snapshot messages ...
       finally:
           disable_snapshot_mode()

Message Convention
------------------

The ``message`` argument to ``build_error_message`` MUST be the EXACT
historical/original error string, including leading/trailing newlines,
indentation, and internal formatting. Do NOT split the original message
across ``message`` + ``detail`` + ``install_hint`` — those extra fields
exist ONLY for ADDITIONAL metadata that was NOT in the original
user-visible string.

Core Types
==========

ErrorCode
    Enum of error codes from E001 (DEPENDENCY_MISSING) through E015
    (NOT_ALLOWED). Every non-trivial error must map to one of these.

ErrorMessage
    Subclass of ``str``. Behaves exactly like a plain string (for backward
    compatibility) but carries structured attributes:

    * ``.error_code``  — the E### string (e.g. ``"E001"``)
    * ``.install_hint`` — optional pip install command string
    * ``.error_path``  — optional structured path (list or string)

Public API
==========

Builder
-------
build_error_message(code, message, path=None, install_hint=None, detail=None)
    The primary constructor. Always use this instead of raw string
    literals for non-trivial errors.

Snapshot mode toggles
---------------------
enable_snapshot_mode()   — turn on snapshot formatting
disable_snapshot_mode()  — turn off snapshot formatting
is_snapshot_mode()       — query current state

Formatting helpers
------------------
format_path(path)              — format a list path like ``['a']['b'][2]``
format_prop_path(name, parent, inds=None)
                               — format a plotly property path
format_install_hint(pkg, extras=None)
                               — generate a ``pip install`` string

Which Modules Must Use build_error_message
==========================================

All non-trivial error messages in the following modules MUST go through
``build_error_message``:

* ``_plotly_utils/basevalidators.py``
* ``plotly/io/_kaleido.py``
* ``plotly/io/_orca.py``
* ``plotly/io/_renderers.py``
* ``plotly/io/_json.py``
* ``plotly/io/_base_renderers.py``
* ``plotly/express/_core.py``
* ``plotly/express/__init__.py``
* ``plotly/figure_factory/__init__.py``
* ``plotly/missing_anywidget.py``

How to Add a New Error
======================

1. Choose the right ``ErrorCode`` value that classifies the problem.
2. Put the FULL user-visible message (exactly as users should see it)
   into the ``message`` parameter — including newlines, indentation, etc.
3. Optional: add ``install_hint=format_install_hint(...)`` for
   dependency-related errors.
4. Optional: add ``path=...`` with structured path metadata.
5. Optional: add ``detail=...`` for supplementary information that does
   NOT change the user-visible output.

Examples
========

Good — missing dependency::

    build_error_message(
        ErrorCode.DEPENDENCY_MISSING,
        "The FigureWidget class requires the anywidget package",
        install_hint=format_install_hint("anywidget"),
    )

Good — validator error preserving historical formatting::

    build_error_message(
        ErrorCode.INVALID_VALUE,
        "\n    Invalid value of type {typ} received for the '{name}' property of {pname}\n"
        "        Received value: {v}\n\n"
        "{valid_clr_desc}".format(typ=type(v), name=name, pname=pname, v=v, valid_clr_desc=desc),
    )

Bad — bypassing the builder with a raw multi-line string::

    raise ValueError(
        "\n    Invalid value ... multi-line raw string ..."
    )

Lint Enforcement
================

Run ``python scripts/lint_error_messages.py`` (or the corresponding pytest
module ``tests/test_core/test_errors/test_lint_error_messages.py``) to
detect multi-line raw error strings that bypass ``build_error_message``.
"""

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

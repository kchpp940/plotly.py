# Error Message Conventions

This document describes the conventions for constructing error messages in
Plotly.py using the `_plotly_utils.error_messages` module. The system is
designed so that error messages carry structured, machine-readable metadata
(error codes, install hints, structured paths) while remaining 100% backward
compatible at the string level.

---

## Module Location

`_plotly_utils/error_messages.py`

Read the module-level docstring there for the canonical reference. This
document expands on those conventions with additional rationale, examples,
and checklists for developers.

---

## Core Design Principles

### Backward Compatibility Above All Else

Existing user code does things like:

```python
try:
    px.scatter(df, x="bad_column", y="y")
except ValueError as e:
    assert "Column 'bad_column' not found" in str(e)
```

That code **must not break**. Therefore:

> The string output of every error message is byte-for-byte identical to the
> historical error string. Error codes, install hints, paths, and detail are
> *never* visible in the default (production) string representation.

Metadata lives on the `ErrorMessage` object as attributes, not in the string.

### Structured Metadata for Tools

Even though the extra fields are invisible to end users, they are invaluable
for:

- **Test snapshotting** — verifying error codes without string-regex hacks.
- **Documentation generation** — producing a catalog of all error codes.
- **IDE / language-server tooling** — surfacing install hints or links.
- **Future telemetry** — aggregating error frequencies by code.

---

## Two Output Modes

### 1. Default Mode (Production)

`build_error_message` returns an `ErrorMessage` whose `str()` value is
**exactly** the `message` argument. Nothing is prepended, nothing is
appended.

```python
from _plotly_utils.error_messages import ErrorCode, build_error_message

msg = build_error_message(
    ErrorCode.DEPENDENCY_MISSING,
    "The FigureWidget class requires the anywidget package",
    install_hint="pip install anywidget",
)

print(str(msg))
# The FigureWidget class requires the anywidget package

print(msg.error_code)    # "E001"
print(msg.install_hint)  # "pip install anywidget"
```

Because `ErrorMessage` is a subclass of `str`, the following all work as
they did before:

```python
assert "FigureWidget" in msg
assert msg == "The FigureWidget class requires the anywidget package"
"Prefix: " + msg
f"{msg}"
re.search(r"requires the (\w+)", msg)
ValueError(msg).args[0] is msg
```

### 2. Snapshot Mode (Tests / Docs Only)

`enable_snapshot_mode()` causes `build_error_message` to include the error
code prefix and the optional metadata sections in the string output:

```python
enable_snapshot_mode()
msg = build_error_message(
    ErrorCode.DEPENDENCY_MISSING,
    "The FigureWidget class requires the anywidget package",
    install_hint="pip install anywidget",
)
print(str(msg))
# [E001] The FigureWidget class requires the anywidget package
# Install: pip install anywidget
```

> **CRITICAL**: Snapshot mode is global process state. It MUST NEVER be
> enabled at import time or in a production code path. It must only be
> enabled temporarily, around the smallest possible block of code, and
> always disabled in a `finally` clause.

Correct pattern:

```python
from _plotly_utils.error_messages import (
    enable_snapshot_mode,
    disable_snapshot_mode,
)

enable_snapshot_mode()
try:
    ... generate or verify snapshot messages ...
finally:
    disable_snapshot_mode()
```

Also see `teardown_method` hooks in the test suite that defensively disable
snapshot mode after every test.

---

## ErrorCode Reference

| Code  | Enum Name             | Use Case                                                    |
|-------|-----------------------|-------------------------------------------------------------|
| E001  | `DEPENDENCY_MISSING`  | An optional dependency is not installed.                    |
| E002  | `INVALID_VALUE`       | A property received a value of the right type but bad value.|
| E003  | `INVALID_ELEMENT`     | A container property contains bad elements.                 |
| E004  | `INVALID_PARAM`       | A function/constructor argument is invalid.                 |
| E005  | `INVALID_FORMAT`      | Parsing failed (JSON, image, etc.).                         |
| E006  | `INVALID_RENDERER`    | A named renderer does not exist or cannot be used.          |
| E007  | `INVALID_ENGINE`      | The chosen engine (kaleido, orca, etc.) is invalid.         |
| E008  | `INVALID_TYPE`        | A value has the wrong Python type.                          |
| E009  | `READ_ONLY_PROPERTY`  | Attempted to set a read-only attribute.                     |
| E010  | `DEPRECATION`         | Using a deprecated API path.                                |
| E011  | `CONFIG_ERROR`        | Misconfiguration (internal config, environment, etc.).      |
| E012  | `LENGTH_MISMATCH`     | Two or more arrays/columns have mismatched lengths.         |
| E013  | `AMBIGUOUS_INPUT`     | Input is ambiguous and cannot be resolved automatically.    |
| E014  | `DATA_CONVERSION`     | Data could not be coerced/converted to the required type.   |
| E015  | `NOT_ALLOWED`         | The operation is explicitly disallowed.                     |

Pick the most specific code that fits. When in doubt, prefer
`INVALID_VALUE` / `INVALID_PARAM` over a catch-all like `CONFIG_ERROR`.

---

## The `message` Argument Is Sacred

The single most important rule:

> **The `message` argument must equal the exact, historical user-visible
> error string.**

That means:

- ✅ Include every leading newline, trailing newline, and space of
  indentation.
- ✅ Do all string formatting (`.format(...)`, f-strings, `%`) **inside**
  the `message` argument so the builder receives the final rendered text.
- ❌ Do NOT move part of the user-visible text into `detail=`,
  `install_hint=`, or any other parameter.
- ❌ Do NOT "clean up" the formatting of the historical message.

Why? Because existing tests and user code perform exact-string or
substring checks against the output. Changing even one whitespace
character is a breaking change.

The `detail`, `install_hint`, and `path` parameters are for **additional**
metadata only — things that were NOT part of the original user-visible
string.

---

## How to Add a New Error — Step by Step

### Step 1. Pick the Right `ErrorCode`

Scan the table above. For example:

- Missing optional package → `DEPENDENCY_MISSING`
- User passed a bad string to `px.scatter(..., trendline=...)` → `INVALID_PARAM`
- A trace property received an out-of-range number → `INVALID_VALUE`

### Step 2. Put the Full User-Visible Text into `message`

Copy the exact string that was (or would have been) raised before this
system existed. Preserve every newline and space.

```python
# GOOD — the whole user-visible message is in `message`
build_error_message(
    ErrorCode.INVALID_VALUE,
    "\n    Invalid value of type {typ} received for the '{name}' property of {pname}\n"
    "        Received value: {v}\n\n"
    "{valid_clr_desc}".format(
        typ=type(v).__name__, name=name, pname=pname, v=repr(v), valid_clr_desc=desc
    ),
)
```

### Step 3. Add Optional Metadata (Only If It Existed Before)

- `install_hint=format_install_hint("package")` — for missing dependencies.
- `path=["x"]` or `path=format_path([...])` — for structured path info.
- `detail=...` — for extra context that does **not** change the user-visible
  string output.

Remember: none of these affect the default string output.

### Step 4. Wrap in the Appropriate Exception Type

```python
raise ValueError(build_error_message(ErrorCode.INVALID_VALUE, "..."))
raise TypeError(build_error_message(ErrorCode.INVALID_TYPE, "..."))
raise ImportError(build_error_message(ErrorCode.DEPENDENCY_MISSING, "..."))
```

---

## Complete Examples

### Example 1: Missing Dependency

```python
from _plotly_utils.error_messages import (
    ErrorCode,
    build_error_message,
    format_install_hint,
)

raise ImportError(
    build_error_message(
        ErrorCode.DEPENDENCY_MISSING,
        "The FigureWidget class requires the anywidget package",
        install_hint=format_install_hint("anywidget"),
    )
)
```

Default output:

```
The FigureWidget class requires the anywidget package
```

Snapshot output:

```
[E001] The FigureWidget class requires the anywidget package
Install: pip install anywidget
```

### Example 2: Validator with Preserved Historical Formatting

```python
from _plotly_utils.error_messages import (
    ErrorCode,
    build_error_message,
    format_prop_path,
)

name, parent = format_prop_path(self.plotly_name, self.parent_name, inds)

raise ValueError(
    build_error_message(
        ErrorCode.INVALID_VALUE,
        "\n    Invalid value of type {typ} received for the '{name}' property of {pname}\n"
        "        Received value: {v}\n\n"
        "{valid_clr_desc}".format(
            typ=type(v).__name__, name=name, pname=parent, v=repr(v), valid_clr_desc=self.description()
        ),
    )
)
```

Note that the leading `\n`, the four-space indent, the two trailing
newlines — everything is preserved exactly as the historical message.

### Example 3: Plotly Express Invalid Parameter

```python
if ecdfnorm not in [None, "percent", "probability"]:
    raise ValueError(
        build_error_message(
            ErrorCode.INVALID_PARAM,
            "`ecdfnorm` must be one of None, 'percent' or 'probability'.",
            detail="'%s' was provided." % ecdfnorm,
        )
    )
```

Here `detail` carries the "bad value" context. In default mode the user
sees only the first sentence; in snapshot mode the detail is appended.

---

## Anti-Patterns (What NOT to Do)

### ❌ Bypassing `build_error_message` Entirely

```python
# BAD — multi-line raw string with no error code, no metadata
raise ValueError("""
    Invalid value of type int received for the 'x' property ...
""")
```

### ❌ Splitting the User-Visible Message Across Parameters

```python
# BAD — the second sentence was historically part of the user-visible string
build_error_message(
    ErrorCode.INVALID_PARAM,
    "Column not found.",
    detail="Expected one of: a, b, c",  # WRONG — this was visible before
)
```

### ❌ Enabling Snapshot Mode Without a `finally`

```python
# BAD — if an exception is raised, snapshot mode stays on forever
enable_snapshot_mode()
assert "[E001]" in str(some_error())
disable_snapshot_mode()
```

### ❌ Enabling Snapshot Mode at Module Import Time

```python
# BAD — pollutes every error message in the process
# (at the top of some_module.py)
from _plotly_utils.error_messages import enable_snapshot_mode
enable_snapshot_mode()
```

---

## Modules Subject to the Convention

The following modules MUST route every non-trivial error through
`build_error_message`:

| Module | Typical Error Types |
|--------|---------------------|
| `_plotly_utils/basevalidators.py` | `INVALID_VALUE`, `INVALID_ELEMENT`, `INVALID_PARAM`, `READ_ONLY_PROPERTY` |
| `plotly/io/_kaleido.py` | `DEPENDENCY_MISSING`, `INVALID_ENGINE`, `CONFIG_ERROR` |
| `plotly/io/_orca.py` | `DEPENDENCY_MISSING`, `INVALID_ENGINE`, `CONFIG_ERROR` |
| `plotly/io/_renderers.py` | `INVALID_RENDERER`, `CONFIG_ERROR` |
| `plotly/io/_json.py` | `INVALID_FORMAT`, `DATA_CONVERSION` |
| `plotly/io/_base_renderers.py` | `INVALID_RENDERER`, `CONFIG_ERROR` |
| `plotly/express/_core.py` | `INVALID_PARAM`, `INVALID_VALUE`, `LENGTH_MISMATCH`, `AMBIGUOUS_INPUT`, `DATA_CONVERSION`, `DEPENDENCY_MISSING` |
| `plotly/express/__init__.py` | `INVALID_PARAM`, `DEPENDENCY_MISSING` |
| `plotly/figure_factory/__init__.py` | `INVALID_PARAM`, `INVALID_VALUE`, `DEPENDENCY_MISSING` |
| `plotly/missing_anywidget.py` | `DEPENDENCY_MISSING` |

Other modules are encouraged to use the system but are not (yet) enforced
by the linter.

---

## Helper Functions

### `format_install_hint(package, pip_extras=None)`

Generates a consistent `pip install` string:

```python
format_install_hint("statsmodels")          # "pip install statsmodels"
format_install_hint("plotly", "kaleido")    # "pip install 'plotly[kaleido]'"
```

### `format_path(path)`

Formats a list/tuple path in the style Python programmers expect:

```python
format_path(["a", "b", 2])    # "['a']['b'][2]"
format_path([])               # ""
```

### `format_prop_path(plotly_name, parent_name, inds=None)`

Formats a plotly property path, returning `(name, parent_name)`. If
`inds` is provided, the name gets bracket suffixes:

```python
format_prop_path("x", "scatter")           # ("x", "scatter")
format_prop_path("colorscale", "marker", [0, 1])  # ("colorscale[0][1]", "marker")
```

---

## Lint Enforcement

The project ships a lint script that scans the modules listed above for
multi-line raw error strings that are not passed through
`build_error_message`.

Run it directly:

```bash
python scripts/lint_error_messages.py
```

Or via the test suite:

```bash
pytest tests/test_core/test_errors/test_lint_error_messages.py
```

The linter flags any `raise ...Error(` that contains a multi-line string
literal (triple-quoted or implicit string concatenation spanning
newlines) without a call to `build_error_message` in the same expression.

If you have a legitimate multi-line string that is NOT an error message
(uncommon in the listed modules), add a `# noqa` comment on the line
with a brief explanation.

---

## Testing Checklist

When you add or modify an error that uses `build_error_message`, verify
the following in tests:

1. **Backward compatibility** — in default mode, `str(msg)` equals the
   exact historical string. Use `==` or substring checks just like user
   code would.
2. **Type check** — `isinstance(msg, ErrorMessage)` and
   `isinstance(msg, str)` are both `True`.
3. **Error code** — `msg.error_code` equals the expected `E###` string.
4. **Metadata populated** — if applicable, `msg.install_hint` and/or
   `msg.error_path` contain the expected values.
5. **Snapshot mode** — wrap a separate assertion in
   `enable_snapshot_mode()` / `disable_snapshot_mode()` (with `finally`)
   and confirm the `[E###]` prefix and optional sections appear.

See `tests/test_optional/test_px/test_error_messages.py` for a thorough
set of reference tests.

---

## Quick Reference Card

```text
# Always import
from _plotly_utils.error_messages import (
    ErrorCode,
    build_error_message,
    format_install_hint,   # if dependency-related
    format_path,           # if path metadata needed
)

# Always wrap
raise <ExceptionType>(build_error_message(
    ErrorCode.<CODE>,
    "<EXACT historical user-visible message>",
    install_hint=format_install_hint("<pkg>"),  # optional
    path=<structured path>,                      # optional
    detail=<extra metadata not in string>,       # optional
))

# In tests only
enable_snapshot_mode()
try:
    ...
finally:
    disable_snapshot_mode()
```

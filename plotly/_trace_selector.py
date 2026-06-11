import re
import warnings


def _values_equal(a, b):
    """
    Compare two values for equality, normalising tuple/list mismatches
    that arise because Plotly trace properties return tuples while users
    typically supply lists.
    """
    if a is b:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(_values_equal(ai, bi) for ai, bi in zip(a, b))
    return a == b


def _resolve_path(obj, path):
    """
    Resolve a dot-separated *path* against *obj*, returning the value
    at that path or a ``_MISSING`` sentinel if any segment is absent.

    Supports both dict-key access and numeric-index access:

    >>> _resolve_path({"a": {"b": 1}}, "a.b")
    1
    >>> _resolve_path({"items": [10, 20]}, "items.1")
    20
    """
    parts = path.split(".")
    cur = obj
    for part in parts:
        if isinstance(cur, dict):
            if part not in cur:
                return _MISSING
            cur = cur[part]
        elif isinstance(cur, (list, tuple)):
            try:
                idx = int(part)
            except ValueError:
                return _MISSING
            if idx < 0 or idx >= len(cur):
                return _MISSING
            cur = cur[idx]
        else:
            return _MISSING
    return cur


class _MissingSentinel:
    pass


_MISSING = _MissingSentinel()


def _match_dict_spec(trace_val, spec):
    """
    Match a dict *spec* against *trace_val* using field-path semantics.

    *spec* is a dict where each key is a dot-separated path and each
    value is the expected value at that path.  A trace matches only
    when **every** path in *spec* resolves and the resolved value
    equals the expected one (using :func:`_values_equal`).

    For ``customdata`` (which is a 2-D array per data-point), the
    spec is checked against **every row** in the array and the trace
    matches when **at least one row** satisfies all spec entries.

    For ``meta`` (which is typically a scalar dict), the spec is
    checked against the value directly.

    Parameters
    ----------
    trace_val : object
        The value retrieved from the trace property (may be a tuple of
        rows for customdata, or a dict for meta).
    spec : dict
        Mapping of dot-separated paths to expected values.

    Returns
    -------
    bool
    """
    if trace_val is None:
        return False

    if isinstance(trace_val, (list, tuple)) and len(trace_val) > 0 and isinstance(
        trace_val[0], (list, tuple, dict)
    ):
        for row in trace_val:
            if _all_paths_match(row, spec):
                return True
        return False

    return _all_paths_match(trace_val, spec)


def _all_paths_match(obj, spec):
    """Return True if every path in *spec* resolves in *obj* and equals expected."""
    for path, expected in spec.items():
        resolved = _resolve_path(obj, path)
        if isinstance(resolved, _MissingSentinel):
            return False
        if not _values_equal(resolved, expected):
            return False
    return True


class TraceSelector:
    """
    A rich selector for filtering traces in a Figure.

    Supports selecting traces by trace type, subplot position,
    legendgroup, name pattern (regex), customdata field paths,
    and meta field paths. All criteria are combined with AND logic --
    a trace must satisfy every non-None criterion to be selected.

    Parameters
    ----------
    type : str or list of str or None
        Trace type(s) to match (e.g. ``"scatter"``, ``["scatter", "bar"]``).
        Case-insensitive comparison against ``trace.type``.
    row : int or None
        Subplot row index (1-based).  Works with figures created via
        :func:`plotly.subplots.make_subplots` **and** with figures that
        use Plotly Express facets (row/col is inferred from axis
        references when no ``_grid_ref`` exists).
    col : int or None
        Subplot column index (1-based).  Same fallback logic as *row*.
    secondary_y : bool or None
        If ``True``, only traces on the secondary y-axis.
        If ``False``, only traces on the primary y-axis.
        If ``None``, do not filter by y-axis.
    legendgroup : str or re.Pattern or None
        Exact string or regex pattern to match against ``trace.legendgroup``.
    name : str or re.Pattern or None
        Exact string or compiled regex pattern to match against ``trace.name``.
        When a plain string is given, it is compiled as a full-match regex
        (``^...$``).  Pass a compiled pattern for partial / substring
        matching, e.g. ``name=re.compile("series_\\d+")``.
    customdata : dict or callable or object or None
        **Dict** — field-path selector: each key is a dot-separated path,
        each value is the expected value at that path.  For 2-D
        customdata arrays (one row per data-point), at least one row
        must satisfy all path constraints.  Numeric path segments
        select into arrays, e.g. ``customdata={"0": "APAC"}`` matches
        traces where the first customdata field of any row is
        ``"APAC"``.

        **Callable** — called with ``trace.customdata``; must return
        a boolean.

        **Other** — compared for equality with ``trace.customdata``
        (using :func:`_values_equal` which normalises list/tuple
        mismatches).
    meta : dict or callable or object or None
        **Dict** — field-path selector: each key is a dot-separated
        path into the trace's ``meta`` value, each value is the
        expected value.  E.g. ``meta={"source": "train"}`` matches
        traces whose ``meta`` dict has ``"source" == "train"``.

        **Callable** — called with ``trace.meta``; must return a
        boolean.

        **Other** — compared for equality with ``trace.meta``.
    selector : dict or callable or int or str or None
        Backward-compatible selector as accepted by
        :meth:`BaseFigure.select_traces`.  Applied *in addition* to
        all the other criteria (AND logic).

    Examples
    --------
    >>> import plotly.graph_objects as go
    >>> import re
    >>> sel = TraceSelector(type="scatter", legendgroup="group_a")
    >>> sel = TraceSelector(name=re.compile("series_\\d+"))
    >>> sel = TraceSelector(row=1, col=2, secondary_y=True)
    >>> sel = TraceSelector(customdata={"0": "APAC"})
    >>> sel = TraceSelector(meta={"source": "train", "version": 2})
    >>> sel = TraceSelector(customdata=lambda cd: cd is not None and len(cd) > 3)
    """

    _ACCEPTED_PARAMS = {
        "type",
        "row",
        "col",
        "secondary_y",
        "legendgroup",
        "name",
        "customdata",
        "meta",
        "selector",
    }

    def __init__(
        self,
        type=None,
        row=None,
        col=None,
        secondary_y=None,
        legendgroup=None,
        name=None,
        customdata=None,
        meta=None,
        selector=None,
    ):
        self.type = type
        self.row = row
        self.col = col
        self.secondary_y = secondary_y
        self.legendgroup = legendgroup
        self.name = name
        self.customdata = customdata
        self.meta = meta
        self.selector = selector

        if isinstance(type, str):
            self._types = {type.lower()}
        elif isinstance(type, (list, tuple, set)):
            self._types = {t.lower() for t in type}
        else:
            self._types = None

        if isinstance(name, str):
            self._name_pattern = re.compile("^" + re.escape(name) + "$")
        elif isinstance(name, re.Pattern):
            self._name_pattern = name
        else:
            self._name_pattern = None

        if isinstance(legendgroup, str):
            self._legendgroup_pattern = re.compile(
                "^" + re.escape(legendgroup) + "$"
            )
        elif isinstance(legendgroup, re.Pattern):
            self._legendgroup_pattern = legendgroup
        else:
            self._legendgroup_pattern = None

        if callable(customdata):
            self._customdata_mode = "callable"
        elif isinstance(customdata, dict):
            self._customdata_mode = "dict"
        elif customdata is not None:
            self._customdata_mode = "exact"
        else:
            self._customdata_mode = None

        if callable(meta):
            self._meta_mode = "callable"
        elif isinstance(meta, dict):
            self._meta_mode = "dict"
        elif meta is not None:
            self._meta_mode = "exact"
        else:
            self._meta_mode = None

    def matches(self, trace):
        """
        Return ``True`` if *trace* satisfies all selection criteria.

        Parameters
        ----------
        trace : BaseTraceType
            A trace object from a Figure.

        Returns
        -------
        bool
        """
        if self._types is not None:
            trace_type = getattr(trace, "type", None)
            if trace_type is None or trace_type.lower() not in self._types:
                return False

        if self._name_pattern is not None:
            trace_name = getattr(trace, "name", None)
            if trace_name is None or not self._name_pattern.search(
                str(trace_name)
            ):
                return False

        if self._legendgroup_pattern is not None:
            trace_lg = getattr(trace, "legendgroup", None)
            if trace_lg is None or not self._legendgroup_pattern.search(
                str(trace_lg)
            ):
                return False

        if self._customdata_mode is not None:
            trace_cd = getattr(trace, "customdata", None)
            if self._customdata_mode == "callable":
                try:
                    if not self.customdata(trace_cd):
                        return False
                except Exception:
                    return False
            elif self._customdata_mode == "dict":
                if not _match_dict_spec(trace_cd, self.customdata):
                    return False
            else:
                if not _values_equal(trace_cd, self.customdata):
                    return False

        if self._meta_mode is not None:
            trace_meta = getattr(trace, "meta", None)
            if self._meta_mode == "callable":
                try:
                    if not self.meta(trace_meta):
                        return False
                except Exception:
                    return False
            elif self._meta_mode == "dict":
                if not _match_dict_spec(trace_meta, self.meta):
                    return False
            else:
                if not _values_equal(trace_meta, self.meta):
                    return False

        if self.selector is not None:
            from plotly.basedatatypes import BaseFigure

            if not BaseFigure._selector_matches(trace, self.selector):
                return False

        return True

    @property
    def uses_subplot(self):
        """Whether this selector references subplot row/col/secondary_y."""
        return (
            self.row is not None
            or self.col is not None
            or self.secondary_y is not None
        )

    def __repr__(self):
        parts = []
        if self.type is not None:
            parts.append(f"type={self.type!r}")
        if self.row is not None:
            parts.append(f"row={self.row!r}")
        if self.col is not None:
            parts.append(f"col={self.col!r}")
        if self.secondary_y is not None:
            parts.append(f"secondary_y={self.secondary_y!r}")
        if self.legendgroup is not None:
            parts.append(f"legendgroup={self.legendgroup!r}")
        if self.name is not None:
            parts.append(f"name={self.name!r}")
        if self.customdata is not None:
            parts.append(f"customdata={self.customdata!r}")
        if self.meta is not None:
            parts.append(f"meta={self.meta!r}")
        if self.selector is not None:
            parts.append(f"selector={self.selector!r}")
        return f"TraceSelector({', '.join(parts)})"

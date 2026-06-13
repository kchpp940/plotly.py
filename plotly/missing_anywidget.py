from .basedatatypes import BaseFigure
from _plotly_utils.error_messages import ErrorCode, build_error_message, format_install_hint


class FigureWidget(BaseFigure):
    """
    FigureWidget stand-in for use when anywidget is not installed. The only purpose
    of this class is to provide something to import as
    `plotly.graph_objs.FigureWidget` when anywidget is not installed. This class
    simply raises an informative error message when the constructor is called
    """

    def __init__(self, *args, **kwargs):
        raise ImportError(
            build_error_message(
                ErrorCode.DEPENDENCY_MISSING,
                "The FigureWidget class requires the anywidget package",
                install_hint=format_install_hint("anywidget"),
            )
        )

import plotly.graph_objs as go
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class AnnotationTarget(Enum):
    INITIAL_LAYOUT = "initial_layout"
    FRAME_LAYOUT = "frame_layout"
    BOTH = "both"


@dataclass
class AnnotationSpec:
    text: str
    x: Optional[float] = None
    y: Optional[float] = None
    xref: str = "paper"
    yref: str = "paper"
    target: AnnotationTarget = AnnotationTarget.INITIAL_LAYOUT
    frame_name: Optional[str] = None
    showarrow: bool = False
    font: Optional[Dict[str, Any]] = None
    align: str = "center"
    xanchor: Optional[str] = None
    yanchor: Optional[str] = None
    xshift: Optional[float] = None
    yshift: Optional[float] = None
    opacity: Optional[float] = None
    textangle: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "text": self.text,
            "showarrow": self.showarrow,
            "align": self.align,
        }
        if self.x is not None:
            result["x"] = self.x
        if self.y is not None:
            result["y"] = self.y
        if self.xref != "paper":
            result["xref"] = self.xref
        if self.yref != "paper":
            result["yref"] = self.yref
        if self.font is not None:
            result["font"] = self.font
        if self.xanchor is not None:
            result["xanchor"] = self.xanchor
        if self.yanchor is not None:
            result["yanchor"] = self.yanchor
        if self.xshift is not None:
            result["xshift"] = self.xshift
        if self.yshift is not None:
            result["yshift"] = self.yshift
        if self.opacity is not None:
            result["opacity"] = self.opacity
        if self.textangle is not None:
            result["textangle"] = self.textangle
        result.update(self.extra)
        return result


class AnnotationCollector:
    def __init__(self):
        self._annotations: List[AnnotationSpec] = []

    def add(self, annotation: AnnotationSpec) -> None:
        self._annotations.append(annotation)

    def add_many(self, annotations: List[AnnotationSpec]) -> None:
        self._annotations.extend(annotations)

    def get_all(self) -> List[AnnotationSpec]:
        return list(self._annotations)

    def get_by_target(self, target: AnnotationTarget) -> List[AnnotationSpec]:
        return [a for a in self._annotations if a.target == target]

    def get_by_frame(self, frame_name: str) -> List[AnnotationSpec]:
        return [
            a for a in self._annotations
            if (a.target == AnnotationTarget.FRAME_LAYOUT and a.frame_name == frame_name)
            or (a.target == AnnotationTarget.BOTH and (a.frame_name is None or a.frame_name == frame_name))
        ]


class AnnotationApplier:
    @staticmethod
    def apply_initial_layout(
        fig: go.Figure,
        collector: AnnotationCollector,
    ) -> None:
        initial_anns = collector.get_by_target(AnnotationTarget.INITIAL_LAYOUT)
        both_anns = collector.get_by_target(AnnotationTarget.BOTH)
        all_anns = initial_anns + both_anns

        if all_anns:
            ann_dicts = [a.to_dict() for a in all_anns]
            existing = fig.layout.annotations or ()
            fig.layout.annotations = list(existing) + ann_dicts

    @staticmethod
    def apply_frame_layouts(
        fig: go.Figure,
        collector: AnnotationCollector,
        frame_names: List[str],
    ) -> None:
        for frame_name in frame_names:
            all_anns = collector.get_by_frame(frame_name)

            if all_anns:
                ann_dicts = [a.to_dict() for a in all_anns]
                for frame in fig.frames:
                    if frame.name == frame_name:
                        if not hasattr(frame, "layout") or frame.layout is None:
                            frame.layout = {}
                        if "annotations" not in frame.layout or frame.layout["annotations"] is None:
                            existing = []
                        else:
                            existing = list(frame.layout["annotations"])
                        existing.extend(ann_dicts)
                        frame.layout["annotations"] = existing
                        break

    @staticmethod
    def apply_all(
        fig: go.Figure,
        collector: AnnotationCollector,
        frame_names: Optional[List[str]] = None,
    ) -> None:
        AnnotationApplier.apply_initial_layout(fig, collector)
        if frame_names:
            AnnotationApplier.apply_frame_layouts(fig, collector, frame_names)


def create_facet_annotations(
    col_labels: List[str],
    row_labels: List[str],
    col_label_prefix: str = "",
    row_label_prefix: str = "",
    subplot_labels: Optional[List[str]] = None,
    nrows: int = 1,
    ncols: int = 1,
    facet_col_wrap: int = 0,
) -> List[AnnotationSpec]:
    annotations: List[AnnotationSpec] = []

    if facet_col_wrap and subplot_labels:
        for i, label in enumerate(subplot_labels):
            if label is None:
                continue
            row_idx = i // ncols
            col_idx = i % ncols
            x = (col_idx + 0.5) / ncols
            y = 1 - (row_idx / nrows)
            annotations.append(
                AnnotationSpec(
                    text=label,
                    x=x,
                    y=y,
                    xref="paper",
                    yref="paper",
                    yanchor="bottom",
                    yshift=10,
                    target=AnnotationTarget.INITIAL_LAYOUT,
                )
            )
    else:
        for j, label in enumerate(col_labels):
            x = (j + 0.5) / ncols
            text = col_label_prefix + str(label) if col_label_prefix else str(label)
            annotations.append(
                AnnotationSpec(
                    text=text,
                    x=x,
                    y=1.0,
                    xref="paper",
                    yref="paper",
                    yanchor="bottom",
                    yshift=10,
                    target=AnnotationTarget.INITIAL_LAYOUT,
                )
            )
        for i, label in enumerate(reversed(row_labels)):
            y = (i + 0.5) / nrows
            text = row_label_prefix + str(label) if row_label_prefix else str(label)
            annotations.append(
                AnnotationSpec(
                    text=text,
                    x=1.0,
                    y=y,
                    xref="paper",
                    yref="paper",
                    xanchor="left",
                    xshift=10,
                    textangle=-90,
                    target=AnnotationTarget.INITIAL_LAYOUT,
                )
            )

    return annotations


def create_trendline_annotation(
    fit_results: Any,
    x: float,
    y: float,
    xref: str = "x",
    yref: str = "y",
    frame_name: Optional[str] = None,
    target: AnnotationTarget = AnnotationTarget.INITIAL_LAYOUT,
) -> AnnotationSpec:
    text = f"R² = {fit_results.rsquared:.4f}" if hasattr(fit_results, "rsquared") else "Trendline"
    return AnnotationSpec(
        text=text,
        x=x,
        y=y,
        xref=xref,
        yref=yref,
        showarrow=True,
        frame_name=frame_name,
        target=target,
        extra=dict(arrowhead=1, ax=20, ay=-30),
    )


def create_stat_annotation(
    text: str,
    x: float,
    y: float,
    xref: str = "paper",
    yref: str = "paper",
    frame_name: Optional[str] = None,
    target: AnnotationTarget = AnnotationTarget.INITIAL_LAYOUT,
) -> AnnotationSpec:
    return AnnotationSpec(
        text=text,
        x=x,
        y=y,
        xref=xref,
        yref=yref,
        showarrow=False,
        align="left",
        xanchor="left",
        yanchor="top",
        frame_name=frame_name,
        target=target,
        font=dict(size=10),
    )


def create_marginal_annotation(
    text: str,
    x: float,
    y: float,
    xref: str = "paper",
    yref: str = "paper",
) -> AnnotationSpec:
    return AnnotationSpec(
        text=text,
        x=x,
        y=y,
        xref=xref,
        yref=yref,
        showarrow=False,
        font=dict(size=9),
        target=AnnotationTarget.INITIAL_LAYOUT,
    )


def create_frame_annotation(
    text: str,
    x: float,
    y: float,
    frame_name: str,
    xref: str = "paper",
    yref: str = "paper",
) -> AnnotationSpec:
    return AnnotationSpec(
        text=text,
        x=x,
        y=y,
        xref=xref,
        yref=yref,
        frame_name=frame_name,
        target=AnnotationTarget.FRAME_LAYOUT,
    )


def extract_subplot_title_specs(fig: go.Figure) -> List[AnnotationSpec]:
    """
    Extract annotations created by make_subplots row/column/subplot titles
    and convert them into AnnotationSpec instances. Clear the figure's
    layout.annotations so that all annotations flow through the unified
    AnnotationCollector/Applier pipeline.
    """
    specs: List[AnnotationSpec] = []
    existing = fig.layout.annotations or ()

    for ann in existing:
        ann_dict = ann.to_plotly_json()
        text = ann_dict.pop("text", "")
        x = ann_dict.pop("x", None)
        y = ann_dict.pop("y", None)
        xref = ann_dict.pop("xref", "paper")
        yref = ann_dict.pop("yref", "paper")
        showarrow = ann_dict.pop("showarrow", False)
        font = ann_dict.pop("font", None)
        align = ann_dict.pop("align", "center")
        xanchor = ann_dict.pop("xanchor", None)
        yanchor = ann_dict.pop("yanchor", None)
        xshift = ann_dict.pop("xshift", None)
        yshift = ann_dict.pop("yshift", None)
        opacity = ann_dict.pop("opacity", None)
        textangle = ann_dict.pop("textangle", None)

        spec = AnnotationSpec(
            text=text,
            x=x,
            y=y,
            xref=xref,
            yref=yref,
            showarrow=showarrow,
            font=font,
            align=align,
            xanchor=xanchor,
            yanchor=yanchor,
            xshift=xshift,
            yshift=yshift,
            opacity=opacity,
            textangle=textangle,
            target=AnnotationTarget.INITIAL_LAYOUT,
            extra=ann_dict,
        )
        specs.append(spec)

    fig.layout.annotations = []
    return specs

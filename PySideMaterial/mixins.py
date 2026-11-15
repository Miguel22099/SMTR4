from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, Literal, Self, cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QBoxLayout,
    QLayout,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from ..events import Event, StateVar
from .protocols import (
    EventEmiter,
    Subscribable,
    SupportsRichTextChanged,
    SupportsSetChecked,
    SupportsSetText,
    SupportsStrTextChanged,
)

type LayoutItem = "QWidget | QLayout | QSpacerItem | Stretch"


@dataclass(frozen=True, slots=True)
class Stretch:
    val: int = 1


class BoxLayoutMixin:
    def __init__(self, *items: LayoutItem, spacing: int = 10, stretch: int = 0) -> None:
        super().__init__()
        assert isinstance(self, QBoxLayout)

        self._stretch = stretch
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

        for item in items:
            match item:
                case QWidget():
                    self.addWidget(
                        item,
                        getattr(item, "_stretch", 0),
                        getattr(item, "_alignment", Qt.AlignmentFlag(0)),
                    )
                case QLayout():
                    self.addLayout(item, getattr(item, "_stretch", 0))
                case QSpacerItem():
                    self.addSpacerItem(item)
                case Stretch():
                    self.addStretch(item.val)
                case _:
                    raise TypeError(
                        f"Elemento no soportado en el layout: {type(item).__name__}"
                    )


class WidgetPropsMixin:
    @property
    def _widget(self) -> QWidget:
        assert isinstance(self, QWidget)
        return self

    def props(
        self,
        *,
        object_name: str | None = None,
        stretch: int | None = None,
        alignment: Qt.AlignmentFlag | None = None,
        font: QFont | str | Sequence[str] | None = None,
    ) -> Self:
        w = self._widget
        if stretch is not None:
            self._stretch = stretch
        if alignment is not None:
            self._alignment = alignment
        if object_name is not None:
            w.setObjectName(object_name)
        if font is not None:
            w.setFont(font)
        return self

    def withFixedSize(
        self, width: int | None = None, height: int | None = None
    ) -> Self:
        w = self._widget
        if width is not None:
            w.setFixedWidth(width)
        if height is not None:
            w.setFixedHeight(height)
        return self

    def withMinimumSize(
        self, width: int | None = None, height: int | None = None
    ) -> Self:
        w = self._widget
        if width is not None:
            w.setMinimumWidth(width)
        if height is not None:
            w.setMinimumHeight(height)
        return self

    def withMaximumSize(
        self, width: int | None = None, height: int | None = None
    ) -> Self:
        w = self._widget
        if width is not None:
            w.setMaximumWidth(width)
        if height is not None:
            w.setMaximumHeight(height)
        return self

    def enabledBy(self, event: EventEmiter[bool], disabled: bool = True) -> Self:
        w = self._widget
        w.setDisabled(disabled)
        event.connect(w.setEnabled)
        return self

    def hiddenBy(self, event: EventEmiter[bool], hidden: bool = True) -> Self:
        w = self._widget
        w.setHidden(hidden)
        event.connect(w.setHidden)
        return self

    def withStyleSheet(self, style_sheet: str) -> Self:
        w = self._widget
        w.setStyleSheet(style_sheet)
        return self

    def withSizePolicy(
        self, horizontal: QSizePolicy.Policy, vertical: QSizePolicy.Policy
    ) -> Self:
        w = self._widget
        w.setSizePolicy(horizontal, vertical)
        return self

    def withAlignment(self, alignment: Qt.AlignmentFlag) -> Self:
        """Alignment used when this widget is placed inside a Row or Column."""
        self._alignment = alignment
        return self

    def bordered(
        self,
        color: str = "#414141",
        width: int = 1,
        radius: int = 8,
        style: Literal["solid", "dashed", "dotted"] = "solid",
    ) -> Self:
        """Adds a border rule scoped to the widget's nearest QtWidgets class."""
        w = self._widget
        selector = next(
            (
                cls.__name__
                for cls in type(w).__mro__
                if cls.__module__.startswith("PySide6.QtWidgets")
            ),
            "QWidget",
        )
        rule = (
            f"{selector} {{ border: {width}px {style} {color};"
            f" border-radius: {radius}px; }}"
        )
        w.setStyleSheet("\n".join(part for part in (w.styleSheet(), rule) if part))
        return self

    def enabledByAll(self, *conditions: StateVar[bool], disabled: bool = True) -> Self:
        """Enables the widget only while every given condition is true."""
        w = self._widget

        combined = Event[bool]()
        buffer = [False for _ in conditions]

        def update(index: int, status: object) -> None:
            buffer[index] = bool(status)
            combined.emit(all(buffer))

        for index, condition in enumerate(conditions):
            condition.connect(partial(update, index))

        w.setDisabled(disabled)
        combined.connect(w.setEnabled)
        return self

    @classmethod
    def renamedTo[T](cls: type[T], object_name: str) -> type[T]:
        assert issubclass(cls, QWidget)

        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            super(new_cls, self).__init__(*args, **kwargs)
            self.setObjectName(object_name)

        new_cls = type(
            object_name,
            (cls,),
            {
                "__init__": __init__,
                "__module__": cls.__module__,
            },
        )
        return cast(type[T], new_cls)


class SetTextMixin(WidgetPropsMixin):
    def textBy(self, event: Subscribable[str]) -> Self:
        target = cast(SupportsSetText, self)
        event.connect(target.setText)
        return self

    def clean(self) -> None:
        target = cast(SupportsSetText, self)
        target.setText("")


class LineTextMixin(SetTextMixin):
    def writeOn(self, state: StateVar[str]) -> Self:
        target = cast(SupportsStrTextChanged, self)
        target.textChanged.connect(state.set_value)
        return self


class RichTextMixin(SetTextMixin):
    def writeOn(self, state: StateVar[str]) -> Self:
        target = cast(SupportsRichTextChanged, self)
        target.textChanged.connect(lambda: state.set_value(target.toPlainText()))
        return self


class CheckableMixin(WidgetPropsMixin):
    def checkBy(self, event: Subscribable[bool]) -> Self:
        target = cast(SupportsSetChecked, self)
        event.connect(target.setChecked)
        return self

    def checkOn(self, event: EventEmiter[bool]) -> Self:
        target = cast(SupportsSetChecked, self)
        target.toggled.connect(event.emit)
        return self

    def clean(self) -> None:
        target = cast(SupportsSetChecked, self)
        target.setChecked(False)

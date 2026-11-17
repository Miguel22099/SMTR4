from collections.abc import Callable, Sequence
from functools import partial
from typing import Any, Literal, Self, cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractButton,
    QBoxLayout,
    QLayout,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from ..events import Event, StateVar
from .core import Stretch
from .protocols import (
    EventEmiter,
    ObjectProperty,
    Subscribable,
    SupportsRichTextChanged,
    SupportsSetChecked,
    SupportsSetText,
    SupportsStrTextChanged,
)

type LayoutItem = "QWidget | QLayout | QSpacerItem | Stretch"


class BoxLayoutMixin:
    def __init__(
        self,
        *items: LayoutItem,
        spacing: int = 10,
        stretch: int = 0,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    ) -> None:
        super().__init__()
        assert isinstance(self, QBoxLayout)

        self._stretch = stretch
        self.setSpacing(spacing)
        self.setContentsMargins(*margins)

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

    @classmethod
    def withProperties[T](cls: type[T], *properties: ObjectProperty) -> type[T]:
        assert issubclass(cls, QBoxLayout)

        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            super(new_cls, self).__init__(*args, **kwargs)
            for p in properties:
                p(self)

        new_cls = type(
            f"Standardized[{cls.__name__}]",
            (cls,),
            {
                "__init__": __init__,
                "__module__": cls.__module__,
            },
        )
        return cast(type[T], new_cls)


class WidgetPropsMixin:
    @property
    def _widget(self) -> QWidget:
        assert isinstance(self, QWidget)
        return self

    def _bind(self, event: Any, callback: Callable[..., Any]) -> None:
        """Suscribe un callback al evento y limpia la conexión al destruir el widget."""
        w = self._widget

        def _safe_callback(*args: Any) -> None:
            try:
                callback(*args)
            except RuntimeError:
                pass

        sub = event.connect(_safe_callback)
        if callable(sub):
            w.destroyed.connect(lambda *_: sub())
        elif hasattr(event, "disconnect"):
            w.destroyed.connect(lambda *_: event.disconnect(_safe_callback))

    def setProps(
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
            old_name = w.objectName()
            w.setObjectName(object_name)
            if old_name and f"#{old_name} {{" in w.styleSheet():
                w.setStyleSheet(
                    w.styleSheet().replace(f"#{old_name} {{", f"#{object_name} {{")
                )
        if font is not None:
            if isinstance(font, str):
                resolved_font = QFont(font)
            elif isinstance(font, Sequence):
                resolved_font = QFont(list(font))
            else:
                resolved_font = font
            w.setFont(resolved_font)
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
        initial = bool(getattr(event, "value", not disabled))
        w.setEnabled(initial)
        self._bind(event, w.setEnabled)
        return self

    def hiddenBy(self, event: EventEmiter[bool], hidden: bool = True) -> Self:
        w = self._widget
        initial = bool(getattr(event, "value", hidden))
        w.setHidden(initial)
        self._bind(event, w.setHidden)
        return self

    def hiddenUntil(self, event: EventEmiter[[]], hidden: bool = True) -> Self:
        w = self._widget
        w.setHidden(hidden)
        self._bind(event, lambda: w.setHidden(False))
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
        """Adds a border rule scoped strictly to this widget via objectName."""
        w = self._widget
        if not w.objectName():
            w.setObjectName(f"_bordered_{id(w)}")

        selector = f"#{w.objectName()}"
        rule = (
            f"{selector} {{ border: {width}px {style} {color};"
            f" border-radius: {radius}px; }}"
        )
        existing = [
            line
            for line in w.styleSheet().splitlines()
            if not line.startswith(f"{selector} {{ border:")
        ]
        existing.append(rule)
        w.setStyleSheet("\n".join(existing))
        return self

    def enabledByAll(self, *conditions: StateVar[bool], disabled: bool = True) -> Self:
        """Enables the widget only while every given condition is true."""
        w = self._widget
        if not conditions:
            w.setDisabled(disabled)
            return self

        combined = Event[bool]()
        refs: list[Any] = getattr(w, "_reactive_refs", [])
        refs.append(combined)
        w._reactive_refs = refs  # type: ignore[attr-defined]

        buffer = [bool(getattr(c, "value", not disabled)) for c in conditions]

        def update(index: int, status: object) -> None:
            buffer[index] = bool(status)
            combined.emit(all(buffer))

        for index, condition in enumerate(conditions):
            self._bind(condition, partial(update, index))

        w.setEnabled(all(buffer))
        self._bind(combined, w.setEnabled)
        return self

    @classmethod
    def withProperties[T](
        cls: type[T], object_name: str, *properties: ObjectProperty
    ) -> type[T]:
        assert issubclass(cls, QWidget)

        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            super(new_cls, self).__init__(*args, **kwargs)
            self.setObjectName(object_name)
            for p in properties:
                p(self)

        new_cls = type(
            object_name,
            (cls,),
            {
                "__init__": __init__,
                "__module__": cls.__module__,
            },
        )
        return cast(type[T], new_cls)


class ButtonMixin(WidgetPropsMixin):
    @property
    def _button(self) -> QAbstractButton:
        assert isinstance(self, QAbstractButton)
        return self

    def onClick(self, action: Callable[[], None]) -> Self:
        self._button.clicked.connect(action)
        return self

    def onPress(self, action: Callable[[], None]) -> Self:
        self._button.pressed.connect(action)
        return self

    def onRelease(self, action: Callable[[], None]) -> Self:
        self._button.released.connect(action)
        return self

    def onToggle(self, action: Callable[[bool], None]) -> Self:
        self._button.toggled.connect(action)
        return self


class SetTextMixin(WidgetPropsMixin):
    def textBy(self, event: Subscribable[str]) -> Self:
        target = cast(SupportsSetText, self)
        self._bind(event, target.setText)
        return self

    def clear(self) -> None:
        target = cast(SupportsSetText, self)
        target.setText("")

    clean = clear


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


class CheckableMixin(ButtonMixin):
    def checkBy(self, event: Subscribable[bool]) -> Self:
        target = cast(SupportsSetChecked, self)
        self._bind(event, target.setChecked)
        return self

    def checkOn(self, event: EventEmiter[bool]) -> Self:
        target = cast(SupportsSetChecked, self)
        target.toggled.connect(event.emit)
        return self

    def clear(self) -> None:
        target = cast(SupportsSetChecked, self)
        target.setChecked(False)

    clean = clear

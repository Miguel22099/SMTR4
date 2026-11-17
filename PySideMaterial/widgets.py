from collections.abc import Callable, Sequence
from typing import Any, Literal, Self, cast

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QBoxLayout,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..converters import coerce_in
from ..events import Event, StateVar, StatusHolder
from ..filters import Filter, TextFilter
from .mixins import (
    BoxLayoutMixin,
    ButtonMixin,
    CheckableMixin,
    LineTextMixin,
    RichTextMixin,
    SetTextMixin,
    WidgetPropsMixin,
)

type ScreenEntry = QWidget | Callable[[], QWidget]
type FormEntry = tuple[str, QWidget] | str
type GroupLayout = QVBoxLayout | QHBoxLayout | QGridLayout
type DropdownItem[T] = str | tuple[str, T]


class MWidget(QWidget, WidgetPropsMixin): ...


class Container(QWidget, WidgetPropsMixin):
    """Frame widget that hosts a single layout."""

    def __init__(self, layout: QLayout, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setLayout(layout)


class ListWidget(QListWidget, WidgetPropsMixin):
    """QListWidget preloaded with items, with selection mode and sorting already configured."""

    def __init__(
        self,
        *data: str,
        selectionMode: QAbstractItemView.SelectionMode = QAbstractItemView.SelectionMode.SingleSelection,
        sorting: bool = False,
        currentRow: int = -1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setSelectionMode(selectionMode)
        self.setSortingEnabled(sorting)
        self.addItems(data)
        if currentRow >= 0:
            self.setCurrentRow(currentRow)

    def bindAction(self, action: Callable[["ListWidget"], object]) -> Self:
        """Runs `action` on this list and returns it, so calls can be chained."""
        action(self)
        return self


class Row(BoxLayoutMixin, QHBoxLayout): ...


class Column(BoxLayoutMixin, QVBoxLayout): ...


class Label(QLabel, SetTextMixin): ...


class Button(QPushButton, SetTextMixin, ButtonMixin): ...


class LineEdit(QLineEdit, LineTextMixin):
    def withMaxLength(self, length: int) -> Self:
        self.setMaxLength(length)
        return self

    def withFilter(self, filter: TextFilter | Filter) -> Self:
        """Re-applies `filter` over the text after every change."""
        f = filter if isinstance(filter, TextFilter) else filter.value

        def apply(text: str) -> None:
            filtered = f(text)
            if filtered == text:
                return
            pos = self.cursorPosition()
            diff = len(text) - len(filtered)
            self.setText(filtered)
            self.setCursorPosition(max(0, pos - diff))

        self.textChanged.connect(apply)
        return self

    def onTextEdited(self, action: Callable[[str], None]) -> Self:
        self.textEdited.connect(action)
        return self


class TextEdit(QTextEdit, RichTextMixin):
    def onTextChanged(self, action: Callable[[str], None]) -> Self:
        self.textChanged.connect(action)
        return self


class PlainTextEdit(QPlainTextEdit, RichTextMixin):
    def onTextChanged(self, action: Callable[[str], None]) -> Self:
        self.textChanged.connect(action)
        return self


class Image(QLabel, WidgetPropsMixin):
    def __init__(self, image: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPixmap(image)


class ImageState(QLabel, WidgetPropsMixin):
    def __init__(
        self, images: Sequence[QPixmap], parent: QWidget | None = None
    ) -> None:
        if not images:
            raise ValueError("ImageState requiere al menos una imagen.")
        super().__init__(parent)
        self._images = images
        self._max = len(self._images) - 1
        self.setPixmap(images[0])
        self.indexChanged = Event[int]()

    def setIndex(self, index: int, /) -> None:
        index = coerce_in(index, 0, self._max)
        self.setPixmap(self._images[index])
        self.indexChanged.emit(index)


class CheckBox(QCheckBox, CheckableMixin, SetTextMixin):
    def onCheck(self, action: Callable[[bool], None]) -> Self:
        self.toggled.connect(action)
        return self

    def onStateChanged(self, action: Callable[[Literal[1, 2, 3]], None]) -> Self:
        self.stateChanged.connect(action)
        return self


class ScreenManager(MWidget):
    def __init__(self, *screens: ScreenEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._screens: list[ScreenEntry] = list(screens)
        self._stack = QStackedLayout(self)
        self.indexChanged = Event[int]()

        self._materialize_leading_eager()
        if self._stack.count() == 0:
            self._materialize_next()

    @property
    def index(self) -> int:
        return max(0, self._stack.currentIndex())

    @property
    def maxIndex(self) -> int:
        return self._stack.count() - 1

    @property
    def canGoBack(self) -> bool:
        return self.index > 0

    @property
    def canGoForward(self) -> bool:
        return self.index + 1 < len(self._screens)

    def _is_lazy(self, idx: int) -> bool:
        return not isinstance(self._screens[idx], QWidget)

    def _materialize_leading_eager(self) -> None:
        while (idx := self._stack.count()) < len(self._screens) and not self._is_lazy(
            idx
        ):
            self._stack.addWidget(cast(QWidget, self._screens[idx]))

    def _materialize_next(self) -> bool:
        idx = self._stack.count()
        if idx >= len(self._screens):
            return False

        entry = self._screens[idx]
        widget = entry if isinstance(entry, QWidget) else entry()
        self._stack.addWidget(widget)
        return True

    def addScreen(self, screen: ScreenEntry) -> Self:
        has_pending_lazy = self._stack.count() < len(self._screens)
        self._screens.append(screen)

        if not has_pending_lazy and isinstance(screen, QWidget):
            self._stack.addWidget(screen)
        return self

    def nextScreen(self) -> None:
        target = self.index + 1
        if target >= self._stack.count() and not self._materialize_next():
            return
        self._stack.setCurrentIndex(target)
        self.indexChanged.emit(target)

    def prevScreen(self) -> None:
        curr = self.index
        if curr <= 0:
            return

        if curr == self.maxIndex and self._is_lazy(curr):
            widget = self._stack.widget(curr)
            if widget is not None:
                self._stack.removeWidget(widget)
                widget.hide()
                widget.deleteLater()

        self._stack.setCurrentIndex(curr - 1)
        self.indexChanged.emit(curr - 1)

    def setIndex(self, index: int, /) -> None:
        target = max(0, min(index, len(self._screens) - 1))
        while self.index < target:
            self.nextScreen()
        while self.index > target:
            self.prevScreen()

    def goToStart(self) -> None:
        self.setIndex(0)

    def insertScreen(self, index: int, screen: ScreenEntry) -> Self:
        target = max(0, min(index, len(self._screens)))
        prev_index = self._stack.currentIndex()
        materialized_count = self._stack.count()

        self._screens.insert(target, screen)

        if target < materialized_count:
            widget = screen if isinstance(screen, QWidget) else screen()
            self._stack.insertWidget(target, widget)

            if prev_index >= target:
                self.indexChanged.emit(self.index)

        elif target == materialized_count:
            if isinstance(screen, QWidget) or materialized_count == 0:
                widget = screen if isinstance(screen, QWidget) else screen()
                self._stack.addWidget(widget)
                self._materialize_leading_eager()

        return self


class Survey(MWidget):
    def __init__(
        self,
        *content: FormEntry,
        policy: QFormLayout.RowWrapPolicy = QFormLayout.RowWrapPolicy.WrapLongRows,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QFormLayout(self)
        layout.setRowWrapPolicy(policy)

        self._fields: list[QLineEdit] = []
        self.formStatus: list[StateVar[str]] = []
        self.anyTextFieldFilled = Event[bool]()
        self.allTextFieldFilled = Event[bool]()

        for entry in content:
            label, widget = (entry, LineEdit()) if isinstance(entry, str) else entry
            layout.addRow(label, widget)

            if isinstance(widget, QLineEdit):
                self._register_field(widget)

    def _register_field(self, field: QLineEdit) -> None:
        status = StateVar(field.text())
        self._fields.append(field)
        self.formStatus.append(status)

        def on_change(text: str) -> None:
            status.set_value(text)
            self._notify_status()

        field.textChanged.connect(on_change)

    def _notify_status(self) -> None:
        self.anyTextFieldFilled.emit(any(s.value for s in self.formStatus))
        self.allTextFieldFilled.emit(all(s.value for s in self.formStatus))

    def clear(self) -> None:
        for field in self._fields:
            field.clear()


class _OptionGroup(MWidget):
    """Base compartida para grupos de botones seleccionables."""

    def __init__(
        self,
        *names: str,
        orientation: GroupLayout | None = None,
        columns: int = 2,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._layout: GroupLayout = (
            orientation if orientation is not None else QVBoxLayout()
        )
        self._columns = max(1, columns)
        self._buttons: list[QAbstractButton] = []

        self.checkStatus = tuple(StatusHolder(False) for _ in names)
        self.anyChecked = StateVar(False)

        self.setLayout(self._layout)

    def _add_button(self, button: QAbstractButton, index: int) -> None:
        self._buttons.append(button)
        status = self.checkStatus[index]

        button.toggled.connect(status.write)
        button.toggled.connect(self._on_toggled)
        if hasattr(status, "connect"):
            self._bind(status, button.setChecked)

        if isinstance(self._layout, QGridLayout):
            row, col = divmod(index, self._columns)
            self._layout.addWidget(button, row, col)
        else:
            self._layout.addWidget(button)

    def _on_toggled(self, checked: bool) -> None:
        self.anyChecked.set_value(any(btn.isChecked() for btn in self._buttons))

    def clearOn(self, event: Any) -> Self:
        self._bind(event, lambda *_: self.clear())
        return self

    def clear(self) -> None:
        for btn in self._buttons:
            btn.setChecked(False)


class CheckBoxGroup(_OptionGroup):
    def __init__(
        self,
        *names: str,
        orientation: GroupLayout | None = None,
        defaultOn: Sequence[int] | int | None = None,
        columns: int = 2,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            *names, orientation=orientation, columns=columns, parent=parent
        )
        self.allChecked = StateVar(False)

        initial: set[int] = (
            set()
            if defaultOn is None
            else {defaultOn}
            if isinstance(defaultOn, int)
            else set(defaultOn)
        )

        for index, name in enumerate(names):
            checkbox = QCheckBox(name)
            self._add_button(checkbox, index)

            if index in initial:
                checkbox.setChecked(True)

    def _on_toggled(self, checked: bool) -> None:
        super()._on_toggled(checked)
        self.allChecked.set_value(
            bool(self._buttons) and all(btn.isChecked() for btn in self._buttons)
        )

    @property
    def selectedIndex(self) -> tuple[int, ...]:
        return tuple(i for i, btn in enumerate(self._buttons) if btn.isChecked())


class RadioGroup(_OptionGroup):
    def __init__(
        self,
        *names: str,
        orientation: GroupLayout | None = None,
        defaultOn: int | None = None,
        columns: int = 2,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            *names, orientation=orientation, columns=columns, parent=parent
        )
        self.container = QButtonGroup(self)
        self.indexChanged = Event[int]()

        self.container.idToggled.connect(self._on_id_toggled)

        for index, name in enumerate(names):
            radio = QRadioButton(name)
            self.container.addButton(radio, index)
            self._add_button(radio, index)

            if defaultOn == index:
                radio.setChecked(True)

    def _on_id_toggled(self, id: int, checked: bool) -> None:
        if checked:
            self.indexChanged.emit(id)

    @property
    def selectedIndex(self) -> int | None:
        checked_id = self.container.checkedId()
        return checked_id if checked_id >= 0 else None

    def clear(self) -> None:
        checked = self.container.checkedButton()
        if checked is None:
            return

        self.container.setExclusive(False)
        checked.setChecked(False)
        self.container.setExclusive(True)
        self.indexChanged.emit(-1)


class Dropdown[T = None](QComboBox, WidgetPropsMixin):
    def __init__(
        self,
        *content: DropdownItem[T],
        placeholder: str = "",
        text: str = "",
        maxVisibleItems: int = 5,
        editable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setEditable(editable)
        self.setMaxVisibleItems(maxVisibleItems)
        if placeholder:
            self.setPlaceholderText(placeholder)

        for item in content:
            if isinstance(item, str):
                self.addItem(item)
            else:
                label, data = item
                self.addItem(label, userData=data)

        if text:
            self.setCurrentText(text)
        elif placeholder:
            self.setCurrentIndex(-1)

    @property
    def selectedData(self) -> T | None:
        return cast(T | None, self.currentData())

    def dataAt(self, index: int) -> T | None:
        return cast(T | None, self.itemData(index))

    def addOption(self, label: str, data: T | None = None) -> Self:
        self.addItem(label, userData=data)
        return self

    def onDataChange(self, action: Callable[[T | None], Any]) -> Self:
        self.currentIndexChanged.connect(lambda _: action(self.selectedData))
        return self

    def onTextChange(self, action: Callable[[str], Any]) -> Self:
        self.currentTextChanged.connect(action)
        return self

    def onIndexChange(self, action: Callable[[int], Any]) -> Self:
        self.currentIndexChanged.connect(action)
        return self

    def onActivated(self, action: Callable[[int], Any]) -> Self:
        self.activated.connect(action)
        return self

    def writeOn(self, state: StateVar[str]) -> Self:
        self.currentTextChanged.connect(state.set_value)
        return self

    def clear(self) -> None:
        self.setCurrentIndex(-1)


class TemporalScreen(MWidget):
    def __init__(self, layout: QBoxLayout, life_time: int) -> None:
        super().__init__()
        self.setLayout(layout)
        self.timer = QTimer(self)
        self.lifeTimeFinished = Event[[]]()

        self.timer.singleShot(life_time, self.finish_existence)

        def delete() -> None:
            self.lifeTimeFinished.disconnect_all()
            del self.lifeTimeFinished

        self.destroyed.connect(delete)

    def onLifeTimeFinished(self, action: Callable[[], None]) -> Self:
        self.lifeTimeFinished.connect(action)
        return self

    def finish_existence(self) -> None:
        self.setParent(None)
        self.deleteLater()
        self.lifeTimeFinished.emit()

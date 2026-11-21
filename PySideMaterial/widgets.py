from collections.abc import Callable, Sequence
from typing import Any, Literal, Self, cast

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QPixmap
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
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..converters import coerce_in
from ..events import Event, StateVar, StatusHolder
from ..filters import Filter, TextFilter
from ..type_defs import Action
from .mixins import (
    BoxLayoutMixin,
    ButtonMixin,
    CheckableMixin,
    LayoutItem,
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

    def bindAction(self, action: Action[["ListWidget"]]) -> Self:
        """Runs `action` on this list and returns it, so calls can be chained."""
        action(self)
        return self


class Table(QTableWidget, WidgetPropsMixin):
    """QTableWidget preloaded with headers, read-only and row-selected.

    Store an arbitrary payload per row via `data` in `addRow`; `onSelect`
    emits that payload when the user selects a row.

    Columns fit their content and share the viewport width. A width chosen by
    dragging a header edge is kept, and the surplus is distributed among the
    remaining columns, so extending the window never leaves uncovered space.
    """

    def __init__(self, *headers: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self._custom_widths: dict[int, int] = {}
        self._fitting = False
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.sectionResized.connect(self._onSectionResized)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def clear(self) -> None:
        self.setRowCount(0)
        self._fitColumns()

    def addRow(self, *cells: str, data: Any = None) -> Self:
        row = self.rowCount()
        self.insertRow(row)
        for col, text in enumerate(cells):
            item = QTableWidgetItem(text)
            if col == 0:
                item.setData(Qt.ItemDataRole.UserRole, data)
            self.setItem(row, col, item)
        self._fitColumns()
        return self

    def _onSectionResized(self, index: int, _old: int, new: int) -> None:
        """Remembers a width the user picked by dragging a header edge, then
        re-fits the remaining columns so no gap is left behind."""
        if self._fitting:
            return
        self._custom_widths[index] = new
        if len(self._custom_widths) < self.columnCount():
            QTimer.singleShot(0, self._fitColumns)

    def _fitColumns(self) -> None:
        """Keeps user-customised widths, sizes the rest to their content and
        shares the viewport width between them.

        Free columns grow proportionally to fill any surplus, so extending the
        window never leaves uncovered space, and never shrink below their
        content size (a scrollbar appears when the viewport is too narrow).
        """
        header = self.horizontalHeader()
        count = self.columnCount()
        if count == 0 or (viewport := self.viewport().width()) <= 0:
            return

        self._custom_widths = {
            i: w for i, w in self._custom_widths.items() if 0 <= i < count
        }
        custom = self._custom_widths
        hints = [max(header.sectionSizeHint(i), 1) for i in range(count)]
        free = [i for i in range(count) if i not in custom]

        widths = dict(custom)
        available = viewport - sum(custom.values())

        if not free:
            # Every column is customised: scale them proportionally so the
            # table still covers the viewport.
            total = sum(custom.values()) or 1
            factor = viewport / total
            fitted = [max(int(w * factor), 1) for w in custom.values()]
            fitted[-1] += viewport - sum(fitted)  # rounding remainder
            widths = dict(zip(custom.keys(), fitted))
        elif available >= sum(hints[i] for i in free):
            # Surplus: grow free columns proportionally until they fill it.
            free_hints = sum(hints[i] for i in free)
            factor = available / free_hints
            fitted = [int(hints[i] * factor) for i in free]
            fitted[-1] += available - sum(fitted)  # rounding remainder
            widths.update(zip(free, fitted))
        else:
            # Free columns keep at least their content size; the table scrolls.
            widths.update((i, hints[i]) for i in free)

        self._fitting = True
        try:
            for i in range(count):
                self.setColumnWidth(i, widths[i])
        finally:
            self._fitting = False

    def resizeEvent(self, event: Any) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._fitColumns()

    @property
    def selectedData(self) -> Any | None:
        item = self.item(self.currentRow(), 0)
        return None if item is None else item.data(Qt.ItemDataRole.UserRole)

    def onSelect(self, action: Action[[Any]]) -> Self:
        def on_selection() -> None:
            if (data := self.selectedData) is not None:
                action(data)

        self.itemSelectionChanged.connect(on_selection)
        return self


class Tree(QTreeWidget, WidgetPropsMixin):
    """QTreeWidget preloaded with headers; each item may carry a payload.

    `addBranch` stores an arbitrary payload in column 0's UserRole, and the
    `onCurrent`/`onSelect` callbacks emit that payload on selection.
    """

    def __init__(self, *headers: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setColumnCount(len(headers))
        self.setHeaderLabels(headers)

    def addBranch(
        self,
        label: str,
        data: Any = None,
        *,
        parent: QTreeWidgetItem | None = None,
    ) -> Self:
        item = QTreeWidgetItem([label])
        if data is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, data)
        if parent is None:
            self.addTopLevelItem(item)
        else:
            parent.addChild(item)
        return self

    @property
    def selectedData(self) -> Any | None:
        item = self.currentItem()
        return None if item is None else item.data(0, Qt.ItemDataRole.UserRole)

    def selectData(self, data: Any) -> Self:
        """Selects the first item whose payload equals `data` (no-op if absent)."""
        stack = [
            item
            for i in range(self.topLevelItemCount())
            if (item := self.topLevelItem(i)) is not None
        ]
        while stack:
            current = stack.pop()
            if current.data(0, Qt.ItemDataRole.UserRole) == data:
                self.setCurrentItem(current)
                return self
            stack.extend(
                child
                for i in range(current.childCount())
                if (child := current.child(i)) is not None
            )
        return self

    def onCurrent(self, action: Action[[Any]]) -> Self:
        """Fires `action(payload)` on every selection change, `None` included."""

        def on_change() -> None:
            action(self.selectedData)

        self.itemSelectionChanged.connect(on_change)
        return self

    def onSelect(self, action: Action[[Any]]) -> Self:
        """Fires `action(payload)` only when a payload-carrying item is selected."""

        def on_change() -> None:
            if (data := self.selectedData) is not None:
                action(data)

        self.itemSelectionChanged.connect(on_change)
        return self


class Row(BoxLayoutMixin, QHBoxLayout):
    def __init__(
        self,
        *items: LayoutItem,
        spacing: int = 10,
        stretch: int = 0,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    ) -> None:
        super().__init__()
        self.setup(*items, spacing=spacing, stretch=stretch, margins=margins)


class Column(BoxLayoutMixin, QVBoxLayout):
    def __init__(
        self,
        *items: LayoutItem,
        spacing: int = 10,
        stretch: int = 0,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    ) -> None:
        super().__init__()
        self.setup(*items, spacing=spacing, stretch=stretch, margins=margins)


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

    def onTextEdited(self, action: Action[[str]]) -> Self:
        self.textEdited.connect(action)
        return self


class TextEdit(QTextEdit, RichTextMixin):
    def onTextChanged(self, action: Action[[str]]) -> Self:
        self.textChanged.connect(action)
        return self


class PlainTextEdit(QPlainTextEdit, RichTextMixin):
    def onTextChanged(self, action: Action[[str]]) -> Self:
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
    def onCheck(self, action: Action[[bool]]) -> Self:
        self.toggled.connect(action)
        return self

    def onStateChanged(self, action: Action[[Literal[1, 2, 3]]]) -> Self:
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

    def onDataChange(self, action: Action[[T | None]]) -> Self:
        self.currentIndexChanged.connect(lambda _: action(self.selectedData))
        return self

    def onTextChange(self, action: Action[[str]]) -> Self:
        self.currentTextChanged.connect(action)
        return self

    def onIndexChange(self, action: Action[[int]]) -> Self:
        self.currentIndexChanged.connect(action)
        return self

    def onActivated(self, action: Action[[int]]) -> Self:
        self.activated.connect(action)
        return self

    def writeOn(self, state: StateVar[str]) -> Self:
        self.currentTextChanged.connect(state.set_value)
        return self

    def clear(self) -> None:
        self.setCurrentIndex(-1)


class Menu(QMenu, WidgetPropsMixin):
    """Dropdown menu chainable actions, separators and submenus."""

    def action(
        self,
        label: str,
        *,
        shortcut: str | None = None,
        on_trigger: Action[[]] | None = None,
        checkable: bool = False,
    ) -> Self:
        act = self.addAction(label)
        if shortcut is not None:
            act.setShortcut(QKeySequence(shortcut))
        act.setCheckable(checkable)
        if on_trigger is not None:
            act.triggered.connect(lambda *_: on_trigger())
        return self

    def toggleAction(
        self,
        label: str,
        state: StateVar[bool],
        *,
        shortcut: str | None = None,
    ) -> Self:
        """Checkable action kept in sync with a boolean StateVar."""
        act = self.addAction(label)
        if shortcut is not None:
            act.setShortcut(QKeySequence(shortcut))
        act.setCheckable(True)
        act.setChecked(bool(state.value))
        act.toggled.connect(state.set_value)
        state.connect(act.setChecked)
        return self

    def separator(self) -> Self:
        self.addSeparator()
        return self

    def subMenu(self, submenu: "Menu") -> Self:
        self.addMenu(submenu)
        return self


class MenuBar(QMenuBar, WidgetPropsMixin):
    def __init__(self, *menus: Menu, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        for menu in menus:
            self.addMenu(menu)


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

    def onLifeTimeFinished(self, action: Action[[]]) -> Self:
        self.lifeTimeFinished.connect(action)
        return self

    def finish_existence(self) -> None:
        self.setParent(None)
        self.deleteLater()
        self.lifeTimeFinished.emit()

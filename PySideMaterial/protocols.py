from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Subscribable[**P](Protocol):
    def connect(self, listener: Callable[P, Any], /) -> Any: ...


@runtime_checkable
class EventEmiter[**P](Subscribable[P], Protocol):
    def emit(self, *args: P.args, **kwargs: P.kwargs) -> None: ...


@runtime_checkable
class SupportsIndex(Protocol):
    index: int

    def setIndex(self, index: int, /) -> None: ...


class _SupportsSetText(Protocol):
    def setText(self, text: str, /) -> None: ...


class _SupportsSetChecked(Protocol):
    toggled: Subscribable[bool]

    def setChecked(self, value: bool) -> None: ...


class _SupportsStrTextChanged(Protocol):
    textChanged: Subscribable[str]


class _SupportsRichTextChanged(Protocol):
    textChanged: Subscribable[[]]

    def toPlainText(self) -> str: ...

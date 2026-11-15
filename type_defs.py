from collections.abc import Callable
from enum import Enum
from typing import Any, Final, Protocol, Self, runtime_checkable

type Function = Callable[[], Any]


@runtime_checkable
class EventEmiter[**P](Protocol):
    def connect(self, listener: Callable[P, Any], /) -> None: ...
    def emit(self, *args: P.args, **kwargs: P.kwargs) -> None: ...


@runtime_checkable
class HasValue[T = object](Protocol):
    value: T


@runtime_checkable
class SupportsJsonTransform(Protocol):
    def to_json(self) -> dict[str, Any]: ...
    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self: ...


class HasId(Protocol):
    id: int


class SupportsComparison(Protocol):
    def __eq__(self, value: Any, /) -> bool: ...
    def __gt__(self, value: Any, /) -> bool: ...
    def __lt__(self, value: Any, /) -> bool: ...


class VoidType(Enum):
    VOID = "Void"

    def __repr__(self) -> str:
        return "Void"


Void: Final = VoidType.VOID

from collections.abc import Callable
from typing import (
    Any,
    Final,
    Literal,
    Protocol,
    Self,
    runtime_checkable,
)

type Action[**P] = Callable[P, Any]
type Optional[T] = T | None
type Nullable[T] = T | NullType


class Singleton:
    _instance: Optional[Self] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


@runtime_checkable
class EventEmiter[**P](Protocol):
    def connect(self, listener: Action[P], /) -> None: ...

    @property
    def emit(self) -> Action[P]: ...

    @emit.setter
    def emit(self, value: Action[P]) -> None: ...


@runtime_checkable
class HasValue[T = object](Protocol):
    value: T


@runtime_checkable
class SupportsJsonTransform(Protocol):
    def to_json(self) -> dict[str, Any]: ...
    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self: ...


class IllegalExpression(Exception): ...


class HasId(Protocol):
    id: int


@runtime_checkable
class SupportsComparison(Protocol):
    def __eq__(self, value: Any, /) -> bool: ...
    def __gt__(self, value: Any, /) -> bool: ...
    def __lt__(self, value: Any, /) -> bool: ...


class NullType(Singleton):
    """Sentinel class, Null is his unique instance and all instances points to it"""

    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "Null"


Null: Final = NullType()

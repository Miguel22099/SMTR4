from abc import ABCMeta
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import (
    Any,
    Final,
    Protocol,
    Self,
    TypeGuard,
    TypeIs,
    dataclass_transform,
    runtime_checkable,
)

from typing_extensions import Literal

type Action[**P] = Callable[P, Any]
type ChainCall[T, R] = Callable[[T], R]


class SingletonMeta(type):
    _instances: dict[type, Any] = {}

    def __call__[T: "SingletonMeta"](cls: type[T], *args: Any, **kwargs: Any) -> T:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass_transform()
class MetaDataclass(ABCMeta):
    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]):
        cls = super().__new__(mcs, name, bases, namespace)
        cls = dataclass()(cls)
        return cls


@runtime_checkable
class EventEmiter[**P](Protocol):
    def connect(self, listener: Action[P], /) -> None: ...
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


class _VoidType(metaclass=SingletonMeta):
    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "Void"


def isVoid(value: Any) -> TypeIs[_VoidType]:
    return isinstance(value, _VoidType)


def isAllType[T](value: Sequence[Any], objective: type[T]) -> TypeGuard[Sequence[T]]:
    return all(isinstance(x, objective) for x in value)


Void: Final = _VoidType()

type Voidable[T] = T | _VoidType

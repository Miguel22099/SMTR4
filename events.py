from collections.abc import Callable, Iterable
from functools import wraps
from types import TracebackType
from typing import Any, Concatenate

from .converters import coerce_in
from .decorators import intercept_methods
from .type_defs import Action, EventEmiter, SupportsComparison, Void


class Event[**P]:
    def __init__(self) -> None:
        self._listeners: list[Action[P]] = []

    def connect(self, listener: Action[P]) -> None:
        self._listeners.append(listener)

    def connect_cast[S](
        self, listener: Action[[S]], converter: Callable[P, S]
    ) -> Action[P]:

        def cast(*args: P.args, **kwargs: P.kwargs) -> None:
            data = converter(*args, **kwargs)
            listener(data)

        self.connect(cast)
        return cast

    def disconnect(self, slot: Action[P]) -> None:
        try:
            self._listeners.remove(slot)
        except ValueError:
            ...

    def disconnect_all(self) -> None:
        self._listeners.clear()

    def emit(self, *args: P.args, **kwargs: P.kwargs) -> None:
        for listener in self._listeners[:]:
            listener(*args, **kwargs)


class SimpleEvent[T]:
    def __init__(self) -> None:
        self._listeners: list[Action[T]] = []

    def connect(self, listener: Action[T]) -> None:
        self._listeners.append(listener)

    def emit(self, val: T) -> None:
        for listener in self._listeners[:]:
            listener(val)

    def trigger[**P, S](
        self, func: Callable[Concatenate[T, P], S]
    ) -> Callable[Concatenate[T, P], S]:
        @wraps(func)
        def emiter(s: T, *args: P.args, **kwargs: P.kwargs) -> S:
            val = func(s, *args, **kwargs)
            self.emit(s)
            return val

        return emiter

    def disconnect(self, slot: Action[[T]]) -> None:
        try:
            self._listeners.remove(slot)
        except ValueError:
            ...


class StateVar[S]:
    """Observable value: every assignment notifies all connected listeners with the new value."""

    def __init__(self, value: S) -> None:
        super().__init__()
        self._value = self._coerce_in(value)
        self._listeners: list[Action[S]] = []
        self._derivated: list[Action[S]] = []

    def __str__(self) -> str:
        return repr(self.value)

    def __repr__(self) -> str:
        return f"StateVar: {repr(self.value)}"

    @property
    def value(self) -> S:
        return self._value

    @value.setter
    def value(self, new: S):
        self._value = new
        self.emit(new)

    def emit(self, value: S) -> None:
        for listener in self._listeners[:]:
            listener(value)

    def set_value(self, val: S):
        self.value = self._coerce_in(val)

    def _coerce_in(self, val: S) -> S:
        return val

    def connect(self, slot: Action[[S]]) -> None:
        self._listeners.append(slot)

    def derivated_state[R](self, converter: Callable[[S], R]) -> "StateVar[R]":
        new = StateVar(converter(self.value))

        def func(val: S) -> None:
            new.set_value(converter(val))

        self.connect(func)
        self._derivated.append(func)
        return new

    def disconnect(self, slot: Action[[S]]) -> None:
        try:
            self._listeners.remove(slot)
        except ValueError:
            ...

    def disconnect_all(self) -> None:
        """Clears all conections, does not affect created derivated state"""
        self._listeners.clear()
        self._listeners.extend(self._derivated)


class IntervalStateVar[S: SupportsComparison](StateVar[S]):
    def __init__(self, value: S, min: S, max: S) -> None:
        super().__init__(value)
        self._min = min
        self._max = max

    def _verified(self, val: S) -> S:
        return coerce_in(val, self._min, self._max)


class StateVarTuple[*TS](StateVar[tuple[*TS]]):
    def __init__(self, *value: *TS) -> None:
        super().__init__(value)

    def set_values(self, *val: *TS):
        return super().set_value(val)


class ComputedState[S](StateVar[S]):
    def __init__[*TS](self, *vars: *TS, converter: Callable[[*TS], S]) -> None:
        def compute() -> S:
            return converter(*vars)

        super().__init__(compute())
        for var in vars:
            if isinstance(var, EventEmiter):

                def bind(*_: Any) -> None:
                    self.set_value(compute())

                var.connect(bind)


class ChainedState[S](StateVar[S]):
    def __init__(self, *dependants: EventEmiter[Any], value: S) -> None:
        super().__init__(value)
        for item in dependants:
            item.connect(lambda _: self.emit(self.value))


class Remember:
    def __new__[S: EventEmiter[Any]](cls, event: S) -> S:
        last = Void
        _emitter = event.emit

        @wraps(event.emit)
        def emitter(*args: Any, **kwargs: Any) -> None:
            nonlocal last
            nonlocal _emitter
            current = (args, kwargs)
            if current == last:
                return
            last = current
            _emitter(*args, **kwargs)

        event.emit = emitter
        return event


class StatusHolder[S]:
    """Plain mutable container that stores a value without notifying anyone."""

    __slots__ = ["value"]

    def __init__(self, value: S) -> None:
        self.value = value

    def write(self, new: S) -> None:
        self.value = new


@intercept_methods(
    "append",
    "extend",
    "remove",
    "pop",
    "insert",
    "clear",
    "sort",
    "__setitem__",
    "__delitem__",
    "__iadd__",
    "__imul__",
    "reverse",
)
class MutableList[T](list[T]):
    def __init__(
        self,
        data: Iterable[T] | None = None,
    ):
        super().__init__(data or ())
        self._event = Event[MutableList[T]]()

    @property
    def contentChanged(self) -> Event["MutableList[T]"]:
        return self._event


class SilencedSignal:
    def __init__(self, event: EventEmiter[Any]) -> None:
        self._event = event
        self._ev = self._event.emit

    def __enter__(self):
        self._event.emit = lambda val: None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._event.emit = self._ev

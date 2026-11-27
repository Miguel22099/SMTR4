from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, cast, overload

from .type_defs import Null, Nullable, NullType, SupportsComparison


@overload
def safe_convert[T, R](
    converter: Callable[[R], T], data: R, default: NullType = ...
) -> Nullable[T]: ...


@overload
def safe_convert[T, R](converter: Callable[[R], T], data: R, default: T) -> T: ...


def safe_convert[T, R](
    converter: Callable[[R], T], data: R, default: Nullable[T] = Null
) -> Nullable[T]:
    try:
        return converter(data)
    except (ValueError, TypeError):
        return default


def coerce_in[S: SupportsComparison](val: S, min: S, max: S) -> S:
    if val < min:
        return min
    if val > max:
        return max
    return val


@dataclass(slots=True, frozen=True)
class Converter[T, R]:
    _converter: Callable[[R], T]

    @overload
    def __call__(
        self,
        data: R,
        default: NullType = ...,
    ) -> Nullable[T]: ...

    @overload
    def __call__(
        self,
        data: R,
        default: T = ...,
    ) -> T: ...

    def __call__(
        self,
        data: R,
        default: Nullable[T] = Null,
    ) -> Nullable[T]:
        return safe_convert(self._converter, data, default)


@dataclass(slots=True, frozen=True)
class Caster[T, R]:
    _target: type[R]
    _converter: Callable[[T], R]

    def __call__(self, val: T | R) -> R:
        if isinstance(val, self._target):
            return val
        return self._converter(cast(T, val))


@dataclass(slots=True, frozen=True)
class Pipe[*Ts, R]:
    func: Callable[[*Ts], R]

    def __call__(self, *args: *Ts) -> R:
        return self.func(*args)

    @overload
    def __or__[*Us, S](
        self: "Pipe[*Ts, tuple[*Us]]",
        other: Callable[[*Us], S],
        /,
    ) -> "Pipe[*Ts, S]": ...

    @overload
    def __or__[S](
        self,
        other: Callable[[R], S],
        /,
    ) -> "Pipe[*Ts, S]": ...

    def __or__[S](self, other: Callable[..., S], /) -> "Pipe[*Ts, S]":
        def wrapper(*args: *Ts) -> S:
            res = self(*args)
            if isinstance(res, tuple):
                return other(*res)
            return other(res)

        return Pipe(wrapper)


@dataclass(slots=True, frozen=True)
class Interval[S: SupportsComparison]:
    min: S
    max: S

    def __contains__(self, value: object) -> bool:
        if isinstance(value, type(self.min)):
            if self.min < value < self.max:
                return True
            elif self.min == value or self.max == value:
                return True
        return False

    def fit_interval(self, value: S) -> S:
        if value < self.min:
            return self.min
        if value > self.max:
            return self.max
        return value


Safe_int: Final = Converter(int)
Safe_float: Final = Converter(float)

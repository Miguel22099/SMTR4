from collections.abc import Callable
from typing import cast, overload

from .type_defs import SupportsComparison, Void, Voidable, _Void


@overload
def safe_convert[T, R](
    converter: Callable[[R], T], data: R, default: _Void = ...
) -> Voidable[T]: ...


@overload
def safe_convert[T, R](converter: Callable[[R], T], data: R, default: T) -> T: ...


def safe_convert[T, R](
    converter: Callable[[R], T], data: R, default: Voidable[T] = Void
) -> Voidable[T]:
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


class Converter[T, R]:
    def __init__(self, converter: Callable[[R], T]) -> None:
        self._converter = converter

    @overload
    def __call__(
        self,
        data: R,
        default: _Void = ...,
    ) -> Voidable[T]: ...

    @overload
    def __call__(
        self,
        data: R,
        default: T = ...,
    ) -> T: ...

    def __call__(
        self,
        data: R,
        default: Voidable[T] = Void,
    ) -> Voidable[T]:
        return safe_convert(self._converter, data, default)


class Caster[T, R]:
    def __init__(self, target: type[R], converter: Callable[[T], R]) -> None:
        self._converter = converter
        self._target = target

    def __call__(self, val: T | R) -> R:
        if isinstance(val, self._target):
            return val
        return self._converter(cast(T, val))

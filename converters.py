from collections.abc import Callable
from typing import cast

from .type_defs import SupportsComparison


def safe_convert[T, S, R](
    converter: Callable[[R], T], data: R, default: S = None
) -> T | S:
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


class Converter[T, R, S]:
    def __init__(self, converter: Callable[[R], T], default: S = None):
        self._converter = converter
        self._default = default

    def __call__(self, data: R) -> T | S:
        return safe_convert(self._converter, data, self._default)


class Caster[T, R]:
    def __init__(self, target: type[R], converter: Callable[[T], R]) -> None:
        self._converter = converter
        self._target = target

    def __call__(self, val: T | R) -> R:
        if isinstance(val, self._target):
            return val
        return self._converter(cast(T, val))

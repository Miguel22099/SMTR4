import os
from collections.abc import Iterable


def money_format(val: int) -> str:
    return f"$ {val:,.0f}"


def percentage_format(val: float, decimals: int = 2) -> str:
    return f"{val:.{decimals}%}"


def remove_duplicates[T](items: Iterable[T]) -> list[T]:
    return list(set(items))


def flatten[T](items: Iterable[Iterable[T]]) -> Iterable[T]:
    yield from (item for group in items for item in group)


def abs_path(base: str, path: str) -> str:
    basedir = os.path.dirname(base)
    return os.path.join(basedir, path)

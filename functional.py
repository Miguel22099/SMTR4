import os
from collections.abc import Callable


def frozen_args[**P, T](func: Callable[P, T]) -> Callable[P, Callable[[], T]]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> Callable[[], T]:
        def manager() -> T:
            return func(*args, **kwargs)

        return manager

    return inner


def money_format(val: int) -> str:
    return f"$ {val:,.0f}"


def abs_path(base: str, path: str) -> str:
    basedir = os.path.dirname(base)
    return os.path.join(basedir, path)

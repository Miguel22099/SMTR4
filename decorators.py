from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate


def intercept_method_call[**P, S, R](
    self_action: Callable[[S], Any] | None = None,
):
    def decorator(
        func: Callable[Concatenate[S, P], R],
    ) -> Callable[Concatenate[S, P], R]:

        @wraps(func)
        def wrapper(self: S, *args: P.args, **kwargs: P.kwargs) -> R:
            val = func(self, *args, **kwargs)
            if self_action is not None:
                self_action(self)

            return val

        return wrapper

    return decorator


def intercept_return[**P, S](action: Callable[[S], Any]):
    def decorator(func: Callable[P, S]) -> Callable[P, S]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> S:
            data = func(*args, **kwargs)
            action(data)
            return data

        return wrapper

    return decorator


def intercept_methods[T](
    *method_names: str,
    event_name: str = "_event",
) -> Callable[[type[T]], type[T]]:
    def wrapper(cls: type[T]) -> type[T]:

        def create_wrapper[**P, S](
            method: Callable[Concatenate[T, P], S],
        ) -> Callable[Concatenate[T, P], S]:
            @wraps(method)
            def wrapper(self: T, *args: P.args, **kwargs: P.kwargs):
                result = method(self, *args, **kwargs)
                getattr(self, event_name).emit(self)
                return result

            return wrapper

        for name in method_names:
            method = getattr(cls, name, None)

            if callable(method):
                setattr(cls, name, create_wrapper(method))

        return cls

    return wrapper


def frozen[**P, T](func: Callable[P, T]) -> Callable[P, Callable[[], T]]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> Callable[[], T]:
        def manager() -> T:
            return func(*args, **kwargs)

        return manager

    return inner


def partial_frozen[**P, T, L](
    func: Callable[Concatenate[L, P], T],
) -> Callable[P, Callable[[L], T]]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> Callable[[L], T]:
        def manager(val: L) -> T:
            return func(val, *args, **kwargs)

        return manager

    return inner

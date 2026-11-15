from collections.abc import Callable
from typing import Any

from .events import Event


class Counter:
    def __init__(
        self,
        on_finish: Callable[[], Any],
        begin: int = 0,
        finish: int = 3,
    ) -> None:
        if finish <= begin:
            raise ValueError("finish must be greater than begin")
        self._begin = begin
        self._finish = finish
        self._count = 0
        self.on_finish = Event[[]]()
        self.on_finish.connect(on_finish)

    def count(self) -> int:
        self._count += 1
        if self._count == self._finish:
            self.on_finish.emit()
            self._count = self._begin
            return self._finish
        return self._count


class SingletonMeta(type):
    _instances: dict[type, Any] = {}

    def __call__[T: "SingletonMeta"](cls: type[T], *args: Any, **kwargs: Any) -> T:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

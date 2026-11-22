from .events import Event
from .type_defs import Action


class Counter:
    def __init__(
        self,
        on_finish: Action[[]],
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

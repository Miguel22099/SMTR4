import random
from typing import Self

from .events import Event
from .type_defs import Action


class ID_Generator:
    __slots__ = ["_counter"]

    def __init__(self, begin: int = 0) -> None:
        if begin < 0:
            raise ValueError("ID must be greater than zero")
        self._counter = begin - 1

    def __call__(self) -> int:
        return self.next()

    def next(self) -> int:
        self._counter += 1
        return self._counter


class Name_Generator:
    NAMES = (
        "Miguel",
        "Daniel",
        "Andrés",
        "Carlos",
        "Juan",
        "David",
        "Sebastián",
        "Alejandro",
        "Santiago",
        "María",
        "Laura",
        "Camila",
        "Valentina",
        "Sofía",
        "Isabella",
        "Daniela",
        "Paula",
        "Gabriela",
    )

    LAST_NAMES = (
        "García",
        "Rodríguez",
        "Martínez",
        "López",
        "González",
        "Hernández",
        "Pérez",
        "Sánchez",
        "Ramírez",
        "Torres",
        "Díaz",
        "Moreno",
        "Muñoz",
        "Rojas",
        "Castro",
        "Vargas",
    )

    def __init__(self, seed: random.Random | None = None) -> None:
        self._seed = seed or random.Random()

    def first_name(self) -> str:
        return self._seed.choice(self.NAMES)

    def last_name(self) -> str:
        return self._seed.choice(self.LAST_NAMES)

    def full_name(self) -> str:
        return f"{self.first_name()} {self.last_name()} {self.last_name()}"


class Phone_Generator:
    def __init__(self, seed: random.Random | None = None) -> None:
        self._seed = seed or random.Random()

    def generate(self) -> str:
        return f"3{self._seed.randint(0, 999_999_999):09}"

    def generate_many(self, quantity: int) -> list[str]:
        return [self.generate() for _ in range(quantity)]


class Counter:
    def __init__(
        self,
        begin: int = 0,
        finish: int = -1,
    ) -> None:
        if finish != -1:
            if finish <= begin:
                raise ValueError("finish must be greater than begin")
        self._begin = begin
        self._finish = finish
        self._count = 0
        self.finished = Event[[]]()

    def count(self) -> int:
        self._count += 1
        if self._count == self._finish:
            self.finished.emit()
            self._count = self._begin
            return self._finish
        return self._count

    def on_finish(self, action: Action[[]]) -> Self:
        self.finished.connect(action)
        return self

import pickle
from collections.abc import Sequence


class Pickle_Repository[T]:
    def __init__(self, file_path: str):
        self._path = file_path

    def save(self, data: Sequence[T]) -> None:
        with open(self._path, "wb") as file:
            pickle.dump(data, file)

    def load(self) -> Sequence[T]:
        try:
            with open(self._path, "rb") as file:
                return pickle.load(file)
        except FileNotFoundError, EOFError:
            return []


class Single_Pickle_Saver[T]:
    def __init__(self, file_path: str):
        self._path = file_path

    def save(self, data: T) -> None:
        with open(self._path, "wb") as file:
            pickle.dump(data, file)

    def load(self) -> T | None:
        try:
            with open(self._path, "rb") as file:
                return pickle.load(file)
        except FileNotFoundError, EOFError:
            return


class Tuple_Pickle_Saver[*TS](Single_Pickle_Saver[tuple(*TS)]):
    def save(self, *data: *TS) -> None:
        return super().save(data)

    def load(self) -> tuple[*TS] | None:
        return super().load()

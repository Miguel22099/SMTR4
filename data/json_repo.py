import json
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from ..classes import Counter
from ..events import MutableList
from ..type_defs import SupportsJsonTransform

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison


class Json_Repository[T: SupportsJsonTransform]:
    def __init__(self, owner: type[T], file_path: str) -> None:
        if not file_path.endswith(".jsonl"):
            raise ValueError("file path of a Json_Repository must end with .jsonl")
        self._path = file_path
        self._owner = owner

    def save(self, data: Sequence[T]) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item.to_json()) + "\n")

    def add(self, item: T) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item.to_json()) + "\n")

    def delete(self, item: T) -> bool:
        data = self.load()
        try:
            data.remove(item)
        except ValueError:
            return False
        self.save(data)
        return True

    def delete_where(self, condition: Callable[[T], bool]) -> int:
        data = self.load()
        filtered = [item for item in data if not condition(item)]

        deleted = len(data) - len(filtered)

        if deleted:
            self.save(filtered)

        return deleted

    def load(self) -> list[T]:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return [
                    self._owner.from_json(json.loads(line))
                    for line in f
                    if line.strip()
                ]
        except FileNotFoundError:
            return []

    def lazy_load(self) -> Iterator[T]:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        yield self._owner.from_json(json.loads(line))
        except FileNotFoundError:
            return

    def bind_repo(self, data: MutableList[T]) -> None:
        data.extend(self.load())
        data.contentChanged.connect(self.save)

    def lazy_bind_repo(self, data: MutableList[T], changes_before_write: int) -> None:
        counter: Counter | None = None

        def unbind(_: MutableList[T]) -> None:
            nonlocal counter

            counter = Counter(
                lambda: self.save(data),
                finish=changes_before_write,
            )

            data.contentChanged.disconnect(unbind)
            data.contentChanged.connect(bind)
            counter.count()

        def bind(_: MutableList[T]) -> None:
            if counter is not None:
                counter.count()

        data.extend(self.load())
        data.contentChanged.connect(unbind)


class Json_list[T: SupportsJsonTransform]:
    """Implements a list in persistent memory, sort, remove and pop materializes the full list in ram and rewrites the file"""

    def __str__(self) -> str:
        return f"[{', '.join(str(x) for x in self)}]"

    def __init__(self, owner: type[T], path: str) -> None:
        if not path.endswith(".jsonl"):
            raise ValueError("file path of a Json_list must end with .jsonl")
        self._owner = owner
        self._path = path
        Path(path).touch(exist_ok=True)

    def __iter__(self) -> Iterator[T]:
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield self._owner.from_json(json.loads(line))

    def __len__(self) -> int:
        with open(self._path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    def __contains__(self, item: object) -> bool:
        return any(element == item for element in self)

    def append(self, item: T) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item.to_json()) + "\n")

    def extend(self, data: Iterable[T]) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item.to_json()) + "\n")

    def clear(self) -> None:
        Path(self._path).write_text("", encoding="utf-8")

    def sort(
        self,
        *,
        key: Callable[[T], "SupportsRichComparison"],
        reverse: bool = False,
    ) -> None:
        data = sorted(self, key=key, reverse=reverse)
        self.clear()
        self.extend(data)

    def remove(self, item: T) -> None:
        data = list(self)
        data.remove(item)
        self.clear()
        self.extend(data)

    def pop(self, index: int = -1) -> T:
        data = list(self)
        item = data.pop(index)
        self.clear()
        self.extend(data)
        return item

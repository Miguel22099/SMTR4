import json
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast, dataclass_transform

from ..classes import Counter
from ..events import MutableList
from ..type_defs import MetaDataclass, SupportsJsonTransform

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


class Single_Json_Saver[T]:
    """Persists a single value as one JSON document.

    Objects exposing `to_json()` are frozen recursively into plain data;
    `revive` rebuilds them on load.
    """

    def __init__(
        self, file_path: str, revive: Callable[[Any], T] | None = None
    ) -> None:
        self._path = file_path
        self._revive = revive

    @staticmethod
    def _freeze(value: Any) -> Any:
        if hasattr(value, "to_json"):
            return value.to_json()
        if isinstance(value, (tuple, list)):
            return [Single_Json_Saver._freeze(item) for item in value]
        return value

    def save(self, data: T | Sequence[T]) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._freeze(data), f, indent=2)

    def save_tuple(self, *data: T) -> None:
        self.save(data)

    def _load_json(self) -> Any | None:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError, json.JSONDecodeError:
            return None

    def load(self) -> T | None:
        data = self._load_json()
        if data is None:
            return None
        return self._revive(data) if self._revive else data


@dataclass_transform()
class _JsonModelMeta(MetaDataclass):
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        if not namespace.get("__abstract_model__", False):
            if "repo_name" not in namespace:
                raise TypeError(f"{name} must define 'repo_name'")
            pointer = cast(Any, cls)
            pointer.repository = Json_Repository(pointer, pointer.repo_name)

        return cls


class JsonModel(metaclass=_JsonModelMeta):
    __abstract_model__ = True

    repository: ClassVar[Json_Repository[Self]]
    repo_name: ClassVar[str]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self:
        return cls(**data)

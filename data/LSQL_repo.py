import sqlite3
from dataclasses import fields, is_dataclass
from types import UnionType
from typing import Any, Union, get_args, get_origin

from ..type_defs import HasId


class SQLite_Repository[T: HasId]:
    def __init__(self, owner: type[T], database: str, table: str):
        if not is_dataclass(owner):
            raise ValueError("owner must be a dataclass")
        self._owner = owner
        self._table = table
        self._connection = sqlite3.connect(database)

        self._create_table()

    def _create_table(self) -> None:
        columns = []

        for field in fields(self._owner):
            sql_type = self._get_sql_type(field.type)

            if field.name == "id":
                sql_type += " PRIMARY KEY"

            columns.append(f"{field.name} {sql_type}")

        query = f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
                {", ".join(columns)}
            )
        """

        self._connection.execute(query)
        self._connection.commit()

    @staticmethod
    def _get_sql_type(annotation: Any) -> str:
        types = {
            int: "INTEGER",
            str: "TEXT",
            float: "REAL",
            bytes: "BLOB",
            bool: "INTEGER",
        }

        origin = get_origin(annotation)

        if origin in (Union, UnionType):
            annotation = next(
                arg for arg in get_args(annotation) if arg is not type(None)
            )

        return types.get(annotation, "TEXT")

    def save(self, data: list[T]) -> None:
        names = [field.name for field in fields(self._owner)]
        placeholders = ", ".join("?" for _ in names)

        query = f"""
            INSERT OR REPLACE INTO {self._table}
            ({", ".join(names)})
            VALUES ({placeholders})
        """

        values = [tuple(getattr(item, name) for name in names) for item in data]

        self._connection.executemany(query, values)
        self._connection.commit()

    def load(self) -> list[T]:
        cursor = self._connection.execute(f"SELECT * FROM {self._table}")

        return [self._owner(*row) for row in cursor.fetchall()]

    def close(self) -> None:
        self._connection.close()

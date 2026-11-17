from collections.abc import Callable
from dataclasses import dataclass
from typing import Concatenate, TypeVar

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..decorators import partial_frozen
from .protocols import ObjectProperty as o_property

W = TypeVar("W", bound=QWidget)


def _object_property_factory[**P, L: QWidget](
    func: Callable[Concatenate[L, P], L],
) -> Callable[P, o_property[L]]:
    return partial_frozen(func)


class Font(QFont):
    def __init__(self, family: str, size: int = 11, bold: bool = False) -> None:
        super().__init__()
        self.setBold(bold)
        self.setFamily(family)
        self.setPointSize(size)


@dataclass(frozen=True, slots=True)
class Stretch:
    val: int = 1


class ObjectProperty:
    class SizeProperty:
        @staticmethod
        @_object_property_factory
        def SizePolicy(
            w: W, hPolicy: QSizePolicy.Policy, vPolicy: QSizePolicy.Policy
        ) -> W:
            w.setSizePolicy(hPolicy, vPolicy)
            return w

        @staticmethod
        @_object_property_factory
        def MaximumSize(w: W, width: int | None = None, height: int | None = None) -> W:
            if width is not None:
                w.setMaximumWidth(width)
            if height is not None:
                w.setMaximumHeight(height)
            return w

    class Appareance:
        @staticmethod
        @_object_property_factory
        def ContentMargins(
            w: W, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0
        ) -> W:
            w.setContentsMargins(left, right, top, bottom)
            return w

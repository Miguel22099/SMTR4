from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..decorators import partial_frozen


class Font(QFont):
    def __init__(self, family: str, size: int = 11, bold: bool = False) -> None:
        super().__init__()
        self.setBold(bold)
        self.setFamily(family)
        self.setPointSize(size)


@dataclass(frozen=True, slots=True)
class Stretch:
    val: int = 1


@partial_frozen
def _SizePolicy[W: QWidget](
    w: W, hPolicy: QSizePolicy.Policy, vPolicy: QSizePolicy.Policy
) -> W:
    w.setSizePolicy(hPolicy, vPolicy)
    return w


@dataclass(frozen=True, slots=True)
class _Applier[G: QWidget]:
    """Widget property transformer; `value` conforms to protocols.ObjectProperty."""

    value: Callable[[G], G]


class ObjectProperty:
    class SizePolicy:
        Expanding = _Applier(
            _SizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        )
        VerticalExpanding = _Applier(
            _SizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )
        HorizontalGrow = _Applier(
            _SizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )
        Minimum = _Applier(
            _SizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        )
        Fixed = _Applier(
            _SizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        )

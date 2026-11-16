from collections.abc import Callable
from enum import Enum


class TextFilter:
    """Immutable chain of character filters.

    Every method returns a new filter, so instances can be reused to build input
    validators such as the ones in `Filter`.
    """

    def __init__(self, *filters: Callable[[str], str]) -> None:
        self.filters = filters

    def __call__(self, text: str) -> str:
        for filter in self.filters:
            text = filter(text)
        return text

    def Allowed(self, chars: str) -> "TextFilter":
        def filter(text: str) -> str:
            return "".join(c for c in text if c in chars)

        return TextFilter(*self.filters, filter)

    def Denied(self, chars: str) -> "TextFilter":
        def filter(text: str) -> str:
            return "".join(c for c in text if c not in chars)

        return TextFilter(*self.filters, filter)

    def Unique(self, chars: str) -> "TextFilter":
        def filtered(text: str) -> str:
            found: set[str] = set()

            def char_filter(char: str) -> bool:
                if char not in chars:
                    return True
                if char in found:
                    return False

                found.add(char)
                return True

            return "".join(filter(char_filter, text))

        return TextFilter(*self.filters, filtered)

    def AtStart(self, chars: str) -> "TextFilter":
        def filtered(text: str) -> str:
            if not text:
                return text

            return text[0] + "".join(c for c in text[1:] if c not in chars)

        return TextFilter(*self.filters, filtered)

    def AtEnd(self, chars: str) -> "TextFilter":
        def filtered(text: str) -> str:
            if not text:
                return text

            return "".join(c for c in text[:-1] if c not in chars) + text[-1]

        return TextFilter(*self.filters, filtered)


class Filter(Enum):
    """Ready-to-use input filters for numeric, decimal and alphabetic text."""

    NumberFilter = TextFilter().Allowed("0123456789")
    NegativeNumberFilter = TextFilter().Allowed("-0123456789").Unique("-").AtStart("-")

    DecimalFilter = TextFilter().Allowed("0123456789.").Unique(".")
    DecimalNegativeNumberFilter = (
        TextFilter().Allowed("0123456789.-").Unique(".").Unique("-").AtStart("-")
    )

    OnlyTextFilter = TextFilter().Denied("0123456789")

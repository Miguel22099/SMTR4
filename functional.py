import os


def money_format(val: int) -> str:
    return f"$ {val:,.0f}"


def abs_path(base: str, path: str) -> str:
    basedir = os.path.dirname(base)
    return os.path.join(basedir, path)

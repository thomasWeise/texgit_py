"""A tool for fixing all occurrences of a Path."""

from contextlib import suppress
from itertools import chain
from os import sep
from re import MULTILINE, Match, escape, sub
from typing import Final

from pycommons.io.path import Path

#: the replacement string for base paths
BASE_PATH_REPLACEMENT: Final[str] = "{...}"

#: the literal string start and ends.
__SE: Final[tuple[tuple[str, str], ...]] = tuple(sorted(chain(
    ((escape(__s), escape(__e)) for __s, __e in (
        (" ", " "), ("'", "'"), ("(", ")"), ("{", "}"), ("[", "]"),
        ("<", ">"), ("`", "`"), (",", " "), (",", ","), ('"', '"'),
        (";", " "), (";", ";"), (" ", ". "))),
    (("^", "$"), ("^", " "), (" ", "$"), ("^", ","), (",", "$"),
     ("^", ";"), (";", "$"), ("^", escape(". ")),
     ("^", escape(".") + "$"))),
))


def replace_base_path(orig: str, base_path: str) -> str:
    r"""
    Replace all occurrences of the `base_path` in the original string.

    Any reasonably delimited occurrence of `base_path` as well as any sub-path
    under `base_path` that points to an existing file or directory are
    replaced with relativizations starting with `{...}`.

    :param orig: the original string
    :param base_path: the base path
    :return: the fixed string

    >>> from pycommons.io.temp import temp_dir
    >>> with temp_dir() as td:
    ...     td.resolve_inside("x").ensure_dir_exists()
    ...     td.resolve_inside("x/y").write_all_str("5")
    ...     a = replace_base_path(f"blablabla {td}/x ", td)
    ...     b = replace_base_path(f"{td}/x/y", td)
    ...     c = replace_base_path(f"{td}/x.", td)
    ...     d = replace_base_path("\n".join(("blaa", f"{td}/x.x", "y")), td)
    ...     e = replace_base_path("\n".join(("blaa", f"{td}/x.", "y")), td)
    ...     f = replace_base_path(f"xc'{td}/x/y'yy", td)
    ...     g = replace_base_path(td, td)
    ...     h = replace_base_path(td + "/", td)
    >>> a
    'blablabla {...}/x '

    >>> b
    '{...}/x/y'

    >>> c
    '{...}/x.'

    >>> d[-6:]
    '/x.x\ny'

    >>> e
    'blaa\n{...}/x.\ny'

    >>> f
    "xc'{...}/x/y'yy"

    >>> g
    '{...}'

    >>> h
    '{...}/'
    """
    if str.__len__(orig) <= 0:
        return ""
    path: Final[Path] = Path(base_path)
    path_re: Final[str] = escape(path)

    def __replacer(data: Match, __bp: Path = path) -> str:
        prefix: Final[str] = data.group(1)
        subpath: Final[str] = data.group(2)
        suffix: Final[str] = data.group(3)
        with suppress(ValueError):
            usesubpath: Final[str] = subpath[str.__len__(sep):] \
                if subpath.startswith(sep) else subpath
            if (str.__len__(usesubpath) <= 0) \
                    or __bp.resolve_inside(usesubpath).exists():
                return f"{prefix}{{...}}{subpath}{suffix}"
        return data.group(0)

    for start, end in __SE:
        orig = sub(f"({start}){path_re}(.*?)({end})", __replacer, orig,
                   flags=MULTILINE)
    return orig

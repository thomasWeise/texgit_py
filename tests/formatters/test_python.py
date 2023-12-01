"""Test the python formatter."""

from os.path import dirname
from typing import Final

import latexgit.formatters.python as fp
from latexgit.utils.path import Path
from latexgit.utils.shell import shell


def test_python() -> None:
    """Test the python formatter."""
    sf: Final[Path] = Path.file(__file__)
    source: Final[str] = sf.read_all_str()
    wd: Path = Path.directory(dirname(dirname(dirname(sf))))
    formatted = shell(
        ["python3", "-m", Path.file(fp.__file__).relative_to(
            wd).replace("/", ".")[:-3],
         "--lines", "1-6", "--args", "format"],
        stdin=source, wants_stdout=True, cwd=wd)
    assert isinstance(formatted, str)
    lines: list[str] = formatted.split("\n")
    assert len(lines) == 6

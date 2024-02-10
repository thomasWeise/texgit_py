"""Test the python formatter."""

from os.path import dirname
from typing import Final

from pycommons.io.path import Path
from pycommons.processes.python import python_command
from pycommons.processes.shell import exec_text_process

import latexgit.formatters.python as fp


def test_python() -> None:
    """Test the python formatter."""
    sf: Final[Path] = Path.file(__file__)
    source: Final[str] = sf.read_all_str()
    wd: Path = Path.directory(dirname(dirname(dirname(sf))))
    call: list[str] = list(python_command(fp.__file__))
    call.extend(["--lines", "1-6", "--args", "format"])
    formatted = exec_text_process(
        call, stdin=source, wants_stdout=True, cwd=wd)
    assert isinstance(formatted, str)
    lines: list[str] = formatted.split("\n")
    assert len(lines) == 7

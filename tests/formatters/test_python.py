"""Test the python formatter."""

from typing import Final

from pycommons.io.path import Path, file_path
from pycommons.processes.python import python_command
from pycommons.processes.shell import STREAM_CAPTURE, Command

import latexgit.formatters.python as fp


def test_python() -> None:
    """Test the python formatter."""
    sf: Final[Path] = file_path(__file__)
    source: Final[str] = sf.read_all_str()
    wd: Path = sf.up(3)
    call: list[str] = list(python_command(fp.__file__))
    call.extend(["--lines", "1-6", "--args", "format"])
    formatted = Command(
        call, stdin=source, stdout=STREAM_CAPTURE,
        working_dir=wd).execute()[0]
    assert isinstance(formatted, str)
    lines: list[str] = formatted.split("\n")
    assert len(lines) == 7

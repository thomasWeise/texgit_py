"""Test the python formatter."""

from typing import Final

from pycommons.io.path import Path, file_path
from pycommons.processes.python import PYTHON_ENV, python_command
from pycommons.processes.shell import STREAM_CAPTURE, Command

import texgit.formatters.python as fp
from texgit.formatters.python import preprocess_python


def test_python_1() -> None:
    """Test the python formatter."""
    sf: Final[Path] = file_path(__file__)
    source: Final[str] = sf.read_all_str()
    wd: Path = sf.up(3)
    call: list[str] = list(python_command(fp.__file__))
    call.extend(["--lines", "1-6", "--args", "format"])
    formatted = Command(
        call, stdin=source, stdout=STREAM_CAPTURE,
        working_dir=wd, env=PYTHON_ENV).execute()[0]
    assert isinstance(formatted, str)
    lines: list[str] = formatted.split("\n")
    assert len(lines) == 7


def test_python_2() -> None:
    """Test the python formatter."""
    sf: Final[Path] = file_path(__file__)
    source: Final[str] = str.rstrip("\n".join(
        sf.read_all_str().splitlines()[12:38]))
    wd: Path = sf.up(3)
    call: list[str] = list(python_command(fp.__file__))
    call.extend(["--args", "format"])
    formatted = Command(
        call, stdin=source, stdout=STREAM_CAPTURE,
        working_dir=wd, env=PYTHON_ENV).execute()[0]
    assert isinstance(formatted, str)
    assert str.rstrip(formatted) == source


def test_python_3() -> None:
    """Test the python formatter."""
    sf: Final[Path] = file_path(__file__)
    source: Final[str] = str.rstrip("\n".join(
        sf.read_all_str().splitlines()[12:38]))
    formatted = preprocess_python(source.splitlines(), None, None, {"format"})
    assert isinstance(formatted, str)
    assert str.rstrip(formatted) == source

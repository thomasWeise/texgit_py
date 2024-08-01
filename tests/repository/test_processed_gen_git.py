"""Test the processed generated git files repository."""

from pycommons.io.path import Path
from pycommons.io.temp import temp_dir
from pycommons.net.url import URL

from latexgit.repository.processed import Processed


def test_processed_gen_git() -> None:
    """Test the processed files repository."""
    with temp_dir() as td:
        proc: Processed = Processed(td)

        file_1, u1 = proc.get_output(
            ("python3", "temp.py"),
            "https://github.com/thomasWeise/pycommons",
            "examples")
        assert isinstance(file_1, Path)
        assert isinstance(u1, URL)
        assert f"{u1}" == "https://github.com/thomasWeise/pycommons"
        td.enforce_contains(file_1)
        file_1.enforce_file()
        assert file_1.is_file()

        file_2, u2 = proc.get_output(
            ("python3", "temp.py"),
            "https://github.com/thomasWeise/pycommons",
            "examples")
        assert isinstance(file_2, Path)
        assert isinstance(u2, URL)
        assert file_1 is file_2
        assert u1 is u2
        td.enforce_contains(file_2)
        file_2.enforce_file()
        assert file_2.is_file()

        proc.close()
        proc = Processed(td)
        file_1b, u3 = proc.get_output(
            ("python3", "temp.py"),
            "https://github.com/thomasWeise/pycommons",
            "examples")
        assert u3 == u1
        assert isinstance(file_1b, Path)
        assert file_1b.is_file()
        assert file_1b == file_1

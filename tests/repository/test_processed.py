"""Test the processed files repository."""


from typing import Final

from latexgit.repository.processed import Processed
from latexgit.utils.path import Path
from latexgit.utils.temp import TempDir


def test_processed() -> None:
    """Test the processed files repository."""
    with TempDir.create() as td:
        proc: Final[Processed] = Processed(td)

        file_1: Final[Path] = proc.get_file(
            "https://github.com/thomasWeise/moptipy",
            "moptipy/api/operators.py")
        file_1.enforce_file()
        td.enforce_contains(file_1)

        file_2: Final[Path] = proc.get_file(
            "https://github.com/thomasWeise/moptipy",
            "moptipy/api/operators.py",
            ("head", "-n", 5))
        file_2.enforce_file()
        assert file_2 != file_1
        td.enforce_contains(file_2)
        assert len(file_2.read_all_list()) == 5

        assert proc.get_file(
            "https://github.com/thomasWeise/moptipy",
            "moptipy/api/operators.py",
            ("head", "-n", 5)) is file_2

        assert proc.get_file(
            "https://github.com/thomasWeise/moptipy",
            "moptipy/api/operators.py") == file_1

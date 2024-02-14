"""Test the processed files repository."""


from typing import Final

from pycommons.io.path import Path
from pycommons.io.temp import temp_dir

from latexgit.repository.processed import Processed


def test_processed() -> None:
    """Test the processed files repository."""
    with temp_dir() as td:
        proc: Final[Processed] = Processed(td)

        file_1, url_1 = proc.get_file_and_url(
            "https://github.com/thomasWeise/moptipy",
            "moptipy/api/operators.py")
        assert isinstance(file_1, Path)
        assert isinstance(url_1, str)
        file_1.enforce_file()
        td.enforce_contains(file_1)
        assert url_1.startswith("https://github.com/thomasWeise/moptipy/blob/")
        assert url_1.endswith("/moptipy/api/operators.py")

        file_2, url_2 = proc.get_file_and_url(
            "https://github.com/thomasWeise/moptipy",
            "moptipy/api/operators.py",
            ("head", "-n", "5"))
        assert isinstance(file_2, Path)
        assert isinstance(url_2, str)
        file_2.enforce_file()
        assert file_2 != file_1
        assert url_2 == url_1
        td.enforce_contains(file_2)
        assert len(list(file_2.open_for_read())) == 5

        file_3, url_3 = proc.get_file_and_url(
            "https://github.com/thomasWeise/moptipy",
            "moptipy/api/operators.py",
            ("head", "-n", "5"))
        assert isinstance(file_3, Path)
        assert file_3 == file_2
        assert isinstance(url_3, str)
        assert url_3 == url_2

        file_4, url_4 = proc.get_file_and_url(
            "https://github.com/thomasWeise/moptipy",
            "moptipy/api/operators.py")
        assert isinstance(file_4, Path)
        assert file_4 == file_1
        assert isinstance(url_4, str)
        assert url_4 == url_2

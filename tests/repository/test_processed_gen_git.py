"""Test the processed generated git files repository."""



from pycommons.io.path import Path
from pycommons.io.temp import temp_dir

from latexgit.repository.processed import Processed


def test_processed_gen_git() -> None:
    """Test the processed files repository."""
    with temp_dir() as td:
        proc: Processed = Processed(td)

        file_1 = proc.get_output(
            ("python3", "temp.py"),
            "https://github.com/thomasWeise/pycommons",
            "examples")
        assert isinstance(file_1, Path)
        td.enforce_contains(file_1)
        file_1.enforce_file()
        assert file_1.is_file()

        proc.close()
        proc = Processed(td)
        file_1b = proc.get_output(
            ("python3", "temp.py"),
            "https://github.com/thomasWeise/pycommons",
            "examples")
        assert isinstance(file_1b, Path)
        assert file_1b.is_file()
        assert file_1b == file_1

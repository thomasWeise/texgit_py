"""Test the processed generated files repository."""


from pycommons.io.path import Path
from pycommons.io.temp import temp_dir

from latexgit.repository.processed import Processed


def test_processed_gen() -> None:
    """Test the processed files repository."""
    with temp_dir() as td:
        proc: Processed = Processed(td)

        file_1, u = proc.get_output(("python3", "--version"))
        assert u is None
        assert isinstance(file_1, Path)
        td.enforce_contains(file_1)
        file_1.enforce_file()
        assert file_1.is_file()

        file_2, u = proc.get_output(("python3", "--version"))
        assert u is None
        assert isinstance(file_2, Path)
        td.enforce_contains(file_2)
        file_2.enforce_file()
        assert file_1 is file_2

        proc.close()
        proc = Processed(td)

        file_3, u = proc.get_output(("python3", "--version"))
        assert u is None
        assert isinstance(file_3, Path)
        assert file_3.is_file()
        assert file_3 == file_1

        file_4, u = proc.get_output(("python3", "--version"))
        assert u is None
        assert isinstance(file_4, Path)
        assert file_3 is file_4

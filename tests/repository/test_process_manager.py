"""Test the file manager."""

from pycommons.io.path import Path
from pycommons.io.temp import temp_dir
from sphinx.cmd.quickstart import suffix

from latexgit.repository.git_manager import GitPath
from latexgit.repository.process_manager import ProcessManager


def test_process_manager_args() -> None:
    """Test the process manager arguments API."""
    with temp_dir() as td, ProcessManager(td) as fm:
        ap1 = fm.filter_argument("(?123?)")
        assert isinstance(ap1, Path)
        assert ap1.is_file()

        ap2 = fm.filter_argument("(?123?)")
        assert isinstance(ap2, Path)
        assert ap2.is_file()
        assert ap1 is ap2

        ap3 = fm.filter_argument("(?1323?)")
        assert isinstance(ap3, Path)
        assert ap3.is_file()
        assert ap1 != ap3

        assert fm.filter_argument("(?1/2:sdf@@x3)") == "(?1/2:sdf@@x3)"


def test_process_arg_file() -> None:
    """Test the process manager arguments API."""
    with temp_dir() as td, ProcessManager(td) as fm:
        ap1, x = fm.get_argument_file("123")
        assert x is True
        assert isinstance(ap1, Path)
        assert ap1.is_file()

        ap2, x = fm.get_argument_file("123")
        assert isinstance(ap2, Path)
        assert x is False
        assert ap2.is_file()
        assert ap1 is ap2

        ap3, x = fm.get_argument_file("1235", "zzzz")
        assert isinstance(ap3, Path)
        assert x is True
        assert ap3.is_file()
        assert ap3.basename().startswith("zzzz")

        ap4, x = fm.get_argument_file("12y35", "zzzz", ".pdf")
        assert isinstance(ap4, Path)
        assert x is True
        assert ap4.is_file()
        assert ap4.basename().startswith("zzzz")
        assert ap4.basename().endswith(".pdf")

        ap5, x = fm.get_argument_file("12y3s5", suffix=".pdf")
        assert isinstance(ap5, Path)
        assert x is True
        assert ap5.is_file()
        assert ap5.basename().endswith(".pdf")

        ap6, x = fm.get_argument_file("1/2", "sdf@@x3")
        assert isinstance(ap6, Path)
        assert ap6.is_file()


def test_process_manager_output() -> None:
    """Test the processed files repository."""
    with temp_dir() as td:
        with ProcessManager(td) as proc:
            file_1 = proc.get_output("v", ("python3", "--version"))
            assert isinstance(file_1, Path)
            td.enforce_contains(file_1)
            file_1.enforce_file()
            assert file_1.is_file()

            file_2 = proc.get_output("v", ("python3", "--version"))
            assert isinstance(file_2, Path)
            td.enforce_contains(file_2)
            file_2.enforce_file()
            assert file_1 is file_2

            file_a = proc.get_output("w", ("python3", "--version"))
            assert isinstance(file_a, Path)
            td.enforce_contains(file_a)
            file_a.enforce_file()
            assert file_1 is not file_a

        with ProcessManager(td) as proc:
            file_3 = proc.get_output("v", ("python3", "--version"))
            assert isinstance(file_3, Path)
            assert file_3.is_file()
            assert file_3 == file_1

            file_4 = proc.get_output("v", ("python3", "--version"))
            assert isinstance(file_4, Path)
            assert file_3 is file_4


def test_process_manager_git() -> None:
    """Test the processed files repository."""
    with temp_dir() as td:
        with ProcessManager(td) as proc:
            gf1 = proc.get_git_file(
                "https://github.com/thomasWeise/moptipy",
                "moptipy/api/operators.py")
            assert isinstance(gf1, GitPath)
            gf1.path.enforce_file()
            td.enforce_contains(gf1.path)
            assert gf1.url.startswith(
                "https://github.com/thomasWeise/moptipy/blob/")
            assert gf1.url.endswith("/moptipy/api/operators.py")

            gf2 = proc.get_git_file(
                "https://github.com/thomasWeise/moptipy",
                "moptipy/api/operators.py",
                "x", ("head", "-n", "5"))
            assert isinstance(gf2, GitPath)
            gf2.path.enforce_file()
            assert gf1 != gf2
            assert gf1.path != gf2.path
            td.enforce_contains(gf2.path)
            assert len(list(gf2.path.open_for_read())) == 5

            gf3 = proc.get_git_file(
                "https://github.com/thomasWeise/moptipy",
                "moptipy/api/operators.py",
                "x", ("head", "-n", "5"))
            assert isinstance(gf3.path, Path)
            assert gf2.path == gf3.path
            assert isinstance(gf2.url, str)
            assert gf2.url == gf3.url

            gf4 = proc.get_git_file(
                "https://github.com/thomasWeise/moptipy",
                "moptipy/api/operators.py")
            assert isinstance(gf4, GitPath)
            assert gf4 == gf1
            assert isinstance(gf4.url, str)
            assert gf4.url == gf1.url

        with ProcessManager(td) as proc:
            gf1b = proc.get_git_file(
                "https://github.com/thomasWeise/moptipy",
                "moptipy/api/operators.py")
            assert gf1b == gf1

            gf2b = proc.get_git_file(
                "https://github.com/thomasWeise/moptipy",
                "moptipy/api/operators.py",
                "x", ("head", "-n", "5"))
            assert gf2b == gf2

            gf3b = proc.get_git_file(
                "https://github.com/thomasWeise/moptipy",
                "moptipy/api/operators.py",
                "x", ("head", "-n", "5"))
            assert gf3b == gf3

            gf4b = proc.get_git_file(
                "https://github.com/thomasWeise/moptipy",
                "moptipy/api/operators.py")
            assert gf4b == gf4


def test_process_manager_git_output() -> None:
    """Test the processed files repository."""
    with temp_dir() as td:
        with ProcessManager(td) as proc:
            file_1 = proc.get_output(
                "x", ("python3", "temp.py"),
                "https://github.com/thomasWeise/pycommons",
                "examples")
            assert isinstance(file_1, Path)
            td.enforce_contains(file_1)
            file_1.enforce_file()
            assert file_1.is_file()

            file_2 = proc.get_output(
                "x", ("python3", "temp.py"),
                "https://github.com/thomasWeise/pycommons",
                "examples")
            assert isinstance(file_2, Path)
            assert file_1 is file_2
            td.enforce_contains(file_2)
            file_2.enforce_file()
            assert file_2.is_file()

        with ProcessManager(td) as proc:
            file_1b = proc.get_output(
                "x", ("python3", "temp.py"),
                "https://github.com/thomasWeise/pycommons",
                "examples")
            assert isinstance(file_1b, Path)
            assert file_1b.is_file()
            assert file_1b == file_1

            file_4 = proc.get_output(
                "y", ("python3", "examples/temp.py"),
                "https://github.com/thomasWeise/pycommons",
                ".")
            assert isinstance(file_4, Path)
            td.enforce_contains(file_4)
            file_4.enforce_file()
            assert file_4.is_file()


def test_processmanager_git_replace_path() -> None:
    """Test the processed files repository."""
    with temp_dir() as td, ProcessManager(td) as proc:
        repo: str = "https://github.com/thomasWeise/programmingWithPythonCode"
        p = proc.get_output("x", ("./_scripts_/pythonIgnoreErrors.sh",
                                  "exceptions", "use_sqrt_raise.py"),
                            repo, ".")
        text = p.read_all_str()
        assert str.__len__(text) > 0
        assert 'File "{...}/exceptions/sqrt_raise.py"' in text

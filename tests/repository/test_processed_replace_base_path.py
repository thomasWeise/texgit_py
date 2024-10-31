"""Test the processed git files repository."""

from pycommons.io.temp import temp_dir

from latexgit.repository.processed import Processed


def test_processed_git_replace_path() -> None:
    """Test the processed files repository."""
    with temp_dir() as td:
        proc: Processed = Processed(td)
        repo: str = "https://github.com/thomasWeise/programmingWithPythonCode"
        p, u = proc.get_output(
            ("./scripts/pythonIgnoreErrors.sh",
             "06_exceptions", "use_sqrt_raise.py"),
            repo, ".")
        text = p.read_all_str()
        assert str.__len__(text) > 0
        assert 'File "{...}/06_exceptions/sqrt_raise.py"' in text
        assert u.startswith(repo)

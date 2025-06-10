"""Test the git manager."""

from pycommons.io.temp import temp_dir

from latexgit.repository.git_manager import GitFile, GitManager


def test_git_manager() -> None:
    """Test the file manager."""
    with temp_dir() as td:
        with GitManager(td) as gm:
            gf1 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_py", "README.md")
            assert isinstance(gf1, GitFile)

            gf2 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_py", "README.md")
            assert isinstance(gf2, GitFile)
            assert gf2.repo is gf1.repo
            assert gf1.path == gf2.path

            gf3 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_tex", "README.md")
            assert isinstance(gf3, GitFile)
            assert gf1.repo != gf3.repo
            assert gf1.path != gf3.path

            gf4 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_py", "SECURITY.md")
            assert isinstance(gf4, GitFile)
            assert gf4.repo is gf1.repo
            assert gf1.path != gf4.path

            gf5 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_tex.git",
                "latexgit.ins")
            assert isinstance(gf5, GitFile)
            assert gf5.repo is gf3.repo
            assert gf5.path != gf3.path

        with GitManager(td) as gm:
            gf1b = gm.get_git_file(
                "http://github.com/thomasWeise/latexgit_py.git", "README.md")
            assert isinstance(gf1b, GitFile)
            assert gf1b == gf1

            gf3b = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_tex", "README.md")
            assert isinstance(gf3b, GitFile)
            assert gf3b == gf3

            gf4b = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_py", "SECURITY.md")
            assert isinstance(gf4b, GitFile)
            assert gf4b == gf4

            gf5b = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_tex", "latexgit.ins")
            assert isinstance(gf5b, GitFile)
            assert gf5 == gf5b

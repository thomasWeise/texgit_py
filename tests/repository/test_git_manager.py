"""Test the git manager."""

from pycommons.io.temp import temp_dir

from texgit.repository.git_manager import GitManager, GitPath


def test_git_manager() -> None:
    """Test the file manager."""
    with temp_dir() as td:
        with GitManager(td) as gm:
            gp1 = gm.get_git_file(
                "https://github.com/thomasWeise/texgit_py", "README.md")
            assert isinstance(gp1, GitPath)

            gp2 = gm.get_git_file(
                "https://github.com/thomasWeise/texgit_py", "README.md")
            assert isinstance(gp2, GitPath)
            assert gp1.repo is gp2.repo
            assert gp1.path == gp2.path

            gp3 = gm.get_git_file(
                "https://github.com/thomasWeise/texgit_tex", "README.md")
            assert isinstance(gp3, GitPath)
            assert gp1.repo is not gp3.repo

            gp4 = gm.get_git_file(
                "https://github.com/thomasWeise/texgit_py", "SECURITY.md")
            assert isinstance(gp4, GitPath)
            assert gp4.repo is gp1.repo

            gp5 = gm.get_git_file(
                "https://github.com/thomasWeise/texgit_tex.git",
                "texgit.ins")
            assert isinstance(gp5, GitPath)
            assert gp5.repo is gp3.repo

        with GitManager(td) as gm:
            gp1b = gm.get_git_file(
                "http://github.com/thomasWeise/texgit_py.git", "README.md")
            assert isinstance(gp1b, GitPath)
            assert gp1b.repo == gp1.repo
            assert gp1.path == gp1b.path

            gp3b = gm.get_git_file(
                "https://github.com/thomasWeise/texgit_tex", "README.md")
            assert isinstance(gp3b, GitPath)
            assert gp3b.repo == gp3.repo
            assert gp3.path == gp3b.path

            gp4b = gm.get_git_file(
                "https://github.com/thomasWeise/texgit_py", "SECURITY.md")
            assert isinstance(gp4b, GitPath)
            assert gp4b.repo == gp4.repo
            assert gp4.path == gp4b.path

            gp5b = gm.get_git_file(
                "https://github.com/thomasWeise/texgit_tex", "texgit.ins")
            assert isinstance(gp5b, GitPath)
            assert gp5b.repo == gp5.repo
            assert gp5.path == gp5b.path

"""Test the git manager."""

from pycommons.io.path import Path
from pycommons.io.temp import temp_dir
from pycommons.net.url import URL

from latexgit.repository.git_manager import GitManager


def test_git_manager() -> None:
    """Test the file manager."""
    with temp_dir() as td:
        with GitManager(td) as gm:
            gf1, url1 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_py", "README.md")
            assert isinstance(gf1, Path)
            assert isinstance(url1, URL)

            gf2, url2 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_py", "README.md")
            assert isinstance(gf2, Path)
            assert isinstance(url2, URL)
            assert url2.host == url1.host
            assert gf1 == gf2

            gf3, url3 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_tex", "README.md")
            assert isinstance(gf3, Path)
            assert isinstance(url3, URL)
            assert gf1 != gf3
            assert gf1.up(1) != gf3.up(1)

            gf4, url4 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_py", "SECURITY.md")
            assert isinstance(gf4, Path)
            assert isinstance(url4, URL)
            assert gf4.up(1) == gf2.up(1)

            gf5, url5 = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_tex.git",
                "latexgit.ins")
            assert isinstance(gf5, Path)
            assert isinstance(url5, URL)

        with GitManager(td) as gm:
            gf1b, url1b = gm.get_git_file(
                "http://github.com/thomasWeise/latexgit_py.git", "README.md")
            assert isinstance(gf1b, Path)
            assert isinstance(url1b, URL)
            assert gf1b == gf1
            assert url1b == url1

            gf3b, url3b = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_tex", "README.md")
            assert isinstance(gf3b, Path)
            assert isinstance(url3b, URL)
            assert gf3b == gf3
            assert url3b == url3

            gf4b, url4b = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_py", "SECURITY.md")
            assert isinstance(gf4b, Path)
            assert isinstance(url4b, URL)
            assert gf4b == gf4
            assert url4b == url4

            gf5b, url5b = gm.get_git_file(
                "https://github.com/thomasWeise/latexgit_tex", "latexgit.ins")
            assert isinstance(gf5b, Path)
            assert gf5 == gf5b
            assert url5 == url5b

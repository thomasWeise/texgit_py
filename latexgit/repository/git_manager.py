"""
A manager for repository repositories.

This class allows to maintain a local stash of repository repositories that
can consistently be accessed without loading any repository multiple
times.
"""

from os import rmdir
from typing import Final

from pycommons.io.path import Path
from pycommons.net.url import URL
from pycommons.types import type_error

from latexgit.repository.file_manager import FileManager
from latexgit.repository.git import GitRepository


def _make_key(u: URL) -> tuple[str, str]:
    """
    Turn a URL into a key.

    :param u: the url
    :return: the key
    """
    pt: str = u.path
    while pt.startswith("/"):
        pt = pt[1:]
    while pt.endswith(".git"):
        pt = pt[:-4]
    pt = pt.replace("/", "_")
    return u.host, pt


class GitManager(FileManager):
    """A git repository manager can provide a set of git repositories."""

    def __init__(self, base_dir: str) -> None:
        """
        Set up the git repository manager.

        :param base_dir: the base directory
        """
        super().__init__(base_dir)
        #: the internal set of github repositories
        self.__repos: Final[dict[tuple[str, str], GitRepository]] = {}

        #: load all the repository repositories
        for the_dir in self.list_realm("git", files=False, directories=True):
            if the_dir.resolve_inside(".git").is_dir():
                gr: GitRepository = GitRepository.from_local(the_dir)
                self.__repos[_make_key(gr.url)] = gr

    def is_git_repository_path(self, path: Path | None) -> bool:
        """
        Check if the given path identifies a directory inside a repository.

        :param path: the path
        :return: `True` if `path` identifies a directory located in a
            repository.
        """
        return (path is not None) and path.is_dir() and any(
            repo.path.contains(path) for repo in self.__repos.values())

    def get_repository(self, url: str) -> GitRepository:
        """
        Get the git repository for the given URL.

        :param url: the URL to load
        :return: the repository
        """
        url = URL(url)
        key: Final[tuple[str, str]] = _make_key(url)
        if key in self.__repos:
            return self.__repos[key]
        name: str = "_".join(key)
        dirpath, found = self.get_dir("git", name)
        if not found:
            raise ValueError("Inconsistent archive state!")
        try:
            gt: Final[GitRepository] = GitRepository.download(url, dirpath)
        except ValueError:
            rmdir(dirpath)
            raise
        self.__repos[key] = gt
        self.__repos[_make_key(gt.url)] = gt
        return gt

    def get_git_file(self, repo_url: str, relative_path: str)\
            -> tuple[Path, URL]:
        """
        Get a path to a file from the given git repository and also the URL.

        :param repo_url: the repository url.
        :param relative_path: the relative path
        :return: a tuple of file and URL
        """
        if not isinstance(relative_path, str):
            raise type_error(relative_path, "relative_path", str)
        repo: Final[GitRepository] = self.get_repository(repo_url)
        file: Final[Path] = repo.path.resolve_inside(
            relative_path)
        file.enforce_file()
        return file, repo.make_url(relative_path)

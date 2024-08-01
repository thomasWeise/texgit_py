"""
A manager for repository repositories.

This class allows to maintain a local stash of repository repositories that
can consistently be accessed without loading any repository multiple
times.
"""

from os import listdir, rmdir
from tempfile import mkdtemp
from typing import Final

from pycommons.io.path import Path, directory_path
from pycommons.net.url import URL
from pycommons.types import type_error

from latexgit.repository.git import GitRepository


class GitManager:
    """A git repository manager can provide a set of git repositories."""

    def __init__(self, base_dir: str) -> None:
        """
        Set up the git repository manager.

        :param base_dir: the base directory
        """
        #: the base directory of the repository manager
        self.base_dir: Final[Path] = Path(base_dir)
        self.base_dir.ensure_dir_exists()
        #: the internal set of github repositories
        self.__repos: Final[dict[str, GitRepository]] = {}

        #: load all the repository repositories
        for the_dir in listdir(self.base_dir):
            fullpath = self.base_dir.resolve_inside(the_dir)
            if fullpath.is_dir() and fullpath.resolve_inside(".git").is_dir():
                gr: GitRepository = GitRepository.from_local(fullpath)
                self.__repos[gr.url] = gr

    def is_git_repo_path(self, path: Path | None) -> bool:
        """
        Check if the given path identifies a directory inside a repository.

        :param path: the path
        :return: `True` if `path` identifies a directory located in a
            repository.
        """
        return (path is not None) and path.is_dir() and any(
            repo.path.contains(path) for repo in self.__repos.values())

    def get_repo(self, url: str) -> GitRepository:
        """
        Get the git repository for the given URL.

        :param url: the URL to load
        :return: the repository
        """
        url = URL(url)
        if url in self.__repos:
            return self.__repos[url]

        dirpath: Final[Path] = directory_path(mkdtemp(
            dir=self.base_dir, prefix="git_"))
        try:
            gt: Final[GitRepository] = GitRepository.download(url, dirpath)
        except ValueError:
            rmdir(dirpath)
            raise
        self.__repos[gt.url] = gt
        self.__repos[url] = gt
        return gt

    def get_file_and_url(self, repo_url: str, relative_path: str) \
            -> tuple[Path, URL]:
        """
        Get a path to a file from the given git repository and also the URL.

        :param repo_url: the repository url.
        :param relative_path: the relative path
        :return: a tuple of file and URL
        """
        if not isinstance(relative_path, str):
            raise type_error(relative_path, "relative_path", str)
        repo: Final[GitRepository] = self.get_repo(repo_url)
        file: Final[Path] = repo.path.resolve_inside(
            relative_path)
        file.enforce_file()
        url: Final[URL] = repo.make_url(relative_path)
        return file, url

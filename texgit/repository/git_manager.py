"""
A manager for repository repositories.

This class allows to maintain a local stash of repository repositories that
can consistently be accessed without loading any repository multiple
times.
"""

from dataclasses import dataclass
from os import rmdir
from typing import Final

from pycommons.io.path import Path
from pycommons.net.url import URL
from pycommons.types import type_error

from texgit.repository.file_manager import FileManager
from texgit.repository.git import GitRepository


@dataclass(frozen=True, init=False, order=True)
class GitPath:
    """An immutable record of a path inside a git repository."""

    #: the absolute path of the file or directory inside the repository
    #: directory
    path: Path
    #: the base name of the file
    basename: str
    #: the repository
    repo: GitRepository
    #: the URL
    url: URL

    def __init__(self, path: Path, repo: GitRepository, url: URL,
                 basename: str | None = None):
        """
        Set up the information about a repository.

        :param path: the absolute path to the file or directory
        :param repo: the repository
        """
        if not isinstance(path, Path):
            raise type_error(path, "path_in_repo", Path)
        if not isinstance(repo, GitRepository):
            raise type_error(repo, "repo", GitRepository)
        if not isinstance(url, URL):
            raise type_error(url, "url", URL)
        basename = path.basename() if basename is None \
            else str.strip(basename)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "repo", repo)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "basename", basename)


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
    while pt.endswith("/"):
        pt = pt[:-1]
    pt = pt.replace("/", "_")
    return "gh" if u.host.lower() == "github.com" else u.host, pt


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

    def _get_sensitive_paths(self) -> list[Path]:
        """
        Get the list of sensitive paths.

        :return: the paths
        """
        paths: Final[list[Path]] = super()._get_sensitive_paths()
        paths.extend(r.path for r in self.__repos.values())
        return paths

    def get_repository(self, url: str) -> GitRepository:
        """
        Get the git repository for the given URL.

        :param url: the URL to load
        :return: the repository
        """
        self._check_open()
        use_url: Final[URL] = URL(url)
        key: Final[tuple[str, str]] = _make_key(use_url)
        if key in self.__repos:
            return self.__repos[key]
        name: str = "_".join(key)
        dirpath, found = self.get_dir("git", name)
        if not found:
            raise ValueError("Inconsistent archive state!")
        try:
            gt: Final[GitRepository] = GitRepository.download(use_url, dirpath)
        except ValueError:
            rmdir(dirpath)
            raise
        self.__repos[key] = gt
        self.__repos[_make_key(gt.url)] = gt
        return gt

    def __get_git(self, repo_url: str, relative_path: str,
                  is_file: bool) -> GitPath:
        """
        Get a file or directory from the given repository.

        :param repo_url: the repository URL
        :param relative_path: the relative path to the file or directory
        :param is_file: should it be a file (`True`) or directory (`False`)
        :return: the path and the URL
        """
        relative_path = str.strip(relative_path)
        repo: Final[GitRepository] = self.get_repository(repo_url)
        dest: Final[Path] = repo.path.resolve_inside(relative_path)
        if is_file:
            dest.enforce_file()
        else:
            dest.enforce_dir()
        return GitPath(dest, repo, repo.make_url(dest))

    def get_git_file(self, repo_url: str, relative_file: str) -> GitPath:
        """
        Get a path to a file from the given git repository and also the URL.

        :param repo_url: the repository url.
        :param relative_file: the relative path
        :return: a tuple of file and URL
        """
        return self.__get_git(repo_url, relative_file, True)

    def get_git_dir(self, repo_url: str, relative_dir: str) -> GitPath:
        """
        Get a path to a directory from the given git repository.

        :param repo_url: the repository url.
        :param relative_dir: the relative path
        :return: a tuple of directory and URL
        """
        return self.__get_git(repo_url, relative_dir, False)

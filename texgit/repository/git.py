"""Tools for interacting with repository."""
import datetime
from dataclasses import dataclass
from re import MULTILINE, Pattern, search
from re import compile as re_compile
from shutil import rmtree, which
from typing import Final, cast

from pycommons.io.console import logger
from pycommons.io.path import Path, file_path
from pycommons.net.url import URL
from pycommons.processes.shell import STREAM_CAPTURE, Command
from pycommons.strings.enforce import (
    enforce_non_empty_str,
    enforce_non_empty_str_without_ws,
)
from pycommons.strings.string_conv import datetime_to_datetime_str
from pycommons.types import type_error


def git() -> Path:
    """
    Get the path to the git executable.

    :return: the path to the git executable
    """
    obj: Final[object] = git
    attr: Final[str] = "__the_path"
    if hasattr(obj, attr):
        return cast("Path", getattr(obj, attr))

    path: str | None = which("git")
    if path is None:
        raise ValueError("Could not find 'repository' installation.")
    result: Final[Path] = file_path(path)
    setattr(obj, attr, result)
    return result


#: the commit pattern
_COMMIT: Final[Pattern] = re_compile(r"^\s*commit\s+(.+?)\s+", flags=MULTILINE)
#: the date
_DATE: Final[Pattern] = re_compile(r"^\s*Date:\s+(.+?)$", flags=MULTILINE)


def _get_base_url(url: str) -> URL:
    """
    Get the base url of a git repository.

    :return: the base url of a git repository.
    """
    base_url: str = URL(url)
    base_url_lower: str = str.lower(base_url)
    if base_url_lower.startswith("ssh://git@github."):
        base_url = f"https://{enforce_non_empty_str(base_url[10:])}"
    if base_url_lower.endswith(".git"):
        base_url = enforce_non_empty_str(base_url[:-4])
    return URL(base_url)


@dataclass(frozen=True, init=False, order=True)
class GitRepository:
    """An immutable record of a repository."""

    #: the repository path
    path: Path
    #: the normalized repository url
    url: URL
    #: the commit
    commit: str
    #: the date and time
    date_time: str

    def __init__(self, path: Path, url: str, commit: str, date_time: str):
        """
        Set up the information about a repository.

        :param path: the path
        :param url: the url
        :param commit: the commit
        :param date_time: the date and time
        """
        if not isinstance(path, Path):
            raise type_error(path, "path", Path)
        path.enforce_dir()
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "url", _get_base_url(url))
        object.__setattr__(self, "commit",
                           enforce_non_empty_str_without_ws(commit))
        if len(self.commit) != 40:
            raise ValueError(f"Invalid commit: {self.commit!r}.")
        try:
            int(self.commit, 16)
        except ValueError as e:
            raise ValueError("Invalid commit information "
                             f"{self.commit!r} for repo {url!r}.") from e
        object.__setattr__(self, "date_time",
                           enforce_non_empty_str(date_time))
        logger(f"found repository in path {self.path!r} with commit "
               f"{self.commit!r} for url {self.url!r} and "
               f"date {self.date_time!r}.")

    @staticmethod
    def download(url: str, dest_dir: str) -> "GitRepository":
        """
        Download a git repository.

        :param url: the repository url
        :param dest_dir: the destination directory
        :return: the repository information
        """
        dest: Final[Path] = Path(dest_dir)
        gt: Final[Path] = git()
        dest.ensure_dir_exists()
        url = URL(url)
        s = f" repository {url!r} to directory {dest!r}"
        logger(f"starting to load{s} via {gt!r}.")
        try:
            Command([
                gt, "-C", dest, "clone", "--depth", "1", url, dest],
                timeout=600, working_dir=dest).execute(True)
        except ValueError:
            if not url.startswith("https://github.com"):
                raise
            url2 = URL(f"ssh://git@{url[8:]}")
            logger(f"timeout when loading url {url!r}, so we try "
                   f"{url2!r} instead, but first delete {dest!r}.")
            rmtree(dest, ignore_errors=True)
            dest.ensure_dir_exists()
            logger(f"{dest!r} deleted and created, now re-trying cloning.")
            Command([
                gt, "-C", dest, "clone", "--depth", "1", url2, dest],
                timeout=600, working_dir=dest).execute(True)
        logger(f"successfully finished loading{s}.")

        return GitRepository.from_local(path=dest, url=url)

    @staticmethod
    def from_local(path: str, url: str | None = None) -> "GitRepository":
        """
        Load all the information from a local repository.

        :param path: the path to the repository
        :param url: the url
        :return: the repository information
        """
        dest: Final[Path] = Path(path)
        gt: Final[str] = git()
        dest.enforce_dir()

        logger(
            f"checking commit information of repo {dest!r} via {gt!r}.")
        stdout: str = enforce_non_empty_str(Command(
            [gt, "-C", dest, "log", "--no-abbrev-commit", "-1"],
            timeout=120, working_dir=dest, stdout=STREAM_CAPTURE).execute(
            True)[0])

        match = search(_COMMIT, stdout)
        if match is None:
            raise ValueError(
                f"Did not find commit information in repo {dest!r}.")
        commit: Final[str] = enforce_non_empty_str_without_ws(match.group(1))
        match = search(_DATE, stdout)
        if match is None:
            raise ValueError(
                f"Did not find date information in repo {dest!r}.")
        date_str: Final[str] = enforce_non_empty_str(match.group(1))
        date_raw: Final[datetime.datetime] = datetime.datetime.strptime(
            date_str, "%a %b %d %H:%M:%S %Y %z")
        if not isinstance(date_raw, datetime.datetime):
            raise type_error(date_raw, "date_raw", datetime.datetime)
        date_time: Final[str] = datetime_to_datetime_str(date_raw)
        logger(f"found commit {commit!r} and date/time {date_time!r} "
               f"for repo {dest!r}.")

        if url is None:
            logger(f"applying {gt!r} to get url information.")
            url = enforce_non_empty_str(Command(
                [gt, "-C", dest, "config", "--get", "remote.origin.url"],
                timeout=120, working_dir=dest, stdout=STREAM_CAPTURE)
                .execute(True)[0])
            url = enforce_non_empty_str_without_ws(
                url.strip().split("\n")[0].strip())
            if url.endswith("/.git"):
                url = enforce_non_empty_str_without_ws(f"{url[:-5]}.git")
            if url.endswith("/"):
                url = enforce_non_empty_str_without_ws(url[:-1])
            logger(f"found url {url!r} for repo {dest!r}.")
            if url.startswith("ssh://git@github.com"):
                url = f"https://{url[10:]}"

        return GitRepository(dest, url, commit, date_time)

    def make_url(self, path: str) -> URL:
        """
        Make a url relative to this git repository.

        :param path: the absolute path
        :return: the url
        """
        pt: Final[Path] = Path(path)
        self.path.enforce_contains(pt)
        if not (pt.exists() and (pt.is_file() or pt.is_dir())):
            raise ValueError(
                f"Path {path!r} does not exist in {self}.")

        relative_path: Final[str] = pt.relative_to(self.path)
        url: Final[URL] = self.url
        return URL(f"{url}/blob/{self.commit}/{relative_path}"
                   if url.host == "github.com" else f"{url}/{relative_path}")

    def get_name(self) -> str:
        """
        Get the name of this git repository in the form 'user/name'.

        :return: the name of this git repository in the form 'user/name'.
        """
        base_url: str = self.url
        if base_url.lower().endswith(".git"):
            base_url = enforce_non_empty_str_without_ws(base_url[:-4])
        si: int = base_url.rfind("/")
        if si <= 0:
            return base_url
        si = max(0, base_url.rfind("/", 0, si - 1))
        return enforce_non_empty_str(base_url[si + 1:].strip())

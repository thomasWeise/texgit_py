"""A post-processed representation of repository files."""

import json
import os
from contextlib import AbstractContextManager
from os.path import getsize
from shutil import rmtree
from tempfile import mkstemp
from typing import Final, Iterable

from pycommons.io.console import logger
from pycommons.io.path import Path, file_path, write_lines
from pycommons.net.url import URL
from pycommons.processes.python import PYTHON_ENV, PYTHON_INTERPRETER
from pycommons.processes.shell import STREAM_CAPTURE, Command
from pycommons.types import type_error

from latexgit.repository.gitmanager import GitManager


def _str_tuple(command: None | str | Iterable[str],
               none_ok: bool = True,
               empty_ok: bool = True,
               raise_errors: bool = False) -> tuple[str, ...] | None:
    """
    Get a string tuple from some source.

    :param command: the original command
    :param none_ok: is `None` OK (and should lead to an empty tuple returned)?
    :param empty_ok: is it OK if an empty tuple is returned?
    :param raise_errors: should we raise errors or just return `None`?
    :return: the tuple
    """
    if command is None:
        if (not raise_errors) or (none_ok and empty_ok):
            return ()
        if none_ok:
            raise ValueError(
                f"Empty command not permitted, but got {command!r}.")
        if empty_ok:
            raise ValueError("None is not OK as command.")
        raise ValueError(
            f"Neither None nor empty commands are OK, but got {command!r}.")

    res: list[str] = []
    if isinstance(command, str):
        command = [command]
    if not isinstance(command, Iterable):
        if raise_errors:
            raise type_error(command, "command", Iterable)
        return None
    for i, o in enumerate(command):
        if not isinstance(o, str):
            if raise_errors:
                raise type_error(o, f"command[{i}]", str)
            return None
        use_o = str.strip(o)
        if str.__len__(use_o) > 0:
            res.append(use_o)
    if list.__len__(res) <= 0:
        if not empty_ok:
            if raise_errors:
                raise ValueError(
                    f"Empty command not OK, but got {command!r}.")
            return None
        return ()
    return tuple(res)


def _write(orig: str, dest: Path) -> None:
    """
    Write the string to the destination.

    :param orig: the original string
    :param dest: the destination
    """
    orig = str.rstrip(orig)
    with dest.open_for_write() as output:
        write_lines(map(str.rstrip, str.rstrip(orig).splitlines()), output)
    logger("Wrote r-stripped string of originally "
           f"{str.__len__(orig)} characters to {dest!r}, "
           f"produced file of size {getsize(dest)} bytes.")


class Processed(AbstractContextManager):
    """A manager for processed files."""

    def __init__(self, base_dir: str) -> None:
        """
        Initialize the post processed manager.

        :param base_dir: the base directory
        """
        #: is the processor still open?
        self.__is_open: bool = True

        #: the base path of the processor
        self.base_path: Final[Path] = Path(base_dir)
        self.base_path.ensure_dir_exists()

        #: the internal repository manager
        self.__git: Final[GitManager] = GitManager(
            self.base_path.resolve_inside("git"))

        #: the directory to store post-processed stuff
        self.__cache_dir: Final[Path] = self.base_path.resolve_inside(
            ".cache")
        self.__cache_dir.ensure_dir_exists()

        #: the mapping of post-processing commands and resources
        self.__cache_mapped: Final[dict[
            tuple[Path, tuple[str, ...]], Path]] = {}

        #: the cache file
        self.__cache_list: Final[Path] = self.__cache_dir.resolve_inside(
            ".cache_list.json")
        #: load the cache list
        self.__cache_list.ensure_file_exists()

        if getsize(self.__cache_list) > 0:  # file size > 0
            s = self.__cache_list.read_all_str()
            if len(s) > 0:  # load all cached mappings
                for key, value in json.loads(s):
                    pt1: Path = Path(key[0])
                    if (not pt1.is_file()) or (
                            not self.__git.base_dir.contains(pt1)):
                        continue
                    pt2: Path = Path(value)
                    if (not pt2.is_file()) or (
                            not self.__cache_dir.contains(pt2)):
                        continue
                    cmd1: tuple[str, ...] | None = _str_tuple(
                        key[1], True, True, False)
                    if cmd1 is None:
                        continue
                    self.__cache_mapped[(pt1, cmd1)] = pt2

        #: the directory to store generated
        self.__generated_dir: Final[Path] = self.base_path.resolve_inside(
            ".generated")
        self.__generated_dir.ensure_dir_exists()

        #: the mapping of command lines and generated resources
        self.__generated_mapped: Final[dict[tuple[
            Path | None, tuple[str, ...]], Path]] = {}

        #: the generated list file
        self.__generated_list: Final[Path] = (
            self.__generated_dir.resolve_inside(".generated_list.json"))
        #: load the generated list
        self.__generated_list.ensure_file_exists()

        if getsize(self.__generated_list) > 0:  # file size > 0
            s = self.__generated_list.read_all_str()
            if len(s) > 0:  # load all cached mappings
                for key, value in json.loads(s):
                    pt3: Path | None = Path(key[0]) \
                        if key[0] is not None else None
                    if not ((pt3 is None) or self.__git.is_git_repo_path(
                            pt3)):
                        continue  # purge dirs not assigned to git repos
                    cmd2: tuple[str, ...] | None = _str_tuple(
                        key[1], False, False, False)
                    if cmd2 is None:
                        continue  # purge empty commands
                    pt4: Path = Path(value)
                    if (not pt4.is_file()) or (
                            not self.__generated_dir.contains(pt4)):
                        continue  # purge invalid cache entries
                    self.__generated_mapped[(pt3, cmd2)] = pt4

    def get_file_and_url(
            self, repo_url: str, relative_path: str,
            processor: Iterable[str] | None = ()) -> tuple[Path, URL]:
        """
        Get a specified, potentially pre-processed file.

        :param repo_url: the repository url
        :param relative_path: the relative path of the file
        :param processor: the pre-processor commands
        :return: the file and the url into the git repository of the original
        """
        if not self.__is_open:
            raise ValueError("already closed!")
        if processor is None:
            processor = ()
        if not isinstance(processor, Iterable):
            raise type_error(processor, "preprocessor", Iterable)
        if not isinstance(repo_url, str):
            raise type_error(repo_url, "repo_url", str)
        if not isinstance(relative_path, str):
            raise type_error(relative_path, "relative_path", str)

        # first step: get source repository file
        ps: Final[tuple[Path, URL]] = self.__git.get_file_and_url(
            repo_url, relative_path)
        path: Final[Path] = ps[0]

        # second step: prepare postprocessing command
        command: Final[tuple[str, ...]] = _str_tuple(
            processor, True, True, True)
        if len(command) <= 0:  # no postprocessing command?
            return path, ps[1]  # then return path to git file directory

        # so there is postprocessing to do: look up in cache
        key: Final[tuple[Path, tuple[str, ...]]] = (path, command)
        log_str: str = f"{path!r} via {' '.join(repr(c) for c in command)}"
        if key in self.__cache_mapped:  # found in cache?
            pt: Path = self.__cache_mapped[key]
            if pt.is_file():
                logger(f"found cache entry {pt!r} for {log_str}.")
                return pt, ps[1]  # return path to cached file

        # not in cache: create new file and apply post-processing
        (handle, fpath) = mkstemp(prefix="proc_", dir=self.__cache_dir)
        os.close(handle)
        dest: Final[Path] = file_path(fpath)
        log_str = f"from {log_str} to {dest!r}"
        logger(f"will pipe data from {path!r} via {log_str}")

        # execute the command
        _write(Command(
            command=command, working_dir=self.__cache_dir,
            stdout=STREAM_CAPTURE, stdin=path.read_all_str()).execute(
            True)[0], dest)
        self.__cache_mapped[key] = dest  # remember in cache
        return dest, ps[1]  # return path

    def get_output(
            self, command: str | Iterable[str],
            repo_url: str | None = None,
            relative_dir: str | None = None) -> tuple[Path, URL | None]:
        """
        Get the output of a certain command.

        :param command: the command itself
        :param repo_url: the optional repository URL
        :param relative_dir: the optional directory inside the repository
            where the command should be executed
        :return: the path to the output and the url of the git repository,
            if any
        """
        if not self.__is_open:
            raise ValueError("already closed!")
        command = _str_tuple(command, False, False, True)
        if isinstance(repo_url, str):
            if str.__len__(repo_url) <= 0:
                repo_url = None
        elif repo_url is not None:
            raise type_error(repo_url, "repo_url", (str, None))
        if isinstance(relative_dir, str):
            if str.__len__(relative_dir) <= 0:
                relative_dir = None
        elif relative_dir is not None:
            raise type_error(relative_dir, "relative_dir", (str, None))
        if (repo_url is None) != (relative_dir is None):
            raise ValueError(f"repo_url and relative_dir must either both be "
                             f"None or neither, but they are {repo_url!r} "
                             f"and {relative_dir!r}.")

        path: Path | None = None
        url: URL | None = None
        if repo_url is not None:
            repo = self.__git.get_repo(repo_url)
            path = repo.path.resolve_inside(relative_dir)
            url = repo.url

        key: tuple[Path | None, tuple[str, ...]] = (path, command)
        log_str: str = f"{' '.join(repr(c) for c in command)} in {path!r}"

        if key in self.__generated_mapped:
            result: Path = self.__generated_mapped[key]
            if result.is_file():
                logger(f"found cache entry {result!r} for {log_str}.")
                return result, url  # return path to cached file

        (handle, fpath) = mkstemp(prefix="gen_", dir=self.__generated_dir)
        os.close(handle)
        dest: Final[Path] = file_path(fpath)
        log_str = f"from {log_str} to {dest!r}"
        logger(f"will pipe data from {path!r} via {log_str}")

        # Now we need to fix the command if we are running inside a virtual
        # environment. If we are running inside a virtual environment, it is
        # necessary to use the same Python interpreter that was used to run
        # latexgit. We should also pass along all the Python-related
        # environment parameters.
        use_cmd: str | tuple[str, ...] = command
        if isinstance(use_cmd, tuple) and (tuple.__len__(use_cmd) > 1) and (
                str.lower(use_cmd[0]).startswith("python3")):
            lcmd: list[str] = list(use_cmd)
            lcmd[0] = PYTHON_INTERPRETER
            use_cmd = tuple(lcmd)

        # execute the command
        _write(Command(command=use_cmd, working_dir=path, env=PYTHON_ENV,
                       stdout=STREAM_CAPTURE).execute(True)[0], dest)
        self.__generated_mapped[key] = dest
        return dest, url

    def close(self) -> None:
        """Close the processed repository and write cache list."""
        opn: bool = self.__is_open
        self.__is_open = False
        if opn:  # only if we were open...
            # flush or clear directory of cached post-processed files
            if len(self.__cache_mapped) > 0:  # we got cached files
                self.__cache_list.write_all_str(json.dumps(  # store cache
                    list(self.__cache_mapped.items())))
            else:  # no cache files? we can delete cache directory
                rmtree(self.__cache_dir, ignore_errors=True)

            # flush or clear directory of generated resources
            if len(self.__generated_mapped) > 0:  # we got generated files
                self.__generated_list.write_all_str(json.dumps(  # store cache
                    list(self.__generated_mapped.items())))
            else:  # no cache files? we can delete cache directory
                rmtree(self.__generated_dir, ignore_errors=True)

    def __exit__(self, exception_type, _, __) -> bool:
        """
        Close the context manager.

        :param exception_type: ignored
        :param _: ignored
        :param __: ignored
        :returns: `True` to suppress an exception, `False` to rethrow it
        """
        self.close()  # close the manager and flush cache
        return exception_type is None

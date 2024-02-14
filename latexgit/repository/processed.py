"""A post-processed representation of repository files."""


import json
import os
from contextlib import AbstractContextManager
from os.path import getsize
from shutil import rmtree
from tempfile import mkstemp
from typing import Final, Iterable

from pycommons.io.console import logger
from pycommons.io.path import Path, file_path
from pycommons.processes.shell import exec_text_process
from pycommons.types import type_error

from latexgit.repository.gitmanager import GitManager


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

        #: the mapped resources
        self.__mapped: Final[dict[tuple[Path, tuple[str, ...]], Path]] = {}

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
                    if not pt1.is_file():
                        continue
                    pt2: Path = Path(value)
                    if not pt2.is_file():
                        continue
                    self.__mapped[(pt1, tuple(key[1]))] = pt2

    def get_file_and_url(
            self, repo_url: str, relative_path: str,
            processor: Iterable[str] | None = ()) -> tuple[Path, str]:
        """
        Get a specified, potentially pre-processed file.

        :param repo_url: the repository url
        :param relative_path: the relative path of the file
        :param processor: the pre-processor commands
        :return: the file
        """
        if not self.__is_open:
            raise ValueError("already closed!")
        if processor is None:
            processor = ()
        if not isinstance(processor, Iterable):
            raise type_error(processor, "preprocessor", Iterable)

        # first step: get source repository file
        ps: Final[tuple[Path, str]] = self.__git.get_file_and_url(
            repo_url, relative_path)
        path: Final[Path] = ps[0]

        # second step: prepare postprocessing command
        command: Final[tuple[str, ...]] = tuple(processor)
        if len(command) <= 0:  # no postprocessing command?
            return path, ps[1]  # then return path to git file directory

        # so there is postprocessing to do: look up in cache
        key: Final[tuple[Path, tuple[str, ...]]] = (path, command)
        logstr: str = f"{path!r} via {' '.join(repr(c) for c in command)}"
        if key in self.__mapped:  # found in cache?
            pt: Path = self.__mapped[key]
            logger(f"found cache entry {pt!r} for {logstr}.")
            return pt, ps[1]  # return path to cached file

        # not in cache: create new file and apply post processing
        (handle, fpath) = mkstemp(prefix="proc_", dir=self.__cache_dir)
        os.close(handle)
        dest: Final[Path] = file_path(fpath)
        logstr = f"from {logstr} to {dest!r}"
        logger(f"will pipe data from {path!r} via {logstr}")

        # execute the command
        ret: Final[str] = exec_text_process(
            command=command, cwd=self.__cache_dir, wants_stdout=True,
            stdin=path.read_all_str())
        dest.write_all_str(ret)

        logger(f"done piping {len(ret)} characters {logstr}")
        self.__mapped[key] = dest  # remember in cache
        return dest, ps[1]  # return path

    def close(self) -> None:
        """Close the processed repository and write cache list."""
        opn: bool = self.__is_open
        self.__is_open = False
        if opn:  # only if we were open...
            if len(self.__mapped) > 0:  # we got cached files
                self.__cache_list.write_all_str(json.dumps(  # store cache
                    list(self.__mapped.items())))
            else:  # no cache files? we can delete cache directory
                rmtree(self.__cache_dir, ignore_errors=True, onerror=None)

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

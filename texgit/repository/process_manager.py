"""
A class for managing files and directories.

A file manager provides a two-level abstraction for assigning names to paths.
It exists within a certain base directory.
Inside the base directory, it provides so-called "realms".
Each realm is a separate namespace.
With a realm, "names" are mapped to paths.
The file manager ensures that the same realm-name combination is always
assigned to the same path.
The first time it is queried, the path is created.
This path can be a file or a directory, depending on what was queried.
Every realm-name combination always uniquely identifies a path and there can
never be another realm-name combination pointing to the same path.
The paths are randomized to avoid potential clashes.

Once the file manager is closed, the realm-name to path associations are
stored.
When a new file manager instance is created for the same base directory, the
associations of realms-names to paths are restored.
This means that a program that creates output files for certain commands can
then find these files again later.
"""
from os import environ
from os.path import getsize
from typing import Final, Iterable, Mapping

from pycommons.ds.immutable_map import immutable_mapping
from pycommons.io.console import logger
from pycommons.io.path import Path, write_lines
from pycommons.processes.python import PYTHON_ENV, PYTHON_INTERPRETER
from pycommons.processes.shell import STREAM_CAPTURE, Command
from pycommons.types import type_error

from texgit.repository.fix_path import replace_base_path
from texgit.repository.git_manager import GitManager, GitPath


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


def __get_sys_env() -> Mapping[str, str]:
    """
    Get the system environment variables in the current environment.

    :return: A mapping of variable names to values.
    """
    base: dict[str, str] = dict(environ)
    base.update(PYTHON_ENV)
    return immutable_mapping(base)


#: the environment that we will pass on
SYS_ENV: Final[Mapping[str, str]] = __get_sys_env()
del __get_sys_env


class ProcessManager(GitManager):
    """A manager for processes."""

    def get_argument_file(self, name: str, prefix: str | None = None,
                          suffix: str | None = None) -> tuple[Path, bool]:
        """
        Create a file in the argument realm.

        :param name: the ID for the file
        :param prefix: the optional prefix
        :param suffix: the optional suffix
        :return: the file, plus a `bool` indicating whether it was just
            created (`True`) or already existed (`False`)
        """
        return self.get_file(
            "args", name, (str.strip(prefix) or None) if prefix else None,
            (str.strip(suffix) or None) if suffix else None)

    def filter_argument(self, arg: str) -> str | None:
        """
        Filter an argument to be passed to any given file.

        This function can be used to rewire arguments of certain programs that
        we want to invoke to specific files.

        :param arg: the argument
        :return: the filtered argument
        """
        arg = str.strip(arg)
        if arg:
            if arg.startswith("(?") and arg.endswith("?)"):
                name: Final[str] = str.strip(arg[2:-2])
                if str.__len__(name) <= 0:
                    raise ValueError(f"Invalid ID in {arg!r}.")
                return self.get_argument_file(name)[0]
            return arg
        return None

    def __execute(self, dest: Path,
                  command: str | Iterable[str],
                  working_dir: Path | None = None,
                  stdin: str | None = None) -> None:
        """
        Make a command and environment.

        :param dest: the destination path
        :param command: the command
        :param working_dir: an optional working directory
        :param stdin: the standard input for the program, or `None`
        """
        # process the command
        cmd_lst: Final[list[str]] = [command] if isinstance(command, str)\
            else list(command)
        for i in range(list.__len__(cmd_lst) - 1, -1, -1):
            cmd: str = str.strip(cmd_lst[i])
            if str.__len__(cmd) <= 0:
                del cmd_lst[i]
                continue

        # process the arguments
        for i in range(list.__len__(cmd_lst) - 1, 0, -1):
            cmd = self.filter_argument(cmd_lst[i])
            if cmd is None:
                del cmd_lst[i]
                continue
            cmd_lst[i] = cmd

        if list.__len__(cmd_lst) <= 0:
            raise ValueError(f"Invalid command {command!r}.")

        # Now we need to fix the command if we are running inside a virtual
        # environment. If we are running inside a virtual environment, it is
        # necessary to use the same Python interpreter that was used to run
        # texgit. We should also pass along all the Python-related
        # environment parameters.
        env: Mapping[str, str] = SYS_ENV
        if str.lower(cmd_lst[0]).startswith("python3"):
            cmd_lst[0] = PYTHON_INTERPRETER
            env = PYTHON_ENV

        # execute the command and capture the output
        output: str = Command(
            command=cmd_lst, working_dir=working_dir, env=env,
            stdout=STREAM_CAPTURE, stdin=stdin).execute(True)[0]

        replace: list[Path] = self._get_sensitive_paths()
        replace.append(dest)
        replace.sort(key=str.__len__, reverse=True)
        for base_dir in replace:  # fix the base path
            output = replace_base_path(output, base_dir)
        _write(output, dest)

    def get_output(
            self, name: str, command: str | Iterable[str],
            repo_url: str | None = None,
            relative_dir: str | None = None) -> Path:
        """
        Get the output of a certain command.

        :param name: the name for the output
        :param command: the command itself
        :param repo_url: the optional repository URL
        :param relative_dir: the optional directory inside the repository
            where the command should be executed
        :return: the path to the output and, if `repo_url` and `relative_dir`
            were not `None`, then a URL pointing to the directory in the
            repository, else `None`
        """
        self._check_open()
        path, is_new = self.get_file("output", name)
        if not is_new:
            return path

        if isinstance(repo_url, str):
            repo_url = str.strip(repo_url) or None
        elif repo_url is not None:
            raise type_error(repo_url, "repo_url", (str, None))

        if isinstance(relative_dir, str):
            relative_dir = str.strip(relative_dir) or None
        elif relative_dir is not None:
            raise type_error(relative_dir, "relative_dir", (str, None))
        if (repo_url is None) != (relative_dir is None):
            raise ValueError(f"repo_url and relative_dir must either both be "
                             f"None or neither, but they are {repo_url!r} "
                             f"and {relative_dir!r}.")
        working_dir: Path | None = None
        if repo_url is not None:
            working_dir = self.get_git_dir(repo_url, relative_dir).path

        self.__execute(dest=path, command=command, working_dir=working_dir)
        return path

    def get_git_file(
            self, repo_url: str, relative_file: str,
            name: str | None = None,
            command: str | Iterable[str] | None = None) -> GitPath:
        """
        Get a path to a postprocessed file from the given git repository.

        :param repo_url: the repository url.
        :param relative_file: the relative path to the file
        :param name: the name for the output
        :param command: the command itself
        :return: a tuple of file and URL
        """
        gf: Final[GitPath] = super().get_git_file(repo_url, relative_file)
        if command:
            name = str.strip(name)
            path, is_new = self.get_file("postprocessed", name)
            if is_new:
                self.__execute(dest=path, command=command,
                               stdin=gf.path.read_all_str())
        else:
            path = gf.path
        return GitPath(path, gf.repo, gf.repo.make_url(gf.path), gf.basename)

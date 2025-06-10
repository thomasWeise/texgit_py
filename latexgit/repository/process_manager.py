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
from typing import Final

from pycommons.io.path import Path

from latexgit.repository.git_manager import GitManager


class ProcessManager(GitManager):
    """A manager for files."""

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
            if arg.startswith("(:") and arg.endswith(":)"):
                args: Final[list[str]] = arg[2:-2].split(":")
                argc: Final[int] = list.__len__(args)
                if not (0 < argc < 4):
                    raise ValueError(f"Invalid argument {arg!r}.")
                name: Final[str] = str.strip(args[0])
                if str.__len__(name) <= 0:
                    raise ValueError(f"Invalid ID in {arg!r}.")
                return self.get_argument_file(
                    name, args[1] if argc > 1 else None,
                    args[2] if argc > 2 else None)[0]
            return arg
        return None

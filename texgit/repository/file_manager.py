"""
A class for managing files and directories.

A :class:`~texgit.repository.file_manager.FileManager` provides a two-level
abstraction for assigning paths to unique IDs.
An ID is a combination of a "realm" and a "name", both of which are non-empty
strings without whitespace.

A file manager resides within a certain base directory.
Inside the base directory, it provides so-called "realms".
Each realm is a separate namespace.
With a realm, "names" are mapped to paths.
The file manager ensures that the same realm-name combination is always
assigned to the same path.
The first time such a combination is queried, the path is created.
This path can be a file or a directory, depending on what was queried.
Every realm-name combination always uniquely identifies a path and there can
never be another realm-name combination pointing to the same path.
If need be, the paths are randomized to avoid potential clashes.

Once the file manager is closed, the realm-name to path associations are
stored.
When a new file manager instance is created for the same base directory, the
associations of realms-names to paths are restored.
This means that a program that creates output files for certain commands can
then find these files again later.

:class:`~texgit.repository.git_manager.GitManager` is the base and root of
the functionality of a managed repository of files and data.
Step-by-step, functionality is added to the manager by derived classes.
We do this iteratively:

:class:`~texgit.repository.git_manager.GitManager` adds the capability to
automatically download and use `git` repositories. For this purpose, it uses
the realm `git`.

:class:`~texgit.repository.process_manager.ProcessManager` adds the ability
to execute programs or scripts and to store their output in files to the
:class:`~texgit.repository.git_manager.GitManager`.
These programs and scripts may be located in `git` repositories that have
automatically been downloaded.
"""
import json
from contextlib import AbstractContextManager, suppress
from os import close as os_close
from os import remove as os_remove
from tempfile import mkstemp
from typing import Callable, Final

from pycommons.io.path import Path

__OK_CHARS: Final[str] = ("abcdefghijklmnopqrstuvwxyz"
                          "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                          "0123456789+-_")

#: the characters that are OK for a file name
_FILENAME_OK: Callable[[str], bool] = set(__OK_CHARS).__contains__

#: characters allowed in a key
__KEY_ALLOWED: Callable[[str], bool] = (
    set(__OK_CHARS).union(":.@/").__contains__)


def _make_key(s: str) -> str:
    """
    Create a compliant key.

    :param s: the string
    :return: the key
    """
    s = str.strip(s)
    if str.__len__(s) <= 0:
        raise ValueError("Non-empty str expected, but got empty string "
                         "or string of only white space.")
    if not all(map(__KEY_ALLOWED, s)):
        raise ValueError("String contains forbidden character.")
    return s


def _make_ignore(path: Path) -> None:
    """
    Create a `.gitignore` file in the given path.

    :param path: the path
    """
    file: Path = path.resolve_inside(".gitignore")
    if not file.exists():
        file.write_all_str("*\n**/*")
    file = path.resolve_inside(".nojekyll")
    if not file.exists():
        file.ensure_file_exists()


class FileManager(AbstractContextManager):
    """A manager for files."""

    def __init__(self, base_dir: str) -> None:
        """
        Set up the git repository manager.

        :param base_dir: the base directory
        """
        #: the base directory of the repository manager
        self.__base_dir: Final[Path] = Path(base_dir)
        self.__base_dir.ensure_dir_exists()
        _make_ignore(self.__base_dir)

        #: the directory with the realms
        self.__realms_dir: Final[Path] = self.__base_dir.resolve_inside(
            "realms")
        self.__realms_dir.ensure_dir_exists()
        _make_ignore(self.__realms_dir)

        #: the internal cache file
        self.__cache_file: Final[Path] = self.__base_dir.resolve_inside(
            ".cache.json")
        #: we are open
        self.__is_open = True

        #: the dictionary of realms and IDs
        self.__map: Final[dict[str, tuple[Path, dict[str, Path]]]] = {}

        #: load the cache
        if self.__cache_file.exists():
            self.__cache_file.enforce_file()
            for key, values in json.loads(
                    self.__cache_file.read_all_str()).items():
                realm = _make_key(key)
                realm_dir = self.__realms_dir.resolve_inside(realm)
                realm_map = {}
                for name, path in values.items():
                    use_name = _make_key(name)
                    use_path = realm_dir.resolve_inside(path)
                    if use_path.exists() and (
                            use_path.is_file() or use_path.is_dir()):
                        realm_map[use_name] = use_path
                if dict.__len__(realm_map) > 0:
                    self.__map[realm] = (realm_dir, realm_map)

    def _check_open(self) -> None:
        """Enforce that the file manager is open."""
        if not self.__is_open:
            raise ValueError("Already closed!")

    def _get_sensitive_paths(self) -> list[Path]:
        """
        Get the list of sensitive paths.

        :return: the list of sensitive paths
        """
        paths: Final[list[Path]] = [
            self.__base_dir, self.__realms_dir, self.__cache_file]
        paths.extend(map(self.__realms_dir.resolve_inside, self.__map.keys()))
        return paths

    def __get(self, realm: str, name: str,
              is_file: bool,
              prefix: str | None = None,
              suffix: str | None = None) -> tuple[Path, bool]:
        """
        Get a file or directory with the given ID in the specified realm.

        :param realm: the realm
        :param name: the id for the file
        :param is_file: is it a file?
        :param prefix: the optional prefix
        :param suffix: the optional suffix
        :return: the generated path and `True` if it was new,
            or `False` if not.
        """
        self._check_open()
        realm = _make_key(realm)
        name = _make_key(name)
        if prefix is not None:
            prefix = _make_key(prefix)
        if suffix is not None:
            suffix = _make_key(suffix)

        if realm in self.__map:
            realm_dir, realm_map = self.__map[realm]
        else:
            realm_dir = self.__realms_dir.resolve_inside(realm)
            realm_dir.ensure_dir_exists()
            _make_ignore(realm_dir)
            realm_map = {}
            self.__map[realm] = realm_dir, realm_map

        result: Path | None = None
        is_new: bool = False
        if name in realm_map:
            result = realm_map[name]
        else:
            is_new = True
            rootname = prefix or "".join(filter(_FILENAME_OK, name))
            usename = rootname
            if suffix:
                usename = f"{usename}{suffix}"

            if usename:
                test = realm_dir.resolve_inside(usename)
                if not test.exists():
                    if is_file:
                        if not test.ensure_file_exists():
                            result = test
                    else:
                        test.ensure_dir_exists()
                        result = test

            if result is None:
                (handle, fpath) = mkstemp(prefix=rootname or None,
                                          suffix=suffix, dir=realm_dir)
                os_close(handle)
                result = Path(fpath)
                if not is_file:
                    with suppress(FileNotFoundError):
                        os_remove(result)
                    result.ensure_dir_exists()
            realm_map[name] = result

        if is_file:
            result.enforce_file()
        else:
            result.enforce_dir()

        bn: Final[str] = result.basename()
        if prefix and (not bn.startswith(prefix)):
            raise ValueError(f"prefix={prefix!r} but f={result!r}.")
        if suffix and (not bn.endswith(suffix)):
            raise ValueError(f"suffix={suffix!r} but f={result!r}.")
        return result, is_new

    def list_realm(self, realm: str, files: bool = True,
                   directories: bool = True) -> tuple[Path, ...]:
        """
        List all the files and directories in a given realm.

        :param realm: the realm that we want to list
        :param files: should we list files?
        :param directories: should we list directories?
        :return: the iterator with the data
        """
        realm = _make_key(realm)
        if realm in self.__map:
            _, realm_map = self.__map[_make_key(realm)]
            return tuple(filter(lambda v: (files and v.is_file()) or (
                directories and v.is_dir()), realm_map.values()))
        return ()

    def get_dir(self, realm: str, name: str) -> tuple[Path, bool]:
        """
        Get a directory representing the given name in the given realm.

        :param realm: the realm
        :param name: the name or ID that the directory should represent
        :return: the directory path and a `bool` indicating whether it was
            newly generated (`True`) or not if it already existed (`False`)
        """
        return self.__get(realm, name, False)

    def get_file(self, realm: str, name: str,
                 prefix: str | None = None,
                 suffix: str | None = None) -> tuple[Path, bool]:
        """
        Get a file representing the given name in the given realm.

        :param realm: the realm
        :param name: the name or ID that the file should represent
        :param prefix: the optional prefix
        :param suffix: the optional suffix
        :return: the generated file path and `True` if it was new, or
            `False` if not.
        """
        return self.__get(realm, name, True, prefix, suffix)

    def close(self) -> None:
        """Close the file manager and write cache list."""
        opn: bool = self.__is_open
        self.__is_open = False
        if opn:  # only if we were open...
            # flush or clear directory of cached post-processed files
            with suppress(FileNotFoundError):
                os_remove(self.__cache_file)
            if len(self.__map) > 0:  # we got cached files
                self.__cache_file.write_all_str(json.dumps(  # store cache
                    {realm: {
                        name: path.relative_to(rv[0])
                        for name, path in rv[1].items()
                    } for realm, rv in self.__map.items()}))

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

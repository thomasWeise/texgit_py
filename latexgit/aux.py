"""Process a LaTeX aux file."""
import argparse
from os.path import dirname, getsize
from typing import Final

from latexgit.repository.processed import Processed
from latexgit.utils.console import logger
from latexgit.utils.help import argparser
from latexgit.utils.path import Path
from latexgit.utils.types import type_error


def __int_to_alpha(index: int) -> str:
    """
    Convert an integer to a alphabetic sequence.

    :param index: the index
    :returns: the sequence

    >>> __int_to_alpha(0)
    'a'
    >>> __int_to_alpha(1)
    'b'
    >>> __int_to_alpha(25)
    'z'
    >>> __int_to_alpha(26)
    'aa'
    >>> __int_to_alpha(27)
    'ab'
    >>> __int_to_alpha(51)
    'az'
    >>> __int_to_alpha(52)
    'ba'
    >>> __int_to_alpha(26 * 27 - 1)
    'zz'
    >>> __int_to_alpha(26 * 27)
    'aaa'
    >>> __int_to_alpha(26 * 27 + 1)
    'aab'
    >>> __int_to_alpha(26 * 27 + 25)
    'aaz'
    >>> __int_to_alpha(26 * 27 + 26)
    'aba'
    >>> __int_to_alpha(26 * 26 * 27 + 26 - 1)
    'zzz'
    >>> __int_to_alpha(26 * 26 * 27 + 26)
    'aaaa'
    >>> __int_to_alpha(26 * 26 * 27 + 26 + 26)
    'aaba'
    >>> __int_to_alpha(26 * 26 * 27 + 26 + 26 * 26)
    'abaa'
    """
    chars: list[int] = []
    while True:
        chars.append(97 + (index % 26))
        index = (index // 26) - 1
        if index < 0:
            break
    chars.reverse()
    return "".join(map(chr, chars))


#: the request header
REQUEST: Final[str] = r"\@latexgit@gitFile"


def __get_request(line: str) \
        -> tuple[str, str, tuple[str, ...] | None] | None:
    r"""
    Get the repository request, if any.

    :param line: the line
    :return: the request, or `None` if none found.

    >>> print(__get_request(""))
    None
    >>> print(__get_request(r"\@latexgit@gitFile{x}{y}{}"))
    ('x', 'y', None)
    >>> print(__get_request(r"\@latexgit@gitFile{x}{y}{a}"))
    ('x', 'y', ('a',))
    >>> print(__get_request(r"\@latexgit@gitFile{x}{y}{a b}"))
    ('x', 'y', ('a', 'b'))
    >>> print(__get_request(r"\@latexgit@gitFile{x}{y}{a\ b}"))
    ('x', 'y', ('a b',))
    >>> print(__get_request(r"\@latexgit@gitFile{x{{y}{y}{a\ b}"))
    ('x{y', 'y', ('a b',))
    >>> print(__get_request(r"\@latexgit@gitFile{x\{y}{y}{a\ b}"))
    ('x{y', 'y', ('a b',))
    >>> print(__get_request(r"\@latexgit@gitFile{x\{y}{}}y}{a\ b}"))
    ('x{y', '}y', ('a b',))
    >>> print(__get_request(r"\@latexgit@gitFile{x\{y}{}}y}{a\ \\b}"))
    ('x{y', '}y', ('a \\b',))
    >>> print(__get_request(r"\@latexgit@gitFile {x\{y}{}}y}{a\ \\b}"))
    ('x{y', '}y', ('a \\b',))
    >>> print(__get_request(r" \@latexgit@gitFile { x\{y}{ }}y }{ a\ \\b } "))
    ('x{y', '}y', ('a \\b',))
    """
    if not isinstance(line, str):
        raise type_error(line, "line", str)
    if len(line) >= 67108864:
        raise ValueError(f"line is {len(line)} characters long?")
    line = line.strip()
    if not line.startswith(REQUEST):
        return None
    line = line[len(REQUEST):].lstrip()
    if (len(line) <= 0) or (line[0] != "{"):
        return None

    # find markers for search-replacing problematic chars
    markers: list[str] = []
    marker: int = 0
    strset: Final[set[str]] = set(line)
    if len(strset) > 1048576:
        raise ValueError(f"{len(strset)} different characters in line?")
    while len(markers) <= 4:
        cmarker: str = chr(marker)
        if cmarker in strset:
            continue
        markers.append(cmarker)
        marker += 1
    del strset
    del cmarker
    del marker

    # replace problematic chars with markers
    line = (line.replace("\\\\", markers[0])
            .replace(r"\{", markers[1])
            .replace("{{", markers[1])
            .replace(r"\}", markers[2])
            .replace("}}", markers[2])
            .replace(r"\ ", markers[3]))

    # find the split positions, exit if they do not exist
    idx_1: Final[int] = line.find("}", 1)
    if idx_1 <= 1:
        return None
    idx_2: Final[int] = line.find("{", idx_1)
    if idx_2 <= idx_1:
        return None
    idx_3: Final[int] = line.find("}", idx_2)
    if idx_3 <= idx_2:
        return None
    idx_4: Final[int] = line.find("{", idx_3)
    if idx_4 <= idx_3:
        return None
    idx_5: Final[int] = line.find("}", idx_4)
    if idx_5 <= idx_4:
        return None

    # extract repository and path information
    repository: Final[str] = line[1:idx_1].replace(markers[0], "\\").replace(
        markers[1], "{").replace(markers[2], "}").replace(
        markers[3], " ").strip()
    if len(repository) <= 0:
        return None
    path: Final[str] = line[idx_2 + 1:idx_3].replace(markers[0], "\\").replace(
        markers[1], "{").replace(markers[2], "}").replace(
        markers[3], " ").strip()
    if len(path) <= 0:
        return None

    # process post information while protecting protected spaces
    post: Final[str] = line[idx_4 + 1:idx_5].replace(markers[0], "\\").replace(
        markers[1], "{").replace(markers[2], "}").strip()
    if len(post) <= 0:
        return repository, path, None

    return repository, path, tuple(t for t in (
        s.replace(markers[3], " ").strip()
        for s in post.split()) if len(t) > 0)


#: the response header
RESPONSE: Final[str] = r"\@latexgit@path"


def __make_path(base_dir: Path, file: Path, index: int) -> str:
    r"""
    Make a path entry command.

    :param base_dir: the base directory
    :param file: the file path
    :param index: the file index
    :return: the `latexgit` compliant path command

    >>> from os.path import dirname
    >>> import latexgit.aux as aa
    >>> fle = Path.file(aa.__file__)
    >>> bd = Path.directory(dirname(dirname(fle)))
    >>> __make_path(bd, fle, 3)
    '\\xdef\\@latexgit@pathd{latexgit/aux.py}%'
    >>> __make_path(bd, fle, 0)
    '\\xdef\\@latexgit@patha{latexgit/aux.py}%'
    """
    base_dir.enforce_dir()
    file.enforce_file()
    return (f"\\xdef{RESPONSE}{__int_to_alpha(index)}{{"
            f"{file.relative_to(base_dir)}}}%")


def run(aux_arg: str, repo_dir_arg: str = "__git__") -> None:
    """
    Execute the `latexgit` tool.

    This tool loads an LaTeX `aux` file, processes all file loading requests,
    and flushes the produced file paths back to the `aux` file.

    :param aux_arg: the `aux` file argument
    :param repo_dir_arg: the repository directory argument
    """
    aux_file: Path = Path.path(aux_arg)
    if not aux_file.is_file():
        aux_file = Path.path(f"{aux_arg}.aux")
    if not aux_file.is_file():
        raise ValueError(f"aux argument {aux_arg!r} does not identify a file "
                         f"and neither does {aux_file!r}")
    logger(f"Using aux file {aux_file!r}.")

    if getsize(aux_file) <= 0:
        logger(f"aux file {aux_file!r} is empty. Nothing to do. Exiting.")
        return
    lines: Final[list[str]] = aux_file.read_all_list()
    lenlines: Final[int] = len(lines)
    if lenlines <= 0:
        logger(f"aux file {aux_file!r} contains no lines. "
               "Nothing to do. Exiting.")
    else:
        logger(f"Loaded {lenlines} lines from aux file {aux_file!r}.")

    base_dir: Final[Path] = Path.directory(dirname(aux_file))
    logger(f"The base directory is {base_dir!r}.")

    proc: Processed | None = None
    append: list[str] = []

    try:
        for line in lines:
            command: tuple[str, str, tuple[str, ...] | None] | None = (
                __get_request(line))
            if command is None:
                continue

            if proc is None:
                git_dir: Path = base_dir.resolve_inside(repo_dir_arg)
                logger(f"The repository directory is {git_dir!r}.")
                proc = Processed(git_dir)

            append.append(__make_path(base_dir, proc.get_file(
                *command), len(append)))
    finally:
        if proc is not None:
            proc.close()
            del proc

    if len(append) <= 0:
        logger("No file requests found. Nothing to do.")

    logger(f"Found and resolved {len(append)} file requests.")
    lines.extend(append)
    aux_file.write_all(lines)
    logger(f"Finished flushing {len(lines)} lines to aux file {aux_file!r}.")


# Execute the latexgit tool
if __name__ == "__main__":
    parser: Final[argparse.ArgumentParser] = argparser(
        __file__, "Execute the latexgit Tool.",
        "Download and provide local paths for files from git repositories.")
    parser.add_argument(
        "aux", help="the aux file to process", type=str, default="")
    parser.add_argument(
        "--repoDir", help="the directory to use for downloads",
        type=str, default="__git__", nargs="?")
    args: Final[argparse.Namespace] = parser.parse_args()

    run(args.aux.strip(), args.repoDir.strip())
    logger("All done.")

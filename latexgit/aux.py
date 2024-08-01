"""Process a LaTeX aux file."""
import argparse
from os.path import dirname, getsize
from typing import Final

from pycommons.io.arguments import make_argparser, make_epilog
from pycommons.io.console import logger
from pycommons.io.path import Path, directory_path, write_lines
from pycommons.net.url import URL
from pycommons.types import type_error

from latexgit.repository.processed import Processed
from latexgit.version import __version__


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


#: the header for git file requests
REQUEST_FILE: Final[str] = r"\@latexgit@gitFile"
#: the header for process result requests
REQUEST_PROCESS: Final[str] = r"\@latexgit@process"


def __get_request(line: str) -> tuple[
        str, str | None, str | None, tuple[str, ...] | None] | None:
    r"""
    Get the repository request, if any.

    :param line: the line
    :return: the request, composed of the request function, the repository
        (if any), the path (if any), and the optional command; or `None` if
        no request was found.

    >>> print(__get_request(""))
    None
    >>> print(__get_request(r"\hello"))
    None
    >>> print(__get_request(r"\@latexgit@gitFile{x}{y}{}"))
    ('\\@latexgit@gitFile', 'x', 'y', None)
    >>> print(__get_request(r"\@latexgit@process{x}{y}{python3 --version}"))
    ('\\@latexgit@process', 'x', 'y', ('python3', '--version'))
    >>> print(__get_request(r"\@latexgit@gitFile{x}{y}{a}"))
    ('\\@latexgit@gitFile', 'x', 'y', ('a',))
    >>> print(__get_request(r"\@latexgit@gitFile{x}{y}{a b}"))
    ('\\@latexgit@gitFile', 'x', 'y', ('a', 'b'))
    >>> print(__get_request(r"\@latexgit@gitFile{x}{y}{a\ b}"))
    ('\\@latexgit@gitFile', 'x', 'y', ('a b',))
    >>> print(__get_request(r"\@latexgit@gitFile{x{{y}{y}{a\ b}"))
    ('\\@latexgit@gitFile', 'x{y', 'y', ('a b',))
    >>> print(__get_request(r"\@latexgit@gitFile{x\{y}{y}{a\ b}"))
    ('\\@latexgit@gitFile', 'x{y', 'y', ('a b',))
    >>> print(__get_request(r"\@latexgit@gitFile{x\{y}{}}y}{a\ b}"))
    ('\\@latexgit@gitFile', 'x{y', '}y', ('a b',))
    >>> print(__get_request(r"\@latexgit@gitFile{x\{y}{}}y}{a\ \\b}"))
    ('\\@latexgit@gitFile', 'x{y', '}y', ('a \\b',))
    >>> print(__get_request(r"\@latexgit@gitFile {x\{y}{}}y}{a\ \\b}"))
    ('\\@latexgit@gitFile', 'x{y', '}y', ('a \\b',))
    >>> print(__get_request(
    ...     r" \@latexgit@gitFile { x\{y}{ }}y }{ a\ \\b } "))
    ('\\@latexgit@gitFile', 'x{y', '}y', ('a \\b',))
    """
    if not isinstance(line, str):
        raise type_error(line, "line", str)
    if str.__len__(line) >= 67108864:
        raise ValueError(f"line is {len(line)} characters long?")
    line = str.strip(line)

    request: Final[str | None] = REQUEST_FILE if str.startswith(
        line, REQUEST_FILE) else (REQUEST_PROCESS if str.startswith(
            line, REQUEST_PROCESS) else None)
    if request is None:
        return None
    line = line[str.__len__(request):].lstrip()
    if (str.__len__(line) <= 0) or (line[0] != "{"):
        raise ValueError(f"rest line={line!r} for {request!r}.")

    # find markers for search-replacing problematic chars
    strset: Final[set[str]] = set(line)
    if set.__len__(strset) > 1048576:
        raise ValueError(
            f"{set.__len__(strset)} different characters "
            f"in line for {request!r}?")
    markers: list[str] = []
    marker: int = 33
    while list.__len__(markers) <= 4:
        cmarker: str = chr(marker)
        if cmarker in strset:
            continue
        markers.append(cmarker)
        strset.add(cmarker)
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
    if idx_1 < 1:
        raise ValueError(f"{request!r}/{line!r}: missing 1 }}")
    idx_2: Final[int] = line.find("{", idx_1)
    if idx_2 <= idx_1:
        raise ValueError(f"{request!r}/{line!r}: missing 1 {{")
    idx_3: Final[int] = line.find("}", idx_2)
    if idx_3 <= idx_2:
        raise ValueError(f"{request!r}/{line!r}: missing 2 }}")
    idx_4: Final[int] = line.find("{", idx_3)
    if idx_4 <= idx_3:
        raise ValueError(f"{request!r}/{line!r}: missing 2 {{")
    idx_5: Final[int] = line.find("}", idx_4)
    if idx_5 <= idx_4:
        raise ValueError(f"{request!r}/{line!r}: missing 3 }}")

    # extract repository and path information
    repository: str | None = line[1:idx_1].replace(markers[0], "\\").replace(
        markers[1], "{").replace(markers[2], "}").replace(
        markers[3], " ").strip()
    if str.__len__(repository) <= 0:
        if request is REQUEST_FILE:
            raise ValueError(f"repository cannot be empty for {request!r}.")
        repository = None
    path: str | None = line[idx_2 + 1:idx_3].replace(
        markers[0], "\\").replace(markers[1], "{").replace(
        markers[2], "}").replace(markers[3], " ").strip()
    if str.__len__(path) <= 0:
        if request is REQUEST_FILE:
            raise ValueError(f"path cannot be empty for {request!r}.")
        path = None
    if (path is None) != (repository is None):
        raise ValueError(
            f"path={path!r} not permitted if repository={repository!r}.")

    # process post information while protecting protected spaces
    post: Final[str] = line[idx_4 + 1:idx_5].replace(markers[0], "\\").replace(
        markers[1], "{").replace(markers[2], "}").strip()

    command: Final[tuple[str, ...] | None] = None if (
        str.__len__(post) <= 0) else tuple(t for t in (
            s.replace(markers[3], " ").strip()
            for s in post.split()) if len(t) > 0)
    if (command is None) and (request is REQUEST_PROCESS):
        raise ValueError(f"command cannot be empty for {request!r}.")
    return request, repository, path, command


#: the response header for the path
RESPONSE_PATH: Final[str] = r"\@latexgit@path"
#: the response header for the url
RESPONSE_URL: Final[str] = r"\@latexgit@url"


def __make_response(
        base_dir: Path, file_and_url: tuple[Path, str | None], index: int) \
        -> tuple[str, str]:
    r"""
    Make a path entry command.

    :param base_dir: the base directory
    :param file_and_url: the file path and the url
    :param index: the file index
    :return: the `latexgit` compliant path command

    >>> from os.path import dirname
    >>> import latexgit.aux as aa
    >>> from pycommons.io.path import file_path
    >>> fle = file_path(aa.__file__)
    >>> bd = directory_path(dirname(dirname(fle)))
    >>> x = __make_response(bd, (fle, 'https://example.com'), 3)
    >>> x[0]
    '\\xdef\\@latexgit@pathd{latexgit/aux.py}%'
    >>> x[1]
    '\\xdef\\@latexgit@urld{https://example.com}%'
    >>> x = __make_response(bd, (fle, 'https://example.com#3_4'), 0)
    >>> x[0]
    '\\xdef\\@latexgit@patha{latexgit/aux.py}%'
    >>> x[1]
    '\\xdef\\@latexgit@urla{https://example.com\\#3_4}%'
    """
    base_dir.enforce_dir()
    suffix: Final[str] = __int_to_alpha(index)
    file: Final[Path] = file_and_url[0]
    url: Final[str] = "" if file_and_url[1] is None \
        else file_and_url[1].replace("#", r"\#")
    file.enforce_file()
    return ((f"\\xdef{RESPONSE_PATH}{suffix}{{"
            f"{file.relative_to(base_dir)}}}%"),
            f"\\xdef{RESPONSE_URL}{suffix}{{{url}}}%")


def run(aux_arg: str, repo_dir_arg: str = "__git__") -> None:
    """
    Execute the `latexgit` tool.

    This tool loads an LaTeX `aux` file, processes all file loading requests,
    and flushes the produced file paths back to the `aux` file.

    :param aux_arg: the `aux` file argument
    :param repo_dir_arg: the repository directory argument
    """
    aux_file: Path = Path(aux_arg)
    if not aux_file.is_file():
        aux_file = Path(f"{aux_arg}.aux")
    if not aux_file.is_file():
        raise ValueError(f"aux argument {aux_arg!r} does not identify a file "
                         f"and neither does {aux_file!r}")
    logger(f"Using aux file {aux_file!r}.")

    if getsize(aux_file) <= 0:
        logger(f"aux file {aux_file!r} is empty. Nothing to do. Exiting.")
        return
    lines: Final[list[str]] = list(aux_file.open_for_read())
    lenlines: Final[int] = len(lines)
    if lenlines <= 0:
        logger(f"aux file {aux_file!r} contains no lines. "
               "Nothing to do. Exiting.")
    else:
        logger(f"Loaded {lenlines} lines from aux file {aux_file!r}.")

    base_dir: Final[Path] = directory_path(dirname(aux_file))
    logger(f"The base directory is {base_dir!r}.")

    proc: Processed | None = None
    append: list[str] = []

    try:
        resolved: int = 0
        for line in lines:
            request: tuple[str, str | None, str | None, tuple[str,
                           ...] | None] | None = __get_request(line)
            if request is None:
                continue

            func: str = request[0]
            repo: str | None = request[1]
            path: str | None = request[2]
            command: tuple[str, ...] | None = request[3]

            if proc is None:
                git_dir: Path = base_dir.resolve_inside(repo_dir_arg)
                logger(f"The repository directory is {git_dir!r}.")
                proc = Processed(git_dir)

            file_and_url: tuple[Path, URL | None] | None
            if func is REQUEST_FILE:
                file_and_url = proc.get_file_and_url(
                    repo_url=repo, relative_path=path, processor=command)
            elif func is REQUEST_PROCESS:
                file_and_url = proc.get_output(
                    command=command, repo_url=repo, relative_dir=path)
            else:
                raise ValueError(f"Invalid request: {func!r}, {repo!r}, "
                                 f"{path!r}, {command!r}.")
            append.extend(__make_response(base_dir, file_and_url, resolved))
            resolved += 1
    finally:
        if proc is not None:
            proc.close()
            del proc

    if len(append) <= 0:
        logger("No file requests found. Nothing to do.")

    logger(f"Found and resolved {resolved} file requests.")
    lines.extend(append)
    with aux_file.open_for_write() as wd:
        write_lines(map(str.rstrip, lines), wd)
    logger(f"Finished flushing {len(lines)} lines to aux file {aux_file!r}.")


# Execute the latexgit tool
if __name__ == "__main__":
    parser: Final[argparse.ArgumentParser] = make_argparser(
        __file__, "Execute the latexgit Tool.",
        make_epilog(
            "Download and provide local paths for "
            "files from git repositories.",
            2023, None, "Thomas Weise",
            url="https://thomasweise.github.io/latexgit_py",
            email="tweise@hfuu.edu.cn, tweise@ustc.edu.cn"),
        __version__)
    parser.add_argument(
        "aux", help="the aux file to process", type=str, default="")
    parser.add_argument(
        "--repoDir", help="the directory to use for downloads",
        type=str, default="__git__", nargs="?")
    args: Final[argparse.Namespace] = parser.parse_args()

    run(args.aux.strip(), args.repoDir.strip())
    logger("All done.")

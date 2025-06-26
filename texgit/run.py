"""Process a LaTeX aux file."""
import argparse
from os.path import dirname, getsize
from typing import Final, Generator

from pycommons.io.arguments import make_argparser, make_epilog
from pycommons.io.console import logger
from pycommons.io.path import Path, directory_path, write_lines
from pycommons.strings.string_tools import escape, unescape

from texgit.repository.git_manager import GitPath
from texgit.repository.process_manager import ProcessManager
from texgit.version import __version__

#: the header for git file requests
REQUEST_GIT_FILE: Final[str] = r"\@texgit@gitFile"
#: the header for argument file requests
REQUEST_ARG_FILE: Final[str] = r"\@texgit@argFile"
#: the header for process result requests
REQUEST_PROCESS: Final[str] = r"\@texgit@process"
#: the forbidden line marker that needs to be purged
FORBIDDEN_LINE: Final[str] = r"\@texgit@needsTexgitPass"

#: the replacements
__REPL: Final[dict[str, str]] = {
    r"\\": "\\", r"\{": "{", "{{": "{", r"\}": "}", "}}": "}", r"\ ": " ",
}


def __get_request(line: str) -> list[str | None] | None:
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
    >>> print(__get_request(r"\@texgit@gitFile{x}{y}{}"))
    ['\\@texgit@gitFile', 'x', 'y', None]
    >>> print(__get_request(r"\@texgit@process{x}{y}{python3 --version}"))
    ['\\@texgit@process', 'x', 'y', 'python3', '--version']
    >>> print(__get_request(r"\@texgit@gitFile{x}{y}{a}"))
    ['\\@texgit@gitFile', 'x', 'y', 'a']
    >>> print(__get_request(r"\@texgit@gitFile{x}{y}{a b}"))
    ['\\@texgit@gitFile', 'x', 'y', 'a', 'b']
    >>> print(__get_request(r"\@texgit@gitFile{x}{y}{a\ b}"))
    ['\\@texgit@gitFile', 'x', 'y', 'a b']
    >>> print(__get_request(r"\@texgit@gitFile{x{{y}{y}{a\ b}"))
    ['\\@texgit@gitFile', 'x{y', 'y', 'a b']
    >>> print(__get_request(r"\@texgit@gitFile{x\{y}{y}{a\ b}"))
    ['\\@texgit@gitFile', 'x{y', 'y', 'a b']
    >>> print(__get_request(r"\@texgit@gitFile{x\{y}{}}y}{a\ b}"))
    ['\\@texgit@gitFile', 'x{y', '}y', 'a b']
    >>> print(__get_request(r"\@texgit@gitFile{x\{y}{}}y}{a\ \\b}"))
    ['\\@texgit@gitFile', 'x{y', '}y', 'a \\b']
    >>> print(__get_request(r"\@texgit@gitFile {x\{y}{}}y}{a\ \\b}"))
    ['\\@texgit@gitFile', 'x{y', '}y', 'a \\b']
    >>> print(__get_request(
    ...     r" \@texgit@gitFile { x\{y}{ }}y }{ a\ \\b } "))
    ['\\@texgit@gitFile', 'x{y', '}y', 'a \\b']
    >>> print(__get_request(
    ...     r" \@texgit@argFile { x\{y}{ }}y }{ a\ \\b }  {xx} {y   }"))
    ['\\@texgit@argFile', 'x{y', '}y', 'a \\b', 'xx', 'y']
    """
    use_line = str.strip(line)
    if str.__len__(use_line) >= 67108864:
        raise ValueError(f"line is {len(use_line)} characters long?")

    request: Final[str | None] = REQUEST_GIT_FILE if str.startswith(
        use_line, REQUEST_GIT_FILE) else (REQUEST_ARG_FILE if str.startswith(
            use_line, REQUEST_ARG_FILE) else (
            REQUEST_PROCESS if str.startswith(use_line, REQUEST_PROCESS)
            else None))
    if request is None:
        return None
    use_line = str.strip(use_line[str.__len__(request):])
    if (str.__len__(use_line) <= 0) or (use_line[0] != "{"):
        raise ValueError(
            f"rest line={use_line!r} for {request!r} in {line!r}.")

    # find markers for search-replacing problematic chars
    use_line, esc = escape(use_line, __REPL.keys())

    # Now we collect all the arguments
    command: list[str | None] = [request]
    idx_0: int = 1
    while True:
        idx_1: int = use_line.find("}", idx_0)
        if idx_1 < idx_0:
            raise ValueError(f"Found {{ but no }} in {line!r}?")
        arg: str = str.strip(use_line[idx_0:idx_1])
        if arg:
            for argi in str.split(arg):
                argj = str.strip(argi)
                if argj:
                    argj = unescape(argj, esc)
                    for k, v in __REPL.items():
                        argj = str.replace(argj, k, v)
                    command.append(argj)
        else:
            command.append(None)
        idx_0 = use_line.find("{", idx_1 + 1)
        if idx_0 <= idx_1:
            break
        idx_0 += 1
    return command


#: the response header for the path
RESPONSE_PATH: Final[str] = "@texgit@path@"
#: the response header for the file name
RESPONSE_NAME: Final[str] = "@texgit@name@"
#: the response header for the escaped file name
RESPONSE_ESCAPED_NAME: Final[str] = "@texgit@escName@"
#: the response header for the url
RESPONSE_URL: Final[str] = "@texgit@url@"

#: the command start A
__CMD_0A: Final[str] = r"\expandafter\xdef\csname "
#: the command start B
__CMD_0B: Final[str] = r"\expandafter\gdef\csname "
#: the command middle
__CMD_1: Final[str] = r"\endcsname{"
#: the command end
__CMD_2: Final[str] = r"}%"


def __make_response(prefix: str, name: str, value: str,
                    xdef: bool = True) -> str:
    """
    Make a response command.

    :param prefix: the prefix
    :param value: the value
    :param xdef: do we do xdef?
    :return: the result

    >>> print(__make_response(RESPONSE_PATH,
    ...       "lst:test", "./git/12.txt").replace(chr(92), "x"))
    xexpandafterxxdefxcsname @texgit@path@lst:testxendcsname{./git/12.txt}%

    >>> print(__make_response(RESPONSE_PATH,
    ...       "lst:test", "./git/12.txt", False).replace(chr(92), "x"))
    xexpandafterxgdefxcsname @texgit@path@lst:testxendcsname{./git/12.txt}%
    """
    return (f"{__CMD_0A if xdef else __CMD_0B}{str.strip(prefix)}"
            f"{str.strip(name)}{__CMD_1}{value}{str.strip(__CMD_2)}")


def __make_path_response(name: str, path: Path, base_dir: Path,
                         basename: str | None = None)\
        -> Generator[str, None, None]:
    r"""
    Make the path response commands.

    :param name: the name prefix
    :param path: the file path
    :param basename: the basename
    :param base_dir: the base directory

    >>> from pycommons.io.temp import temp_dir
    >>> with temp_dir() as td:
    ...     list(__make_path_response("x", td.resolve_inside("yy"), td, None))
    ['\\expandafter\\xdef\\csname @texgit@path@x\\endcsname{yy}%']
    >>> with temp_dir() as td:
    ...     v = list(__make_path_response("x", td.resolve_inside("yy"), td,
    ...             "bla y_x"))
    >>> v[0]
    '\\expandafter\\xdef\\csname @texgit@path@x\\endcsname{yy}%'
    >>> v[1]
    '\\expandafter\\xdef\\csname @texgit@name@x\\endcsname{bla y_x}%'
    >>> v[2]
    '\\expandafter\\gdef\\csname @texgit@escName@x\\endcsname{bla~y\\_x}%'
    """
    yield __make_response(RESPONSE_PATH, name, path.relative_to(base_dir))
    if basename is not None:
        yield __make_response(RESPONSE_NAME, name, basename)
        yield __make_response(
            RESPONSE_ESCAPED_NAME, name,
            basename.replace("$", "\\$").replace("_", "\\_").replace(
                " ", "~"), False)  # this one must be gdef!


def cmd_git_file(base_dir: Path, pm: ProcessManager,
                 command: list[str | None]) -> Generator[str, None, None]:
    """
    Get a file from `git`, maybe post-processed.

    :param base_dir: the base directory
    :param pm: the process manager
    :param command: the command
    :return: the answer
    """
    name: Final[str] = str.strip(command[1])
    repo_url: Final[str] = str.strip(command[2])
    relative_file: Final[str] = str.strip(command[3])
    cmd: list[str] | None = command[4:]
    ll: Final[int] = list.__len__(cmd)
    if ll == 0 or ((ll == 1) and (cmd[0] is None)):
        cmd = None
    gp: Final[GitPath] = pm.get_git_file(
        repo_url, relative_file, name, cmd)
    yield from __make_path_response(
        name, gp.path, base_dir, gp.basename)
    if gp.url:
        yield __make_response(RESPONSE_URL, name, gp.url)


def cmd_arg_file(base_dir: Path, pm: ProcessManager,
                 command: list[str | None]) -> Generator[str, None, None]:
    """
    Get an argument file.

    :param base_dir: the base directory
    :param pm: the process manager
    :param command: the command
    :return: the answer
    """
    name: Final[str] = str.strip(command[1])
    prefix: Final[str | None] = command[2]
    suffix: Final[str | None] = command[3]
    af: Final[Path] = pm.get_argument_file(name, prefix, suffix)[0]
    yield from __make_path_response(name, af, base_dir, af.basename())


def cmd_exec(base_dir: Path, pm: ProcessManager,
             command: list[str | None]) -> Generator[str, None, None]:
    """
    Execute a command and capture the output.

    :param base_dir: the base directory
    :param pm: the process manager
    :param command: the command
    :return: the answer
    """
    name: Final[str] = str.strip(command[1])
    repo_url: Final[str | None] = command[2]
    relative_dir: Final[str | None] = command[3]
    cmd: list[str] = command[4:]
    yield from __make_path_response(
        name, pm.get_output(name, cmd, repo_url, relative_dir), base_dir)


def run(aux_arg: str, repo_dir_arg: str = "__git__") -> None:
    """
    Execute the `texgit` tool.

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

    pm: ProcessManager | None = None
    append: list[str] = []
    stripped_lines: list[str] = list(map(str.strip, lines))
    deleted: int = 0  # the number of lines deleted

    try:
        resolved: int = 0
        for idx, line in enumerate(stripped_lines):
            if line.startswith(FORBIDDEN_LINE):
                del lines[idx - deleted]
                deleted += 1

            request: list[str | None] | None = __get_request(line)
            if request is None:
                continue

            if pm is None:
                git_dir: Path = base_dir.resolve_inside(repo_dir_arg)
                logger(f"The repository directory is {git_dir!r}.")
                pm = ProcessManager(git_dir)

            func = str.strip(request[0])
            if func == REQUEST_GIT_FILE:
                append.extend(cmd_git_file(base_dir, pm, request))
            elif func == REQUEST_ARG_FILE:
                append.extend(cmd_arg_file(base_dir, pm, request))
            elif func == REQUEST_PROCESS:
                append.extend(cmd_exec(base_dir, pm, request))
            else:
                raise ValueError(f"Invalid command {func} in line {line!r}.")
            resolved += 1
    finally:
        if pm is not None:
            pm.close()
            del pm

    if (len(append) <= 0) and (deleted <= 0):
        logger("No file requests or deletion markers found. Nothing to do.")
        return

    logger(f"Found and resolved {resolved} file requests.")
    for app in map(str.strip, append):  # make the texgit invocation idempotent
        if app and (app not in stripped_lines):
            lines.append(app)
    with aux_file.open_for_write() as wd:
        write_lines(lines, wd)
    logger(f"Finished flushing {len(lines)} lines to aux file {aux_file!r}.")


# Execute the texgit tool
if __name__ == "__main__":
    parser: Final[argparse.ArgumentParser] = make_argparser(
        __file__, "Execute the texgit Tool.",
        make_epilog(
            "Download and provide local paths for "
            "files from git repositories and execute programs.",
            2023, 2025, "Thomas Weise",
            url="https://thomasweise.github.io/texgit_py",
            email="tweise@hfuu.edu.cn, tweise@ustc.edu.cn"),
        __version__)
    parser.add_argument(
        "aux", help="the aux file to process", type=str, default="")
    parser.add_argument(
        "--repoDir", help="the directory to use for caching output",
        type=str, default="__git__", nargs="?")
    args: Final[argparse.Namespace] = parser.parse_args()

    run(args.aux.strip(), args.repoDir.strip())
    logger("All done.")

"""The tool for invoking shell commands."""

import subprocess  # nosec
from typing import Any, Callable, Final, Iterable

from latexgit.utils.console import logger
from latexgit.utils.path import Path
from latexgit.utils.types import check_int_range, type_error


def shell(command: str | Iterable[str],
          timeout: int = 3600,
          cwd: str | None = None,
          wants_stdout: bool = False,
          exit_code_to_str: dict[int, str] | None = None,
          check_stderr: Callable[[str], BaseException | None]
          = lambda _: None,
          stdin: str | None = None) -> str | None:
    """
    Execute a text-based command on the shell.

    The command is executed and its stdout and stderr and return code are
    captured. If the command had a non-zero exit code, an exception is
    thrown. The command itself, as well as the parameters are logged via
    the logger. If `wants_stdout` is `True`, the command's stdout is returned.
    Otherwise, `None` is returned.

    :param command: the command to execute
    :param timeout: the timeout in seconds
    :param cwd: the directory to run inside
    :param wants_stdout: if `True`, the stdout is returned, if `False`,
        `None` is returned
    :param exit_code_to_str: an optional map
        converting erroneous exit codes to strings
    :param check_stderr: an optional callable that is applied to the std_err
        string and may raise an exception if need be
    :param stdin: optional data to be written to stdin
    """
    check_int_range(timeout, "timeout", 1, 360_000_000)
    if isinstance(command, str):
        command = [command]
    if not isinstance(command, Iterable):
        raise type_error(command, "command", Iterable)

    cmd = [str(s).strip() for s in command]
    cmd = [s for s in cmd if len(s) > 0]
    execstr: str = " ".join(repr(c) for c in cmd)
    if (len(cmd) <= 0) or (len(execstr) <= 0):
        raise ValueError(f"Command {execstr!r} empty after stripping!")

    arguments: Final[dict[str, Any]] = {}

    if cwd is not None:
        if not isinstance(cwd, str):
            raise type_error(cwd, "cwd", str)
        wd = Path.directory(cwd)
        execstr = f"{execstr} in {wd!r}"
        arguments["cwd"] = wd

    if stdin is not None:
        if not isinstance(stdin, str):
            raise type_error(stdin, "stdin", str)
        arguments["input"] = stdin

    # nosemgrep
    ret = subprocess.run(  # nosec # noqa
        args=cmd, check=False, text=True, timeout=timeout,  # nosec # noqa
        capture_output=True, **arguments)  # nosec # noqa

    logging = [f"finished executing {execstr}.",
               f"obtained return value {ret.returncode}."]

    if (ret.returncode != 0) and exit_code_to_str:
        ec: str | None = exit_code_to_str.get(ret.returncode, None)
        if ec:
            logging.append(f"meaning of return value: {ec}")

    stdout = ret.stdout
    if stdout:
        stdout = stdout.strip()
        if stdout:
            logging.append(f"\nstdout:\n{stdout}")
    else:
        stdout = ""

    stderr = ret.stderr
    if stderr:
        stderr = stderr.strip()
        if stderr:
            logging.append(f"\nstderr:\n{stderr}")
    logger("\n".join(logging))

    if ret.returncode != 0:
        raise ValueError(
            f"Error {ret.returncode} when executing {execstr} compressor.")

    if stderr:
        exception = check_stderr(stderr)
        if exception is not None:
            raise exception

    return stdout if wants_stdout else None

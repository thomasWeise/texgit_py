"""Test the interaction with the file system and temp files."""

from typing import Final

from pycommons.io.path import Path, write_lines
from pycommons.io.temp import temp_dir, temp_file

from texgit.run import (
    REQUEST_GIT_FILE,
    RESPONSE_ESCAPED_NAME,
    RESPONSE_NAME,
    RESPONSE_PATH,
    run,
)


def test_aux() -> None:
    """Test the aux processor."""
    mrepo: Final[str] = \
        "https://github.com/thomasWeise/programmingWithPythonCode"
    with (temp_dir() as td,
          temp_file(td, suffix=".aux") as tf):
        txt = [
            r"\relax",
            f"{REQUEST_GIT_FILE} {{a}}{{{mrepo}}}{{"
            f"functions/def_factorial.py}}{{"
            f"python3 -m texgit.formatters.python --args format}}",
            r"\gdef \@abspage@last{1}"]
        with tf.open_for_write() as wd:
            write_lines(txt, wd)

        run(tf)
        got_1 = list(tf.open_for_read())

        assert len(got_1) == (len(txt) + 4)

        res_files: list[str] = [s for s in got_1 if RESPONSE_PATH in s]
        assert len(res_files) == 1
        res_file: str = res_files[0]
        find: str = "endcsname{"
        i1: int = res_file.index(find) + len(find)
        res_path: Path = td.resolve_inside(
            res_file[i1:res_file.index("}", i1)])

        res_files = [s for s in got_1 if RESPONSE_NAME in s]
        assert len(res_files) == 1
        res_file = res_files[0]
        i1 = res_file.index(find) + len(find)
        res_file = res_file[i1:res_file.index("}", i1)]
        assert res_file == "def_factorial.py"

        res_files = [s for s in got_1 if RESPONSE_ESCAPED_NAME in s]
        assert len(res_files) == 1
        res_file = res_files[0]
        i1 = res_file.index(find) + len(find)
        res_file = res_file[i1:res_file.index("}", i1)]
        assert res_file == "def\\_factorial.py"

        processed_file = res_path.read_all_str()
        assert "\n\n\n" in processed_file

"""Test the interaction with the file system and temp files."""

from typing import Final

from pycommons.io.path import write_lines
from pycommons.io.temp import temp_dir, temp_file

from latexgit.aux import REQUEST, RESPONSE_PATH, RESPONSE_URL, run


def test_aux() -> None:
    """Test the aux processor."""
    mrepo: Final[str] = "https://github.com/thomasWeise/moptipy"
    with (temp_dir() as td,
          temp_file(td, suffix=".aux") as tf):
        txt = [
            r"\relax",
            f"{REQUEST} {{{mrepo}}}{{README.md}}{{head -n 5}}",
            f"{REQUEST} {{{mrepo}}}{{LICENSE}}{{}}",
            f"{REQUEST} {{{mrepo}}}{{Makefile}}{{sort}}",
            r"\gdef \@abspage@last{1}"]
        with tf.open_for_write() as wd:
            write_lines(txt, wd)

        run(tf)
        got_1 = list(tf.open_for_read())

        assert len(got_1) == (len(txt) + 6)
        assert len([s for s in got_1 if s.startswith(
            f"\\xdef{RESPONSE_PATH}")]) == 3
        assert len([s for s in got_1 if s.startswith(
            f"\\xdef{RESPONSE_URL}")]) == 3

        with tf.open_for_write() as wd:
            write_lines(txt, wd)
        run(tf)
        got_2 = list(tf.open_for_read())

        assert got_1 == got_2

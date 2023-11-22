"""Test the interaction with the file system and temp files."""

from typing import Final

from latexgit.aux import REQUEST, RESPONSE, run
from latexgit.utils.temp import TempDir, TempFile


def test_aux() -> None:
    """Test the aux processor."""
    mrepo: Final[str] = "https://github.com/thomasWeise/moptipy"
    with (TempDir.create() as td,
          TempFile.create(td, suffix=".aux") as tf):
        txt = [
            r"\relax",
            f"{REQUEST} {{{mrepo}}}{{README.md}}{{head -n 5}}",
            f"{REQUEST} {{{mrepo}}}{{LICENSE}}{{}}",
            f"{REQUEST} {{{mrepo}}}{{Makefile}}{{sort}}",
            r"\gdef \@abspage@last{1}"]
        tf.write_all(txt)

        run(tf)
        got_1 = tf.read_all_list()

        assert len(got_1) == (len(txt) + 3)
        assert len([s for s in got_1 if s.startswith(
            f"\\xdef{RESPONSE}")]) == 3

        tf.write_all(txt)
        run(tf)
        got_2 = tf.read_all_list()

        assert got_1 == got_2

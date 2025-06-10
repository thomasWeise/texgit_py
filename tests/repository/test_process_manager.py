"""Test the file manager."""

from pycommons.io.path import Path
from pycommons.io.temp import temp_dir

from latexgit.repository.process_manager import ProcessManager


def test_process_manager() -> None:
    """Test the process manager."""
    with temp_dir() as td, ProcessManager(td) as fm:
        ap1 = fm.filter_argument("(:123:)")
        assert isinstance(ap1, Path)
        assert ap1.is_file()

        ap2 = fm.filter_argument("(:123:)")
        assert isinstance(ap2, Path)
        assert ap2.is_file()
        assert ap1 is ap2

        ap3 = fm.filter_argument("(:1235:zzzz:)")
        assert isinstance(ap3, Path)
        assert ap3.is_file()
        assert ap3.basename().startswith("zzzz")

        ap4 = fm.filter_argument("(:12y35:zzzz: .pdf:)")
        assert isinstance(ap4, Path)
        assert ap4.is_file()
        assert ap4.basename().startswith("zzzz")
        assert ap4.basename().endswith(".pdf")

        ap5 = fm.filter_argument("(:12y3s5::.pdf:)")
        assert isinstance(ap5, Path)
        assert ap5.is_file()
        assert ap5.basename().endswith(".pdf")

        ap6 = fm.filter_argument("(:1/2,sdf@@x3:)")
        assert isinstance(ap6, Path)
        assert ap6.is_file()

        assert fm.filter_argument("(:1/2:sdf@@x3)") == "(:1/2:sdf@@x3)"

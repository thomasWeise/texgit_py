"""Test the file manager."""

from pycommons.io.path import Path
from pycommons.io.temp import temp_dir

from latexgit.repository.file_manager import FileManager


def test_file_manager() -> None:
    """Test the file manager."""
    with temp_dir() as td:
        with FileManager(td) as fm:
            p1, t = fm.get_file("A", "test")
            assert t
            assert isinstance(p1, Path)
            assert p1.is_file()
            p2, t = fm.get_file("A", "test")
            assert p2 is p1
            assert not t
            p3, t = fm.get_file("sdfsdf", "test")
            assert isinstance(p3, Path)
            assert p3.is_file()
            assert t
            p4, t = fm.get_file("sdfsdf", "test")
            assert p3 is p4
            assert not t
            assert p3 != p1
            p5, t = fm.get_file("A", "other", prefix="pfx")
            assert isinstance(p5, Path)
            assert t
            assert p5.is_file()
            assert p5.basename().startswith("pfx")
            assert p5 != p1
            p6, t = fm.get_file("A", "new", suffix=".sfx")
            assert t
            assert isinstance(p6, Path)
            assert p6.is_file()
            assert p6.basename().endswith(".sfx")
            assert p6 != p1
            assert p6 != p5
            assert set(fm.list_realm("A")) == {p1, p5, p6}
            assert set(fm.list_realm("sdfsdf")) == {p3}
            assert tuple.__len__(fm.list_realm("A", False, True)) == 0
            assert tuple.__len__(fm.list_realm("sdfsdf", False, True)) == 0
            assert tuple.__len__(fm.list_realm("C")) == 0
            p7, t = fm.get_dir("sdfsdf", "hello")
            assert t
            assert p7.is_dir()
            p8, t = fm.get_file("sdfsdf", name="v", suffix=".s")
            assert p8.is_file()
            assert t
            p9, t = fm.get_file("sdfsdf", name=p8.basename())
            assert p9.is_file()
            assert t
            assert p8 != p9
            px, t = fm.get_dir("sdfsdf", p9.basename())
            assert px.is_dir()
            assert t
            pxy, t = fm.get_dir("sdfsdf", p9.basename())
            assert px is pxy
            assert t is False
            assert set(fm.list_realm("sdfsdf", directories=False)) == {
                p3, p8, p9}
            assert set(fm.list_realm("sdfsdf", files=False)) == {p7, px}

        with FileManager(td) as fm:
            p1b, t = fm.get_file("A", "test")
            assert not t
            assert p1b == p1
            p2b, t = fm.get_file("A", "test")
            assert not t
            assert p2b is p1b
            p3b, t = fm.get_file("sdfsdf", "test")
            assert not t
            assert p3b == p3
            p4b, t = fm.get_file("sdfsdf", "test")
            assert not t
            assert p3b is p4b
            p5b, t = fm.get_file("A", "other", prefix="pfx")
            assert not t
            assert p5b == p5
            p6b, t = fm.get_file("A", "new", suffix=".sfx")
            assert not t
            assert p6b == p6
            assert set(fm.list_realm("A")) == {p1, p5, p6}
            assert set(fm.list_realm("sdfsdf", directories=False)) == {
                p3, p8, p9}
            assert set(fm.list_realm("sdfsdf", files=False)) == {p7, px}
            py, t = fm.get_file("A", ".gitignore")
            assert isinstance(py, Path)
            assert py.is_file()
            assert py.basename() != ".gitignore"
            assert t

            ap1 = fm.filter_argument("(@123@)")
            assert isinstance(ap1, Path)
            assert ap1.is_file()

            ap2 = fm.filter_argument("(@123@)")
            assert isinstance(ap2, Path)
            assert ap2.is_file()
            assert ap1 is ap2

            ap3 = fm.filter_argument("(@1235:zzzz@)")
            assert isinstance(ap3, Path)
            assert ap3.is_file()
            assert ap3.basename().startswith("zzzz")

            ap4 = fm.filter_argument("(@12y35:zzzz: .pdf@)")
            assert isinstance(ap4, Path)
            assert ap4.is_file()
            assert ap4.basename().startswith("zzzz")
            assert ap4.basename().endswith(".pdf")

            ap5 = fm.filter_argument("(@12y3s5::.pdf@)")
            assert isinstance(ap5, Path)
            assert ap5.is_file()
            assert ap5.basename().endswith(".pdf")

            ap6 = fm.filter_argument("(@1/2,sdf@@x3@)")
            assert isinstance(ap6, Path)
            assert ap6.is_file()

            assert fm.filter_argument("(@1/2:sdf@@x3)") == "(@1/2:sdf@@x3)"

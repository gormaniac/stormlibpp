"""Tests for stormlibpp.stormpkg."""

import os

import pytest
import stormlibpp


class TestStormPkg:
    def test_not_subclass(self):
        with pytest.raises(RuntimeError):
            badcls = stormlibpp.StormPkg()

    def test_missing_proto(self):
        class X(stormlibpp.StormPkg):
            pass

        with pytest.raises(stormlibpp.errors.StormPkgNoProtoError):
            x = X()

    def test_bad_pkg_name(self):
        class Bad(stormlibpp.StormPkg):
            pass

        with pytest.raises(stormlibpp.errors.StormPkgBadDefError):
            badname = Bad(proto_name="badname")

    def test_missing_storm_file(self):
        class Missing(stormlibpp.StormPkg):
            pass

        with pytest.raises(stormlibpp.errors.StormPkgNoProtoError):
            missing = Missing(
                proto_name="missingstorm",
                proto_dir=os.path.abspath(os.path.dirname(__file__)),
            )

    def test_multi_pkg(self):
        class Test(stormlibpp.StormPkg):
            pass

        class OtherTest(stormlibpp.StormPkg):
            pass

        test = Test()
        othertest = OtherTest()

        assert isinstance(test.asdict(), dict)
        assert isinstance(othertest.pkgdef, dict)

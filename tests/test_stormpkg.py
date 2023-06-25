"""Tests for stormlibpp.stormpkg."""

import os

import pytest
import stormlibpp


class TestStormPkg:
    def test_not_subclass(self):
        with pytest.raises(RuntimeError):
            stormlibpp.StormPkg()

    def test_missing_proto(self):
        class X(stormlibpp.StormPkg):
            """If using StormPkg defaults, we can just define a docstring.
            
            We could also just write ``pass``.
            """

        with pytest.raises(stormlibpp.errors.StormPkgNoProtoError):
            X()

    def test_bad_pkg_name(self):
        class Bad(stormlibpp.StormPkg):
            proto_name = "badname"

        with pytest.raises(stormlibpp.errors.StormPkgBadDefError):
            Bad()

    def test_missing_storm_file(self):
        class Missing(stormlibpp.StormPkg):
            proto_name = "missingstorm"

        with pytest.raises(stormlibpp.errors.StormPkgNoProtoError):
            Missing(proto_dir=os.path.abspath(os.path.dirname(__file__)))

    def test_multi_pkg(self):
        class Test(stormlibpp.StormPkg):
            pass

        class OtherTest(stormlibpp.StormPkg):
            pass

        test = Test()
        othertest = OtherTest()

        assert isinstance(test.asdict(), dict)
        assert isinstance(othertest.pkgdef, dict)
        assert "othertest.lib" in othertest.modnames

    def test_storm_parse(self):
        class BadStorm(stormlibpp.StormPkg):
            pass

        with pytest.raises(stormlibpp.errors.StormPkgSyntaxError):
            BadStorm()

    def test_storm_parse_disable(self):
        class BadStorm(stormlibpp.StormPkg):
            pass

        assert "badstorm" in BadStorm(check_syntax=False).cmdnames

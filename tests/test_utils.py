"""Tests for stormlibpp.utils."""


import stormlibpp


class TestNormVer:

    def test_normver_str(self):
        ver = "1.2.3"
        verstr, vertup = stormlibpp.utils.normver(ver)
        assert verstr == ver
        assert vertup == (1,2,3)

    def test_normver_tup(self):
        ver = (1,2,3)
        verstr, vertup = stormlibpp.utils.normver(ver)
        assert vertup == ver
        assert verstr == "1.2.3"

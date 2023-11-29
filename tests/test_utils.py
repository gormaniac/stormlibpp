"""Tests for stormlibpp.utils."""


import stormlibpp
import io
import json


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


class TestJsonGenr:
    def test_json_genr_dict(self):
        input = {"proto": "http", "host": "1.2.3.4"}
        fd = io.StringIO(json.dumps(input))

        for k, v in stormlibpp.utils.json_genr(fd):
            assert k in input
            assert v in input.values()


    def test_json_genr_list(self):
        input = ["1.2.3.4", "1.2.3.5"]
        fd = io.StringIO(json.dumps(input))

        gen = stormlibpp.utils.json_genr(fd)

        assert next(gen) == [0, input[0]]
        assert next(gen) == [1, input[1]]

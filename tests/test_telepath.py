"""Tests for stormlibpp.telepath."""


import stormlibpp


class SubTeleRet(stormlibpp.TelepathRetn):
    data: str


class TestTelepathRetn:
    def test_gen_telepath_ret(self):
        ret = stormlibpp.genDefaultTelepathRetn()
        assert ret == dict(status=True, mesg="", data=None)

    def test_gen_telepath_ret_opts(self):
        ret = stormlibpp.genDefaultTelepathRetn(SubTeleRet, default_data="default")
        assert ret == dict(status=True, mesg="", data="default")


class TestCustomRetns:
    def test_gen_boolretn(self):
        ret = stormlibpp.genDefaultTelepathRetn(
            stormlibpp.telepath.BoolRetn, default_data=False
        )
        assert ret == dict(status=True, mesg="", data=False)

"""Tests for stormlibpp.svc."""

import logging

import pytest
import synapse.exc as s_exc
import synapse.lib.cell as s_cell
import synapse.tests.utils as s_test

from stormlibpp.svc import (
    RetnApi,
    SvcError,
    checkGuid,
    checkName,
    errRetn,
    retn,
    retnGenr,
    safeJoin,
)
from stormlibpp.telepath import BoolRetn


class FakeApiError(Exception):
    def __init__(self, mesg):
        super().__init__(mesg)
        self.mesg = mesg


class FakeCell:
    """Stands in for a service's Cell: just the methods the API calls."""

    apikey = "sekrit-key"

    async def lookup(self, valu):
        if valu == "boom":
            raise KeyError("boom")
        if valu == "api":
            raise FakeApiError(f"Bad request with key {self.apikey}")
        if valu == "svc":
            raise SvcError("No such thing.")
        if valu == "int":
            int("x")
        return {"valu": valu}

    async def export(self, count, fail=False):
        for i in range(count):
            yield i
        if fail:
            raise RuntimeError(f"export broke, key {self.apikey}")


class FakeApi(RetnApi):
    RETN_METHS = ("lookup",)
    GENR_METHS = ("export",)
    RETN_ERRORS = (SvcError, FakeApiError)

    def __init__(self, cell):
        self.cell = cell

    def _retnRedact(self, mesg):
        return mesg.replace(self.cell.apikey, "<redacted>")

    async def setThing(self, valu) -> BoolRetn:
        if valu is None:
            raise ValueError("valu is required")
        return BoolRetn(status=True, mesg="Set.", data=True)

    async def items(self):
        yield BoolRetn(status=True, mesg="", data=True)
        raise RuntimeError("items broke")

    async def _private(self):
        raise RuntimeError("not guarded")

    def syncHelper(self):
        raise RuntimeError("not guarded either")


class TestErrRetn:
    def test_expected(self):
        retn = errRetn(SvcError("Nope."))
        assert retn == {"status": False, "mesg": "Nope.", "data": None}

    def test_input(self):
        retn = errRetn(ValueError("bad int"))
        assert retn["mesg"] == "Invalid input: bad int"

    def test_synerr_mesg(self):
        retn = errRetn(s_exc.BadArg(mesg="Bad arg here."))
        assert retn["mesg"] == "Invalid input: Bad arg here."

    def test_authdeny(self):
        retn = errRetn(s_exc.AuthDeny(mesg="User is not an admin [visi]"))
        assert retn["mesg"] == "User is not an admin [visi]"

    def test_unexpected_logged(self, caplog):
        with caplog.at_level(logging.ERROR, logger="stormlibpp.svc"):
            retn = errRetn(KeyError("k"), name="Api.lookup")
        assert retn["status"] is False
        assert retn["mesg"] == "Unexpected error: KeyError: 'k'"
        assert "Api.lookup" in caplog.text
        assert caplog.records[0].exc_info

    def test_redact(self):
        retn = errRetn(SvcError("key=abc"), redact=lambda m: m.replace("abc", "***"))
        assert retn["mesg"] == "key=***"

    def test_no_expected_errors(self):
        retn = errRetn(SvcError("Nope."), errors=())
        assert retn["mesg"] == "Unexpected error: SvcError: Nope."


class TestRetnFuncs(s_test.SynTest):
    async def test_retn(self):
        async def ok():
            return 1

        async def bad():
            raise SvcError("bad")

        assert await retn(ok()) == {"status": True, "mesg": "", "data": 1}
        assert await retn(bad()) == {"status": False, "mesg": "bad", "data": None}

    async def test_retn_genr(self):
        async def genr():
            yield 1
            raise SvcError("stopped")

        items = [i async for i in retnGenr(genr())]
        assert items == [
            {"status": True, "mesg": "", "data": 1},
            {"status": False, "mesg": "stopped", "data": None},
        ]


class TestRetnApi(s_test.SynTest):
    async def test_generated_retn(self):
        api = FakeApi(FakeCell())
        assert await api.lookup("x") == {
            "status": True,
            "mesg": "",
            "data": {"valu": "x"},
        }
        assert (await api.lookup("svc"))["mesg"] == "No such thing."
        assert (await api.lookup("api"))["mesg"] == "Bad request with key <redacted>"
        assert (await api.lookup("int"))["mesg"].startswith("Invalid input: ")
        retn = await api.lookup("boom")
        assert retn == {
            "status": False,
            "mesg": "Unexpected error: KeyError: 'boom'",
            "data": None,
        }
        # Bad arguments from Storm are caught too.
        assert (await api.lookup())["mesg"].startswith("Invalid input: ")
        assert FakeApi.lookup.__qualname__ == "FakeApi.lookup"

    async def test_generated_genr(self):
        api = FakeApi(FakeCell())
        items = [i async for i in api.export(2)]
        assert [i["data"] for i in items] == [0, 1]

        items = [i async for i in api.export(1, fail=True)]
        assert items[0] == {"status": True, "mesg": "", "data": 0}
        assert items[1]["status"] is False
        assert (
            items[1]["mesg"]
            == "Unexpected error: RuntimeError: export broke, key <redacted>"
        )

    async def test_guarded(self):
        api = FakeApi(FakeCell())
        assert await api.setThing(1) == {"status": True, "mesg": "Set.", "data": True}
        assert await api.setThing(None) == {
            "status": False,
            "mesg": "Invalid input: valu is required",
            "data": None,
        }
        items = [i async for i in api.items()]
        assert items[0]["status"] is True
        assert items[1]["mesg"] == "Unexpected error: RuntimeError: items broke"

    async def test_not_guarded(self):
        api = FakeApi(FakeCell())
        with pytest.raises(RuntimeError):
            await api._private()
        with pytest.raises(RuntimeError):
            api.syncHelper()

    def test_hand_written_wins(self):
        class Api(RetnApi):
            RETN_METHS = ("lookup",)

            async def lookup(self, valu):
                return BoolRetn(status=True, mesg="custom", data=True)

        assert getattr(Api.lookup, "_retn_guarded", False)
        assert Api.lookup.__wrapped__.__qualname__.endswith("Api.lookup")

    def test_both_lists(self):
        with pytest.raises(TypeError, match="RETN_METHS and GENR_METHS"):

            class Api(RetnApi):
                RETN_METHS = ("x",)
                GENR_METHS = ("x",)

    async def test_subclass_of_subclass(self):
        class Child(FakeApi):
            async def extra(self):
                raise SvcError("child")

        api = Child(FakeCell())
        assert (await api.extra())["mesg"] == "child"
        assert (await api.lookup("svc"))["mesg"] == "No such thing."


class TelCell(s_cell.Cell):
    async def lookup(self, valu):
        if valu == "boom":
            raise KeyError(valu)
        return valu

    async def export(self, count):
        for i in range(count):
            yield i
        raise SvcError("done early")


class TelApi(RetnApi, s_cell.CellApi):
    RETN_METHS = ("lookup",)
    GENR_METHS = ("export",)

    @s_cell.adminapi()
    async def adminThing(self):
        return BoolRetn(status=True, mesg="", data=True)


TelCell.cellapi = TelApi


class TestRetnApiTelepath(s_test.SynTest):
    """The generated and guarded methods work over a real Telepath proxy."""

    async def test_telepath(self):
        async with self.getTestCell(TelCell) as cell:
            async with cell.getLocalProxy() as prox:
                self.eq(
                    {"status": True, "mesg": "", "data": "x"}, await prox.lookup("x")
                )
                self.eq(
                    "Unexpected error: KeyError: 'boom'",
                    (await prox.lookup("boom"))["mesg"],
                )

                items = [i async for i in prox.export(2)]
                self.eq([0, 1], [i["data"] for i in items[:2]])
                self.eq({"status": False, "mesg": "done early", "data": None}, items[2])

                self.true((await prox.adminThing())["data"])

            user = await cell.auth.addUser("lowuser")
            await user.setPasswd("secret")
            async with cell.getLocalProxy(user="lowuser") as prox:
                retn = await prox.adminThing()
                self.false(retn["status"])
                self.isin("User is not an admin [lowuser]", retn["mesg"])


class TestPaths:
    def test_check_name(self):
        assert checkName("rule-1.yar") == "rule-1.yar"
        for bad in (
            "",
            ".",
            "..",
            ".hidden",
            "a/b",
            "a\\b",
            "a\x00",
            "x" * 129,
            None,
            1,
        ):
            with pytest.raises(SvcError):
                checkName(bad)

    def test_check_guid(self):
        guid = "a" * 32
        assert checkGuid(guid) == guid
        for bad in ("A" * 32, "a" * 31, "../" + "a" * 29, None):
            with pytest.raises(SvcError, match="rule id"):
                checkGuid(bad, "rule id")

    def test_safe_join(self, tmp_path):
        assert (
            safeJoin(tmp_path, "feeds", "a.rules")
            == tmp_path.resolve() / "feeds" / "a.rules"
        )
        for parts in ((), ("..",), (".",), ("../etc",), ("a", "..")):
            with pytest.raises(SvcError):
                safeJoin(tmp_path, *parts)

    def test_safe_join_symlink(self, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        root = tmp_path / "root"
        root.mkdir()
        (root / "link").symlink_to(outside)
        with pytest.raises(SvcError, match="outside"):
            safeJoin(root, "link", "file")

"""Tests for the slib.pdns Storm package. CIRCL Passive DNS is mocked with VCR cassettes."""

import base64
import contextlib
import json
import os

import synapse.tests.utils as s_test
import vcr

from ... import DIRNAME

# Real CIRCL responses, recorded with scripts/pkgs/record_circl.py.
CASSETTES = os.path.join(DIRNAME, "tests/pkgs/pdns/cassettes")

CMDS = ("slib.pdns.lookup", "slib.pdns.admin.key")
MODS = ("slib.pdns.lib", "slib.pdns.privsep", "slib.pdns.lib.admin")
SOURCE = "696c119cb73c4a079a2865108c96668a"

AUTH = "Basic " + base64.b64encode(b"myuser:mypasswd").decode()


def dribbleHeaders(r1, r2):
    """A VCR matcher: the requests have the same dribble-* headers."""

    def dribble(req):
        return {k.lower(): v for k, v in req.headers.items() if k.lower().startswith("dribble-")}

    assert dribble(r1) == dribble(r2), f"{dribble(r1)} != {dribble(r2)}"


@contextlib.contextmanager
def cassette(name, dribble=False):
    """Play a cassette, failing on any request it doesn't have.

    The requests the package sent are in the cassette's "sent" list. With dribble=True, the
    dribble-* request headers must match the cassette's too.
    """
    myvcr = vcr.VCR(record_mode="none")
    myvcr.register_matcher("dribble", dribbleHeaders)
    match_on = ["method", "scheme", "host", "port", "path", "query"]
    if dribble:
        match_on.append("dribble")

    with myvcr.use_cassette(os.path.join(CASSETTES, f"{name}.yaml"), match_on=match_on) as cass:
        cass.sent = []
        play = cass.play_response

        def playAndSave(req):
            resp = play(req)
            cass.sent.append(req)
            return resp

        cass.play_response = playAndSave
        yield cass


def reqHeader(cass, indx, name):
    """A header of a request the package sent, ignoring case."""
    for key, valu in cass.sent[indx].headers.items():
        if key.lower() == name.lower():
            return valu
    return None


class PdnsTest(s_test.StormPkgTest):

    pkgprotos = (os.path.join(DIRNAME, "src/pkgs/pdns/pdns.yaml"),)

    async def auth(self, core):
        msgs = await core.stormlist("slib.pdns.admin.key myuser mypasswd")
        self.stormHasNoWarnErr(msgs)

    async def test_pdns_pkg(self):
        async with self.getTestCore() as core:
            for cmd in CMDS:
                self.isin(cmd, core.stormcmds)
            for mod in MODS:
                self.isin(mod, core.stormmods)
                self.stormHasNoErr(await core.stormlist(f"$mod = $lib.import({mod})"))

            msgs = await core.stormlist("slib.pdns.lookup --help")
            self.stormIsInPrint("FQDNs to look up", msgs)

            # onload makes the meta:source.
            nodes = await core.nodes(f"meta:source={SOURCE}")
            self.len(1, nodes)
            self.eq("circl.lu passive dns", nodes[0].get("name"))

    async def test_pdns_admin_key(self):
        async with self.getTestCore() as core:
            msgs = await core.stormlist("slib.pdns.admin.key myuser mypasswd")
            self.stormIsInPrint("Saved the CIRCL Passive DNS credentials", msgs)
            self.eq("myuser", await core.callStorm('return($lib.globals.get("slib:pdns:auth:user"))'))
            self.eq("mypasswd", await core.callStorm('return($lib.globals.get("slib:pdns:auth:passwd"))'))

            msgs = await core.stormlist("slib.pdns.admin.key myuser")
            self.stormIsInErr("requires a username and a password", msgs)

            msgs = await core.stormlist("slib.pdns.admin.key --clear")
            self.stormIsInPrint("Removed the CIRCL Passive DNS credentials", msgs)
            self.none(await core.callStorm('return($lib.globals.get("slib:pdns:auth:user"))'))
            self.none(await core.callStorm('return($lib.globals.get("slib:pdns:auth:passwd"))'))

            # No credentials, no request.
            with cassette("domain") as cass:
                msgs = await core.stormlist("slib.pdns.lookup --query circl.lu")
                self.stormIsInErr("credentials are not set", msgs)
                self.eq(0, cass.play_count)

    async def test_pdns_perms(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            visi = await core.auth.addUser("visi")
            opts = {"user": visi.iden}

            msgs = await core.stormlist("slib.pdns.lookup --query circl.lu", opts=opts)
            self.stormIsInErr("requires permission: slib.pdns.user", msgs)
            msgs = await core.stormlist("slib.pdns.admin.key a b", opts=opts)
            self.stormIsInErr("requires permission: slib.pdns.admin", msgs)

            # A user can make requests, but can't read the credentials.
            await visi.addRule((True, ("slib", "pdns", "user")))
            with cassette("domain"):
                retn = await core.callStorm("return($lib.import(slib.pdns.lib).request(circl.lu))", opts=opts)
            self.true(retn["status"])
            msgs = await core.stormlist('$lib.print($lib.globals.get("slib:pdns:auth:passwd"))', opts=opts)
            self.stormIsInErr("must have permission globals.get", msgs)

            # No privsep function hands the credentials back. Every function in an asroot module
            # can be called by the user, even ones whose names start with "_".
            secrets = ("mypasswd", base64.b64encode(b"myuser:mypasswd").decode())
            self.false(any(s in json.dumps(retn) for s in secrets))
            msgs = await core.stormlist("$lib.print($lib.import(slib.pdns.privsep)._headers())", opts=opts)
            self.stormIsInErr("_headers", msgs)
            self.false(any(s in json.dumps(msgs) for s in secrets))

            # Modeling runs as the user, so it needs node edit perms too.
            with cassette("domain"):
                msgs = await core.stormlist("slib.pdns.lookup --query circl.lu", opts=opts)
            self.stormIsInErr("must have permission node.", msgs)

    async def test_pdns_request(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("domain") as cass:
                retn = await core.callStorm("return($lib.import(slib.pdns.lib).request(circl.lu))")
                self.eq(AUTH, reqHeader(cass, 0, "Authorization"))
                self.none(reqHeader(cass, 0, "dribble-disable-active-query"))

            self.true(retn["status"])
            self.len(85, retn["data"]["records"])
            self.eq([], retn["data"]["errors"])
            self.none(retn["data"]["cursor"])
            self.eq(
                {"rrtype": "A", "rrname": "185.194.93.14", "rdata": "circl.lu", "count": 8617,
                 "time_first": 1696798385, "time_last": 1790942704, "origin": "https://www.circl.lu/pdns/"},
                retn["data"]["records"][1],
            )

            with cassette("unauthorized"):
                retn = await core.callStorm("return($lib.import(slib.pdns.lib).request(circl.lu))")
            self.false(retn["status"])
            self.isin("rejected the credentials", retn["mesg"])

    async def test_pdns_lookup_domain(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            await core.nodes("[ inet:fqdn=circl.lu ]")
            with cassette("domain"):
                msgs = await core.stormlist("inet:fqdn=circl.lu | slib.pdns.lookup")
            self.stormHasNoWarnErr(msgs)

            # Without --yield the inbound nodes pass through.
            self.eq([("inet:fqdn", "circl.lu")], [m[1][0] for m in msgs if m[0] == "node"])

            # rrname is the value, rdata is the owner.
            nodes = await core.nodes("inet:dns:a=(circl.lu, 185.194.93.14)")
            self.len(1, nodes)
            self.eq((1696798385000, 1790942704000), nodes[0].get(".seen"))
            self.eq({"circl.lu 185.194.93.14": {"count": 8617, "time_first": 1696798385, "time_last": 1790942704}},
                    await nodes[0].getData("slib:pdns"))
            self.len(1, await core.nodes(f"inet:dns:a=(circl.lu, 185.194.93.14) <(seen)- meta:source={SOURCE}"))

            self.len(2, await core.nodes("inet:dns:a:fqdn=circl.lu"))
            self.len(3, await core.nodes("inet:dns:aaaa:fqdn=circl.lu"))
            self.len(1, await core.nodes("inet:dns:aaaa=(circl.lu, 2a00:5980:93::14)"))
            self.len(1, await core.nodes("inet:dns:mx=(circl.lu, cppy.circl.lu)"))
            self.len(8, await core.nodes("inet:dns:ns:zone=circl.lu"))
            self.len(1, await core.nodes("inet:dns:ns=(circl.lu, ns-a.eurodns.com)"))
            self.len(1, await core.nodes('inet:dns:txt:fqdn=circl.lu +:txt^="google-site-verification="'))

            soas = await core.nodes("inet:dns:soa:fqdn=circl.lu +:ns=ns1.eurodns.com")
            self.len(1, soas)
            self.eq("hostmaster@eurodns.com", soas[0].get("email"))

            # Looking up again doesn't make more nodes.
            count = len(await core.nodes("inet:dns:a inet:dns:aaaa inet:dns:mx inet:dns:ns inet:dns:soa inet:dns:txt"))
            with cassette("domain"):
                msgs = await core.stormlist("slib.pdns.lookup --query circl.lu --yield")
            self.stormHasNoWarnErr(msgs)
            yielded = [m[1] for m in msgs if m[0] == "node"]
            self.len(85, yielded)
            self.eq(count, len(await core.nodes("inet:dns:a inet:dns:aaaa inet:dns:mx inet:dns:ns inet:dns:soa inet:dns:txt")))

    async def test_pdns_lookup_opts(self):
        async with self.getTestCore() as core:
            await self.auth(core)

            with cassette("domain_noactive") as cass:
                msgs = await core.stormlist("slib.pdns.lookup --query circl.lu --no-active")
                self.stormHasNoWarnErr(msgs)
                self.eq("1", reqHeader(cass, 0, "dribble-disable-active-query"))

            with cassette("rrtype") as cass:
                msgs = await core.stormlist("slib.pdns.lookup --query circl.lu --rrtype ns --yield")
                self.stormHasNoWarnErr(msgs)
                self.eq("NS", reqHeader(cass, 0, "dribble-filter-rrtype"))
            nodes = [m[1] for m in msgs if m[0] == "node"]
            self.len(8, nodes)
            self.eq({"inet:dns:ns"}, {n[0][0] for n in nodes})

    async def test_pdns_lookup_cname(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("fqdn_cname"):
                msgs = await core.stormlist("[ inet:fqdn=www.circl.lu ] | slib.pdns.lookup --yield")
            self.stormHasNoWarnErr(msgs)

            # www.circl.lu CNAME cfss1.circl.lu, and the case variants of cpab.circl.lu are one node.
            self.len(1, await core.nodes("inet:dns:cname=(www.circl.lu, cfss1.circl.lu)"))
            self.len(1, await core.nodes("inet:dns:cname=(www.circl.lu, cpab.circl.lu)"))
            self.len(2, await core.nodes("inet:dns:cname:fqdn=www.circl.lu"))

            # Each case variant keeps its own count and times, they don't overwrite each other.
            nodes = await core.nodes("inet:dns:cname=(www.circl.lu, cpab.circl.lu)")
            data = await nodes[0].getData("slib:pdns")
            self.len(16, data)
            self.eq({"count": 29001, "time_first": 1696779474, "time_last": 1790939251}, data["www.circl.lu cpab.circl.lu"])
            self.eq({"count": 12, "time_first": 1713939878, "time_last": 1727363163}, data["www.circl.lu cpAb.circl.lu"])
            # .seen covers every variant.
            self.eq(1696779474000, nodes[0].get(".seen")[0])

            # A repeated lookup replaces the same keys.
            with cassette("fqdn_cname"):
                msgs = await core.stormlist("slib.pdns.lookup --query www.circl.lu")
            self.stormHasNoWarnErr(msgs)
            nodes = await core.nodes("inet:dns:cname=(www.circl.lu, cpab.circl.lu)")
            self.eq(data, await nodes[0].getData("slib:pdns"))

    async def test_pdns_lookup_ips(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            await core.nodes("[ inet:ipv4=185.194.93.14 inet:ipv6=2a00:5980:93::14 ]")

            # The printable address is sent (the cassette's URL), not inet:ipv4's int.
            with cassette("ipv4") as cass:
                msgs = await core.stormlist("inet:ipv4=185.194.93.14 | slib.pdns.lookup")
                self.stormHasNoWarnErr(msgs)
                self.eq(1, cass.play_count)
            self.len(8, await core.nodes("inet:dns:a:ipv4=185.194.93.14"))
            self.len(1, await core.nodes("inet:dns:a=(d4-project.org, 185.194.93.14)"))

            with cassette("ipv6") as cass:
                msgs = await core.stormlist("inet:ipv6=2a00:5980:93::14 | slib.pdns.lookup")
                self.stormHasNoWarnErr(msgs)
                self.eq(1, cass.play_count)
            self.len(4, await core.nodes("inet:dns:aaaa:ipv6=2a00:5980:93::14"))

    async def test_pdns_lookup_empty(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("empty"):
                msgs = await core.stormlist("slib.pdns.lookup --query nonexistent-zzqx-example-12345.com --yield")
            self.stormHasNoWarnErr(msgs)
            self.len(0, [m for m in msgs if m[0] == "node"])

    async def test_pdns_lookup_maxset(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("maxset"):
                msgs = await core.stormlist("slib.pdns.lookup --query cdn1.wixdns.net")
            self.stormHasNoErr(msgs)
            self.stormIsInWarn("only returned 1000 of the 13518377 CNAME records for cdn1.wixdns.net", msgs)

            # Wildcard owners (ex. *.bymo.io CNAME cdn1.wixdns.net) aren't valid inet:fqdns.
            self.len(0, await core.nodes("inet:dns:cname:fqdn=bymo.io"))
            self.len(1, await core.nodes("inet:dns:cname=(0-site.astranot.net, cdn1.wixdns.net)"))

    async def test_pdns_lookup_paginate(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("paginate", dribble=True) as cass:
                msgs = await core.stormlist(
                    "slib.pdns.lookup --query cdn1.wixdns.net --rrtype CNAME --page-size 25 --max-pages 2"
                )
                self.stormHasNoErr(msgs)
                self.eq(2, cass.play_count)
                self.none(reqHeader(cass, 0, "dribble-paginate-cursor"))
                self.eq("8475240723766813860", reqHeader(cass, 1, "dribble-paginate-cursor"))
            self.stormIsInWarn("Stopped after 2 pages", msgs)
            self.gt(len(await core.nodes("inet:dns:cname:cname=cdn1.wixdns.net")), 25)

    async def test_pdns_lookup_errors(self):
        async with self.getTestCore() as core:
            await self.auth(core)

            with cassette("unauthorized"):
                msgs = await core.stormlist("slib.pdns.lookup --query circl.lu")
            self.stormIsInWarn("rejected the credentials set with slib.pdns.admin.key (HTTP 401)", msgs)

            with cassette("domain") as cass:
                msgs = await core.stormlist("[ inet:url=https://circl.lu ] | slib.pdns.lookup")
                self.stormIsInWarn('"inet:url" is not supported', msgs)
                self.eq(0, cass.play_count)

    async def test_pdns_model_soa(self):
        async with self.getTestCore() as core:
            q = "return($lib.import(slib.pdns.lib).modelRecord($rec))"
            rec = {"rrtype": "SOA", "rdata": "example.com", "count": 1, "time_first": 1, "time_last": 2,
                   "rrname": "not_a#host bad. 1 2 3 4 5"}
            self.nn(await core.callStorm(q, opts={"vars": {"rec": rec}}))
            soas = await core.nodes("inet:dns:soa:fqdn=example.com")
            self.len(1, soas)
            self.none(soas[0].get("ns"))
            self.none(soas[0].get("email"))

            # Unsupported rrtypes make nothing.
            rec = {"rrtype": "PTR", "rdata": "1.2.3.4", "rrname": "example.com", "count": 1, "time_first": 1, "time_last": 2}
            self.none(await core.callStorm(q, opts={"vars": {"rec": rec}}))

    async def test_pdns_soa_email(self):
        async with self.getTestCore() as core:
            q = "return($lib.import(slib.pdns.lib).soaEmail($valu))"
            self.eq("hostmaster@eurodns.com", await core.callStorm(q, opts={"vars": {"valu": "hostmaster.eurodns.com."}}))
            self.eq("john.doe@example.com", await core.callStorm(q, opts={"vars": {"valu": "john\\.doe.example.com"}}))
            self.none(await core.callStorm(q, opts={"vars": {"valu": "localhost"}}))

"""Tests for the slib.ipapi Storm package.

ip-api.com is never called: most tests point slib.ipapi at a fake ip-api.com (fakeipapi.py)
with the slib:ipapi:url global, and the real free/pro URLs are checked with VCR cassettes.
"""

import contextlib
import json
import os
import time

import synapse.tests.utils as s_test
import vcr

from ... import DIRNAME
from .fakeipapi import RAW_DATA, FakeIpApi

CASSETTES = os.path.join(DIRNAME, "tests/pkgs/ipapi/cassettes")

SRCGUID = "c177b2a9c0eff5c2984946d439de23ea"

CMDS = (
    "slib.ipapi.query",
    "slib.ipapi.apikey",
    "slib.ipapi.admin.apikey",
    "slib.ipapi.admin.settag",
    "slib.ipapi.admin.disabletag",
    "slib.ipapi.admin.enabletag",
)
MODS = ("slib.ipapi.lib", "slib.ipapi.privsep", "slib.ipapi.admin")

QUERY = "slib.ipapi.query --query 8.8.8.8"


def data(**kwargs) -> dict:
    """RAW_DATA, updated with kwargs (keys like "as" can be passed with **{"as": ...})."""
    return {**RAW_DATA, **kwargs}


class IpApiBase(s_test.StormPkgTest):

    pkgprotos = (
        os.path.join(DIRNAME, "src/pkgs/utils/utils.yaml"),
        os.path.join(DIRNAME, "src/pkgs/ipapi/ipapi.yaml"),
    )

    @contextlib.asynccontextmanager
    async def getFakeCore(self):
        """A Cortex with slib.ipapi pointed at a fake ip-api.com. Yields (core, fake)."""
        async with FakeIpApi() as fake:
            async with self.getTestCore() as core:
                await core.callStorm('$lib.globals.set("slib:ipapi:url", $url)', opts={"vars": {"url": fake.url}})
                yield core, fake

    async def query(self, core, text=QUERY, warns=False, opts=None):
        msgs = await core.stormlist(text, opts=opts)
        if warns:
            self.stormHasNoErr(msgs)
        else:
            self.stormHasNoWarnErr(msgs)
        return msgs


class IpApiPkgTest(IpApiBase):

    async def test_ipapi_pkg(self):
        async with self.getTestCore() as core:
            for cmd in CMDS:
                self.isin(cmd, core.stormcmds)
            for mod in MODS:
                self.isin(mod, core.stormmods)
                self.stormHasNoErr(await core.stormlist(f"$mod = $lib.import({mod})"))

            pkgdef = await core.getStormPkg("slib.ipapi")
            for cdef in pkgdef["commands"]:
                for cmdinput in cdef.get("cmdinputs", ()):
                    self.nn(core.model.form(cmdinput["form"]))
            self.stormIsInPrint("IPs to query ip-api.com for", await core.stormlist("slib.ipapi.query --help"))

            # onload makes the meta:source and the default tag settings.
            self.len(1, await core.nodes(f"meta:source={SRCGUID}"))
            self.true(await core.callStorm('return($lib.globals.get("slib:ipapi:tag:enabled"))'))
            self.eq("rep.ipapi.infra", await core.callStorm('return($lib.globals.get("slib:ipapi:tag:prefix"))'))

            # Reloading the package keeps custom settings.
            await core.stormlist("slib.ipapi.admin.settag myorg")
            await core.stormlist("slib.ipapi.admin.disabletag")
            await core.addStormPkg(pkgdef)
            await core.callStorm("$lib.time.sleep(0.2)")
            self.eq("myorg", await core.callStorm('return($lib.globals.get("slib:ipapi:tag:prefix"))'))
            self.false(await core.callStorm('return($lib.globals.get("slib:ipapi:tag:enabled"))'))

    async def test_ipapi_urls(self):
        """The real free and pro endpoint URLs (replayed from cassettes, never called)."""

        async with self.getTestCore() as core:
            with vcr.use_cassette(os.path.join(CASSETTES, "free.yaml"), record_mode="none") as cass:
                await self.query(core, f"{QUERY} --yield")
                self.eq(1, cass.play_count)

        async with self.getTestCore() as core:
            self.stormHasNoErr(await core.stormlist("slib.ipapi.admin.apikey testkey"))
            with vcr.use_cassette(os.path.join(CASSETTES, "pro.yaml"), record_mode="none") as cass:
                await self.query(core)
                self.eq(1, cass.play_count)
            self.len(1, await core.nodes("inet:ipv4=8.8.8.8 +:asn"))


class IpApiQueryTest(IpApiBase):

    async def test_ipapi_query_string(self):
        async with self.getFakeCore() as (core, fake):
            msgs = await self.query(core, f"{QUERY} --yield")
            nodes = [m[1][0] for m in msgs if m[0] == "node"]
            self.eq([("inet:ipv4", 0x08080808)], nodes)
            self.eq(["8.8.8.8"], fake.ips())

            node = (await core.nodes("inet:ipv4=8.8.8.8"))[0]
            self.eq(15169, node.get("asn"))
            self.eq((39.03, -77.5), node.get("latlong"))
            self.eq("us.va.ashburn", node.get("loc"))
            self.eq("dns.google", node.get("dns:rev"))

            places = await core.nodes("geo:place")
            self.len(1, places)
            self.eq("ashburn, virginia, united states", places[0].get("name"))
            self.eq(places[0].ndef[1], node.get("place"))

            telems = await core.nodes("inet:ipv4=8.8.8.8 -> geo:telem:node")
            self.len(1, telems)
            self.eq("ashburn, virginia, united states", telems[0].get("place:name"))

            # "8.8.8.8" is also a valid inet:ipv6 (::ffff:8.8.8.8), which must not be made.
            self.len(0, await core.nodes("inet:ipv6"))

            # Without --yield, --query yields nothing.
            msgs = await self.query(core)
            self.len(0, [m for m in msgs if m[0] == "node"])

    async def test_ipapi_query_ipv6(self):
        async with self.getFakeCore() as (core, fake):
            await self.query(core, 'slib.ipapi.query --query "2001:4860:4860::8888" --yield')
            await core.nodes("[ inet:ipv6=2001:4860:4860::1 ]")
            await self.query(core, "inet:ipv6=2001:4860:4860::1 | slib.ipapi.query")
            self.eq(["2001:4860:4860::8888", "2001:4860:4860::1"], fake.ips())

            for ip in ("2001:4860:4860::8888", "2001:4860:4860::1"):
                node = (await core.nodes(f"inet:ipv6={ip}"))[0]
                self.eq(15169, node.get("asn"))
                self.eq("us.va.ashburn", node.get("loc"))
            self.len(0, await core.nodes("inet:ipv4"))

    async def test_ipapi_query_nodes(self):
        async with self.getFakeCore() as (core, fake):
            await core.nodes("[ inet:ipv4=8.8.8.8 inet:fqdn=example.com ]")

            msgs = await self.query(core, "inet:ipv4=8.8.8.8 inet:fqdn=example.com | slib.ipapi.query", warns=True)
            self.stormIsInWarn("is not supported", msgs)
            # The printable address is sent, not the inet:ipv4 int.
            self.eq(["8.8.8.8"], fake.ips())

            # Inbound nodes pass through, the IP once it's modeled.
            self.sorteq([("inet:ipv4", 0x08080808), ("inet:fqdn", "example.com")],
                        [m[1][0] for m in msgs if m[0] == "node"])
            self.eq(15169, (await core.nodes("inet:ipv4=8.8.8.8"))[0].get("asn"))

            # Unsupported forms never reach ip-api.com, which answers an empty query with the
            # requester's own IP.
            msgs = await self.query(core, "inet:fqdn=example.com | slib.ipapi.query", warns=True)
            self.stormIsInWarn("is not supported", msgs)
            self.len(1, fake.requests)

    async def test_ipapi_query_invalid(self):
        async with self.getFakeCore() as (core, fake):
            msgs = await self.query(core, "slib.ipapi.query --query not-an-ip --yield", warns=True)
            self.stormIsInWarn("was given an invalid IP address: not-an-ip", msgs)
            self.len(0, [m for m in msgs if m[0] == "node"])

            # --query ignores inbound nodes.
            await core.nodes("[ inet:ipv4=1.1.1.1 inet:ipv4=2.2.2.2 ]")
            msgs = await self.query(core, f"inet:ipv4 | {QUERY}")
            self.len(0, [m for m in msgs if m[0] == "node"])
            self.eq(["8.8.8.8"], fake.ips())

    async def test_ipapi_query_fail(self):
        async with self.getFakeCore() as (core, fake):
            fake.results["10.0.0.1"] = {"status": "fail", "message": "reserved range"}
            msgs = await self.query(core, "slib.ipapi.query --query 10.0.0.1 --yield", warns=True)
            self.stormIsInWarn("There was an error querying the IPAPI service for '10.0.0.1'", msgs)
            self.stormIsInWarn("returned a fail status for IP address: 10.0.0.1 - reserved range", msgs)
            self.len(0, [m for m in msgs if m[0] == "node"])

            # A failed inbound node passes through unchanged.
            await core.nodes("[ inet:ipv4=10.0.0.1 ]")
            msgs = await self.query(core, "inet:ipv4=10.0.0.1 | slib.ipapi.query", warns=True)
            self.eq([("inet:ipv4", 0x0A000001)], [m[1][0] for m in msgs if m[0] == "node"])
            self.none((await core.nodes("inet:ipv4=10.0.0.1"))[0].get("asn"))

    async def test_ipapi_batch(self):
        async with self.getFakeCore() as (core, fake):
            fake.results["2.2.2.2"] = {"status": "fail", "message": "reserved range"}
            await core.nodes("[ inet:ipv4=1.1.1.1 inet:ipv4=2.2.2.2 inet:ipv4=3.3.3.3 ]")

            msgs = await self.query(core, "inet:ipv4 | slib.ipapi.query", warns=True)
            self.stormIsInWarn("error querying the IPAPI service for '2.2.2.2'", msgs)

            # One batch request, no single IP requests.
            self.eq([], fake.ips())
            self.len(1, fake.batches())
            self.sorteq(["1.1.1.1", "2.2.2.2", "3.3.3.3"], fake.batches()[0])

            # Every inbound node comes back out, including the failed one.
            self.sorteq([0x01010101, 0x02020202, 0x03030303],
                        [m[1][0][1] for m in msgs if m[0] == "node"])
            self.len(1, await core.nodes("inet:ipv4=1.1.1.1 +:asn"))
            self.len(1, await core.nodes("inet:ipv4=3.3.3.3 +:asn"))
            self.len(0, await core.nodes("inet:ipv4=2.2.2.2 +:asn"))

    async def test_ipapi_batch_chunks(self):
        async with self.getFakeCore() as (core, fake):
            await core.nodes("for $i in $lib.range(150) { [ inet:ipv4=`10.0.0.{$i}` ] }")
            msgs = await self.query(core, "inet:ipv4 | slib.ipapi.query")
            self.eq([100, 50], [len(b) for b in fake.batches()])
            self.len(150, [m for m in msgs if m[0] == "node"])

    async def test_ipapi_batch_lib(self):
        async with self.getFakeCore() as (core, fake):
            retn = await core.callStorm("return($lib.import(slib.ipapi.lib).queryBatch((1.1.1.1, 2.2.2.2)))")
            self.true(retn["status"])
            self.eq(["1.1.1.1", "2.2.2.2"], [r["data"]["query"] for r in retn["data"]])

            # privsep.queryBatch chunks by 100.
            ips = [f"10.0.1.{i}" for i in range(201)]
            retn = await core.callStorm("return($lib.import(slib.ipapi.privsep).queryBatch($ips))", opts={"vars": {"ips": ips}})
            self.eq(201, len(retn["data"]))
            self.eq([2, 100, 100, 1], [len(b) for b in fake.batches()])

            for bad in ("1.1.1.1", ["1.1.1.1", 5]):
                retn = await core.callStorm("return($lib.import(slib.ipapi.privsep).queryBatch($ips))", opts={"vars": {"ips": bad}})
                self.false(retn["status"])
                self.isin("requires a list of IP address strings", retn["mesg"])

    async def test_ipapi_batch_errors(self):
        async with self.getFakeCore() as (core, fake):
            await core.nodes("[ inet:ipv4=1.1.1.1 inet:ipv4=2.2.2.2 ]")

            # A batch request that fails fails each node, without erroring the command.
            fake.replies.append((500, {}, "Internal Server Error"))
            msgs = await self.query(core, "inet:ipv4 | slib.ipapi.query", warns=True)
            self.stormIsInWarn("HTTP 500", msgs)
            self.len(2, [m for m in msgs if m[0] == "node"])

            # A batch answer that isn't a list.
            fake.replies.append((200, {}, {"status": "fail", "message": "invalid query"}))
            msgs = await self.query(core, "inet:ipv4 | slib.ipapi.query", warns=True)
            self.stormIsInWarn("returned a dict instead of a list", msgs)

            # A batch answer with too few results.
            fake.replies.append((200, {}, [dict(RAW_DATA, query="1.1.1.1")]))
            msgs = await self.query(core, "inet:ipv4 | slib.ipapi.query", warns=True)
            self.stormIsInWarn("no result in the batch response", msgs)
            self.len(1, await core.nodes("inet:ipv4=1.1.1.1 +:asn"))


class IpApiHttpTest(IpApiBase):

    async def test_ipapi_shape(self):
        """privsep renames "as" to "as_" and parses it into asnum and asorg."""

        async with self.getFakeCore() as (core, fake):
            q = "return($lib.import(slib.ipapi.privsep).query(8.8.8.8))"
            for asfield, asnum, asorg in (
                ("AS15169 Google LLC", 15169, "Google LLC"),
                ("AS64512", 64512, ""),
                ("AS007 Bond", 7, "Bond"),
                ("", None, ""),
                ("weird", None, ""),
            ):
                fake.results["8.8.8.8"] = data(**{"as": asfield})
                retn = await core.callStorm(q)
                self.true(retn["status"])
                self.eq((asfield, asnum, asorg), (retn["data"]["as_"], retn["data"]["asnum"], retn["data"]["asorg"]))
                self.notin("as", retn["data"])

            fake.results["8.8.8.8"] = {k: v for k, v in RAW_DATA.items() if k != "as"}
            retn = await core.callStorm(q)
            self.eq(("", None), (retn["data"]["as_"], retn["data"]["asnum"]))

    async def test_ipapi_ratelimit_retry(self):
        async with self.getFakeCore() as (core, fake):
            fake.replies.append((429, {"X-Ttl": "0.3"}, {"status": "fail", "message": "rate limited"}))
            start = time.monotonic()
            await self.query(core)
            self.ge(time.monotonic() - start, 0.25)
            self.eq(["8.8.8.8", "8.8.8.8"], fake.ips())
            self.len(1, await core.nodes("inet:ipv4=8.8.8.8 +:asn"))

    async def test_ipapi_ratelimit_capped(self):
        async with self.getFakeCore() as (core, fake):
            for _ in range(5):
                fake.replies.append((429, {"X-Ttl": "0.05"}, {"status": "fail", "message": "rate limited"}))
            msgs = await self.query(core, warns=True)
            self.stormIsInWarn("still rate limiting requests after 3 retries", msgs)
            # The first request, and 3 retries.
            self.len(4, fake.requests)

    async def test_ipapi_ratelimit_shared(self):
        async with self.getFakeCore() as (core, fake):
            # A response with no requests left makes the next /json request wait for the reset.
            fake.headers = {"X-Rl": "0", "X-Ttl": "0.4"}
            await self.query(core)
            self.nn(await core.callStorm('return($lib.globals.get("slib:ipapi:ratelimit:json:until"))'))
            fake.headers = {"X-Rl": "44", "X-Ttl": "60"}

            # /batch has its own limit, so it doesn't wait.
            start = time.monotonic()
            await core.callStorm("return($lib.import(slib.ipapi.lib).queryBatch((1.1.1.1, 2.2.2.2)))")
            self.lt(time.monotonic() - start, 0.3)

            start = time.monotonic()
            await self.query(core, "slib.ipapi.query --query 1.1.1.1")
            self.ge(time.monotonic() - start, 0.2)

            # One request left (X-Rl 1) doesn't wait.
            await core.callStorm('$lib.globals.pop("slib:ipapi:ratelimit:json:until")')
            fake.headers = {"X-Rl": "1", "X-Ttl": "60"}
            await self.query(core)
            self.none(await core.callStorm('return($lib.globals.get("slib:ipapi:ratelimit:json:until"))'))

    async def test_ipapi_http_errors(self):
        async with self.getFakeCore() as (core, fake):
            fake.replies.append((500, {}, "Internal Server Error"))
            msgs = await self.query(core, warns=True)
            self.stormIsInWarn("An HTTP error occurred while trying to query ip-api.com for 8.8.8.8 - HTTP 500", msgs)

            fake.replies.append((200, {}, "<html><body>Service temporarily unavailable</body></html>"))
            msgs = await self.query(core, warns=True)
            self.stormIsInWarn("returned invalid JSON for 8.8.8.8", msgs)

            # Nothing listening.
            await core.callStorm('$lib.globals.set("slib:ipapi:url", "http://127.0.0.1:1")')
            msgs = await self.query(core, warns=True)
            self.stormIsInWarn("An HTTP error occurred while trying to query ip-api.com for 8.8.8.8", msgs)

            retn = await core.callStorm("return($lib.import(slib.ipapi.lib).query(8.8.8.8))")
            self.false(retn["status"])
            self.none(retn["data"])

    async def test_ipapi_headers(self):
        async with self.getTestCore() as core:
            q = "return($lib.import(slib.ipapi.privsep)._ttl($headers))"
            for headers, millis in (
                ({"X-Ttl": "5"}, 5000),
                ({"x-ttl": "0.25"}, 250),
                ({"X-TTL": "1.5"}, 1500),
                ({"X-Ttl": "007"}, 7000),
                ({"X-Ttl": "soon"}, 60000),
                ({"X-Ttl": "-1"}, 60000),
                ({}, 60000),
            ):
                self.eq(millis, await core.callStorm(q, opts={"vars": {"headers": headers}}), msg=headers)


class IpApiKeyTest(IpApiBase):

    async def test_ipapi_keys(self):
        async with self.getFakeCore() as (core, fake):
            user = await core.auth.addUser("user")
            await user.addRule((True, ("node",)))
            await user.addRule((True, ("slib", "ipapi", "user")))
            uopts = {"user": user.iden}

            def keys():
                return [r["query"].get("key") for r in fake.requests]

            # No keys: the free endpoints.
            await self.query(core, opts=uopts)

            # The global key.
            self.stormIsInPrint("No global ip-api.com pro key is set", await core.stormlist("slib.ipapi.admin.apikey"))
            self.stormIsInPrint("Saved the global ip-api.com pro key", await core.stormlist("slib.ipapi.admin.apikey globalkey"))
            self.stormIsInPrint("A global ip-api.com pro key is set", await core.stormlist("slib.ipapi.admin.apikey"))
            self.stormIsInPrint("Updated the global", await core.stormlist("slib.ipapi.admin.apikey globalkey2"))
            await self.query(core, opts=uopts)

            # A user's own key takes precedence.
            msgs = await core.stormlist("slib.ipapi.apikey", opts=uopts)
            self.stormIsInPrint("You don't have an ip-api.com pro key set", msgs)
            msgs = await core.stormlist("slib.ipapi.apikey userkey", opts=uopts)
            self.stormIsInPrint("Saved your ip-api.com pro key in vault slib.ipapi:user", msgs)
            self.stormIsInPrint("is set in vault", await core.stormlist("slib.ipapi.apikey", opts=uopts))
            await self.query(core, opts=uopts)
            # Other users still use the global key.
            await self.query(core)

            self.stormIsInPrint("Deleted your ip-api.com pro key", await core.stormlist("slib.ipapi.apikey --clear", opts=uopts))
            self.stormIsInPrint("Deleted the global", await core.stormlist("slib.ipapi.admin.apikey --clear"))
            await self.query(core, opts=uopts)

            self.eq([None, "globalkey2", "userkey", "globalkey2", None], keys())

            # Users can't read the global key, or set it.
            msgs = await core.stormlist("slib.ipapi.admin.apikey somekey", opts=uopts)
            self.stormIsInErr("slib.ipapi.admin", msgs)
            await core.stormlist("slib.ipapi.admin.apikey secretkey")
            msgs = await core.stormlist("$lib.print($lib.vault.bytype(ipapi, scope=global).secrets)", opts=uopts)
            self.stormNotInPrint("secretkey", msgs)

            # Every slib.ipapi.privsep function can be called by a user, so none returns the global
            # key. (globalKey() used to.)
            msgs = await core.stormlist("$lib.print($lib.import(slib.ipapi.privsep).globalKey())", opts=uopts)
            self.stormIsInErr("globalKey", msgs)
            self.notin("secretkey", json.dumps(msgs))
            retn = await core.callStorm("return($lib.import(slib.ipapi.privsep).query(8.8.8.8))", opts=uopts)
            self.notin("secretkey", json.dumps(retn))

    async def test_ipapi_key_no_ratelimit(self):
        """The pro endpoints have no rate limit, so their responses never hold up queries."""

        async with self.getFakeCore() as (core, fake):
            await core.stormlist("slib.ipapi.admin.apikey prokey")
            fake.headers = {"X-Rl": "0", "X-Ttl": "60"}
            await self.query(core)
            self.none(await core.callStorm('return($lib.globals.get("slib:ipapi:ratelimit:json:until"))'))

    async def test_ipapi_key_scrubbed(self):
        async with self.getTestCore() as core:
            await core.stormlist("slib.ipapi.admin.apikey supersecretkey")
            await core.callStorm('$lib.globals.set("slib:ipapi:url", "http://127.0.0.1:1")')
            msgs = await core.stormlist(QUERY)
            self.stormIsInWarn("An HTTP error occurred", msgs)
            warns = " ".join(m[1]["mesg"] for m in msgs if m[0] == "warn")
            self.notin("supersecretkey", warns)


class IpApiModelTest(IpApiBase):

    async def test_ipapi_model_no_asn(self):
        """IPs with no ASN ("as", "asname", "isp" and "org" all "") are still modeled."""

        async with self.getFakeCore() as (core, fake):
            fake.results["8.8.8.8"] = data(**{"as": "", "asname": "", "isp": "", "org": ""})
            await self.query(core, f"{QUERY} --yield")

            node = (await core.nodes("inet:ipv4=8.8.8.8"))[0]
            self.none(node.get("asn"))
            self.eq((39.03, -77.5), node.get("latlong"))
            self.len(0, await core.nodes("inet:asn"))
            self.len(0, await core.nodes("ou:org"))
            self.len(1, await core.nodes("geo:telem"))

    async def test_ipapi_model_asn_and_orgs(self):
        async with self.getFakeCore() as (core, fake):
            await self.query(core)

            asns = await core.nodes("inet:asn")
            self.len(1, asns)
            self.eq(("inet:asn", 15169), asns[0].ndef)
            self.eq("google", asns[0].get("name"))

            # The AS's org, from the name after the AS number. It's also the ISP.
            owners = await core.nodes("inet:asn=15169 -> ou:org")
            self.len(1, owners)
            self.eq("google llc", owners[0].get("name"))
            self.eq(("google",), owners[0].get("names"))
            self.eq("company.isp.", owners[0].get("orgtype"))

            # The IP's WHOIS org owns the IP.
            whois = await core.nodes("inet:ipv4=8.8.8.8 <(owns)- ou:org")
            self.len(1, whois)
            self.eq("google public dns", whois[0].get("name"))
            self.none(whois[0].get("orgtype"))

            node = (await core.nodes("inet:ipv4=8.8.8.8"))[0]
            self.eq(15169, node.get("asn"))
            self.eq("dns.google", node.get("dns:rev"))

            # Re-querying keeps one AS org, and adds names rather than replacing them.
            await core.nodes("inet:asn=15169 -> ou:org [ :names+=alphabet ]")
            await self.query(core)
            owners = await core.nodes("inet:asn=15169 -> ou:org")
            self.len(1, owners)
            self.eq(("alphabet", "google"), owners[0].get("names"))

    async def test_ipapi_model_asn_owner(self):
        async with self.getFakeCore() as (core, fake):
            # The owner falls back to the ISP when "as" only has the number.
            fake.results["8.8.8.8"] = data(**{"as": "AS64512", "asname": "", "org": "", "reverse": ""})
            await self.query(core)

            asn = (await core.nodes("inet:asn=64512"))[0]
            self.none(asn.get("name"))
            owner = (await core.nodes("inet:asn=64512 -> ou:org"))[0]
            self.eq("google llc", owner.get("name"))
            self.none(owner.get("names"))
            self.eq("company.isp.", owner.get("orgtype"))
            self.len(0, await core.nodes("inet:ipv4=8.8.8.8 <(owns)- ou:org"))
            self.none((await core.nodes("inet:ipv4=8.8.8.8"))[0].get("dns:rev"))

        async with self.getFakeCore() as (core, fake):
            # The AS's org isn't the ISP.
            fake.results["8.8.8.8"] = data(isp="Some Reseller")
            await self.query(core)
            owner = (await core.nodes("inet:asn=15169 -> ou:org"))[0]
            self.eq("google llc", owner.get("name"))
            self.none(owner.get("orgtype"))

        async with self.getFakeCore() as (core, fake):
            fake.results["8.8.8.8"] = data(**{"as": "not-a-valid-asn-format"})
            await self.query(core, f"{QUERY} --yield")
            self.len(1, await core.nodes("inet:ipv4=8.8.8.8"))
            self.len(0, await core.nodes("inet:asn"))

    async def test_ipapi_model_place_and_telem(self):
        async with self.getFakeCore() as (core, fake):
            # An existing pol:country is reused, not duplicated.
            await core.nodes("[ pol:country=* :iso2=us :name='united states' ]")
            await self.query(core)

            places = await core.nodes("geo:place")
            self.len(1, places)
            self.eq("us.va.ashburn", places[0].get("loc"))

            telem = (await core.nodes("geo:telem"))[0]
            self.eq(("inet:ipv4", 0x08080808), telem.get("node"))
            self.eq(places[0].ndef[1], telem.get("place"))
            self.eq("us.va.ashburn", telem.get("place:loc"))
            self.eq("us", telem.get("place:country:code"))
            first = telem.get("time")
            self.nn(first)

            countries = await core.nodes("pol:country")
            self.len(1, countries)
            self.eq(countries[0].ndef[1], telem.get("place:country"))

            # Re-querying the same IP at the same place reuses the telem and keeps its :time.
            await self.query(core)
            telems = await core.nodes("geo:telem")
            self.len(1, telems)
            self.eq(first, telems[0].get("time"))

        async with self.getFakeCore() as (core, fake):
            await self.query(core)
            countries = await core.nodes("pol:country")
            self.len(1, countries)
            self.eq("us", countries[0].get("iso2"))

        async with self.getFakeCore() as (core, fake):
            fake.results["8.8.8.8"] = data(countryCode="USA")
            await self.query(core)
            telem = (await core.nodes("geo:telem"))[0]
            self.none(telem.get("place:country"))
            self.none(telem.get("place:country:code"))
            self.len(0, await core.nodes("pol:country"))

    async def test_ipapi_model_place_names_and_loc(self):
        async with self.getFakeCore() as (core, fake):
            # Empty place name parts are skipped.
            fake.results["8.8.8.8"] = data(city="")
            await self.query(core)
            self.eq(["virginia, united states"], [n.get("name") for n in await core.nodes("geo:place")])

        async with self.getFakeCore() as (core, fake):
            # Each loc part must be under the one before it, so a missing region drops the city.
            fake.results["8.8.8.8"] = data(region="", city="St. Louis")
            await self.query(core)
            self.eq("us", (await core.nodes("inet:ipv4=8.8.8.8"))[0].get("loc"))
            fake.results["8.8.8.8"] = data(region="MO", city="St. Louis")
            await self.query(core)
            self.eq("us.mo.st louis", (await core.nodes("inet:ipv4=8.8.8.8"))[0].get("loc"))

        async with self.getFakeCore() as (core, fake):
            fake.results["8.8.8.8"] = data(countryCode="")
            await self.query(core)
            node = (await core.nodes("inet:ipv4=8.8.8.8"))[0]
            self.none(node.get("loc"))
            self.eq((39.03, -77.5), node.get("latlong"))

    async def test_ipapi_model_source_edges(self):
        async with self.getFakeCore() as (core, fake):
            await self.query(core)
            seen = await core.nodes(f"meta:source={SRCGUID} -(seen)> *")
            self.eq(["geo:telem", "inet:asn", "inet:ipv4"], sorted(n.ndef[0] for n in seen))

    async def test_ipapi_model_invalid_ip(self):
        async with self.getTestCore() as core:
            msgs = await core.stormlist("yield $lib.import(slib.ipapi.lib).modelResult(({'query': 'nope'}), (null))")
            self.stormIsInWarn("ip-api.com returned an invalid IP address: nope", msgs)
            self.len(0, await core.nodes("inet:ipv4"))


class IpApiTagTest(IpApiBase):

    async def test_ipapi_tags(self):
        async with self.getFakeCore() as (core, fake):
            await self.query(core)
            tags = (await core.nodes("inet:ipv4=8.8.8.8"))[0].tags
            self.isin("rep.ipapi.infra.hosting", tags)
            self.notin("rep.ipapi.infra.mobile", tags)
            self.notin("rep.ipapi.infra.proxy", tags)

        async with self.getFakeCore() as (core, fake):
            fake.results["8.8.8.8"] = data(hosting=False, proxy=True, mobile=True)
            await self.query(core)
            tags = (await core.nodes("inet:ipv4=8.8.8.8"))[0].tags
            self.isin("rep.ipapi.infra.proxy", tags)
            self.isin("rep.ipapi.infra.mobile", tags)
            self.notin("rep.ipapi.infra.hosting", tags)

        async with self.getFakeCore() as (core, fake):
            msgs = await core.stormlist("slib.ipapi.admin.settag Rep.MyOrg")
            self.stormHasNoErr(msgs)
            self.stormIsInPrint("#rep.myorg.hosting", msgs)
            await self.query(core)
            self.isin("rep.myorg.hosting", (await core.nodes("inet:ipv4=8.8.8.8"))[0].tags)

            self.stormHasNoErr(await core.stormlist("slib.ipapi.admin.disabletag"))
            await core.nodes("inet:ipv4=8.8.8.8 | [ -#rep ]")
            await self.query(core)
            self.eq({}, (await core.nodes("inet:ipv4=8.8.8.8"))[0].tags)

    async def test_ipapi_settag(self):
        async with self.getTestCore() as core:
            for prefix, mesg in (("''", "non-empty tag prefix"), ('"not a..tag"', "requires a valid tag prefix")):
                self.stormIsInErr(mesg, await core.stormlist(f"slib.ipapi.admin.settag {prefix}"))
                self.eq("rep.ipapi.infra", await core.callStorm('return($lib.globals.get("slib:ipapi:tag:prefix"))'))

            await core.callStorm('$lib.globals.pop("slib:ipapi:tag:prefix")')
            msgs = await core.stormlist("slib.ipapi.admin.enabletag")
            self.stormHasNoErr(msgs)
            self.stormIsInWarn("no tag prefix is set", msgs)
            await core.stormlist("slib.ipapi.admin.settag rep.ipapi")
            self.stormHasNoWarnErr(await core.stormlist("slib.ipapi.admin.enabletag"))

    async def test_ipapi_getipapitag(self):
        async with self.getTestCore() as core:
            q = "return($lib.import(slib.ipapi.privsep).getIpApiTag())"
            self.eq("rep.ipapi.infra", await core.callStorm(q))

            await core.nodes("slib.ipapi.admin.disabletag")
            self.none(await core.callStorm(q))

            await core.nodes("slib.ipapi.admin.enabletag")
            await core.nodes('$lib.globals.pop("slib:ipapi:tag:prefix")')
            self.stormIsInErr("tag prefix is not set", await core.stormlist(q))

            await core.nodes('$lib.globals.set("slib:ipapi:tag:prefix", "bad..tag")')
            self.stormIsInErr('tag prefix "bad..tag" is not a valid tag', await core.stormlist(q))

    async def test_ipapi_bad_tag_config(self):
        """A bad tag setting only means untagged results, the query still runs."""

        async with self.getFakeCore() as (core, fake):
            await core.nodes('$lib.globals.pop("slib:ipapi:tag:prefix")')
            msgs = await self.query(core, f"{QUERY} --yield", warns=True)
            self.stormIsInWarn("Querying without tags", msgs)
            node = (await core.nodes("inet:ipv4=8.8.8.8"))[0]
            self.eq(15169, node.get("asn"))
            self.eq({}, node.tags)


class IpApiPermsTest(IpApiBase):

    async def test_ipapi_perms(self):
        async with self.getFakeCore() as (core, fake):
            admin = await core.auth.addUser("admin")
            await admin.addRule((True, ("slib", "ipapi", "admin")))

            # A user needs no perms on globals, vaults or $lib.inet.http, only slib.ipapi.user
            # and node edits.
            user = await core.auth.addUser("user")
            await user.addRule((True, ("node",)))
            await user.addRule((True, ("slib", "ipapi", "user")))

            nobody = await core.auth.addUser("nobody")

            await self.query(core, f"{QUERY} --yield", opts={"user": user.iden})
            self.len(1, await core.nodes("inet:ipv4=8.8.8.8 +:asn"))

            self.stormIsInErr("slib.ipapi.user", await core.stormlist(QUERY, opts={"user": nobody.iden}))
            self.stormIsInErr("slib.ipapi.admin", await core.stormlist("slib.ipapi.admin.settag x", opts={"user": user.iden}))

            for cmd in ("slib.ipapi.admin.settag adminprefix", "slib.ipapi.admin.disabletag", "slib.ipapi.admin.enabletag"):
                self.stormHasNoErr(await core.stormlist(cmd, opts={"user": admin.iden}))
            self.eq("adminprefix", await core.callStorm('return($lib.globals.get("slib:ipapi:tag:prefix"))'))

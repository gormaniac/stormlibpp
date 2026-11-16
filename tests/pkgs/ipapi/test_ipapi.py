"""Tests for the slib.ipapi Storm package. ip-api.com is mocked with VCR cassettes."""

import contextlib
import os
import time

import synapse.tests.utils as s_test
import vcr

from ... import DIRNAME

CASSETTES = os.path.join(DIRNAME, "tests/pkgs/ipapi/cassettes")

CMDS = ("slib.ipapi.query", "slib.ipapi.admin.settag", "slib.ipapi.admin.disabletag", "slib.ipapi.admin.enabletag")
MODS = ("slib.ipapi.lib", "slib.ipapi.privsep", "slib.ipapi.admin")

# A successful ip-api.com result, the way slib.ipapi.privsep.query() returns it (with "as" as "as_").
SUCCESS_DATA = {
    "query": "8.8.8.8", "status": "success", "country": "United States", "countryCode": "US",
    "region": "VA", "regionName": "Virginia", "city": "Ashburn", "zip": "20149", "lat": 39.03,
    "lon": -77.5, "timezone": "America/New_York", "isp": "Google LLC", "org": "Google Public DNS",
    "as_": "AS15169 Google LLC", "asname": "GOOGLE", "mobile": False, "proxy": False, "hosting": True,
}

MODEL = "$lib.import(slib.ipapi.lib).modelResult($data, $prefix)"


@contextlib.contextmanager
def cassette(name):
    """Play a cassette, failing on any request it doesn't have."""
    with vcr.use_cassette(os.path.join(CASSETTES, f"{name}.yaml"), record_mode="none") as cass:
        yield cass


class IpApiTest(s_test.StormPkgTest):

    pkgprotos = (
        os.path.join(DIRNAME, "src/pkgs/utils/utils.yaml"),
        os.path.join(DIRNAME, "src/pkgs/ipapi/ipapi.yaml"),
    )

    async def model(self, core, data, prefix="rep.ipapi.infra"):
        msgs = await core.stormlist(MODEL, opts={"vars": {"data": data, "prefix": prefix}})
        self.stormHasNoWarnErr(msgs)

    async def test_ipapi_pkg(self):
        async with self.getTestCore() as core:
            for cmd in CMDS:
                self.isin(cmd, core.stormcmds)
            for mod in MODS:
                self.isin(mod, core.stormmods)
                self.stormHasNoErr(await core.stormlist(f"$mod = $lib.import({mod})"))

            msgs = await core.stormlist("slib.ipapi.query --help")
            self.stormIsInPrint("IPs to query ip-api.com for", msgs)

            # onload makes the meta:source and the default tag settings.
            self.len(1, await core.nodes("meta:source=c177b2a9c0eff5c2984946d439de23ea"))
            self.true(await core.callStorm('return($lib.globals.get("slib:ipapi:tag:enabled"))'))
            self.eq("rep.ipapi.infra", await core.callStorm('return($lib.globals.get("slib:ipapi:tag:prefix"))'))

            # Reloading the package keeps custom settings.
            await core.stormlist("slib.ipapi.admin.settag myorg")
            await core.stormlist("slib.ipapi.admin.disabletag")
            pkgdef = await core.getStormPkg("slib.ipapi")
            await core.addStormPkg(pkgdef)
            await core.callStorm("$lib.time.sleep(0.2)")
            self.eq("myorg", await core.callStorm('return($lib.globals.get("slib:ipapi:tag:prefix"))'))
            self.false(await core.callStorm('return($lib.globals.get("slib:ipapi:tag:enabled"))'))

    async def test_ipapi_query_success(self):
        async with self.getTestCore() as core:
            with cassette("success") as cass:
                msgs = await core.stormlist("slib.ipapi.query --query 8.8.8.8 --yield")
                self.stormHasNoWarnErr(msgs)
                self.eq(1, cass.play_count)

            nodes = [m[1] for m in msgs if m[0] == "node"]
            self.len(1, nodes)
            self.eq(("inet:ipv4", 0x08080808), nodes[0][0])

            ipv4 = (await core.nodes("inet:ipv4=8.8.8.8"))[0]
            self.eq(15169, ipv4.get("asn"))
            self.eq((39.03, -77.5), ipv4.get("latlong"))
            self.eq("us.va.ashburn", ipv4.get("loc"))
            self.isin("rep.ipapi.infra.hosting", ipv4.tags)
            self.notin("rep.ipapi.infra.mobile", ipv4.tags)
            self.notin("rep.ipapi.infra.proxy", ipv4.tags)

            orgs = await core.nodes("inet:asn=15169 -> ou:org")
            self.len(1, orgs)
            self.eq("google llc", orgs[0].get("name"))
            self.eq("company.isp.", orgs[0].get("orgtype"))
            self.eq(("15169", "as15169 google llc", "google"), orgs[0].get("names"))

            places = await core.nodes("geo:place")
            self.len(1, places)
            self.eq("ashburn, virginia, united states", places[0].get("name"))
            self.eq(places[0].ndef[1], ipv4.get("place"))

            telems = await core.nodes("inet:ipv4=8.8.8.8 -> geo:telem:node")
            self.len(1, telems)
            self.eq("ashburn, virginia, united states", telems[0].get("place:name"))

            # "8.8.8.8" is also a valid inet:ipv6 (::ffff:8.8.8.8), which must not be made.
            self.len(0, await core.nodes("inet:ipv6"))

    async def test_ipapi_query_nodes(self):
        async with self.getTestCore() as core:
            await core.nodes("[ inet:ipv4=8.8.8.8 inet:fqdn=example.com ]")

            # The printable address is sent (the cassette's URL), not the inet:ipv4 int.
            with cassette("success") as cass:
                msgs = await core.stormlist("inet:ipv4=8.8.8.8 inet:fqdn=example.com | slib.ipapi.query")
                self.stormHasNoErr(msgs)
                self.stormIsInWarn("is not supported", msgs)
                self.eq(1, cass.play_count)

            # Without --yield the inbound nodes pass through.
            nodes = [m[1][0] for m in msgs if m[0] == "node"]
            self.sorteq([("inet:ipv4", 0x08080808), ("inet:fqdn", "example.com")], nodes)
            self.eq(15169, (await core.nodes("inet:ipv4=8.8.8.8"))[0].get("asn"))

            # Unsupported forms never reach ip-api.com.
            with cassette("success") as cass:
                msgs = await core.stormlist("inet:fqdn=example.com | slib.ipapi.query")
                self.stormIsInWarn("is not supported", msgs)
                self.eq(0, cass.play_count)

    async def test_ipapi_query_ipv6(self):
        async with self.getTestCore() as core:
            await core.nodes("[ inet:ipv6=2001:4860:4860::8888 ]")
            with cassette("success_ipv6"):
                msgs = await core.stormlist("inet:ipv6=2001:4860:4860::8888 | slib.ipapi.query --yield")
                self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes("inet:ipv6=2001:4860:4860::8888")
            self.len(1, nodes)
            self.eq(15169, nodes[0].get("asn"))
            self.eq("us.va.ashburn", nodes[0].get("loc"))
            self.len(0, await core.nodes("inet:ipv4"))

    async def test_ipapi_query_no_asn(self):
        async with self.getTestCore() as core:
            with cassette("success_noas"):
                msgs = await core.stormlist("slib.ipapi.query --query 192.0.2.1")
                self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes("inet:ipv4=192.0.2.1")
            self.len(1, nodes)
            self.none(nodes[0].get("asn"))
            self.len(0, await core.nodes("inet:asn"))

    async def test_ipapi_query_errors(self):
        async with self.getTestCore() as core:
            for name, ip, mesg in (
                ("fail", "10.0.0.1", "returned a fail status for IP address: 10.0.0.1 - reserved range"),
                ("servererror", "1.2.3.4", "HTTP 500"),
                ("badjson", "1.2.3.4", "returned invalid JSON"),
            ):
                with cassette(name):
                    msgs = await core.stormlist(f"slib.ipapi.query --query {ip} --yield")
                self.stormHasNoErr(msgs)
                self.stormIsInWarn("There was an error querying the IPAPI service", msgs)
                self.stormIsInWarn(mesg, msgs)
                self.len(0, [m for m in msgs if m[0] == "node"])

            with cassette("servererror"):
                retn = await core.callStorm("return($lib.import(slib.ipapi.lib).query(1.2.3.4))")
            self.false(retn["status"])
            self.none(retn["data"])

    async def test_ipapi_ratelimit_retry(self):
        async with self.getTestCore() as core:
            with cassette("ratelimit_retry") as cass:
                start = time.monotonic()
                msgs = await core.stormlist("slib.ipapi.query --query 8.8.8.8")
                took = time.monotonic() - start
                self.stormHasNoWarnErr(msgs)
                self.eq(2, cass.play_count)
            # X-Ttl was 0.3 seconds.
            self.ge(took, 0.25)
            self.len(1, await core.nodes("inet:ipv4=8.8.8.8 +:asn"))

            with cassette("ratelimit_giveup") as cass:
                msgs = await core.stormlist("slib.ipapi.query --query 8.8.8.8")
                self.stormIsInWarn("gave up after 5 retries", msgs)
                self.eq(6, cass.play_count)

    async def test_ipapi_ratelimit_shared(self):
        async with self.getTestCore() as core:
            # The first response says no requests are left, so the next query waits for the reset.
            with cassette("zero_left") as cass:
                self.stormHasNoWarnErr(await core.stormlist("slib.ipapi.query --query 1.1.1.1"))
                until = await core.callStorm('return($lib.globals.get("slib:ipapi:ratelimit:until"))')
                self.nn(until)

                start = time.monotonic()
                self.stormHasNoWarnErr(await core.stormlist("slib.ipapi.query --query 2.2.2.2"))
                self.ge(time.monotonic() - start, 0.3)
                self.eq(2, cass.play_count)

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

    async def test_ipapi_model(self):
        async with self.getTestCore() as core:
            # Empty place name parts are skipped.
            await self.model(core, dict(SUCCESS_DATA, city=""))
            self.eq(["virginia, united states"], [n.get("name") for n in await core.nodes("geo:place")])

        async with self.getTestCore() as core:
            # Each loc part must be under the one before it, so a missing region drops the city.
            await self.model(core, dict(SUCCESS_DATA, region="", city="St. Louis"))
            self.eq("us", (await core.nodes("inet:ipv4=8.8.8.8"))[0].get("loc"))
            await self.model(core, dict(SUCCESS_DATA, region="MO", city="St. Louis"))
            self.eq("us.mo.st louis", (await core.nodes("inet:ipv4=8.8.8.8"))[0].get("loc"))

        async with self.getTestCore() as core:
            await self.model(core, dict(SUCCESS_DATA, countryCode=""))
            node = (await core.nodes("inet:ipv4=8.8.8.8"))[0]
            self.none(node.get("loc"))
            self.eq((39.03, -77.5), node.get("latlong"))

        async with self.getTestCore() as core:
            # A malformed "as" field doesn't error, and makes no inet:asn.
            await self.model(core, dict(SUCCESS_DATA, as_="not-a-valid-asn-format"))
            self.len(1, await core.nodes("inet:ipv4=8.8.8.8"))
            self.len(0, await core.nodes("inet:asn"))

        async with self.getTestCore() as core:
            await self.model(core, dict(SUCCESS_DATA, proxy=True, mobile=True), prefix="myorg")
            tags = (await core.nodes("inet:ipv4=8.8.8.8"))[0].tags
            self.isin("myorg.hosting", tags)
            self.isin("myorg.proxy", tags)
            self.isin("myorg.mobile", tags)

        async with self.getTestCore() as core:
            await self.model(core, SUCCESS_DATA, prefix=None)
            self.eq({}, (await core.nodes("inet:ipv4=8.8.8.8"))[0].tags)

    async def test_ipapi_admin(self):
        async with self.getTestCore() as core:
            self.stormHasNoErr(await core.stormlist("slib.ipapi.admin.settag myorg"))
            with cassette("success"):
                await core.stormlist("slib.ipapi.query --query 8.8.8.8")
            self.isin("myorg.hosting", (await core.nodes("inet:ipv4=8.8.8.8"))[0].tags)

            msgs = await core.stormlist("slib.ipapi.admin.settag ''")
            self.stormIsInErr("non-empty tag prefix", msgs)
            self.eq("myorg", await core.callStorm('return($lib.globals.get("slib:ipapi:tag:prefix"))'))

            self.stormHasNoErr(await core.stormlist("slib.ipapi.admin.disabletag"))
            await core.nodes("inet:ipv4=8.8.8.8 | [ -#myorg ]")
            with cassette("success"):
                await core.stormlist("slib.ipapi.query --query 8.8.8.8")
            self.eq({}, (await core.nodes("inet:ipv4=8.8.8.8"))[0].tags)

            self.stormHasNoErr(await core.stormlist("slib.ipapi.admin.enabletag"))
            self.true(await core.callStorm('return($lib.globals.get("slib:ipapi:tag:enabled"))'))

            # Enabled without a prefix is a config error.
            await core.callStorm('$lib.globals.pop("slib:ipapi:tag:prefix")')
            msgs = await core.stormlist("slib.ipapi.query --query 8.8.8.8")
            self.stormIsInErr("tag prefix is not set", msgs)

    async def test_ipapi_perms(self):
        async with self.getTestCore() as core:
            admin = await core.auth.addUser("admin")
            await admin.addRule((True, ("slib", "ipapi", "admin")))

            # A user needs no perms on globals or $lib.inet.http, only slib.ipapi.user and node edits.
            user = await core.auth.addUser("user")
            await user.addRule((True, ("node",)))
            await user.addRule((True, ("slib", "ipapi", "user")))

            nobody = await core.auth.addUser("nobody")

            with cassette("success"):
                msgs = await core.stormlist("slib.ipapi.query --query 8.8.8.8 --yield", opts={"user": user.iden})
            self.stormHasNoWarnErr(msgs)
            self.len(1, await core.nodes("inet:ipv4=8.8.8.8 +:asn"))

            msgs = await core.stormlist("slib.ipapi.query --query 8.8.8.8", opts={"user": nobody.iden})
            self.stormIsInErr("slib.ipapi.user", msgs)

            msgs = await core.stormlist("slib.ipapi.admin.settag someprefix", opts={"user": user.iden})
            self.stormIsInErr("slib.ipapi.admin", msgs)

            for cmd in ("slib.ipapi.admin.settag adminprefix", "slib.ipapi.admin.disabletag", "slib.ipapi.admin.enabletag"):
                self.stormHasNoErr(await core.stormlist(cmd, opts={"user": admin.iden}))
            self.eq("adminprefix", await core.callStorm('return($lib.globals.get("slib:ipapi:tag:prefix"))'))

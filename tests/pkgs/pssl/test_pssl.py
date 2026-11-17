"""Tests for the slib.pssl Storm package. CIRCL Passive SSL is mocked with VCR cassettes."""

import base64
import contextlib
import os

import synapse.tests.utils as s_test
import vcr

from ... import DIRNAME

# Real CIRCL responses, recorded with scripts/pkgs/record_circl.py.
CASSETTES = os.path.join(DIRNAME, "tests/pkgs/pssl/cassettes")

CMDS = ("slib.pssl.lookup", "slib.pssl.admin.key")
MODS = ("slib.pssl.lib", "slib.pssl.privsep", "slib.pssl.lib.admin")
SOURCE = "7aa991399fab4171a80682a69a1a8d54"

AUTH = "Basic " + base64.b64encode(b"myuser:mypasswd").decode()

# The certificate in the cfetch cassette.
CIRCL_SHA1 = "7c552ab044c76d1df4f5ddf358807bfdcd07fa57"
# The certificate in the cquery cassette.
CQUERY_SHA1 = "c46fed822dadac3f31f9bb4d1a78a1d9eae4567b"


@contextlib.contextmanager
def cassette(name):
    """Play a cassette, failing on any request it doesn't have.

    The requests the package sent are in the cassette's "sent" list.
    """
    myvcr = vcr.VCR(record_mode="none")
    with myvcr.use_cassette(os.path.join(CASSETTES, f"{name}.yaml")) as cass:
        cass.sent = []
        play = cass.play_response

        def playAndSave(req):
            resp = play(req)
            cass.sent.append(req)
            return resp

        cass.play_response = playAndSave
        yield cass


class PsslTest(s_test.StormPkgTest):

    pkgprotos = (
        os.path.join(DIRNAME, "src/pkgs/utils/utils.yaml"),
        os.path.join(DIRNAME, "src/pkgs/pssl/pssl.yaml"),
    )

    async def auth(self, core):
        msgs = await core.stormlist("slib.pssl.admin.key myuser mypasswd")
        self.stormHasNoWarnErr(msgs)

    async def test_pssl_pkg(self):
        async with self.getTestCore() as core:
            for cmd in CMDS:
                self.isin(cmd, core.stormcmds)
            for mod in MODS:
                self.isin(mod, core.stormmods)
                self.stormHasNoErr(await core.stormlist(f"$mod = $lib.import({mod})"))

            msgs = await core.stormlist("slib.pssl.lookup --help")
            self.stormIsInPrint("CIDR blocks (/23 to /32)", msgs)

            # onload makes the meta:source.
            nodes = await core.nodes(f"meta:source={SOURCE}")
            self.len(1, nodes)
            self.eq("circl.lu passive ssl", nodes[0].get("name"))

    async def test_pssl_admin_key(self):
        async with self.getTestCore() as core:
            msgs = await core.stormlist("slib.pssl.admin.key myuser mypasswd")
            self.stormIsInPrint("Saved the CIRCL Passive SSL credentials", msgs)
            self.eq("myuser", await core.callStorm('return($lib.globals.get("slib:pssl:auth:user"))'))
            self.eq("mypasswd", await core.callStorm('return($lib.globals.get("slib:pssl:auth:passwd"))'))

            msgs = await core.stormlist("slib.pssl.admin.key")
            self.stormIsInErr("requires a username and a password", msgs)

            msgs = await core.stormlist("slib.pssl.admin.key --clear")
            self.stormIsInPrint("Removed the CIRCL Passive SSL credentials", msgs)
            self.none(await core.callStorm('return($lib.globals.get("slib:pssl:auth:user"))'))

            # No credentials, no request.
            with cassette("query_ip") as cass:
                msgs = await core.stormlist("slib.pssl.lookup --query 172.228.24.7")
                self.stormIsInErr("credentials are not set", msgs)
                self.eq(0, cass.play_count)

    async def test_pssl_perms(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            visi = await core.auth.addUser("visi")
            opts = {"user": visi.iden}

            msgs = await core.stormlist("slib.pssl.lookup --query 172.228.24.7", opts=opts)
            self.stormIsInErr("requires permission: slib.pssl.user", msgs)
            msgs = await core.stormlist("slib.pssl.admin.key a b", opts=opts)
            self.stormIsInErr("requires permission: slib.pssl.admin", msgs)

            # A user can make requests, but can't read the credentials.
            await visi.addRule((True, ("slib", "pssl", "user")))
            with cassette("query_ip"):
                retn = await core.callStorm('return($lib.import(slib.pssl.lib).query("172.228.24.7"))', opts=opts)
            self.true(retn["status"])
            msgs = await core.stormlist('$lib.print($lib.globals.get("slib:pssl:auth:passwd"))', opts=opts)
            self.stormIsInErr("must have permission globals.get", msgs)

            # Modeling runs as the user, so it needs node edit perms too.
            with cassette("query_ip"):
                msgs = await core.stormlist("slib.pssl.lookup --query 172.228.24.7", opts=opts)
            self.stormIsInErr("must have permission node.", msgs)

    async def test_pssl_requests(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            lib = "$lib.import(slib.pssl.lib)"

            with cassette("query_ip") as cass:
                retn = await core.callStorm(f'return({lib}.query("172.228.24.7"))')
                self.eq(AUTH, cass.sent[0].headers["Authorization"])
            self.true(retn["status"])
            self.len(8, retn["data"]["172.228.24.7"]["certificates"])

            with cassette("cquery"):
                retn = await core.callStorm(f"return({lib}.cquery({CQUERY_SHA1}))")
            self.true(retn["status"])
            self.eq(1066, retn["data"]["hits"])

            with cassette("cfetch"):
                retn = await core.callStorm(f"return({lib}.cfetch({CIRCL_SHA1}))")
            self.true(retn["status"])
            self.true(retn["data"]["pem"].startswith("-----BEGIN CERTIFICATE-----"))

            # CIRCL's 400 error messages are passed on.
            for name, query, mesg in (
                ("query_cidr_too_big", 'query("172.228.24.0/20")', "Maximum CIDR block size reached >/23"),
                ("query_ipv6", 'query("2a00:5980:93::14")', "IPv6 is not (yet) supported"),
                ("cfetch_missing", 'cfetch("0000000000000000000000000000000000000000")', "Not existing certificate"),
                ("cfetch_badhash", 'cfetch("notasha1")', "Incorrect format of the certificate fingerprint"),
                ("unauthorized", 'query("172.228.24.7")', "rejected the credentials"),
            ):
                with cassette(name):
                    retn = await core.callStorm(f"return({lib}.{query})")
                self.false(retn["status"])
                self.isin(mesg, retn["mesg"])

    async def test_pssl_lookup_ip(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            await core.nodes("[ inet:ipv4=172.228.24.7 ]")

            # The printable address is sent (the cassette's URL), not inet:ipv4's int.
            with cassette("query_ip") as cass:
                msgs = await core.stormlist("inet:ipv4=172.228.24.7 | slib.pssl.lookup")
                self.stormHasNoWarnErr(msgs)
                self.eq(1, cass.play_count)

            # Without --yield the inbound nodes pass through.
            self.eq([("inet:ipv4", 0xACE41807)], [m[1][0] for m in msgs if m[0] == "node"])

            self.len(8, await core.nodes("inet:tls:servercert:server=tcp://172.228.24.7"))
            self.len(8, await core.nodes("inet:ipv4=172.228.24.7 -> inet:server -> inet:tls:servercert -> crypto:x509:cert"))
            self.len(8, await core.nodes(f"meta:source={SOURCE} -(seen)> inet:tls:servercert"))

            # Not fetched, so the subject is CIRCL's.
            certs = await core.nodes("crypto:x509:cert:sha1=37221925980c05deefac014f9a72b4765e716341")
            self.len(1, certs)
            self.eq("C=JP, ST=Tokyo, L=Minato-ku, O=Sony corporation, OU=NPS, CN=psn-rsc.prod.dl.playstation.net",
                    certs[0].get("subject"))
            self.none(certs[0].get("sha256"))

            # Looking up again doesn't make more nodes.
            with cassette("query_ip"):
                msgs = await core.stormlist("slib.pssl.lookup --query 172.228.24.7 --yield")
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == "node"]
            self.len(8, nodes)
            self.eq({"inet:tls:servercert"}, {n[0][0] for n in nodes})
            self.len(8, await core.nodes("crypto:x509:cert"))
            self.len(8, await core.nodes("inet:tls:servercert"))

    async def test_pssl_lookup_cidr(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("query_cidr"):
                msgs = await core.stormlist("[ inet:cidr4=172.228.24.0/28 ] | slib.pssl.lookup --yield")
            self.stormHasNoWarnErr(msgs)
            self.len(77, [m for m in msgs if m[0] == "node"])
            self.len(9, await core.nodes("inet:server"))
            self.len(53, await core.nodes("crypto:x509:cert"))

    async def test_pssl_lookup_empty(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("query_empty"):
                msgs = await core.stormlist("slib.pssl.lookup --query 185.194.93.14 --yield --fetch")
            self.stormHasNoWarnErr(msgs)
            self.len(0, [m for m in msgs if m[0] == "node"])

            with cassette("cquery_empty") as cass:
                msgs = await core.stormlist("slib.pssl.lookup --query 0000000000000000000000000000000000000000 --yield --fetch")
                # No hits, so nothing to fetch.
                self.eq(1, cass.play_count)
            self.stormHasNoWarnErr(msgs)
            self.len(0, [m for m in msgs if m[0] == "node"])
            self.len(0, await core.nodes("crypto:x509:cert"))

    async def test_pssl_lookup_cert(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            await core.nodes(f"[ crypto:x509:cert=* :sha1={CQUERY_SHA1} ]")

            with cassette("cquery"):
                msgs = await core.stormlist(f"crypto:x509:cert:sha1={CQUERY_SHA1} | slib.pssl.lookup --yield")
            self.stormHasNoWarnErr(msgs)
            self.len(1066, [m for m in msgs if m[0] == "node"])

            # The existing cert is used.
            self.len(1, await core.nodes("crypto:x509:cert"))
            self.len(1066, await core.nodes(f"crypto:x509:cert:sha1={CQUERY_SHA1} -> inet:tls:servercert"))
            self.len(1, await core.nodes("inet:tls:servercert:server=tcp://172.231.209.35"))

            # A hash:sha1 works too.
            with cassette("cquery") as cass:
                msgs = await core.stormlist(f"[ hash:sha1={CQUERY_SHA1} ] | slib.pssl.lookup")
                self.stormHasNoWarnErr(msgs)
                self.eq(1, cass.play_count)

            msgs = await core.stormlist("[ crypto:x509:cert=* ] | slib.pssl.lookup")
            self.stormIsInWarn("has no :sha1 to look up", msgs)
            msgs = await core.stormlist("[ inet:fqdn=circl.lu ] | slib.pssl.lookup")
            self.stormIsInWarn('"inet:fqdn" is not supported', msgs)

    async def test_pssl_lookup_fetch(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("cfetch"):
                cert = await core.callStorm(
                    "$lib.import(slib.pssl.lib)"
                    f" $retn = $lib.import(slib.pssl.lib).cfetch({CIRCL_SHA1})"
                    f" return($lib.import(slib.pssl.lib).modelCfetch($retn.data, {CIRCL_SHA1}).iden())"
                )

            nodes = await core.nodes(f"crypto:x509:cert:sha1={CIRCL_SHA1}")
            self.len(1, nodes)
            node = nodes[0]
            self.eq(cert, node.iden())
            self.eq("e4c455e2cbee25cb7db41a2b40b1804d6bff048b5d54c58629ff7c7f7914f59c", node.get("sha256"))
            self.eq("0ba225d842a31945d1064ef8eea0600f", node.get("md5"))
            self.eq("062bd1".rjust(40, "0"), node.get("serial"))  # Synapse zero pads :serial
            self.eq(2, node.get("version"))
            self.eq("1.2.840.113549.1.9.1=info@circl.lu,CN=*.circl.lu,OU=Web Services,"
                    "O=CIRCL - Computer Incident Response Center Luxembourg,L=Luxembourg,ST=Luxembourg,C=LU",
                    node.get("subject"))
            self.eq("CN=LuxTrust Qualified CA,O=LuxTrust S.A.,C=LU", node.get("issuer"))
            self.eq(1405599856000, node.get("validity:notbefore"))
            self.eq(1468758256000, node.get("validity:notafter"))
            self.eq("1.2.840.113549.1.1.5", node.get("algo"))
            self.false(node.get("selfsigned"))
            self.eq(("http://crl.luxtrust.lu/LTQCA.crl",), node.get("crl:urls"))
            self.eq((("uri", "http://crl.luxtrust.lu/LTQCA.crl"),), node.get("ext:crls"))
            self.eq(("circl.lu",), node.get("identities:fqdns"))
            # identities are from the CN and SANs only, not the subject emailAddress.
            self.eq((), node.get("identities:emails"))
            # ICSI's first/last seen days.
            self.eq((16469 * 86400000, 16750 * 86400000), node.get(".seen"))

            keys = await core.nodes(f"crypto:x509:cert:sha1={CIRCL_SHA1} -> rsa:key")
            self.len(1, keys)
            self.eq(2048, keys[0].get("bits"))
            self.eq(65537, keys[0].get("pub:exp"))

    async def test_pssl_lookup_query_fetch(self):
        async with self.getTestCore() as core:
            await self.auth(core)
            with cassette("query_fetch") as cass:
                msgs = await core.stormlist("slib.pssl.lookup --query 172.228.24.7 --fetch --yield")
                self.stormHasNoWarnErr(msgs)
                self.eq(9, cass.play_count)

            nodes = [m[1][0][0] for m in msgs if m[0] == "node"]
            self.eq(8, nodes.count("inet:tls:servercert"))
            self.eq(8, nodes.count("crypto:x509:cert"))

            # Every cert is parsed, and the fetched :subject (the RFC 4514 DN) replaces CIRCL's.
            certs = await core.nodes("crypto:x509:cert")
            self.len(8, certs)
            for cert in certs:
                self.nn(cert.get("sha256"))
                self.nn(cert.get("issuer"))
                self.notin(", ", cert.get("subject"))

            # Not every cert has ICSI seen times.
            self.len(5, await core.nodes("crypto:x509:cert +.seen"))

    async def test_pssl_lookup_errors(self):
        async with self.getTestCore() as core:
            await self.auth(core)

            with cassette("query_cidr_too_big"):
                msgs = await core.stormlist("slib.pssl.lookup --query 172.228.24.0/20")
            self.stormIsInWarn("Maximum CIDR block size reached >/23", msgs)

            with cassette("unauthorized"):
                msgs = await core.stormlist("slib.pssl.lookup --query 172.228.24.7")
            self.stormIsInWarn("rejected the credentials set with slib.pssl.admin.key (HTTP 401)", msgs)

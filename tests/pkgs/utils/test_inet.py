import os

import synapse.tests.utils as s_test

from ... import DIRNAME


class InetTest(s_test.StormPkgTest):

    pkgprotos = (os.path.join(DIRNAME, "src/pkgs/utils/utils.yaml"),)

    async def test_inet_asnNum(self):
        async with self.getTestCore() as core:
            q = "return($lib.import(slib.utils.inet).asnNum($v))"
            for valu, num in (
                ("15169", 15169), ("AS15169", 15169), ("as15169", 15169), (15169, 15169),
                ("AS15169 Google LLC", 15169), (" AS13335 ", 13335),
                ("", None), (None, None), ("not-a-valid-asn-format", None), ("AS", None), ("ASX1", None),
                ("15169x", None),
            ):
                self.eq(num, await core.callStorm(q, opts={"vars": {"v": valu}}), msg=valu)

    async def test_inet_asnNode(self):
        async with self.getTestCore() as core:
            inet = "$inet = $lib.import(slib.utils.inet)"

            nodes = await core.nodes(f"{inet} yield $inet.asnNode(AS15169)")
            self.len(1, nodes)
            self.eq(("inet:asn", 15169), nodes[0].ndef)
            self.none(nodes[0].get("owner"))

            nodes = await core.nodes(f'{inet} yield $inet.asnNode("AS15169 Google LLC", orgname="Google LLC")')
            self.len(1, nodes)
            org = (await core.nodes('ou:name="google llc" -> ou:org'))[0]
            self.eq(org.ndef[1], nodes[0].get("owner"))
            self.none(org.get("orgtype"))

            # The same org name reuses the org, and names/orgtype are set on it.
            nodes = await core.nodes(
                f'{inet} yield $inet.asnNode(15169, orgname="Google LLC", names=(google, "as15169 google llc"), orgtype=company.isp)'
            )
            self.len(1, await core.nodes("ou:org"))
            org = (await core.nodes("ou:org"))[0]
            self.eq(("as15169 google llc", "google"), org.get("names"))
            self.eq("company.isp.", org.get("orgtype"))

            # No ASN number makes nothing.
            self.len(0, await core.nodes(f'{inet} yield $inet.asnNode("bogus", orgname="Nobody")'))
            self.len(0, await core.nodes("ou:name=nobody"))

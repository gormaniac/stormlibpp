import os

import synapse.tests.utils as s_test

from ... import DIRNAME

class DnsStormTest(s_test.StormPkgTest):

    assetdir = os.path.join(DIRNAME, 'tests/pkgs/testassets')
    pkgprotos = (os.path.join(DIRNAME, 'src/pkgs/dnsstorm/dnsstorm.yaml'),)

    async def test_dns_queries(self):

        async with self.getTestCore() as core:

            queries = [
                "dns.request --query google.com",
                "dns.request --query google.com --type NS",
                "dns.request --query google.com --type MX",
                "[inet:fqdn=google.com] | dns.request --type TXT",
                "dns.request --query google.com --type AAAA",
                "[inet:ipv4=1.1.1.1 inet:ipv4=8.8.8.8] | dns.request --type PTR",
                # TODO Get working examples of these
                # "dns.request --query google.com --type CNAME",
            ]

            for query in queries:
                msgs = await core.stormlist(query)
                print([m[1] for m in msgs if m[0] == 'node'])
                # TODO - Fix use of $lib.dict to remove warnings.
                # self.stormHasNoWarnErr(msgs)

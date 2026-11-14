"""Pytest suites for lookup-storm."""

import os

import synapse.tests.utils as s_test

from ... import DIRNAME


class LookupTest(s_test.StormPkgTest):
    """Tests for lookup-storm."""

    pkgprotos = (os.path.join(DIRNAME, "src/pkgs/lookup-storm/lookup-storm.yaml"),)

    async def test_lookup_queries(self):
        """Individually test all possible valid values for a lookup command."""

        async with self.getTestCore() as core:
            queries = [
                'lookup "::1234:5678"',
                'lookup "::"',
                'lookup "2001:db8:3333:4444:5555:6666:7777:8888"',
                'lookup "da39a3ee5e6b4b0d3255bfef95601890afd80709"',
                'lookup "d41d8cd98f00b204e9800998ecf8427e"',
                "lookup 1.1.1.1",
                'lookup "1.1.0.0/24"',
                'lookup "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"',
                'lookup "c:/a/path/to/test.exe"',
                r'lookup "C:\Windows\System32\calc.exe"',
                'lookup http://example.com',
                'lookup tcp://1.1.1.1:80',
            ]

            for query in queries:
                msgs = await core.stormlist(query)
                print([m[1] for m in msgs if m[0] == "node"])
                self.stormHasNoWarnErr(msgs)

    async def test_lookup_multi(self):
        """Multiple inputs to a lookup command."""

        async with self.getTestCore() as core:
            queries = [
                (
                    'lookup 1.1.1.1 "1.1.0.0/24" "2001:db8:3333:4444:5555:6666:7777:8888" '
                    '"::1234:5678" "::" 8.8.8.8 123.123.123.123 example.com "test@example.com"'
                ),
                """lookup 
                d41d8cd98f00b204e9800998ecf8427e
                da39a3ee5e6b4b0d3255bfef95601890afd80709
                e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
                """,
                r'lookup d41d8cd98f00b204e9800998ecf8427e "1.1.1.1" "C:\Windows\System32\calc.exe"',
                'lookup http://example.com tcp://1.1.1.1:80',
            ]

            for query in queries:
                msgs = await core.stormlist(query)
                print([m[1] for m in msgs if m[0] == "node"])
                self.stormHasNoWarnErr(msgs)

    async def test_lookup_read_only_empty(self):
        """Test the --read-only flag."""

        async with self.getTestCore() as core:
            query = "lookup --read-only http://example.com tcp://1.1.1.1:80"

            msgs = await core.stormlist(query)
            assert [m[1] for m in msgs if m[0] == "node"] == []
            self.stormHasNoWarnErr(msgs)

    async def test_lookup_read_only(self):
        """Test the --read-only flag."""

        async with self.getTestCore() as core:
            query1 = "[inet:server=tcp://1.1.1.1:80]"

            await core.stormlist(query1)

            query2 = "lookup --read-only http://example.com tcp://1.1.1.1:80"
            msgs = await core.stormlist(query2)

            assert len([m[1] for m in msgs if m[0] == "node"]) == 1
            self.stormHasNoWarnErr(msgs)

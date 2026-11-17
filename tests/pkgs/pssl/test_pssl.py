"""Tests for the slib.pssl Storm package. CIRCL Passive SSL is mocked with VCR cassettes."""

import contextlib
import os

import synapse.tests.utils as s_test
import vcr

from ... import DIRNAME

# Real CIRCL responses, recorded with scripts/pkgs/record_circl.py.
CASSETTES = os.path.join(DIRNAME, "tests/pkgs/pssl/cassettes")

CMDS = ("slib.pssl.lookup", "slib.pssl.admin.key")
MODS = ("slib.pssl.lib", "slib.pssl.lib.admin")


@contextlib.contextmanager
def cassette(name, **kwargs):
    """Play a cassette, failing on any request it doesn't have."""
    with vcr.use_cassette(os.path.join(CASSETTES, f"{name}.yaml"), record_mode="none", **kwargs) as cass:
        yield cass


class PsslTest(s_test.StormPkgTest):

    pkgprotos = (
        os.path.join(DIRNAME, "src/pkgs/utils/utils.yaml"),
        os.path.join(DIRNAME, "src/pkgs/pssl/pssl.yaml"),
    )

    async def test_pssl_pkg(self):
        async with self.getTestCore() as core:
            for cmd in CMDS:
                self.isin(cmd, core.stormcmds)
            for mod in MODS:
                self.isin(mod, core.stormmods)
                self.stormHasNoErr(await core.stormlist(f"$mod = $lib.import({mod})"))

            # onload makes the meta:source.
            self.len(1, await core.nodes("meta:source=7aa991399fab4171a80682a69a1a8d54"))

    # TODO - slib.pssl.admin.key

    # TODO - slib.pssl.lookup, cassettes: query_ip, query_cidr, query_empty, query_cidr_too_big,
    # query_ipv6, cquery, cquery_empty, cfetch, cfetch_missing, cfetch_badhash, query_fetch,
    # unauthorized

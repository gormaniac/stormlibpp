"""Tests for the slib.pdns Storm package. CIRCL Passive DNS is mocked with VCR cassettes."""

import contextlib
import os

import synapse.tests.utils as s_test
import vcr

from ... import DIRNAME

# Real CIRCL responses, recorded with scripts/pkgs/record_circl.py.
CASSETTES = os.path.join(DIRNAME, "tests/pkgs/pdns/cassettes")

CMDS = ("slib.pdns.lookup", "slib.pdns.admin.key")
MODS = ("slib.pdns.lib", "slib.pdns.lib.admin")


@contextlib.contextmanager
def cassette(name, **kwargs):
    """Play a cassette, failing on any request it doesn't have.

    The dribble-* request headers aren't matched by default, pass ex.
    match_on=("method", "uri", "headers") for the paginate cassette.
    """
    with vcr.use_cassette(os.path.join(CASSETTES, f"{name}.yaml"), record_mode="none", **kwargs) as cass:
        yield cass


class PdnsTest(s_test.StormPkgTest):

    pkgprotos = (os.path.join(DIRNAME, "src/pkgs/pdns/pdns.yaml"),)

    async def test_pdns_pkg(self):
        async with self.getTestCore() as core:
            for cmd in CMDS:
                self.isin(cmd, core.stormcmds)
            for mod in MODS:
                self.isin(mod, core.stormmods)
                self.stormHasNoErr(await core.stormlist(f"$mod = $lib.import({mod})"))

            # onload makes the meta:source.
            self.len(1, await core.nodes("meta:source=696c119cb73c4a079a2865108c96668a"))

    # TODO - slib.pdns.admin.key

    # TODO - slib.pdns.lookup, cassettes: domain, domain_noactive, fqdn_cname, ipv4, ipv6,
    # rrtype, empty, maxset, paginate, unauthorized

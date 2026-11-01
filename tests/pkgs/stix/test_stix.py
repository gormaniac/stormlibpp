"""Pytest suites for the stix Storm package."""

import os

import synapse.tests.utils as s_test

from ... import DIRNAME


class StixTest(s_test.StormPkgTest):
    """Tests for the stix Storm package."""

    pkgprotos = (os.path.join(DIRNAME, "src/pkgs/stix/stix.yaml"),)

    async def test_stix_loads(self):
        """The package loads, and its module and command parse."""

        async with self.getTestCore() as core:
            self.nn(await core.getStormPkg("stormlibpp-stix"))
            msgs = await core.stormlist("$lib.import(slib.stix.lib)")
            self.stormHasNoWarnErr(msgs)
            self.nn(core.getStormCmd("slib.stix.ingest"))

    async def test_stix_ingest_args(self):
        """--url and --obj can't be used together."""

        async with self.getTestCore() as core:
            opts = {"vars": {"bundle": {"type": "bundle"}}}
            msgs = await core.stormlist(
                "slib.stix.ingest --url https://127.0.0.1/stix.json --obj $bundle", opts=opts
            )
            self.stormIsInErr("Cannot use both --url and --obj!", msgs)

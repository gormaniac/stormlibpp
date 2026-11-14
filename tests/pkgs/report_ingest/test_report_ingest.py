"""Pytest suites for the report-ingest Storm package."""

import os

import synapse.tests.utils as s_test

from ... import DIRNAME

# Nothing listens on port 1, so requests to it fail without leaving the host.
BAD_URL = "http://127.0.0.1:1/report.html"


class ReportIngestTest(s_test.StormPkgTest):
    """Tests for the report-ingest Storm package."""

    pkgprotos = (os.path.join(DIRNAME, "src/pkgs/report-ingest/report-ingest.yaml"),)

    async def test_report_ingest_request_error(self):
        """A failed report request warns and raises the package's own error."""

        async with self.getTestCore() as core:
            msgs = await core.stormlist(f'[inet:url="{BAD_URL}"] | slib.report.ingest')
            self.stormIsInWarn(f'Error requesting the report URL "{BAD_URL}"', msgs)
            self.stormIsInErr("Could not get the report URL!", msgs)
            self.stormNotInPrint("HTTP Error:", msgs)

    async def test_report_ingest_request_error_debug(self):
        """--debug also prints the HTTP error."""

        async with self.getTestCore() as core:
            msgs = await core.stormlist(f'[inet:url="{BAD_URL}"] | slib.report.ingest --debug')
            self.stormIsInPrint("HTTP Error:", msgs)
            self.stormIsInErr("Could not get the report URL!", msgs)

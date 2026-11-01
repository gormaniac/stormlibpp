# Fail any test that uses a deprecated Synapse API.
#
# Synapse doesn't report deprecations through Python's warnings module, so pytest's
# filterwarnings can't catch them. They're logged instead:
#   - synapse.common.deprecated() logs "<name> is deprecated in <ver>..." for Python APIs,
#     tools, and Storm APIs. It's lru_cached, so it only logs once per process.
#   - Storm runtime deprecations ($lib.dict(), deprecated props, cron.add --hourly...) go
#     through Snap.warn(), which sends a Storm warn message and usually logs it too.
#   - Loading a Storm package logs deprecated package keys, ex. a command's forms key.
# This collects all three for each test and fails the test if any were seen. Deprecations
# logged outside a test (ex. a deprecated import at collection time) are listed in the
# terminal summary instead. Mark a test with @pytest.mark.allow_synapse_deprecations if it
# has to exercise a deprecated API on purpose.

import logging
import re

import pytest
import synapse.common as s_common
import synapse.lib.snap as s_snap


# Deprecation messages that aren't about the code under test.
_IGNORED = (
    # The Cortex's startup advice about its own unused deprecated model elements.
    re.compile(r"^Detected \d+ deprecated properties unlocked and not in use"),
    # Synapse's test model, loaded by getTestCore(), extends a deprecated type.
    re.compile(r"^The type test:\S+ is based on a deprecated type"),
)


class _SynDeprecations(logging.Handler):
    """Collects Synapse deprecation messages, per test and outside of tests."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.intest = None
        self.outside = set()

    def add(self, mesg: str) -> None:
        """Record a message if it's about a deprecation."""
        if "deprecat" not in mesg.lower() or any(r.search(mesg) for r in _IGNORED):
            return
        if self.intest is not None:
            self.intest.add(mesg)
        else:
            self.outside.add(mesg)

    def emit(self, record: logging.LogRecord) -> None:
        """Record deprecation messages logged by any synapse logger."""
        self.add(record.getMessage())


_SYN_DEPRS = _SynDeprecations()


def pytest_configure(config: pytest.Config) -> None:
    """Register the opt out marker and start listening to the synapse loggers."""
    config.addinivalue_line(
        "markers",
        "allow_synapse_deprecations: don't fail the test for using deprecated Synapse APIs.",
    )
    logging.getLogger("synapse").addHandler(_SYN_DEPRS)


def pytest_terminal_summary(terminalreporter) -> None:
    """List deprecations that were logged outside of a test, ex. at import time."""
    if _SYN_DEPRS.outside:
        terminalreporter.section("Synapse deprecations outside of tests")
        for mesg in sorted(_SYN_DEPRS.outside):
            terminalreporter.line(mesg)


def _allowed(request: pytest.FixtureRequest) -> bool:
    """Whether the test is marked with allow_synapse_deprecations."""
    if request.node.get_closest_marker("allow_synapse_deprecations"):
        return True
    # SynTest wraps its async test methods on the instance, which hides their marks from
    # pytest, so check the method on the class too.
    func = getattr(request.cls, getattr(request.node, "originalname", request.node.name), None)
    return any(m.name == "allow_synapse_deprecations" for m in getattr(func, "pytestmark", ()))


@pytest.fixture(autouse=True)
def _failOnSynapseDeprecations(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Fail the test if it used a deprecated Synapse API."""
    if _allowed(request):
        yield
        return

    # Storm warn messages sent with log=False never reach the logging handler.
    warn = s_snap.Snap.warn

    async def _warn(self, mesg, log=True, **info):
        if not log:
            _SYN_DEPRS.add(mesg)
        return await warn(self, mesg, log=log, **info)

    monkeypatch.setattr(s_snap.Snap, "warn", _warn)

    # Let each test see deprecations already logged by an earlier test.
    s_common.deprecated.cache_clear()
    _SYN_DEPRS.intest = seen = set()
    try:
        yield
    finally:
        _SYN_DEPRS.intest = None

    if seen:
        pytest.fail(
            "Used deprecated Synapse APIs:\n" + "\n".join(sorted(seen)),
            pytrace=False,
        )

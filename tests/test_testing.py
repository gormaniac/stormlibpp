"""Tests for stormlibpp.testing."""

import pytest

from stormlibpp.testing import (
    assertMainHelp,
    assertVersionsMatch,
    findVersions,
    stormLint,
)

pytest_plugins = ["pytester"]


def _svc(tmp_path, pyver="0.1.0", initver="0.1.0", yamlver="0.1.0", lockver="0.1.0"):
    """Write a minimal Storm service project and return its path."""

    root = tmp_path / "svc"
    pkg = root / "src" / "mysvc"
    (pkg / "pkgproto").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "my_svc"\nversion = "{pyver}"\n'
    )
    (pkg / "__init__.py").write_text(f'"""My svc."""\n\n__version__ = "{initver}"\n')
    (pkg / "pkgproto" / "slib.my.yaml").write_text(
        f"name: slib.my\nversion: {yamlver}\n"
    )
    if lockver is not None:
        (root / "uv.lock").write_text(
            'version = 1\n\n[[package]]\nname = "synapse"\nversion = "2.256.0"\n\n'
            f'[[package]]\nname = "my-svc"\nversion = "{lockver}"\n'
        )
    return root


class TestVersions:
    def test_match(self, tmp_path):
        root = _svc(tmp_path)
        assert findVersions(root) == {
            "pyproject.toml": "0.1.0",
            "src/mysvc/__init__.py": "0.1.0",
            "src/mysvc/pkgproto/slib.my.yaml": "0.1.0",
            "uv.lock": "0.1.0",
        }
        assert assertVersionsMatch(root) == "0.1.0"

    def test_no_lock(self, tmp_path):
        root = _svc(tmp_path, lockver=None)
        assert "uv.lock" not in findVersions(root)
        assertVersionsMatch(root)

    @pytest.mark.parametrize(
        "kwargs", [{"initver": "0.2.0"}, {"yamlver": "0.2.0"}, {"lockver": "0.0.9"}]
    )
    def test_mismatch(self, tmp_path, kwargs):
        root = _svc(tmp_path, **kwargs)
        with pytest.raises(AssertionError, match="don't match"):
            assertVersionsMatch(root)

    def test_missing_yaml(self, tmp_path):
        root = _svc(tmp_path)
        (root / "src" / "mysvc" / "pkgproto" / "slib.my.yaml").unlink()
        with pytest.raises(AssertionError, match="package prototype"):
            assertVersionsMatch(root)


class TestChecks:
    def test_storm_lint(self, tmp_path):
        (tmp_path / "ok.storm").write_text("$x = (1)\n$lib.print($x)\n")
        assert stormLint(tmp_path / "ok.storm", select="E") == []

        (tmp_path / "bad.storm").write_text("$x = (\n")
        findings = stormLint(tmp_path / "bad.storm", select="E")
        assert findings

    def test_storm_lint_usage_error(self, tmp_path):
        with pytest.raises(RuntimeError, match="Storm linter failed"):
            stormLint(tmp_path / "missing.storm", select="NOPE")

    def test_main_help(self):
        assert "usage" in assertMainHelp("synapse.tools.storm.lint").lower()
        with pytest.raises(AssertionError, match="exited"):
            assertMainHelp("stormlibpp.no_such_module")


class TestPlugin:
    def test_fails_deprecated_api(self, pytester):
        pytester.makeconftest('pytest_plugins = ["stormlibpp.testing"]')
        pytester.makepyfile("""
            import synapse.common as s_common

            def test_uses_deprecated():
                s_common.deprecated("old.thing", curv="2.1.0")

            def test_clean():
                pass
            """)
        result = pytester.runpytest_subprocess()
        # The check runs in an autouse fixture's teardown, so pytest reports an error.
        result.assert_outcomes(passed=2, errors=1)
        result.stdout.fnmatch_lines(
            ["*Used deprecated Synapse APIs*", "*old.thing is deprecated*"]
        )

    def test_allow_marker(self, pytester):
        pytester.makeconftest('pytest_plugins = ["stormlibpp.testing"]')
        pytester.makepyfile("""
            import pytest
            import synapse.common as s_common

            @pytest.mark.allow_synapse_deprecations
            def test_uses_deprecated():
                s_common.deprecated("old.marked", curv="2.1.0")
            """)
        pytester.runpytest_subprocess().assert_outcomes(passed=1)

    def _outside(self, pytester, ini=""):
        pytester.makeconftest('pytest_plugins = ["stormlibpp.testing"]')
        if ini:
            pytester.makeini(f"[pytest]\nstormlibpp_outside_deprecations = {ini}\n")
        # A deprecation logged when the test module is imported, at collection time.
        pytester.makepyfile("""
            import synapse.common as s_common

            s_common.deprecated("old.import.time", curv="2.1.0")

            def test_ok():
                pass
            """)
        return pytester.runpytest_subprocess()

    def test_outside_fails_run(self, pytester):
        result = self._outside(pytester)
        result.assert_outcomes(passed=1)
        assert result.ret == pytest.ExitCode.TESTS_FAILED
        result.stdout.fnmatch_lines(
            ["*outside of tests (failing the run)*", "*old.import.time*"]
        )

    def test_outside_warn(self, pytester):
        result = self._outside(pytester, ini="warn")
        assert result.ret == pytest.ExitCode.OK
        result.stdout.fnmatch_lines(["*Synapse deprecations outside of tests*"])

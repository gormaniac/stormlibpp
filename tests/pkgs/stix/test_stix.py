"""Pytest suites for the stix Storm package."""

import json
import os
import pathlib
import subprocess
import sys
import tomllib
from unittest.mock import patch

import pytest
import synapse.lib.stormhttp as s_stormhttp
import synapse.tests.utils as s_test
import synapse.tools.storm.pkg.gen as s_genpkg
import yaml

from ... import DIRNAME


@pytest.mark.parametrize("tag_source", ["project", "argument", "environment"])
def test_built_config_url(tmp_path, tag_source):
    root = pathlib.Path(DIRNAME)
    with (root / "pyproject.toml").open("rb") as source:
        tag = "v" + tomllib.load(source)["project"]["version"]
    package = s_genpkg.loadPkgProto(
        str(root / "src/pkgs/stix/stix.yaml"), readonly=True
    )
    output = tmp_path / "stix.json"
    output.write_text(json.dumps(package))
    command = [
        sys.executable,
        str(root / "scripts/pkgs/pin_stix_config.py"),
        str(output),
    ]
    if tag_source == "argument":
        command.extend(["--release-tag", tag])
    env = dict(os.environ)
    env.pop("RELEASE_TAG", None)
    if tag_source == "environment":
        env["RELEASE_TAG"] = tag
    result = subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    built = json.loads(output.read_text())
    module = next(
        module for module in built["modules"] if module["name"] == "slib.stix.lib"
    )
    assert (
        f"https://github.com/gormaniac/stormlibpp/releases/download/{tag}/stix_import_conf.json"
        in module["storm"]
    )
    assert "__STORMLIBPP_RELEASE_TAG__" not in output.read_text()
    assert "raw.githubusercontent.com" not in module["storm"]
    assert built["version"] == package["version"]


def test_mismatched_release_tag_fails(tmp_path):
    root = pathlib.Path(DIRNAME)
    output = tmp_path / "stix.json"
    output.write_text("{}")
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/pkgs/pin_stix_config.py"),
            str(output),
            "--release-tag",
            "v0.0.0",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "does not match" in result.stderr
    assert output.read_text() == "{}"


@pytest.mark.parametrize(
    "package",
    [
        {"name": "other"},
        {
            "name": "stormlibpp-stix",
            "modules": [{"name": "slib.stix.lib", "storm": "return()"}],
        },
    ],
)
def test_invalid_package_is_not_stamped(tmp_path, package):
    root = pathlib.Path(DIRNAME)
    output = tmp_path / "stix.json"
    original = json.dumps(package)
    output.write_text(original)
    result = subprocess.run(
        [sys.executable, str(root / "scripts/pkgs/pin_stix_config.py"), str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert output.read_text() == original


def test_release_includes_stix_config():
    root = pathlib.Path(DIRNAME)
    workflow = yaml.safe_load((root / ".github/workflows/release.yml").read_text())
    steps = workflow["jobs"]["release"]["steps"]
    release = next(
        step
        for step in steps
        if step.get("uses", "").startswith("softprops/action-gh-release@")
    )
    assert "data/stix_import_conf.json" in release["with"]["files"].splitlines()
    assert release["with"]["fail_on_unmatched_files"] is True
    assert steps.index(
        next(step for step in steps if step.get("run") == "make build")
    ) < steps.index(release)


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
                "slib.stix.ingest --url https://127.0.0.1/stix.json --obj $bundle",
                opts=opts,
            )
            self.stormIsInErr("Cannot use both --url and --obj!", msgs)

    async def test_pinned_download_and_overrides(self):
        root = pathlib.Path(DIRNAME)
        with (root / "pyproject.toml").open("rb") as source:
            tag = "v" + tomllib.load(source)["project"]["version"]
        package = s_genpkg.loadPkgProto(
            str(root / "src/pkgs/stix/stix.yaml"), readonly=True
        )
        with self.getTestDir() as directory:
            output = pathlib.Path(directory) / "stix.json"
            output.write_text(json.dumps(package))
            subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts/pkgs/pin_stix_config.py"),
                    str(output),
                    "--release-tag",
                    tag,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            package = json.loads(output.read_text())

        requests = []

        async def request(http, method, url, **kwargs):
            requests.append(url)
            return s_stormhttp.HttpResp({"code": 200, "body": b'{"objects": {}}'})

        async with self.getTestCore() as core:
            await core.addStormPkg(package)
            with patch("synapse.lib.stormhttp.LibHttp._httpRequest", request):
                result = await core.callStorm(
                    "$mod=$lib.import(slib.stix.lib) return($mod.pullConfig())"
                )
                assert result == {"objects": {}}
                expected_url = f"https://github.com/gormaniac/stormlibpp/releases/download/{tag}/stix_import_conf.json"
                assert requests == [expected_url]
                requests.clear()
                result = await core.callStorm(
                    "$mod=$lib.import(slib.stix.lib) return($mod.pullConfig(url=$url))",
                    opts={"vars": {"url": "https://example.com/custom.json"}},
                )
                assert result == {"objects": {}}
                assert requests == ["https://example.com/custom.json"]
                requests.clear()
                messages = await core.stormlist(
                    "$mod=$lib.import(slib.stix.lib) $mod.ingest($bundle, config=$config)",
                    opts={
                        "vars": {
                            "bundle": {
                                "type": "bundle",
                                "id": "bundle--00000000-0000-4000-8000-000000000001",
                                "objects": [],
                            },
                            "config": {
                                "bundle": {},
                                "objects": {},
                                "relationships": [],
                            },
                        }
                    },
                )
                self.stormHasNoWarnErr(messages)
                assert requests == []

            async def missing(http, method, url, **kwargs):
                requests.append(url)
                return s_stormhttp.HttpResp({"code": 404, "body": b""})

            with patch("synapse.lib.stormhttp.LibHttp._httpRequest", missing):
                messages = await core.stormlist(
                    "$mod=$lib.import(slib.stix.lib) $mod.pullConfig()"
                )
                self.stormIsInErr("Could not pull the STIX import config!", messages)
                assert requests == [expected_url]

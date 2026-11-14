"""Tests for the STIX import configuration and mappings."""

import copy
import json
import pathlib
import subprocess
import sys
import tarfile
import uuid
import zipfile

import pytest
import synapse.tests.utils as s_test

from stormlibpp import errors
from stormlibpp.stix import BLANK_CONF, BundleConf
from stormlibpp import utils


def test_config_isolation():
    first = BundleConf(map={})
    second = BundleConf(map={})
    first.bundle_conf["objects"]["test"] = {}
    assert second.bundle_conf == BLANK_CONF
    assert "test" not in BLANK_CONF["objects"]


def test_repeated_load():
    mapping = {"relationships": [{"type": [None, "uses", None], "storm": "uses.storm"}]}
    config = BundleConf(map=mapping)
    config.load()
    expected = copy.deepcopy(config.bundle_conf)
    config.load()
    assert config.bundle_conf == expected
    config.bundle_conf["relationships"][0]["type"][1] = "changed"
    assert mapping["relationships"][0]["type"][1] == "uses"
    assert config.map["relationships"][0]["type"][1] == "uses"


def test_failed_load_is_atomic():
    config = BundleConf(map={"bundle": "bundle.storm"})
    config.load()
    expected = copy.deepcopy(config.bundle_conf)
    config.map["objects"] = {"missing": "missing.storm"}
    with pytest.raises(errors.BundleConfLoadStormError):
        config.load()
    assert config.bundle_conf == expected


@pytest.mark.parametrize(
    "path",
    sorted(
        (pathlib.Path(__file__).parents[1] / "src/stormlibpp/stix/storm").rglob(
            "*.storm"
        )
    ),
)
def test_storm_syntax(path):
    utils.chk_storm_syntax(path.read_text())


def test_default_config_loads():
    config = BundleConf()
    config.load()
    assert len(config.bundle_conf["objects"]) == 38
    assert len(config.bundle_conf["relationships"]) == 6


def test_custom_config_and_save(tmp_path):
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects/example.storm").write_text(
        "[ inet:ipv4=1.2.3.4 ] return($node)"
    )
    output = tmp_path / "config.json"
    config = BundleConf(
        storm_path=str(tmp_path),
        default=False,
        out=str(output),
        map={"objects": {"example": "example.storm"}},
    )
    config.load()
    config.save()
    assert json.loads(output.read_text()) == config.bundle_conf
    assert json.loads(str(config)) == config.bundle_conf
    assert "{Custom Map}" in repr(config)
    alternate = tmp_path / "alternate.json"
    config.save(alternate)
    assert json.loads(alternate.read_text()) == config.bundle_conf


def test_syntax_error_is_wrapped(tmp_path):
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects/bad.storm").write_text("[ invalid syntax")
    config = BundleConf(
        storm_path=str(tmp_path), default=False, map={"objects": {"bad": "bad.storm"}}
    )
    with pytest.raises(errors.BundleConfLoadStormError, match="Storm syntax error"):
        config.load()
    assert config.bundle_conf == BLANK_CONF


def test_save_error_is_wrapped(tmp_path):
    config = BundleConf(out=str(tmp_path / "missing/config.json"), map={})
    with pytest.raises(errors.BundleConfSaveError):
        config.save()
    config.bundle_conf["objects"]["invalid"] = object()
    with pytest.raises(errors.BundleConfSaveError):
        config.save(tmp_path / "invalid.json")


def test_generated_config_is_current(tmp_path):
    script = pathlib.Path(__file__).parents[1] / "scripts/build_stix_conf.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_built_distributions(tmp_path):
    root = pathlib.Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(tmp_path),
            str(root),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    expected_storm = {
        path.relative_to(root / "src").as_posix()
        for path in (root / "src/stormlibpp/stix/storm").rglob("*.storm")
    }
    wheel = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        assert expected_storm <= names
        assert any(name.endswith("licenses/LICENSES/Apache-2.0.txt") for name in names)
        installed = tmp_path / "installed"
        archive.extractall(installed)
    with tarfile.open(next(tmp_path.glob("*.tar.gz"))) as archive:
        names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}
        assert {"src/" + name for name in expected_storm} <= names
        assert {
            "LICENSES/Apache-2.0.txt",
            "scripts/build_stix_conf.py",
            "data/stix_import_conf.json",
            "tests/data/cisa_stix_bun.json",
        } <= names
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from stormlibpp.stix import BundleConf; config = BundleConf(); config.load(); assert len(config.bundle_conf['objects']) == 38",
        ],
        cwd=installed,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


OBJECT_CASES = {
    "artifact": ("file:bytes", {"payload_bin": "aGVsbG8="}),
    "attack-pattern": (
        "ou:technique",
        {"name": "Example technique", "description": "Example"},
    ),
    "autonomous-system": ("inet:asn", {"number": 64512, "name": "Example AS"}),
    "campaign": ("ou:campaign", {"name": "Example campaign"}),
    "course-of-action": ("risk:mitigation", {"name": "Example mitigation"}),
    "directory": ("it:fs:file", {"path": "/tmp/example"}),
    "domain-name": ("inet:fqdn", {"value": "example.com"}),
    "email-addr": (
        "inet:email",
        {"value": "test@example.com", "display_name": "Test User"},
    ),
    "email-message": (
        "inet:email:message",
        {"subject": "Example", "body": "Example body", "date": "2024-01-01T00:00:00Z"},
    ),
    "file": (
        "file:bytes",
        {"name": "example.exe", "hashes": {"SHA-256": "a" * 64}, "size": 123},
    ),
    "grouping": (
        "meta:note",
        {"context": "suspicious-activity", "description": "Example"},
    ),
    "identity": (
        "ps:contact",
        {"identity_class": "organization", "name": "Example Org"},
    ),
    "incident": (
        "risk:compromise",
        {"name": "Example incident", "description": "Example"},
    ),
    "indicator": (
        "it:sec:stix:indicator",
        {"pattern_type": "stix", "pattern": "[ipv4-addr:value = '1.2.3.4']"},
    ),
    "infrastructure": (
        "it:host",
        {"name": "Example host", "infrastructure_types": ["command-and-control"]},
    ),
    "intrusion-set": (
        "ou:org",
        {"name": "Example intrusion set", "aliases": ["Example alias"]},
    ),
    "ipv4-addr": ("inet:ipv4", {"value": "1.2.3.4"}),
    "ipv6-addr": ("inet:ipv6", {"value": "2001:db8::1"}),
    "location": (
        "geo:place",
        {
            "name": "Example place",
            "country": "US",
            "latitude": 40.0,
            "longitude": -74.0,
        },
    ),
    "mac-addr": ("inet:mac", {"value": "00:11:22:33:44:55"}),
    "malware-analysis": (
        "it:av:scan:result",
        {
            "product": "Example scanner",
            "result": "malicious",
            "result_name": "Example.Malware",
        },
    ),
    "malware": ("it:prod:soft", {"name": "Example malware", "is_family": False}),
    "mutex": ("it:dev:mutex", {"name": "ExampleMutex"}),
    "network-traffic": (
        "inet:flow",
        {
            "start": "2024-01-01T00:00:00Z",
            "src_port": 12345,
            "dst_port": 443,
            "protocols": ["tcp"],
            "src_byte_count": 100,
            "dst_byte_count": 200,
        },
    ),
    "note": ("meta:note", {"content": "Example note"}),
    "observed-data": (
        "meta:note",
        {
            "first_observed": "2024-01-01T00:00:00Z",
            "last_observed": "2024-01-02T00:00:00Z",
            "number_observed": 2,
        },
    ),
    "opinion": ("meta:note", {"opinion": "strongly-agree", "explanation": "Example"}),
    "process": (
        "it:exec:proc",
        {
            "pid": 123,
            "created_time": "2024-01-01T00:00:00Z",
            "command_line": "example --test",
            "cwd": "/tmp",
        },
    ),
    "report": (
        "media:news",
        {"name": "Example report", "published": "2024-01-01T00:00:00Z"},
    ),
    "sighting": (
        "meta:note",
        {
            "first_seen": "2024-01-01T00:00:00Z",
            "last_seen": "2024-01-02T00:00:00Z",
            "count": 2,
        },
    ),
    "software": (
        "it:prod:soft",
        {"name": "Example software", "vendor": "Example vendor"},
    ),
    "threat-actor": (
        "ps:contact",
        {"name": "Example actor", "aliases": ["Example actor alias"]},
    ),
    "tool": ("it:prod:soft", {"name": "Example tool"}),
    "url": ("inet:url", {"value": "https://example.com/"}),
    "user-account": (
        "it:account",
        {
            "account_type": "posix",
            "account_login": "example",
            "user_id": "1000",
            "credential": "example-password",
        },
    ),
    "vulnerability": (
        "risk:vuln",
        {
            "name": "CVE-2024-1234",
            "description": "Example",
            "external_references": [
                {"source_name": "cve", "external_id": "CVE-2024-1234"}
            ],
        },
    ),
    "windows-registry-key": (
        "it:dev:regval",
        {
            "key": "HKEY_LOCAL_MACHINE\\Software\\Example",
            "values": [{"name": "Example", "data": "hello", "data_type": "REG_SZ"}],
        },
    ),
    "x509-certificate": (
        "crypto:x509:cert",
        {
            "serial_number": "01",
            "version": "3",
            "signature_algorithm": "sha256WithRSAEncryption",
            "subject": "CN=example.com",
            "issuer": "CN=Example CA",
            "validity_not_before": "2024-01-01T00:00:00Z",
            "validity_not_after": "2025-01-01T00:00:00Z",
            "hashes": {"SHA-256": "b" * 64},
        },
    ),
}


def make_object(object_type, **properties):
    return {
        "type": object_type,
        "spec_version": "2.1",
        "id": f"{object_type}--{uuid.uuid4()}",
        "created": "2024-01-01T00:00:00Z",
        "modified": "2024-01-01T00:00:00Z",
        **properties,
    }


def make_bundle(*objects):
    return {"type": "bundle", "id": f"bundle--{uuid.uuid4()}", "objects": list(objects)}


class TestStixIngest(s_test.SynTest):
    async def ingest(self, core, bundle):
        config = BundleConf()
        config.load()
        messages = await core.stormlist(
            "yield $lib.stix.import.ingest($bundle, config=$config)",
            opts={"vars": {"bundle": bundle, "config": config.bundle_conf}},
        )
        self.stormHasNoWarnErr(messages)
        return [message[1][0] for message in messages if message[0] == "node"]

    async def test_object_mappings(self):
        config = BundleConf()
        config.load()
        assert set(OBJECT_CASES) == set(config.bundle_conf["objects"])
        async with self.getTestCore() as core:
            for object_type, (form, properties) in OBJECT_CASES.items():
                with self.subTest(object_type=object_type):
                    obj = make_object(object_type, **properties)
                    bundle = make_bundle(obj)
                    opts = {"vars": {"bundle": bundle, "config": config.bundle_conf}}
                    messages = await core.stormlist(
                        "yield $lib.stix.import.ingest($bundle, config=$config)",
                        opts=opts,
                    )
                    self.stormHasNoWarnErr(messages)
                    nodes = [
                        message[1][0]
                        for message in messages
                        if message[0] == "node" and message[1][0][0] == form
                    ]
                    assert nodes, (object_type, messages)
                    stored = await core.callStorm(
                        f"{form}=$value return($lib.json.save($node.data.get($key)))",
                        opts={
                            "vars": {
                                "value": nodes[0][1],
                                "key": f"stix:object:bundle:{bundle['id']}",
                            }
                        },
                    )
                    assert json.loads(stored) == obj

    async def test_cisa_bundle(self):
        config = BundleConf()
        config.load()
        path = pathlib.Path(__file__).parent / "data/cisa_stix_bun.json"
        bundle = json.loads(path.read_text())
        async with self.getTestCore() as core:
            messages = await core.stormlist(
                "yield $lib.stix.import.ingest($bundle, config=$config)",
                opts={"vars": {"bundle": bundle, "config": config.bundle_conf}},
            )
            warnings = [
                message[1]["mesg"] for message in messages if message[0] == "warn"
            ]
            assert warnings == [
                "STIX bundle ingest has no object definition for: marking-definition."
            ]
            assert not [message for message in messages if message[0] == "err"]
            assert await core.nodes("file:bytes")
            assert await core.nodes("it:av:scan:result")
            assert await core.nodes("inet:ipv4")

    async def test_relationships_and_reingest(self):
        campaign = make_object("campaign", name="Campaign")
        intrusion = make_object("intrusion-set", name="Intrusion")
        actor = make_object("threat-actor", name="Actor")
        identity = make_object("identity", name="Identity", identity_class="individual")
        tool = make_object("tool", name="Tool")
        indicator = make_object(
            "indicator", pattern_type="stix", pattern="[ipv4-addr:value = '1.2.3.4']"
        )
        address = make_object("ipv4-addr", value="1.2.3.4")
        note = make_object(
            "note", content="Example", object_refs=[tool["id"], address["id"]]
        )
        relationships = [
            make_object(
                "relationship",
                source_ref=source["id"],
                target_ref=target["id"],
                relationship_type=verb,
            )
            for source, verb, target in (
                (campaign, "attributed-to", intrusion),
                (intrusion, "attributed-to", actor),
                (actor, "attributed-to", identity),
                (campaign, "uses", tool),
                (indicator, "indicates", tool),
                (tool, "communicates-with", address),
            )
        ]
        bundle = make_bundle(
            *relationships,
            campaign,
            intrusion,
            actor,
            identity,
            tool,
            indicator,
            address,
            note,
        )
        async with self.getTestCore() as core:
            first = await self.ingest(core, bundle)
            second = await self.ingest(core, bundle)
            assert set(first) == set(second)
            for query in (
                "ou:campaign :org -> ou:org",
                "ps:contact :org -> ou:org",
                "ps:contact -(attributed-to)> ps:contact",
                "ou:campaign -(uses)> it:prod:soft",
                "it:sec:stix:indicator -(indicates)> it:prod:soft",
                "it:prod:soft -(communicates-with)> inet:ipv4",
                "meta:note -(refs)> inet:ipv4",
            ):
                assert await core.nodes(query), query

    async def test_references_and_flow_properties(self):
        address = make_object("ipv4-addr", value="1.2.3.4")
        domain = make_object(
            "domain-name",
            value="example.com",
            resolves_to_refs=[address["id"], "ipv4-addr--missing"],
        )
        directory = make_object("directory", path="/tmp")
        file = make_object(
            "file", name="example.exe", parent_directory_ref=directory["id"]
        )
        flow = make_object(
            "network-traffic",
            src_ref=address["id"],
            dst_ref=address["id"],
            src_port=12345,
            dst_port=443,
            src_byte_count=100,
            dst_byte_count=200,
        )
        async with self.getTestCore() as core:
            await self.ingest(core, make_bundle(domain, file, flow, directory, address))
            assert await core.nodes("inet:dns:a=(example.com, 1.2.3.4)")
            assert await core.nodes("file:filepath +:path=/tmp/example.exe")
            nodes = await core.nodes("inet:flow")
            assert len(nodes) == 1
            for prop, value in {
                "src:ipv4": 0x01020304,
                "dst:ipv4": 0x01020304,
                "src:port": 12345,
                "dst:port": 443,
                "src:txbytes": 100,
                "dst:txbytes": 200,
            }.items():
                assert nodes[0].get(prop) == value

    async def test_sparse_objects_and_reused_software(self):
        async with self.getTestCore() as core:
            for object_type, properties in (
                ("file", {"name": "nohash.txt"}),
                ("malware", {"is_family": False}),
                (
                    "windows-registry-key",
                    {"key": "HKEY_LOCAL_MACHINE\\Software\\Example"},
                ),
                (
                    "user-account",
                    {
                        "account_type": "windows-domain",
                        "account_login": "example",
                        "user_id": "S-1-5-21-1",
                    },
                ),
                (
                    "user-account",
                    {"account_type": "twitter", "account_login": "example"},
                ),
                ("user-account", {"account_type": "other", "account_login": "example"}),
                ("artifact", {"payload_bin": ""}),
                ("x509-certificate", {"issuer": "CN=Example"}),
                ("identity", {"name": "Unknown", "identity_class": "unknown"}),
            ):
                with self.subTest(object_type=object_type, properties=properties):
                    nodes = await self.ingest(
                        core, make_bundle(make_object(object_type, **properties))
                    )
                    assert len(nodes) >= 2
            for object_type in ("software", "malware", "tool"):
                obj = make_object(object_type, name="Shared software")
                await self.ingest(core, make_bundle(obj))
                bundle = make_bundle(obj)
                await self.ingest(core, bundle)
                stored = await core.callStorm(
                    'it:prod:soft:name="shared software" return($lib.json.save($node.data.get($key)))',
                    opts={"vars": {"key": f"stix:object:bundle:{bundle['id']}"}},
                )
                assert json.loads(stored) == obj

    async def test_artifact_hash_mismatch(self):
        import hashlib

        artifact = make_object(
            "artifact",
            payload_bin="aGVsbG8=",
            hashes={
                "MD5": hashlib.md5(b"hello", usedforsecurity=False).hexdigest(),
                "SHA-256": "0" * 64,
            },
        )
        config = BundleConf()
        config.load()
        async with self.getTestCore() as core:
            messages = await core.stormlist(
                "yield $lib.stix.import.ingest($bundle, config=$config)",
                opts={
                    "vars": {
                        "bundle": make_bundle(artifact),
                        "config": config.bundle_conf,
                    }
                },
            )
            warnings = [
                message[1]["mesg"] for message in messages if message[0] == "warn"
            ]
            assert warnings == [
                f"STIX artifact {artifact['id']} failed hash verification."
            ]
            assert not await core.nodes("file:bytes")

# STIX Import Configuration

`stormlibpp.stix.BundleConf` builds a standalone configuration for Synapse's
`$lib.stix.import.ingest`. It uses the project's supported Synapse 2.x dependency
range. Every packaged handler is syntax-checked, and all 38 object mappings are
covered by temporary-Cortex ingest tests.

## Python Usage

```python
from stormlibpp.stix import BundleConf

config = BundleConf(out="bundle_conf.json")
config.load()
config.save()

# With a Cortex or Telepath proxy:
# async for message in core.storm(
#     "yield $lib.stix.import.ingest($bundle, config=$config)",
#     opts={"vars": {"bundle": bundle, "config": config.bundle_conf}},
# ):
#     ...
```

`load()` validates each Storm file before replacing the config. Repeated calls
do not accumulate relationships, and instances never share mutable config state.
`save()` does not create missing directories. Load/syntax failures raise
`BundleConfLoadStormError`; write/serialization failures raise `BundleConfSaveError`.

For a custom mapping, pass `default=False`, a `storm_path`, and a `map` with
`bundle`, `objects`, and/or `relationships` entries. Paths are relative to the
corresponding subdirectory (`bundle/`, `objects/`, `relationships/`); see the
[mapping API](stormlibpp/stormlibpp.stix.storm_mapping.rst).

## Supported Mappings

| STIX Types | Cortex Forms |
| --- | --- |
| artifact, file | file:bytes |
| attack-pattern | ou:technique |
| autonomous-system | inet:asn |
| campaign | ou:campaign |
| course-of-action | risk:mitigation |
| directory | it:fs:file |
| domain-name, ipv4-addr, ipv6-addr, mac-addr, url | inet:fqdn, inet:ipv4, inet:ipv6, inet:mac, inet:url |
| email-addr, email-message | inet:email, inet:email:message |
| grouping, note, observed-data, opinion, sighting | meta:note |
| identity, threat-actor | ps:contact; system identities use it:host |
| incident | risk:compromise |
| indicator | it:sec:stix:indicator; YARA/Snort patterns use their rule forms |
| infrastructure | it:host |
| intrusion-set | ou:org |
| location | geo:place |
| malware-analysis | it:av:scan:result |
| malware, software, tool | it:prod:soft; unnamed malware uses meta:note |
| mutex | it:dev:mutex |
| network-traffic | inet:flow |
| process | it:exec:proc |
| report | media:news |
| user-account | it:account, inet:web:acct, or auth:creds |
| vulnerability | risk:vuln |
| windows-registry-key | it:dev:regval |
| x509-certificate | crypto:x509:cert |

Each returned object node retains the complete source object in node data at
`stix:object:bundle:<bundle-id>`, and the bundle has `refs` edges to imported
nodes. Synapse resolves standard `object_refs` after all objects are ingested.

Supported relationship triples are campaign/attributed-to/intrusion-set,
intrusion-set/attributed-to/threat-actor, and threat-actor/attributed-to/identity.
`uses`, `indicates`, and `communicates-with` light edges accept any mapped
source/target types. Unsupported relationship types produce Synapse warnings.
The first two attribution mappings set the campaign/contact `:org` property;
the third creates an `attributed-to` edge between the distinct contacts.

## Scope and Limitations

- This is a useful subset of STIX 2.1, not a lossless semantic conversion or a
  full STIX validator. Unsupported fields remain in source node data.
- Marking definitions are not mapped. Ingest warns, and does not apply STIX
  markings or enforce sharing restrictions. Apply access controls separately.
  Extension definitions, language-content objects, and custom object types
  require a custom config.
- DNS `resolves_to_refs`, file `parent_directory_ref`, and IPv4/IPv6 flow
  endpoints resolve within the supplied bundle, independent of object order.
  Email address references, process-specific references, sighting references,
  and protocol-stack interpretation are deferred. They remain in node data.
- Process `cwd` is not an executable path and is not assigned to `:path`.
- A registry object can create multiple value nodes, but Synapse tracks only
  the last returned value for subsequent relationship/reference resolution.
  All created values retain the source object and bundle reference.
- Software-like objects reuse nodes by normalized name, as Synapse's default
  importer does. Separate STIX objects with the same name may share a node.
  Within one bundle, the last such object is retained in that node-data slot.
- Detailed extension modeling, ATT&CK-node matching, kill-chain phases, and
  dedicated note nodes for unmapped descriptions are deferred.
- Artifacts can download their URL; only ingest trusted bundles. Supported
  hashes (MD5, SHA-1, SHA-256, SHA-512) must all match before storage. Encrypted
  payloads remain ciphertext, with a warning; no decryption is attempted.

## Build and Verification

```sh
python scripts/build_stix_conf.py
python scripts/build_stix_conf.py --check
pytest tests/test_stix.py
```

The script works from any directory and always reads this checkout's sources.
The generated `data/stix_import_conf.json` is consumed independently of the
Python package. `make build` regenerates it before building the wheel/sdist;
the Python distributions include the Storm sources needed by `BundleConf`.
The regression suite fails when the checked-in config is stale and tests the
CISA fixture with this custom config, without downloading fixture data.

The separate `stix` Power-Up remains a work in progress. This builder and config
do not depend on that Power-Up or its planned post-processing commands.
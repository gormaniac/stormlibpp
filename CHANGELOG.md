## Unreleased
### Features
- Adds version 0.1.0 of the `slib.pdns` Rapid Power-Up, which looks up FQDNs and IPs in [CIRCL Passive DNS](https://www.circl.lu/services/passive-dns/) and models the DNS records CIRCL has seen. `slib.pdns.lookup` takes `inet:fqdn`, `inet:ipv4` and `inet:ipv6` nodes or a `--query` string, and can filter by record type (`--rrtype`), skip CIRCL's active resolver (`--no-active`) and page through large results (`--page-size`, `--max-pages`). Records are modeled as `inet:dns:*` nodes with CIRCL's first and last seen times as `.seen`. CIRCL needs an account: an admin saves the credentials with `slib.pdns.admin.key`, and users can't read them. Requires Synapse 2.207.0 or newer.
- Adds version 0.1.0 of the `slib.pssl` Rapid Power-Up, which looks up IPs, CIDR blocks (/23 to /32) and certificates in [CIRCL Passive SSL](https://www.circl.lu/services/passive-ssl/) and models the X.509 certificates seen on each IP as `inet:tls:servercert` nodes. `slib.pssl.lookup` takes `inet:ipv4`, `inet:cidr4`, `crypto:x509:cert` and `hash:sha1` nodes or a `--query` string. `--fetch` also downloads each certificate and parses it with `slib.utils.x509` into a full `crypto:x509:cert`. Requires `slib.utils`. CIRCL needs an account: an admin saves the credentials with `slib.pssl.admin.key`, and users can't read them. Requires Synapse 2.207.0 or newer.
- Adds `scripts/pkgs/record_circl.py`, which records the CIRCL Passive DNS and Passive SSL responses the `slib.pdns` and `slib.pssl` tests replay.
### Fixes
- **Security:** `slib.ipapi` (1.1.1) no longer lets a `slib.ipapi.user` read the global ip-api.com pro key. `slib.ipapi.privsep.globalKey()` returned it, and every function in an asroot module can be called by its users. The key is now only read inside `query()` and `queryBatch()`, and only sent to their fixed request paths.
- `slib.ipapi` imports `slib.utils.inet` and its privsep module once when its modules load, instead of on every call.
- `slib.utils` (0.2.2) and `slib.ipapi` (1.1.1) require Synapse 2.207.0 or newer, the first with Storm's `str.join`, which `slib.utils.x509` uses. They declared 2.162.0.

## v1.1.1 - 2026-11-17
### Features
- N/A
### Fixes
- `stormlibpp.testing`: deprecations logged by a test marked `allow_synapse_deprecations` no longer count as outside of a test, which failed the run.

## v1.1.0 - 2026-11-16
### Features
- Release `slib.ipapi` version `1.1.0`, with the changes the `slib.ipapi` 0.3.0 Storm Service got in the stormsvcs repo after this package was ported from it:
  - Inbound nodes are queried in batches of up to 100 with ip-api.com's `/batch` endpoint, which has its own rate limit.
  - Models reverse DNS (`:dns:rev`), `inet:asn:name`, the IP's WHOIS org (`-(owns)>`), `geo:place:loc`, `-(seen)>` edges from the package's `meta:source`, and one `geo:telem` per IP and place.
  - `--query` warns about strings that aren't IP addresses, the tag prefix must be a valid tag, and a bad tag setting warns instead of stopping the query.
  - ip-api.com pro keys (HTTPS, no rate limit): `slib.ipapi.apikey` sets your own key and `slib.ipapi.admin.apikey` the global key, both in `ipapi` vaults. Keys are scrubbed from warnings.
  - Requests time out after 30 seconds, and a rate limited request is retried 3 times.
  - The `slib:ipapi:url` global overrides the ip-api.com base URL, which the tests use for a fake ip-api.com.
### Fixes
- `slib.utils` 0.2.1: `slib.utils.inet.asnNode()` adds `names` to the owner org's `:names` instead of replacing them.
- `slib.ipapi` 1.1.0 only waits for ip-api.com's rate limit window when no requests are left (`X-Rl` 0), not when one is.

## v1.0.0 - 2026-11-16
### Features
- Add `stormlibpp.stix.BundleConf` to build standalone STIX import configs from Storm files, with 38 object mappings, six relationship mappings, and source-object node data.
- Release `stormlibpp-stix` version `0.2.0`. Built packages download the config from their matching repository release instead of following `main`; custom config and URL overrides remain supported.
- Attach `stix_import_conf.json` to GitHub Releases and add automated config-freshness, Cortex ingest, release-pinning, and distribution-content checks.
- Adds version 1.0.0 of the `slib.ipapi` Rapid Power-Up, which enriches IPs from ip-api.com. It replaces the `slib.ipapi` Storm Service from the stormsvcs repo with the same commands, perms and settings, but no service to deploy. ip-api.com's rate limit (45 requests a minute) is now shared by every query on the Cortex through its rate limit headers, and rate limited queries wait and retry. To upgrade, remove the service with `service.del` and load the package.
- Adds `slib.utils.inet` to the utils package, with the ASN and owner org modeling that `slib.ipapi` and `ipinfo` share.
- Adds a pure Storm X.509 certificate parser to the utils package, `slib.utils.x509`, and bumps slib.utils to 0.2.0. It parses certificates and CT precertificate TBSCertificates (DER, PEM or base64) into Storm primitives, including the RFC 5280 extensions (subjectDirectoryAttributes is kept raw), RFC 6962 SCT lists and RSA-PSS/EC/EdDSA/DSA keys, and lists recoverable DER and RFC 5280 deviations as warnings. Its output matches Python cryptography on a corpus of real root CA and CT certificates.
- Add `stormlibpp.svc`, the shared building blocks for a Storm service's Telepath API, so services stop hand-rolling their own:
  - `RetnApi`, a `CellApi` mixin. List the cell's methods in `RETN_METHS`/`GENR_METHS` and it generates API methods that return (or yield) `TelepathRetn`s. No public async method on the API can raise to Storm: unexpected errors are logged with a traceback and returned as `status=False` with an `Unexpected error: ...` message, bad input as `Invalid input: ...`, and `RETN_ERRORS` (default `SvcError`) and `AuthDeny` with their own message. `_retnRedact()` scrubs secrets from every error message.
  - `retn()`, `retnGenr()` and `errRetn()`, the same wrapping as functions.
  - `SvcError`, the base for errors whose message is meant for the Storm user.
  - `safeJoin()`, `checkName()` and `checkGuid()`, for values from Storm that end up in a file path.
- Add `stormlibpp.testing`, a pytest plugin for Storm service and package test suites (enable it with `pytest_plugins = ["stormlibpp.testing"]`, install with the `testing` extra). It moves the Synapse deprecation harness out of each project's `conftest.py`, now also fails the run for deprecations logged outside of a test (ex. a deprecated import at collection time; set `stormlibpp_outside_deprecations = warn` to only list them, which the terminal summary says when it fails a run), and adds `localhost` to `NO_PROXY` for fake upstream servers.
- Add `stormlibpp.testing.checks`: `assertVersionsMatch()` checks a service's version in `pyproject.toml`, `__init__.py`, its Storm package prototypes and `uv.lock`; `stormLint()` runs Synapse's Storm linter; `assertMainHelp()` checks `python -m <module> --help` works.
- StormLib++'s own tests use the new plugin.
- Implements stormgen Markdown-to-node extraction and offline conversion, including properties, tags, tag properties and constant values.
- Adds `compile_storm()` and asynchronous `apply()` APIs for creating and updating Cortex nodes, including generated GUIDs, runtime expressions and directed edges.
- Adds optional documentation-to-`meta:note` conversion with deduplication.
- Adds a compiler CLI via `python -m stormlibpp.stormgen`, accepting files or standard input and emitting standalone Storm.
- Supports full-document, single-form and embedded node definitions, with configurable heading levels.
- Adds documentation, examples and regression coverage for extraction, conversion, compilation, application and the CLI.
- **Note:** Documents containing Storm expressions are executable input and must be trusted. Cortex application is not guaranteed atomic.
### Fixes
- Isolate config-builder state and make repeated loads atomic and idempotent. Fix Storm syntax and runtime mappings, preserve metadata on reused software nodes, and reject artifact hash mismatches.
- Correct the STIX command examples to use `slib.stix.ingest`.
- STIX ingest no longer fails on optional fields: `malware-analysis` objects without `result` or `result_name`, and `user-account` objects without `account_login`.
- STIX ingest saves the bundle as node data when the `it:sec:stix:bundle` node already exists, not only when it is created.
- ipinfo (0.1.2) models ASNs with `slib.utils.inet`, and no longer makes an `ou:org` with an empty name when ipinfo.io has no AS name.
- Corrects heading scope, property/tag ownership and repeated parsing to prevent unrelated content or duplicate entries from being extracted.
- Preserves literal Markdown values separately from executable Storm expressions and validates generated syntax before submission.
- Rejects malformed definitions and operations unsupported by offline conversion instead of silently omitting them.

## v0.12.1 - 2026-11-01
### Features
- Bump the GitHub Actions the workflows use to their latest releases, which run on Node.js 24 (GitHub deprecated the Node.js 20 runtime the old ones used).
- CI catches Storm syntax errors in every package: a test loads every package under `src/pkgs/` into a Cortex, and a new `make lint-storm` step runs Synapse's Storm linter before the tests. The dev environment (Pipfile) now requires Synapse `>=2.256.0`, the first release with the linter.
### Fixes
- report-ingest raises its own "Could not get the report URL!" error when a report request fails, instead of `'boolean' object is not callable` from a `$lib.debug(...)` call. `--debug` now prints the HTTP error. Its help examples also use the right command name.

## v0.12.0 - 2026-11-01
### Features
- The test suite fails on deprecated Synapse API use (see `tests/conftest.py`) and on Python `DeprecationWarning`s raised from StormLib++ code. This only affects test runs, the library and CLIs still treat deprecation warnings normally.
- Requires Synapse `>=2.225.0`, where Synapse's tools moved to their new module paths.
- Publish the Python package to PyPI from the Release GitHub Action.
- Add a manually run Prepare Release GitHub Action that bumps the version, rolls the CHANGELOG, tags, and runs the release.
### Fixes
- Migrate off deprecated Synapse APIs:
  - `$lib.dict()`/`$lib.list()` are replaced with `({})`/`([])` literals in the dnsstorm, ipinfo, and stix packages.
  - Storm packages use `synapse_version` instead of `synapse_minversion`, and `cmdinputs` instead of the command `forms` key.
  - `stormlibpp.stormpkg` and the package build scripts use `synapse.tools.storm.pkg.gen` instead of `synapse.tools.genpkg`.
- `stormlibpp.hfeed` and `stormlibpp.stormcli` (used by `hstorm` and `import`) work with current Synapse, which removed `synapse.tools.feed.makeargparser()` and moved `StormCli` into `synapse.tools.storm._cli`.
- `HttpCortex` no longer uses aiohttp's deprecated `read_timeout` argument.
- The ipinfo package sends the API token; its `Authorization` header used a plain string instead of a format string.
- Bumps the patch version of every StormLib++ Storm package.
- The stix package loads: fix its Storm syntax errors and its `$lib.debug(...)` calls (`$lib.debug` is a boolean, not a function).
- The release steps moved from the README to the contribution guide.

## v0.11.0 - 2026-07-26
### Features
- Adds version 0.1.0 of an ipinfo.io Rapid Power-Up - slib.ipinfo
- Adds version 0.1.0 of a utils Rapid Power-Up - slib.utils - for shared StormLib++ storm code
- Cleans up docs
### Fixes
- N/A

## v0.10.4 - 2026-07-10
### Features
- Move docs theme to Shibuya
### Fixes
- Remove a circular import that made it's way into stormlibpp.node

## v0.10.3 - 2026-07-09
### Features
- Docs improvements.
- Add build, release, and test GitHub Actions.
- Proper NOTICE file and headers.
### Fixes
- Typos
- Removing extraneous files

## v0.10.2 - 2024-05-16
### Features
- N/A
### Fixes
- Quit gracefully for auth failures in `stormlibpp.hstorm` ([#36](https://github.com/gormaniac/stormlibpp/pull/36)).

## v0.10.1 - 2024-03-26
### Features
- Adds `slib` prefix to `dnsstorm` module.
### Fixes
- N/A

## v0.10.0 - 2024-03-26
### Features
- Adds export/import methods to `HttpCortex` for greater CLI parity ([#28](https://github.com/gormaniac/stormlibpp/pull/28)).
- Improves `ItemContainer` to use a `dict` under the hood ([#28](https://github.com/gormaniac/stormlibpp/pull/28)).
- An HTTP based version of the `synapse.tools.feed` script - `hfeed` ([#29](https://github.com/gormaniac/stormlibpp/pull/29)).
- Moves the `dnsstorm` and `lookup-storm` Synapse Power-Ups into the StormLib++ project ([#30](https://github.com/gormaniac/stormlibpp/pull/30)).
### Fixes
- N/A

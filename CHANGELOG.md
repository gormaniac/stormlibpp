## Unreleased
### Features
- Add `stormlibpp.svc`, the shared building blocks for a Storm service's Telepath API, so services stop hand-rolling their own:
  - `RetnApi`, a `CellApi` mixin. List the cell's methods in `RETN_METHS`/`GENR_METHS` and it generates API methods that return (or yield) `TelepathRetn`s. No public async method on the API can raise to Storm: unexpected errors are logged with a traceback and returned as `status=False` with an `Unexpected error: ...` message, bad input as `Invalid input: ...`, and `RETN_ERRORS` (default `SvcError`) and `AuthDeny` with their own message. `_retnRedact()` scrubs secrets from every error message.
  - `retn()`, `retnGenr()` and `errRetn()`, the same wrapping as functions.
  - `SvcError`, the base for errors whose message is meant for the Storm user.
  - `safeJoin()`, `checkName()` and `checkGuid()`, for values from Storm that end up in a file path.
- Add `stormlibpp.testing`, a pytest plugin for Storm service and package test suites (enable it with `pytest_plugins = ["stormlibpp.testing"]`, install with the `testing` extra). It moves the Synapse deprecation harness out of each project's `conftest.py`, now also fails the run for deprecations logged outside of a test (ex. a deprecated import at collection time; set `stormlibpp_outside_deprecations = warn` to only list them), and adds `localhost` to `NO_PROXY` for fake upstream servers.
- Add `stormlibpp.testing.checks`: `assertVersionsMatch()` checks a service's version in `pyproject.toml`, `__init__.py`, its Storm package prototypes and `uv.lock`; `stormLint()` runs Synapse's Storm linter; `assertMainHelp()` checks `python -m <module> --help` works.
- StormLib++'s own tests use the new plugin.
### Fixes

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
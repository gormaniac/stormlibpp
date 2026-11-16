# stix

Work In Progress!

An extension to the builtin stix Storm Library methods that rely on the StormLib++ project's custom stix ingestion config. This Package automatically pulls, and uses, this config with the `$lib.stix.import.ingest` method. It also attempts to resolve in object relationships after all nodes have been created.

It will share some code with the StormLib++ custom stix config, but since this config is meant to be stand alone, the config will not rely on this library - resulting in necessary code-reuse.

## Versioned Import Configuration

Each built package downloads the standalone `stix_import_conf.json` asset from
the same StormLib++ GitHub release that produced the package. It does not follow
`main` or `latest`. For example:

```text
https://github.com/gormaniac/stormlibpp/releases/download/v0.12.1/stix_import_conf.json
```

The repository release tag is independent of this Storm package's own version.
`make build-storm` stamps the repository version from `pyproject.toml` into the
built `dist/stix.json`. Release CI supplies `RELEASE_TAG` and rejects a mismatch.
Install the built JSON package, not the source YAML: the source module contains
a build marker rather than a usable default download URL.

The release workflow regenerates the config and attaches it as a standalone
asset. Old releases are not backfilled. A missing asset or failed HTTP download
raises an error; there is no automatic fallback to another release or `main`.

For unpublished development versions or private configurations, pass a config
directly to `$lib.import(slib.stix.lib).ingest(..., config=$config)`, or retrieve
one explicitly with `$lib.import(slib.stix.lib).pullConfig(url=$url)`.
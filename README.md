# StormLib++

StormLib++ is a collection of Python code that make life as a Storm service developer easier paired with a collection of Synapse Rapid Power-Ups to make life as a Synapse analyst easier.

See the project's [documentation](https://docs.gormo.com/stormlibpp/) for more info.

## Releasing

Releases are cut from GitHub Actions with the **Prepare Release** workflow, and pending changes are tracked under a `## Unreleased` header in `CHANGELOG.md`. See the [contribution guide](https://docs.gormo.co/stormlibpp/contributing/) for full details.

1. Add entries to the `## Unreleased` section at the top of `CHANGELOG.md` (under its `### Features` and `### Fixes` headers) as changes land on `main`.
2. Go to **Actions → Prepare Release → Run workflow** on `main`, pick a `patch`/`minor`/`major` bump (or enter an explicit version).

The workflow runs the tests, bumps the version, renames `## Unreleased` to `## v#.#.# - <date>` (starting a fresh empty `## Unreleased` above it), commits, and pushes a `v#.#.#` tag. The **Release** workflow then builds the package, uploads it to PyPI (using the `PYPI_DEPLOY_TOKEN` secret), creates a GitHub Release with the changelog entry as notes and the Python and Storm packages and docs attached, and notifies the docs site. Pushing a `v*` tag manually (e.g. `make release VERSION=#.#.#`) also triggers the Release workflow.

If `main` is protected against direct pushes, add a `RELEASE_TOKEN` repository secret: a fine-grained personal access token for this repository with **Contents: read and write**, from an account allowed to bypass the branch protection rule. Prepare Release pushes with it when it is set. In that case the tag push itself starts the Release workflow, so it appears as its own run rather than as a job inside Prepare Release.

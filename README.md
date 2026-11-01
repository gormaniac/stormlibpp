# StormLib++

StormLib++ is a collection of Python code that make life as a Storm service developer easier paired with a collection of Synapse Rapid Power-Ups to make life as a Synapse analyst easier.

See the project's [documentation](https://docs.gormo.com/stormlibpp/) for more info.

## Releasing

Releases are cut from GitHub Actions:

1. (Optional) Add a `## v#.#.# - YYYY-MM-DD` entry to `CHANGELOG.md` on `main` - it becomes the GitHub Release notes.
2. Go to **Actions → Prepare Release → Run workflow** on `main`, pick a `patch`/`minor`/`major` bump (or enter an explicit version).

The workflow runs the tests, bumps the version, commits and pushes a `v#.#.#` tag, then runs the **Release** workflow, which builds the package, uploads it to PyPI (using the `PYPI_DEPLOY_TOKEN` secret), creates a GitHub Release with the Python and Storm packages and docs attached, and notifies the docs site. Pushing a `v*` tag manually (e.g. `make release VERSION=#.#.#`) also triggers the Release workflow.

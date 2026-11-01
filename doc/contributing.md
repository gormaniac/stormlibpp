# Contribution Guide

Contributions are welcome, please open any PR you wish in this project's [Github repo](https://github.com/gormaniac/stormlibpp)!

## Project TODO

- TBD

## GitHub CI

The project uses CI to perform the building/releasing/testing tasks automagically. CI relies on the Makefile to make sure all tasks are standardized across automation and local use.

Each PR runs a build and test job. This allows you to make sure your code works and builds properly before merges. Each build job also builds this docs site to make sure nothing broke on that front.

### Releases

Releases are cut entirely from CI by the project maintainer:

1. As changes land on `main`, add entries to the `## Unreleased` section at the top of `CHANGELOG.md`, under its `### Features` and `### Fixes` headers (see the Changelog section below).
2. Go to **Actions → Prepare Release → Run workflow** on `main`.
3. Pick a `patch`, `minor`, or `major` version bump, or enter an explicit version.

The **Prepare Release** workflow runs the tests, bumps the version, updates `CHANGELOG.md` (see the Changelog section below), commits to `main`, and pushes a `vX.Y.Z` tag using the `RELEASE_TOKEN` secret (see below). That tag push starts the **Release** workflow, which:

- builds the Python package, the Storm packages, and these docs,
- publishes the Python package to [PyPI](https://pypi.org/project/stormlibpp/),
- creates a GitHub Release with the version's changelog entry as its notes and the Python package, Storm package JSON files, and docs attached,
- notifies the docs site so it picks up the new docs.

Pushing a `v*` tag yourself (e.g. with `make release VERSION=x.x.x`) also runs the **Release** workflow.

The workflows rely on these repository secrets:

- `PYPI_DEPLOY_TOKEN` - the PyPI API token used to upload the package.
- `DOCS_DISPATCH_TOKEN` - used to notify the docs site repo.
- `RELEASE_TOKEN` (required) - `main` is protected by branch protection, so Prepare Release pushes the release commit and tag with this token instead of the default `GITHUB_TOKEN`. It must be a token for this repo with **Contents: read and write** (e.g. a fine-grained personal access token), from an account allowed to bypass the branch protection rule. Prepare Release fails right away if it is missing. Because the tag is pushed with this token rather than `GITHUB_TOKEN`, the tag push starts the **Release** workflow, which shows up as its own run under Actions. If the token expires or is revoked, the push step will fail and the token needs to be replaced.

### Changelog

Changes are recorded in `CHANGELOG.md` under a `## Unreleased` header at the top of the file, as they land on `main`:

```markdown
## Unreleased
### Features
- Describe new features here.
### Fixes
- Describe bug fixes here.
```

Please add an entry there with your PR. When a release is cut, `## Unreleased` is renamed to `## vX.Y.Z - YYYY-MM-DD`, any empty `### Features` or `### Fixes` section gets `- N/A`, and a fresh, empty `## Unreleased` section is added above it. If a `## vX.Y.Z` entry was already written by hand, the changelog is left as is.

## The Makefile

Most of this project's repeatable tasks are managed by the `Makefile`. There is a `make help` command that can be run to display a list of available make commands and a simple help message describing what they do.

More complex tasks are stored in the `scripts` folder and are called from the `Makefile`. But the scripts may still be used standalone.

## Dev Environment

A Pipfile is included in this project to enforce a consistent dev environment. Install it with the `pipenv` tool, or use the Makefile:
```bash
make setup
```

## Testing

There is a `pytest` test suite for this project in the `tests/` directory. You can run it with the project's Makefile or directly with `pytest`:
```bash
make tests
```

```bash
pytest tests/ -svx
```

## Building and Releasing

The build/release process is managed by the Makefile. Building can be done without releasing, but releasing always forces a fresh build, even if it rebuilds the same exact code. A `VERSION` argument is required when releasing, but not when building.

Make sure that all changes are committed before releasing. `git commit` and `git push` are run, so any staged changes, or uncommitted changes in certain folders, may be committed by accident.

Build:
```bash
make build
```

The above command only builds the `stormlibpp` Python package. To build the Storm Packages included in StormLib++, run the command:
```bash
make build-storm
```

Release:
```bash
make release VERSION=1.2.3
```

Releases are normally cut from CI with the **Prepare Release** workflow instead (see the Releases section above). `make release` does the same version bump and `CHANGELOG.md` update locally, then pushes the commit and tag, which starts the **Release** workflow.

## Docs

This documentation is built with Sphinx and is configured in the `doc` folder. Documentation is automatically built everytime that `make release` is executed. But they may also be built separately using this command:
```bash
make docs
```

There is also a Makefile command to open the current version of the docs locally:
```bash
make read-docs
```

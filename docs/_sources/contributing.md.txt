# Contribution Guide

Contributions are welcome, please open any PR you wish in this project's [Github repo](https://github.com/gormaniac/stormlibpp)!

## Project TODO

- TBD

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

## Docs

This documentation is built with Sphinx and is configured in the `doc` folder. Documentation is automatically built everytime that `make release` is executed. But they may also be built separately using this command:
```bash
make docs
```

There is also a Makefile command to open the current version of the docs locally:
```bash
make read-docs
```

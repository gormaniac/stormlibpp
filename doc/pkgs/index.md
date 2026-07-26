# Power-Ups

StormLib++ comes with some helpful Storm Rapid Power-Ups.

## Power-Up Docs

```{toctree}
:glob: true
:maxdepth: 2

*
```

## Installation

There are several ways to install StormLib++'s Power-Ups. Each Power-Up is built and released with every `stormlibpp` package release. The JSON definition for each Power-Up is attached to the repo's [Github Release page](https://github.com/gormaniac/stormlibpp/releases/latest).

To install ALL Power-Ups in StormLib++, you can use the following `make` commands:
```bash
make build-storm && make push-storm CORTEX="<Cortex Telepath URL>"
```

To pick and choose which packages you want, you may use the prebuilt package JSON files included released this repo along with the `pkg.load` Storm command. Or, build and push them yourself. Example with `dnsstorm`:
```
pkg.load --raw https://github.com/gormaniac/stormlibpp/releases/download/v0.10.4/dnsstorm.json
```

Versions of a Power-Up will be pinned to a StormLib++ release, the specific version will be called out in the [Changelog](https://docs.gormo.co/stormlibpp/changelog/).

Bleeding edge versions of any Power-Up can always be downloaded and built by cloning the `main` branch of the StormLib++ repo instead of a downloading a prebuilt version from Releases. Like this example with `dnsstorm`:
```bash
git clone https://github.com/gormaniac/stormlibpp
# Install the Synapse Python packge if needed
python3 -m synapse.tools.genpkg --no-docs --push "<Cortex Telepath URL>" stormlibpp/src/pkgs/dnsstorm/dnsstorm.yaml
```

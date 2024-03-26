# Power-Ups

StormLib++ comes with many helpful Storm Rapid Power-Ups.

## Installation
To install ALL Power-Ups in StormLib++, you can use the following `make` commands:
```bash
make build-storm && make push-storm CORTEX="<Cortex Telepath URL>"
```

To pick and choose which packages you want, you may use the prebuilt package JSON files included in this repo along with the `pkg.load` Storm command. Or, build and push them yourself. See indivudual Power-Up installation instructions for more info.

## Power-Up Docs

```{toctree}
:glob: true
:maxdepth: 2

*
```
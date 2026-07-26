# Installing StormLib++

## Installing The Python Package
The StormLib++ Python package is published on PyPi, you can install the latest version via:
```bash
pip install stormlibpp
```

You can always install this package from source:

Using the project's Makefile + pipenv
```bash
git clone https://github.com/gormaniac/stormlibpp.git
cd stormlibpp/
make setup          # runs pipenv to install all deps
make install-self   # runs 'pip install -e .' within the pipenv
```

Or with plain pip (you'll probably have to handle dependencies on your own):
```bash
git clone https://github.com/gormaniac/stormlibpp.git
cd stormlibpp/
pip install .
```

## Installing Rapid Power-Ups

The easiest way to install StormLib++'s Storm Rapid Power-Ups is to reference the Power-Up built and packaged with each StormLib++ GitHub release with Synapse's `pkg.load` command:
```bash
pkg.load --raw https://github.com/gormaniac/stormlibpp/releases/latest/download/dnsstorm.json
pkg.load --raw https://github.com/gormaniac/stormlibpp/releases/latest/download/lookup-storm.json
pkg.load --raw https://github.com/gormaniac/stormlibpp/releases/latest/download/report-ingest.json
pkg.load --raw https://github.com/gormaniac/stormlibpp/releases/latest/download/stix.json
```

See the [Power-Ups page](https://docs.gormo.co/stormlibpp/pkgs/#Installation) for more options.
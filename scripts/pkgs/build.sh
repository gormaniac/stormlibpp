#!/usr/bin/env bash
set -euo pipefail

# Build Storm Packages

mkdir -p dist

for pkg in $(ls src/pkgs/)
do
    echo "Building the $pkg Storm Package"
    fileBase="src/pkgs/$pkg/$pkg"
    pipenv run python3 -m synapse.tools.storm.pkg.gen --save "dist/$pkg.json" "$fileBase.yaml"
done

pipenv run python3 scripts/pkgs/pin_stix_config.py dist/stix.json
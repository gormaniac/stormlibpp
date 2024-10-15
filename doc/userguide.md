# User Guide

StormLib++ is split into 2 parts:
1) A collection of Synapse Rapid Power-Ups (Storm Packages).
2) A mono-Python module with many semi-related submodules - some are CLI tools, some are simply libraries, and some are both.


## StormLib++ Power-Ups

StormLib++ contains 4 different Synapse Rapid Power-Ups stored in the repo's `src/pkgs/` directory:
- [`dnsstorm`](https://gormo.co/stormlibpp/pkgs/dnsstorm.html)
    - A Synapse Rapid Power-Up that brings DNS over HTTPS capabilities to a Cortex using Clourdflare.
- [`lookup-storm`](https://gormo.co/stormlibpp/pkgs/lookup-storm.html)
    - Lookup common atomic indicators in Synapse as strings rather than a `<form>=<valu>` pair.
- [`report-ingest`](https://gormo.co/stormlibpp/pkgs/report-ingest.html)
    - A tool to download and model Threat Intel reports from the web.
- [`stix`](https://gormo.co/stormlibpp/pkgs/stix.html)
    - An extension to the builtin stix Storm Library methods that rely on the StormLib++ project’s custom stix ingestion config.
    - *Still a work in progress, see the repo's [stix branch](https://github.com/gormaniac/stormlibpp/tree/stix).*


Each Power-Up is self contained with their respective `src/pkgs/` folder, and are versioned individually.

Built versions of each Power-Up are available as JSON files alongside the Power-Up's source code. These can be referenced to install a Power-Up from a Storm CLI - like this example for `dnsstorm` v1.1:
```
pkg.load --raw https://raw.githubusercontent.com/gormaniac/stormlibpp/v0.10.1/src/pkgs/dnsstorm/dnsstorm.json
```

Versions of a Power-Up will be pinned to a StormLib++ release, the specific version will be called out in the [Changelog](https://gormo.co/stormlibpp/changelog.html). Giving users the ability to download a specific version of a built Power-Up by referencing the git tag of a StormLib++ version ([example for `dnsstorm` v1.1](https://github.com/gormaniac/stormlibpp/blob/v0.10.1/src/pkgs/dnsstorm/dnsstorm.json)). Bleeding edge versions of any Power-Up can always be downloaded by referencing the `main` branch of the StormLib++ repo instead of a git tag.

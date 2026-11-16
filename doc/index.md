# StormLib++ Docs

StormLib++ is a collection of Python code that make life as a Storm service developer easier paired with a collection of Synapse Rapid Power-Ups to make life as a Synapse analyst easier. See this [blog post](https://gormo.co/blog/post_20240517_stormlibpp_intro/) outlining it's features.

StormLib++ is split into 2 parts:
1) A mono-Python module with many semi-related submodules - some are CLI tools, some are simply libraries, and some are both.
2) A collection of Synapse Rapid Power-Ups (Storm Packages).

## The StormLib++ Python Package

### CLI Tools

- [`python -m stormlibpp.import`](https://docs.gormo.co/stormlibpp/stormlibpp/stormlibpp.import/)
    - Recursively execute all Storm scripts in a folder (or folders) on a Synapse Cortex and import data from json/csv/text files.
- [`python -m stormlibpp.tmpcortex`](https://docs.gormo.co/stormlibpp/stormlibpp/stormlibpp.tmpcortex/)
    - Start a temporary Synapse Cortex for testing, data will not persist but it is an otherwise full featured Cortex.
- [`python -m stormlibpp.hstorm`](https://docs.gormo.co/stormlibpp/stormlibpp/stormlibpp.hstorm/)
    - A version of Synapse's `synapse.tools.storm` CLI that works over HTTPS instead of Telepath (Axon features aren't supported).
- [`python -m stormlibpp.hfeed`](https://docs.gormo.co/stormlibpp/stormlibpp/stormlibpp.hstorm/)
    - A wrapper of Synapse's `synapse.tools.feed` script that works over HTTPS instead of Telepath.

### Python Objects

- [`stormlibpp.node.StormNode`](https://docs.gormo.co/stormlibpp/stormlibpp/stormlibpp.node/#stormlibpp.node.StormNode)
    - A `storm:node` Storm object in a Python runtime. It can be used to create, manipulate, or read Storm Nodes in Python.
- [`stormlibpp.stormpkg.StormPkg`](https://docs.gormo.co/stormlibpp/stormlibpp/stormlibpp.stormpkg/#stormlibpp.stormpkg.StormPkg)
    - A Python representation of a Storm package, proto and definition. This module makes the process of defining Storm Packages for Storm Advanced Power-Ups in Python easier. Rather than defining a Service’s Storm package in a Python dict, this object allows you to define a typical Rapid Power-Up in Yaml and `.storm` files and attach it to a Storm Service API class.
- [`stormlibpp.telepath.TelepathRetn`](https://docs.gormo.co/stormlibpp/stormlibpp/stormlibpp.telepath/#stormlibpp.telepath.TelepathRetn)
    - This object and it's many defined subclasses can be used in a Storm Advanced Power-Up's API to give developers a simple way to return standardized objects over Telepath (and it helps with type hints 🙂).

## StormLib++ Power-Ups

StormLib++ contains 4 different Synapse Rapid Power-Ups stored in the repo's `src/pkgs/` directory:
- [`dnsstorm`](https://docs.gormo.co/stormlibpp/pkgs/dnsstorm/)
    - A Synapse Rapid Power-Up that brings DNS over HTTPS capabilities to a Cortex using Clourdflare.
- [`lookup-storm`](https://docs.gormo.co/stormlibpp/pkgs/lookup-storm/)
    - Lookup common atomic indicators in Synapse as strings rather than a `<form>=<valu>` pair.
- [`report-ingest`](https://docs.gormo.co/stormlibpp/pkgs/report-ingest/)
    - A tool to download and model Threat Intel reports from the web.
- [`stix`](https://docs.gormo.co/stormlibpp/pkgs/stix/)
    - An extension to the builtin stix Storm Library methods that rely on the StormLib++ project’s custom stix ingestion config.
    - *Still a work in progress, see the repo's [stix branch](https://github.com/gormaniac/stormlibpp/tree/stix).*

See the [pkgs](https://docs.gormo.co/stormlibpp/pkgs/) page for more info.

## Contents

```{toctree}
:hidden: true

Home <self>
```

```{toctree}
:maxdepth: 2

installation
contributing
pkgs/index
```

```{toctree}
:maxdepth: 1

stormlibpp/stormlibpp
changelog
```

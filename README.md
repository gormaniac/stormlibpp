# StormLib++

StormLib++ is a collection of Python code that make life as a Storm service developer easier.

## Stormgen

Stormgen turns structured Markdown into Synapse node data or executable Storm,
including properties, tags, edges and optional documentation notes. It supports
offline extraction and conversion, Storm compilation, and application through a
caller-provided Cortex connection.

See the [Stormgen guide](doc/stormgen_design.md) and
[example document](tests/data/stormgen-example.md). Compile a document with:

```sh
python -m stormlibpp.stormgen nodes.md
```

Documents containing Storm expressions are executable input. Only compile or
apply trusted documents under appropriately scoped Cortex permissions.

See [release notes](CHANGELOG.md) for changes.

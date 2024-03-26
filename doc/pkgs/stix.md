# stix

Work In Progress!

An extension to the builtin stix Storm Library methods that rely on the StormLib++ project's custom stix ingestion config. This Package automatically pulls, and uses, this config with the `$lib.stix.import.ingest` method. It also attempts to resolve in object relationships after all nodes have been created.

It will share some code with the StormLib++ custom stix config, but since this config is meant to be stand alone, the config will not rely on this library - resulting in necessary code-reuse.
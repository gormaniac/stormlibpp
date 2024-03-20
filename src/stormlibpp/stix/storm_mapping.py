"""Stores the default file mapping used in ``stormlibpp.stix.BundleConf``."""

MAP = {
    "bundle": "bundle.storm",
    "objects": {
        "artifact": "artifact.storm",
        "attack-pattern": "attack-pattern.storm",
        "autonomous-system": "autonomous-system.storm",
        "campaign": "campaign.storm",
        "course-of-action": "course-of-action.storm",
        "directory": "directory.storm",
        "domain-name": "domain-name.storm",
        "email-addr": "email-addr.storm",
        "email-message": "email-message.storm",
        "file": "file.storm",
        "grouping": "grouping.storm",
        "identity": "identity.storm",
        "incident": "incident.storm",
        "indicator": "indicator.storm",
        "infrastructure": "infrastructure.storm",
        "intrusion-set": "intrusion-set.storm",
        "ipv4-addr": "ipv4-addr.storm",
        "ipv6-addr": "ipv6-addr.storm",
        "location": "location.storm",
        "mac-addr": "mac-addr.storm",
        "malware-analysis": "malware-analysis.storm",
        "malware": "malware.storm",
        "mutex": "mutex.storm",
        "network-traffic": "network-traffic.storm",
        "note": "note.storm",
        "observed-data": "observed-data.storm",
        "opinion": "opinion.storm",
        "process": "process.storm",
        "relationship": "relationship.storm",
        "report": "report.storm",
        "sighting": "sighting.storm",
        "software": "software.storm",
        "threat-actor": "threat-actor.storm",
        "tool": "tool.storm",
        "url": "url.storm",
        "user-account": "user-account.storm",
        "vulnerability": "vulnerability.storm",
        "windows-registry-key": "windows-registry-key.storm",
        "x509-certificate": "x509-certificate.storm",
    },
    "relationships": [
        {
            "type": ["campaign", "attributed-to", "intrusion-set"],
            "storm": "camp_to_intset.storm",
        },
        {
            "type": ["intrusion-set", "attributed-to", "threat-actor"],
            "storm": "intset_to_ta.storm",
        },
        {
            "type": [None, "uses", None],
            "storm": "uses.storm",
        },
        {
            "type": [None, "indicates", None],
            "storm": "indicates.storm",
        },
        {
            "type": ["threat-actor", "attributed-to", "identity"],
            "storm": "ta_to_id.storm",
        },
    ],
}
"""A mapping of items in a ``$lib.stix.import.config()`` to Storm file names.

The name of each top-level key is a folder in a parent directory passed to
``BundleConf`` as ``storm_path``. These keys also match the top-level keys
of a ``$lib.stix.import.config()``.

``BundleConf`` uses this mapping to create a valid ``$lib.stix.import.config()``,
loading Storm code from the files designated files.

The ``bundle`` should only ever point to a single Storm file.

Each sub-key of ``objects`` is the name of a Stix object, and points to a single
file that has Storm code to create a node from that Stix object.

The ``relationships`` values are almost exactly the same as those found in a
``$lib.stix.import.config()``. Except that the ``storm`` key points to a file
with Storm code.

The default mapping represents a file structure like this::

    storm/
    ├── bundle
    │   └── bundle.storm
    ├── objects
    │   ├── artifact.storm
    │   ├── attack-pattern.storm
    │   ├── autonomous-system.storm
    │   ├── campaign.storm
    │   ├── course-of-action.storm
    │   ├── directory.storm
    │   ├── domain-name.storm
    │   ├── email-addr.storm
    │   ├── email-message.storm
    │   ├── file.storm
    │   ├── grouping.storm
    │   ├── identity.storm
    │   ├── incident.storm
    │   ├── indicator.storm
    │   ├── infrastructure.storm
    │   ├── intrusion-set.storm
    │   ├── ipv4-addr.storm
    │   ├── ipv6-addr.storm
    │   ├── location.storm
    │   ├── mac-addr.storm
    │   ├── malware-analysis.storm
    │   ├── malware.storm
    │   ├── mutex.storm
    │   ├── network-traffic.storm
    │   ├── note.storm
    │   ├── observed-data.storm
    │   ├── opinion.storm
    │   ├── process.storm
    │   ├── relationship.storm
    │   ├── report.storm
    │   ├── sighting.storm
    │   ├── software.storm
    │   ├── threat-actor.storm
    │   ├── tool.storm
    │   ├── url.storm
    │   ├── user-account.storm
    │   ├── vulnerability.storm
    │   ├── windows-registry-key.storm
    │   └── x509-certificate.storm
    └── relationships
        ├── camp_to_intset.storm
        ├── indicates.storm
        ├── intset_to_ta.storm
        ├── ta_to_id.storm
        └── uses.storm
"""
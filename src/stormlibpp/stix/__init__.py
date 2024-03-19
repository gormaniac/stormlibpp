"""Code to aid in building objects for the ``$lib.stix`` Storm library."""

import json
import pathlib

from .. import errors
from .. import utils


MAP = {
    "bundle": "bundle.storm",
    "objects": {
        "campaign": "campaign.storm",
        "course-of-action": "course-of-action.storm",
        "identity": "identity.storm",
        "indicator": "indicator.storm",
        "intrusion-set": "intrusion-set.storm",
        "malware": "malware.storm",
        "report": "report.storm",
        "threat-actor": "threat-actor.storm",
        "tool": "tool.storm",
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

Expects a file structure like this::
    storm/
    ├── bundle/
    │   └── bundle.storm
    ├── objects/
    │   ├── campaign.storm
    │   ├── course-of-action.storm
    │   ├── identity.storm
    │   ├── indicator.storm
    │   ├── intrusion-set.storm
    │   ├── malware.storm
    │   ├── report.storm
    │   ├── threat-actor.storm
    │   └── tool.storm
    └── relationships/
        ├── camp_to_intset.storm
        ├── indicates.storm
        ├── intset_to_ta.storm
        ├── ta_to_id.storm
        └── uses.storm
"""

BLANK_CONF = {
    "addbundle": True,
    "bundle": {},
    "objects": {},
    "relationships": [],
}
"""A blank ``$lib.stix.import.config()``."""


class BundleConfError(RuntimeError):
    """An error raised by BundleConf."""


class BundleConfSaveError(BundleConfError):
    """Raise when a BundleConf can't be saved."""


class BundleConfLoadStormError(BundleConfError):
    """Raise when a BundleConf can't load a Storm file."""


class BundleConf:
    """Create a ``$lib.stix.import.config()`` compatible config from storm files.

    Parameters
    ----------
    storm_path : str, optional
        The path the to folder containing Storm code, by default "storm".
    storm_rel : bool, optional
        Whether ``storm_path`` is relative to the file that this object is declared
        in, by default True.
    out : str, optional
        The path to save output in, by default ``bundle_conf.json``.
    dot_storm : bool, optional
        Whether storm files in ``map`` end with a ``.storm`` extension, by default True.
    map : dict, optional
        A custom mapping of ``$lib.stix.import.config()`` to Storm files. By
        default ``MAP``. See ``MAP`` docstrings for details.
    """

    def __init__(
        self,
        storm_path: str = "storm",
        storm_rel: bool = True,
        out: str = "bundle_conf.json",
        dot_storm: bool = True,
        map: dict = MAP,
    ) -> None:
        if storm_rel:
            self.path = (pathlib.Path(__file__).parent / storm_path).expanduser().resolve()
        else:
            self.path = pathlib.Path(storm_path).expanduser().resolve()

        self.out = pathlib.Path(out).expanduser().resolve()
        self.dot_storm = dot_storm

        self.map = map

        self.bundle_conf = BLANK_CONF

    def __repr__(self):
        return "BundleConf(storm_path='{p}', out='{o}', dot_storm={d})".format(
            p=self.path,
            o=self.out,
            d=self.dot_storm,
        )

    def __str__(self) -> str:
        return json.dumps(self.bundle_conf)
    
    def _load_storm(self, key: str, rel_path: str):
        # TODO - figureout .storm extension stuff
        # ext = ".storm" if self.dot_storm else ""
        # path = str(self.path / key / f"{rel_path}{ext}")
        path = str(self.path / key / rel_path)

        try:
            with open(path, "r") as fd:
                storm = fd.read()
                utils.chk_storm_syntax(storm)
        except OSError as err:
            raise BundleConfLoadStormError(
                f"Unable to load the Storm code from {path}: {err}"
            ) from err
        except errors.StormSyntaxError as err:
            raise BundleConfLoadStormError(
                f"Storm syntax error in {path}: {err}"
            ) from err
        
        return storm

    def load(self):
        for key, val in self.map.items():
            if key == "bundle":
                self.bundle_conf[key].update({"storm": self._load_storm(key, val)})
            elif key == "relationships":
                for item in val:
                    self.bundle_conf[key].append({"type": item["type"], "storm": self._load_storm(key, item["storm"])})
            elif key == "objects":
                for item in val:
                    self.bundle_conf[key].update({item: {"storm": self._load_storm(key, val[item])}})

    def save(self, out: str | pathlib.Path = ""):
        path = out if out else self.out
        try:
            with open(path, "w") as fd:
                json.dump(self.bundle_conf, fd, indent=2)
        except (TypeError, OSError) as err:
            raise BundleConfSaveError(
                f"Unable to save the Storm Stix bundle config to {path}: {err}"
            ) from err

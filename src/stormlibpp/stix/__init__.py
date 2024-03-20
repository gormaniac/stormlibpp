"""Code to aid in building objects for the ``$lib.stix`` Storm library."""

import json
import pathlib

from . import storm_mapping
from .. import errors
from .. import utils


BLANK_CONF = {
    "addbundle": True,
    "bundle": {},
    "objects": {},
    "relationships": [],
}
"""A blank ``$lib.stix.import.config()``."""


class BundleConf:
    """Create a ``$lib.stix.import.config()`` compatible config from storm files.

    Parameters
    ----------
    storm_path : str, optional
        The path the to folder containing Storm code, by default "storm".
    default : bool, optional
        Whether to build the default import config dict packaged with stormlibpp.
        Ignores the ``storm_path`` object if True. By default True.
    out : str, optional
        The path to save output in, by default "bundle_conf.json".
    map : dict, optional
        A custom mapping of ``$lib.stix.import.config()`` to Storm files. By
        default ``storm_mapping.MAP``. See ``storm_mapping.MAP`` docstrings for details.
    """

    def __init__(
        self,
        storm_path: str = "storm",
        default: bool = True,
        out: str = "bundle_conf.json",
        map: dict = storm_mapping.MAP,
    ) -> None:
        self.default = default

        if self.default:
            self.path = (pathlib.Path(__file__).parent / "storm").expanduser().resolve()
        else:
            self.path = pathlib.Path(storm_path).expanduser().resolve()

        self.out = pathlib.Path(out).expanduser().resolve()

        self.map = map

        self.bundle_conf = BLANK_CONF

    def __repr__(self):
        return (
            "BundleConf(storm_path='{p}', out='{o}', default={d}, map={m})"
        ).format(
            p=self.path,
            o=self.out,
            d=self.default,
            m="{Default Map}" if self.map == storm_mapping.MAP else "{Custom Map}"
        )

    def __str__(self) -> str:
        return json.dumps(self.bundle_conf)
    
    def _load_storm(self, key: str, rel_path: str):
        path = str(self.path / key / rel_path)

        try:
            with open(path, "r") as fd:
                storm = fd.read()
                utils.chk_storm_syntax(storm)
        except OSError as err:
            raise errors.BundleConfLoadStormError(
                f"Unable to load the Storm code from {path}: {err}"
            ) from err
        except errors.StormSyntaxError as err:
            raise errors.BundleConfLoadStormError(
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
            raise errors.BundleConfSaveError(
                f"Unable to save the Storm Stix bundle config to {path}: {err}"
            ) from err

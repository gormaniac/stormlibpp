"""Build or check the standalone STIX import configuration from this checkout."""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stormlibpp.stix import BundleConf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail if the checked-in config is stale."
    )
    args = parser.parse_args()
    config = BundleConf(out=ROOT / "data/stix_import_conf.json")
    config.load()
    if args.check:
        try:
            current = json.loads(config.out.read_text())
        except (OSError, ValueError):
            current = None
        if current != config.bundle_conf:
            parser.exit(
                1, "STIX config is stale; run python scripts/build_stix_conf.py.\n"
            )
    else:
        config.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Pin a built STIX package's config URL to the repository release version."""

import argparse
import json
import os
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
RELEASE_TAG_MARKER = "__STORMLIBPP_RELEASE_TAG__"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=pathlib.Path)
    parser.add_argument("--release-tag", default=os.environ.get("RELEASE_TAG"))
    args = parser.parse_args()
    with (ROOT / "pyproject.toml").open("rb") as source:
        version = tomllib.load(source)["project"]["version"]
    expected_tag = f"v{version}"
    release_tag = args.release_tag or expected_tag
    if release_tag != expected_tag:
        parser.error(f"Release tag {release_tag} does not match {expected_tag}.")

    package = json.loads(args.package.read_text())
    if package.get("name") != "stormlibpp-stix":
        parser.error("Expected the built stormlibpp-stix package.")
    modules = [
        module
        for module in package.get("modules", ())
        if module["name"] == "slib.stix.lib"
    ]
    if len(modules) != 1 or modules[0].get("storm", "").count(RELEASE_TAG_MARKER) != 1:
        parser.error("Expected exactly one STIX release-tag marker in slib.stix.lib.")
    modules[0]["storm"] = modules[0]["storm"].replace(RELEASE_TAG_MARKER, release_tag)
    args.package.write_text(json.dumps(package, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

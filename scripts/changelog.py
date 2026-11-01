"""Print the CHANGELOG.md section for a given version.

Intended to be executed from project root. Exits non-zero if the version has
no entry in the changelog.

Usage: python3 scripts/changelog.py <version|vversion>
"""

import re
import sys

CHANGELOG = "CHANGELOG.md"

try:
    version = sys.argv[1].lstrip("v")
except IndexError:
    print("Must specify a version!", file=sys.stderr)
    sys.exit(2)

header = re.compile(rf"^## v{re.escape(version)}(\s|$)")

lines = []
found = False
with open(CHANGELOG, "r") as fd:
    for line in fd:
        if line.startswith("## "):
            if found:
                break
            found = bool(header.match(line))
            continue
        if found:
            lines.append(line)

if not found:
    print(f"No CHANGELOG entry found for v{version}", file=sys.stderr)
    sys.exit(1)

print("".join(lines).strip())

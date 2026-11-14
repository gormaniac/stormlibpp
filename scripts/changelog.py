"""Manage CHANGELOG.md entries.

Intended to be executed from project root.

Usage:
    python3 scripts/changelog.py notes <version>
        Print the body of the CHANGELOG entry for <version>. Exits 1 if there
        is no entry for it.

    python3 scripts/changelog.py release <version> [<date>]
        Turn the "## Unreleased" section into "## v<version> - <date>" (date
        defaults to today, UTC) and start a fresh, empty "## Unreleased"
        section above it. Does nothing if <version> already has an entry.
        Exits 1 if there is neither an entry for <version> nor a non-empty
        Unreleased section.

<version> may be given with or without a leading "v".
"""

import datetime
import re
import sys

CHANGELOG = "CHANGELOG.md"
UNRELEASED = "## Unreleased"
SUBSECTIONS = ("### Features", "### Fixes")
UNRELEASED_TEMPLATE = UNRELEASED + "\n" + "\n".join(SUBSECTIONS) + "\n"


def read():
    with open(CHANGELOG, "r") as fd:
        return fd.read()


def split_sections(text):
    """Split the changelog into (preamble, [section, ...]) on "## " headers."""
    parts = re.split(r"(?m)^(?=## )", text)
    return parts[0], parts[1:]


def is_version_header(section, version):
    first = section.splitlines()[0]
    return re.match(rf"^## v{re.escape(version)}(\s|$)", first) is not None


def has_content(section):
    """True if a section has anything beyond its headers and blank lines."""
    return any(
        line.strip() and not line.startswith("#") for line in section.splitlines()
    )


def fill_empty_subsections(body):
    """Put "- N/A" under any Features/Fixes header that has no entries."""
    lines = body.rstrip("\n").splitlines()
    out = []
    for i, line in enumerate(lines):
        out.append(line)
        if line.strip() in SUBSECTIONS:
            nxt = next((l for l in lines[i + 1 :] if l.strip()), None)
            if nxt is None or nxt.startswith("#"):
                out.append("- N/A")
    return "\n".join(out) + "\n\n"


def notes(version):
    _, sections = split_sections(read())
    for section in sections:
        if is_version_header(section, version):
            print(section.split("\n", 1)[1].strip() if "\n" in section else "")
            return 0
    print(f"No CHANGELOG entry found for v{version}", file=sys.stderr)
    return 1


def release(version, date):
    preamble, sections = split_sections(read())

    if any(is_version_header(s, version) for s in sections):
        print(f"CHANGELOG already has an entry for v{version}", file=sys.stderr)
        return 0

    for i, section in enumerate(sections):
        if section.splitlines()[0].strip() == UNRELEASED:
            if not has_content(section):
                break
            body = section.split("\n", 1)[1] if "\n" in section else ""
            released = f"## v{version} - {date}\n" + fill_empty_subsections(body)
            sections[i] = UNRELEASED_TEMPLATE + "\n" + released
            with open(CHANGELOG, "w") as fd:
                fd.write(preamble + "".join(sections))
            print(f"Released the Unreleased CHANGELOG section as v{version}", file=sys.stderr)
            return 0

    print(
        f"No CHANGELOG entry for v{version} and no non-empty '{UNRELEASED}' section",
        file=sys.stderr,
    )
    return 1


def main(argv):
    if len(argv) < 2 or argv[0] not in ("notes", "release"):
        print(__doc__, file=sys.stderr)
        return 2

    version = argv[1].lstrip("v")
    if argv[0] == "notes":
        return notes(version)

    date = argv[2] if len(argv) > 2 else datetime.datetime.now(datetime.UTC).date().isoformat()
    return release(version, date)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

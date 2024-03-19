import argparse
import io
import re
import os
import pathlib


PATTERNS = {
    "TODO": re.compile(r"((#\s(TODO)\s-\s)(.+$))"),
    "NOTE": re.compile(r"((#\s(NOTE)\s-\s)(.+$))"),
    "FIXME": re.compile(r"((#\s(FIXME)\s-\s)(.+$))"),
    "BUG": re.compile(r"((#\s(BUG)\s-\s)(.+$))"),
    "HACK": re.compile(r"((#\s(HACK)\s-\s)(.+$))"),
    "ALL": re.compile(r"((#\s([A-Z]+|\!\!\!|\?\?\?)\s-\s)(.+$))"),
}


class CodeTags:
    def __init__(self, filename: str) -> None:
        self.tags: dict[str, list] = dict()
        self.filename = str(filename)

    def __repr__(self) -> str:
        return f'CodeTags(filename="{self.filename}")'
    
    def __str__(self) -> str:
        out = io.StringIO(f"Code tags in {self.filename}:\n")
        for tag, comments in self.tags.items():
            print(tag, file=out)
            for comment in comments:
                print(f"\t- {comment}", file=out)
        out.flush()
        out.seek(0)
        return out.read()

    def add(self, tag_name: str, comment: str):
        if tag_name not in self.tags:
            self.tags[tag_name] = list()

        self.tags[tag_name].apppend(comment)

    @classmethod
    def find(
        cls,
        filename: str,
        only: str = "",
        normal: bool = False,
        all: bool = False,
    ):
        """Find all PEP-350 code tags in filename."""

        if all:
            patterns = [PATTERNS["ALL"]]
        elif normal:
            patterns = [ptrn for key, ptrn in PATTERNS.items() if key != "ALL"]
        elif only:
            try:
                patterns = [PATTERNS[only.upper()]]
            except KeyError as err:
                raise ValueError(
                    f"The specific code tag {only} is not supported"
                ) from err
        else:
            raise ValueError("Invalid options passed to CodeTags.find!")

        code_tags = cls(filename)

        try:
            with open(filename, "r") as fd:
                fdata = fd.read()
                for pattern in patterns:
                    for match_obj in pattern.finditer(fdata):
                        code_tags.add(match_obj.group(2), match_obj.group(3))
        except (IOError, re.error) as e:
            raise RuntimeError(f"Unable to find code tags in {filename}: {e}")
        
        return code_tags

    def print(self, fd=None):
        print(str(self), file=fd)


def find_code_tags(
    folder: str,
    only: str = "",
    normal: bool = False,
    all: bool = False,
):
    """Walk folder and find PEP-350 code tags."""

    for dpath, _, fnames in os.walk(folder):

        if (".git" in dpath) or ("doc" in dpath):
            continue

        for fname in fnames:
            fullpath = os.path.join(dpath, fname)
            yield CodeTags.find(fullpath, only=only, normal=normal, all=all)


def main():
    """The main function."""

    parser = argparse.ArgumentParser(
        description="Convert this Python project template into a named Python project."
    )
    parser.add_argument(
        "-t",
        "--tag",
        help="A specific code tag to look for.",
        choices=[key.lower() for key in PATTERNS.keys() if key != "ALL"],
    )
    parser.add_argument(
        "-a",
        "--all",
        help="Look for all code tags  in PEP-350.",
        action="store_true"
    )

    args = parser.parse_args()

    if (not args.all) and (not args.tag):
        normal = True
    else:
        normal = False
    
    folder = pathlib.Path(__file__).parent.parent.resolve()

    for code_tags in find_code_tags(folder, only=args.tag, normal=normal, all=args.all):
        code_tags.print()


if __name__ == "__main__":
    main()

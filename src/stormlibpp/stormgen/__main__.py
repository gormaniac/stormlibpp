"""Compile Markdown documents to standalone Storm without connecting to a Cortex."""

import argparse
from pathlib import Path
import sys

from . import compile_storm, parse


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="Markdown file, or - for standard input")
    parser.add_argument("--doc-type", choices=("full", "forms", "embedded"), default="full")
    parser.add_argument("--form", default="", help="Form for a single-form document or embedded fallback")
    parser.add_argument("--form-level", type=int, default=2)
    parser.add_argument("--nodes-header", default="Nodes")
    parser.add_argument("--comments", action="store_true", help="Create notes from node documentation")
    args = parser.parse_args(argv)
    try:
        text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
        program = compile_storm(
            parse(text), args.doc_type, args.nodes_header, args.form,
            form_level=args.form_level, comments=args.comments,
        )
        sys.stdout.write(program.to_storm())
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f"{parser.prog}: error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

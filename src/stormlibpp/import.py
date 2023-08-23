"""Recursively execute all Storm scripts in a given folder on a given Synapse Cortex over HTTP."""


import argparse
import asyncio
import copy
import csv
import functools
import getpass
import json
import os
import pathlib
import sys

import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.telepath as s_telepath

from .httpcore import HttpCortex
from .output import OUTP, handle_msg
from .stormcli import start_storm_cli


def endswith(text, items):
    for item in items:
        if text.endswith(item):
            return True
    return False


def csv_genr(fd):
    for row in csv.reader(fd):
        yield row


def json_genr(fd):
    # TODO - Support nested key to start with
    data = json.load(fd)

    if type(data, dict):
        for key, row in data.items():
            yield [key, row]
    else:
        count = 0
        for row in data:
            yield [count, row]
            count += 1


def txt_genr(fd):
    for row in fd.readlines():
        yield row.strip()


async def import_storm_text(core, text, stormopts, print_skips):
        async for msg in core.storm(text, opts=stormopts):
            handle_msg(msg, print_skips=print_skips)
    

async def import_storml_file(core, storm_script, stormopts, print_skips):
    with open(storm_script, "r") as fd:
        for line in txt_genr(fd):
            await import_storm_text(core, line, stormopts, print_skips)


class Importer:
    genrs = {
        "csv": csv_genr,
        "txt": txt_genr,
        "json": json_genr,
    }

    def __init__(
        self, core, files, ftype, text, stormopts={}, outp=OUTP, header=False, debug=False
    ) -> None:
        self.file_type = ftype
        self.text = text
        self.core = core
        self.files = files
        self.outp = outp
        self.header = header
        self.debug = debug

        # TODO - Make sure this is actually necessary - or if just copy suffices
        self.stormopts = copy.deepcopy(stormopts)

    def iterrows(self):
        for path in self.files:
            with open(path, "r", encoding="utf8") as fd:
                if self.header and self.file_type in ("csv", "txt"):
                    fd.readline()

                for rows in s_common.chunks(self.genrs[self.file_type](fd), 1000):
                    yield rows

    async def add_data(self):
        nodecount = 0

        self.stormopts["editformat"] = "splices"
        vars = self.stormopts.setdefault("vars", {})

        for rows in self.iterrows():
            vars["rows"] = rows

            async for mesg in self.core.storm(self.text, opts=self.stormopts):
                if mesg[0] == "node":
                    nodecount += 1

                elif mesg[0] in ("err", "warn") and not self.debug:
                    self.outp.printf(repr(mesg))

                elif mesg[0] == "print":
                    self.outp.printf(mesg[1].get("mesg"))

                if self.debug:
                    self.outp.printf(repr(mesg))

        return nodecount


def find_data_file(orig: str, files: list[str]):
    """Find a data file in a list of files that has the same name (and path) as the original file."""

    extension_map = {
        ".csv": "csv",
        ".json": "json",
        ".txt": "txt",
    }

    origparent = pathlib.Path(orig).parent
    origname = pathlib.Path(orig).stem

    # TODO - Support multiple files with a _\d+ suffix
    for fname in files:
        fpath = pathlib.Path(fname)
        if fpath.parent == origparent and fpath.stem == origname and fpath.suffix in extension_map.keys():
            return fname, extension_map[fpath.suffix]

    return None


def get_args(argv: list[str]):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "folders", help="The folder(s) containing Storm scripts to execute", nargs="+"
    )
    parser.add_argument(
        "--cli",
        help="Start a Storm CLI connected to the Cortex after all scripts are executed",
        action="store_true",
    )
    parser.add_argument(
        "--cortex",
        help="The URL of the Synapse Cortex to execute the Storm scripts on",
        type=str,
    )
    parser.add_argument(
        "--csv-header",
        help="All CSVs processed by this script have headers",
        action="store_true",
    )
    parser.add_argument(
        "--debug",
        help=(
            "Does two things - sets all Storm runtimes to debug mode AND prints all"
            " Storm messages (including node/node:edits) during imports"
        ),
        action="store_true",
    )
    parser.add_argument(
        "--http",
        help="Connect to the Cortex over HTTP instead of Telepath",
        action="store_true",
    )
    parser.add_argument(
        "--local",
        help=(
            "Start a temp Cortex locally to execute the Storm scripts"
            " on and enter a CLI for afterwards"
        ),
        action="store_true",
    )
    parser.add_argument(
        "--no-verify",
        help="Skips verification of the Cortex's certificate when using --http",
        action="store_true",
    )
    parser.add_argument(
        "--user",
        help=(
            "The Synapse user to authenticate with -"
            " by default the return of getpass.getuser()"
        ),
        default=getpass.getuser(),
    )
    parser.add_argument(
        "--view",
        help="An optional view to work in - otherwise the Cortex's default is chosen",
        default=None,
    )
    # TODO - Support a logfile
    # TODO - Support custom "vars" or "stormopts" for each storm invocation
    # TODO - User controled print skips

    return parser.parse_args(argv)


async def main(argv: list[str]):
    args = get_args(argv)
    stormopts = {"repr": True}

    if args.debug:
        print_skips = []
        stormopts["debug"] = True
    else:
        print_skips = ["node", "node:edits"]

    # TODO - Break the loading and then importing code out into methods
    if args.cortex and args.local:
        return "Can't use both --cortex and --local!"
    elif args.cortex:
        if args.http:
            synuser = args.user
            synpass = getpass.getpass()
            core_obj = functools.partial(
                HttpCortex, args.cortex, synuser, synpass, ssl_verify=not args.no_verify
            )
        else:
            # TODO - Actually get this working... maybe wrap it in a context manager? find dif method?
            # The issue is that this becomes a coroutine and not a context manager like the others
            # core_obj = functools.partial(s_telepath.openurl, args.cortex)
            return "Telepath is currently not supported 😬 use --http"
    elif args.local:
        core_obj = s_cortex.getTempCortex
    else:
        return "Must provide a Cortex URL (--cortex) or use a temp Cortex (--local)!"

    storm_scripts = []
    data_files = []
    for folder in args.folders:
        path = pathlib.Path(folder).expanduser().resolve()
        if path.exists() and path.is_dir():
            for dir, dirs, files in os.walk(path):
                dirs.sort()  # NOTE - Ensures the next iteration of dirs is in order.
                for file in sorted(files):
                    fullpath = os.path.join(dir, file)
                    if endswith(file, (".storm", ".storml")):
                        storm_scripts.append(fullpath)
                    elif endswith(file, (".json", ".txt", ".csv")):
                        data_files.append(fullpath)
        else:
            print(f"{path} doesn't exist!")

    async with s_telepath.withTeleEnv():  # NOTE - We only need this for Telepath connections but still have to run it each time
        async with core_obj() as core:
            for storm_script in storm_scripts:  # NOTE - Don't use sorted here - it will put folders ahead of files
                with open(storm_script, "r") as fd:
                    text = fd.read()

                if file_info := find_data_file(storm_script, data_files):
                    fpath, ftype = file_info
                    await Importer(
                        core,
                        [fpath],
                        ftype,
                        text,
                        stormopts=stormopts,
                        header=args.csv_header,
                        debug=args.debug,
                    ).add_data()
                else:
                    if storm_script.endswith(".storml"):
                        # TODO - This will wind up opening and closing the file twice.
                        # Do we want that? Maybe we do because we won't get here much?
                        await import_storml_file(core, storm_script, stormopts, print_skips)
                    else:
                       await import_storm_text(core, text, stormopts, print_skips)

            if args.cli:
                await start_storm_cli(core, outp=OUTP, opts=args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))

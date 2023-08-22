"""Recursively execute all Storm scripts in a given folder on a given Synapse Cortex over HTTP."""


import argparse
import asyncio
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


class Importer:
    def __init__(self, core, files, ftype, stormopts={}, outp=OUTP, header=False, debug=False) -> None:
        self.file_type = ftype
        self.core = core
        self.files = files
        self.outp = outp
        self.header = header
        self.debug = debug
        self.stormopts = stormopts

        self.genrs = {
            "csv": self.csv_genr,
            "txt": self.txt_genr,
            "json": self.json_genr,
        }

    def json_genr(self, fd):
        for row in json.load(fd):
            yield row

    def txt_genr(self, fd):
        for row in fd.readlines():
            yield row.strip()

    def csv_genr(self, fd):
        for row in csv.reader(fd):
            yield row

    def iterrows(self):
        for path in self.files:

            with open(path, 'r', encoding='utf8') as fd:

                if self.header:
                    fd.readline()

                for rows in s_common.chunks(self.genrs[self.file_type](), 1000):
                    yield rows

    async def add_data(self):

        nodecount = 0

        self.stormopts['editformat'] = 'splices'
        vars = self.stormopts.setdefault('vars', {})

        for rows in self.iterrows():

            vars['rows'] = rows

            async for mesg in self.core.storm(self.text, opts=self.stormopts):

                if mesg[0] == 'node':
                    nodecount += 1

                elif mesg[0] in ('err', 'warn') and not self.debug:
                    self.outp.printf(repr(mesg))

                elif mesg[0] == 'print':
                    self.outp.printf(mesg[1].get('mesg'))

                if self.debug:
                    self.outp.printf(repr(mesg))
        
        return nodecount


def find_data_file(orig: str, files: list[str]):
    """Find a data file in a list of files that has the same name (and path) as the original file."""

    origparent = pathlib.Path(orig).parent
    origname = pathlib.Path(orig).stem

    data_names = (f"{origname}.csv", f"{origname}.json", f"{origname}.txt")
    extension_map = {
        ".csv": "csv",
        ".json": "json",
        ".txt": "txt",
    }

    for fname in files:
        fpath = pathlib.Path(fname)
        if fpath.parent == origparent and fpath.stem in data_names:
            return fname, extension_map[fpath.suffix]
    
    return None


def get_args(argv: list[str]):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", help="The folder(s) containing Storm scripts to execute", nargs="+")
    parser.add_argument("--cli", help="Start a Storm CLI connected to the Cortex after all scripts are executed", action="store_true")
    parser.add_argument("--cortex", help="The URL of the Synapse Cortex to execute the Storm scripts on", type=str)
    parser.add_argument("--csv-header", help="All CSVs processed by this script have headers", action="store_true")
    parser.add_argument("--debug", help="Does two things - sets all Storm runtimes to debug mode AND prints all Storm messages during CSV imports", action="store_true")
    parser.add_argument("--http", help="Connect to the Cortex over HTTP instead of Telepath", action="store_true")
    parser.add_argument("--local", help="Start a temp Cortex locally to execute the Storm scripts on and enter a CLI for afterwards", action="store_true")
    parser.add_argument("--no-verify", help="Skips verification of the Cortex's certificate when using --http", action="store_true")
    parser.add_argument("--user", help="The Synapse user to authenticate with - by default the return of getpass.getuser()", default=getpass.getuser())
    parser.add_argument("--view", help="An optional view to work in - otherwise the Cortex's default is chosen", default=None)

    return parser.parse_args(argv)


async def main(argv: list[str]):
    args = get_args(argv)
    stormopts = {"repr": True}

    # TODO - Break the loading and then importing code out into methods
    if args.cortex and args.local:
        return "Can't use both --cortex and --local!"
    elif args.cortex:
        if args.http:
            synuser = args.user
            synpass = getpass.getpass()
            core_obj = functools.partial(HttpCortex, args.cortex, synuser, synpass, ssl_verify=not args.no_verify)
        else:
            core_obj = functools.partial(s_telepath.openurl, args.cortex)
    elif args.local:
        core_obj = s_cortex.getTempCortex

    storm_scripts = []
    data_files = []
    for folder in args.folders:
        path = pathlib.Path(folder).expanduser().resolve()
        if path.exists() and path.is_dir():
            for dir, _, files in os.walk(path):
                for file in files:
                    fullpath = os.path.join(dir, file)
                    if file.endswith(".storm"):
                        storm_scripts.append(fullpath)
                    elif file.endswith(".csv"):  # TODO - Handle JSON and TXT files here too
                        data_files.append(fullpath)
        else:
            print(f"{path} doesn't exist!")

    # TODO - Support a logfile
    async with s_telepath.withTeleEnv():  # NOTE - We only need this for Telepath connections but still have to run it each time
        async with core_obj() as core:
            for storm_script in storm_scripts:
                with open(storm_script, "r") as fd:
                    text = fd.read()

                if (file_info := find_data_file(storm_script, data_files)):
                    fpath, ftype = file_info
                    await Importer(core, [fpath], ftype, text, stormopts=stormopts, csv_header=args.csv_header, debug=args.debug).add_data()
                else:
                    async for msg in core.storm(text, opts=stormopts):
                        handle_msg(msg, print_skips=["node", "node:edits"])

            if args.cli:
                await start_storm_cli(core, outp=OUTP, opts=args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))

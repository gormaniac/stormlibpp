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


async def csv_import(core, csvfiles, text, stormopts={}, outp=OUTP, csv_header=False, debug=False):
    """Import the given CSV files to the given core using the provided query text.
    
    This is modified from synapse.tools.csvtool.runCsvImport
    """

    def iterrows():
        for path in csvfiles:

            with open(path, 'r', encoding='utf8') as fd:

                if csv_header:
                    fd.readline()

                def genr():

                    for row in csv.reader(fd):
                        yield row

                for rows in s_common.chunks(genr(), 1000):
                    yield rows

    rowgenr = iterrows()

    async def addCsvData(core):

        nodecount = 0

        stormopts['editformat'] = 'splices'
        vars = stormopts.setdefault('vars', {})

        for rows in rowgenr:

            vars['rows'] = rows

            async for mesg in core.storm(text, opts=stormopts):

                if mesg[0] == 'node':
                    nodecount += 1

                elif mesg[0] == 'err' and not debug:
                    outp.printf(repr(mesg))

                elif mesg[0] == 'print':
                    outp.printf(mesg[1].get('mesg'))

                if debug:
                    outp.printf(repr(mesg))

    nodecount = await addCsvData(core)

    return nodecount


def find_csv_file(orig: str, files: list[str]):
    """Find a CSV file in a list of files that has the same name (and path) as the original file."""

    origparent = pathlib.Path(orig).parent
    origname = pathlib.Path(orig).stem

    for fname in files:
        if pathlib.Path(fname).parent == origparent and pathlib.Path(fname).stem == f"{origname}.csv":
            return fname


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
        if path.exists() and path.is_dir:
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

                if (csv_file := find_csv_file(storm_script, data_files)):
                    await csv_import(core, [csv_file], text, stormopts=stormopts, csv_header=args.csv_header, debug=args.debug)
                else:
                    async for msg in core.storm(text, opts=stormopts):
                        handle_msg(msg, print_skips=["node", "node:edits"])

            if args.cli:
                await start_storm_cli(core, outp=OUTP, opts=args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))

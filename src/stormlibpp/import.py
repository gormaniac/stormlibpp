"""Recursively execute all Storm scripts in a given folder on a given Synapse Cortex over HTTP."""


import argparse
import asyncio
import functools
import getpass
import os
import pathlib
import sys

import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

from .httpcore import HttpCortex
from .output import OUTP, handle_msg
from .stormcli import start_storm_cli


def get_args(argv: list[str]):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", help="The folder(s) containing Storm scripts to execute", nargs="+")
    parser.add_argument("--cli", help="Start a Storm CLI connected to the Cortex after all scripts are executed", action="store_true")
    parser.add_argument("--cortex", help="The URL of the Synapse Cortex to execute the Storm scripts on", type=str)
    parser.add_argument("--http", help="Connect to the Cortex over HTTP instead of Telepath", action="store_true")
    parser.add_argument("--local", help="Start a temp Cortex locally to execute the Storm scripts on and enter a CLI for afterwards", action="store_true")
    parser.add_argument("--no-verify", help="Skips verification of the Cortex's certificate when using --http", action="store_true")
    parser.add_argument("--user", help="The Synapse user to authenticate with - by default the return of getpass.getuser()", default=getpass.getuser())
    parser.add_argument("--view", help="An optional view to work in - otherwise the Cortex's default is chosen", default=None)

    return parser.parse_args(argv)


async def main(argv: list[str]):
    args = get_args(argv)

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
    data_files = []  # TODO - Actually use these files
    for folder in args.folders:
        path = pathlib.Path(folder).expanduser().resolve()
        if path.exists() and path.is_dir:
            for dir, _, files in os.walk(path):
                for file in files:
                    fullpath = os.path.join(dir, file)
                    if file.endswith(".storm"):
                        storm_scripts.append(fullpath)
                    elif file.endswith(".json") or file.endswith(".csv") or file.endswith(".txt"):
                        data_files.append(fullpath)
        else:
            print(f"{path} doesn't exist!")

    async with s_telepath.withTeleEnv():  # NOTE - We only need this for Telepath connections but still have to run it each time
        async with core_obj() as core:
            for storm_script in storm_scripts:
                with open(storm_script, "r") as fd:
                    text = fd.read()
                async for msg in core.storm(text, opts={"repr": True}):
                    handle_msg(msg)

            if args.cli:
                await start_storm_cli(core, outp=OUTP, opts=args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))

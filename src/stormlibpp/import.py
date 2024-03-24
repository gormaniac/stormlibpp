"""
Recursively execute all Storm scripts in a folder (or folders) on a Synapse Cortex.

All sub-folders of the given folder(s) are imported. Sub-folders, and their files,
are imported in alphabetical order. Each folder passed to this script is imported
in the order it is passed. This allows users to build large nested folders of importable
data, like a grouping of an organization's "static" nodes, and keep them in source
control. Groupings of like Storm scripts can be stored in the same folder, and the
order of execution, if it matters, can be manipulated by prepending numbers to the
folder/file names.

Storm scripts can import ``.csv``, ``.json``, and ``.txt`` files. These are referred
to as "data files." Data files are recognized by name, they must have the same name
as the Storm script, but with the appropriate extension. Multiple data files
can be specified for a Storm script by appending an underscore and a number to
the file name of the data file. The following regex is used to find data files,
where ``scriptname`` is the name of the Storm script minus the ``.storm`` extension:
``scriptname(_\d+)?``.

Just like with the out of the box csvtool, a ``$rows`` variable is injected into
the Storm runtime that can be iterated over to do something with each row of the
data file. 

For JSON data files, a "row" is a tuple with an identifier and the top-level
object within the JSON object. If the JSON file defines a list, each item in the list
is a the top-level object in the row. If the JSON file defines a standard object, each
key of the JSON object is passed as the identifier, and the object the key references
is the top-level object. See ``utils.json_genr`` for implementation details. For CSV
and TXT files, each line is a "row" in the ``$rows`` variable. A JSON lines file should
use the ``.txt`` extension and each line of JSON will be a "row" in the Storm script's
``$rows`` variable.

Storm scripts that do not have data files associated with them will be executed as is
on the Cortex.

A special Storm script extension is recognized by this tool - ``.storml``. Rather than
running these Storm scripts all in one. Each line in the ``.storml`` file is executed
on the Cortex in its own runtime. Data files are not supported for ``.storml`` scripts.

This script attempts to support the same thing as the out of the box csvtool.
A local test Cortex can be spun up to test imports. A CLI can be dropped into
to support this testing, or observe the newly imported nodes. A specific view
can be given, instead of using the Cortex's default view. A log file is supported
so that a script's messages can be viewed. All prints, or other output, from the
Storm scripts is printed to the console.

There are some differences though:

* By default, ``node`` and ``node:edits`` messages are not printed.
* HTTP communication with the Cortex is supported along with Telepath.

    * The same authentication rules as the ``hstorm`` tool apply.

* Specific Storm message types can be skipped from output.
* A YAML file with custom ``stormopts`` used by every script can be supplied.

"""

# TODO - Finish docstrings for this file

import argparse
import asyncio
import copy
import io
import functools
import os
import pathlib
import re
import sys

import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.telepath as s_telepath
import yaml

from ._args import USER_PARSER, VERIFY_PARSER
from .httpcore import HttpCortex
from .output import handle_msg, log_storm_msg, OUTP
from .stormcli import start_storm_cli
from .utils import (
    csv_genr,
    endswith,
    get_cortex_creds,
    get_cortex_obj,
    json_genr,
    txt_genr,
)


DESCRIPTION = """
Recursively execute all Storm scripts in a folder (or folders) on a Synapse Cortex.

Data can optionally be imported from .csv, .json, and .txt files, like with csvtool.

If no data is given for a Storm script, it is executed as is.

See the stormlibpp.import docs for feature specifics:
https://gormo.co/stormlibpp/stormlibpp.html#module-stormlibpp.import
"""


Cortex = HttpCortex | s_cortex.CoreApi
StormCode = str
"""A string containing valid Storm code to run on a Cortex."""
StormOpts = dict
"""
Storm Options to pass to a Storm runtime.

https://synapse.docs.vertex.link/en/latest/synapse/devguides/storm_api.html#storm-opts
"""


async def import_storm_text(
    core: Cortex,
    text: StormCode,
    stormopts: StormOpts,
    print_skips: list,
    logfd: io.BufferedRandom,
):
    async for msg in core.storm(text, opts=stormopts):
        handle_msg(msg, print_skips=print_skips, logfd=logfd)


async def import_storml_file(
    core: Cortex,
    storm_script: StormCode,
    stormopts: StormOpts,
    print_skips: list,
    logfd: io.BufferedRandom,
):
    with open(storm_script, "r") as fd:
        for line in txt_genr(fd):
            await import_storm_text(core, line, stormopts, print_skips, logfd)


class Importer:
    genrs = {
        "csv": csv_genr,
        "txt": txt_genr,
        "json": json_genr,
    }

    def __init__(
        self,
        core,
        files,
        ftype,
        text,
        stormopts={},
        outp=OUTP,
        header=False,
        debug=False,
        logfd=None,
        splices=False,
    ) -> None:
        self.file_type = ftype
        self.text = text
        self.core = core
        self.files = files
        self.outp = outp
        self.header = header
        self.debug = debug
        self.logfd = logfd

        if splices:
            self.edit_format = "splices"
        else:
            self.edit_format = "nodeedits"

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

        self.stormopts["editformat"] = self.edit_format
        vars = self.stormopts.setdefault("vars", {})

        for rows in self.iterrows():
            vars["rows"] = rows

            async for mesg in self.core.storm(self.text, opts=self.stormopts):
                # TODO - Use handle_msg here instead?
                if mesg[0] == "node":
                    nodecount += 1

                elif mesg[0] in ("err", "warn") and not self.debug:
                    self.outp.printf(repr(mesg))

                elif mesg[0] == "print":
                    self.outp.printf(mesg[1].get("mesg"))

                if self.debug:
                    self.outp.printf(repr(mesg))

                log_storm_msg(self.logfd, mesg)

        return nodecount


def find_data_files(orig: str, files: list[str]) -> tuple[str, str]:
    """
    Find all data files in a list of files that have the same name (and path) as the original file.
    """

    extension_map = {
        ".csv": "csv",
        ".json": "json",
        ".txt": "txt",
    }

    origparent = pathlib.Path(orig).parent
    origname = pathlib.Path(orig).stem
    origre = re.compile(f"{origname}(_\d+)?")

    data_files = []

    for fname in files:
        fpath = pathlib.Path(fname)
        if (
            fpath.parent == origparent
            and origre.match(fpath.stem)
            and fpath.suffix in extension_map.keys()
        ):
            data_files.append((fname, extension_map[fpath.suffix]))

    return data_files


def get_args(argv: list[str]):
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        parents=[USER_PARSER, VERIFY_PARSER],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
        "--view",
        help="An optional view to work in - otherwise the Cortex's default is chosen",
        default=None,
    )
    parser.add_argument(
        "--logfile", help="Set a logfile to save each Storm message as a JSON line"
    )
    parser.add_argument(
        "--print-skips",
        help="A list of Storm message types that will not be printed as long as --debug is not used",
        nargs="+",
        default=["node", "node:edits"],
    )
    parser.add_argument(
        "--stormopts-file",
        help=(
            "A YAML file that defines custom stormopts to pass with each execution "
            "of Storm code. The 'rows' key of the 'vars' opt will always be overwritten "
            "by this script. The '--debug' flag will also override the 'debug' opt in "
            "this file. 'repr' is always set to True regardless of this file's contents."
        ),
    )
    parser.add_argument(
        "--splices",
        help=(
            "Use the legacy 'splices' editformat while importing. Use while"
            " importing data to a Cortex that is running a version <2.156.0."
        ),
        action="store_true",
    )
    # TODO - Add --quiet mode
    # TODO - support hidetags/hideprops

    return parser.parse_args(argv)


def collect_files(folders):
    storm_scripts = []
    data_files = []
    for folder in folders:
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

    return storm_scripts, data_files


async def import_data(
    core_obj,
    storm_scripts,
    data_files,
    stormopts,
    csv_header,
    debug,
    print_skips,
    cli,
    logfd,
    args,
    splices,
):
    async with core_obj() as core:
        # TODO - Perhaps use an asyncio.map here or something similar to parallelize
        # NOTE - Don't use sorted here - it will put folders ahead of files
        for storm_script in storm_scripts:
            with open(storm_script, "r") as fd:
                text = fd.read()

            if file_infos := find_data_files(storm_script, data_files):
                for file_info in file_infos:
                    fpath, ftype = file_info
                    await Importer(
                        core,
                        [fpath],
                        ftype,
                        text,
                        stormopts=stormopts,
                        header=csv_header,
                        debug=debug,
                        logfd=logfd,
                        splices=splices,
                    ).add_data()
            else:
                if storm_script.endswith(".storml"):
                    # NOTE - This will wind up opening and closing the file twice.
                    # Do we want that? Maybe we do because we won't get here much?
                    await import_storml_file(
                        core, storm_script, stormopts, print_skips, logfd=logfd
                    )
                else:
                    await import_storm_text(
                        core, text, stormopts, print_skips, logfd=logfd
                    )

        if cli:
            await start_storm_cli(core, outp=OUTP, opts=args)


async def main(argv: list[str]):
    args = get_args(argv)

    if args.stormopts_file:
        stormopts = yaml.safe_load(args.stormopts_file)
    else:
        stormopts = {}

    stormopts.update({"repr": True})

    if args.debug:
        print_skips = []
        stormopts["debug"] = True
    else:
        print_skips = args.print_skips

    # TODO - Break the loading and then importing code out into methods
    try:
        # TODO - Support tokens here
        username, password = get_cortex_creds(args.user)
        core_obj = await get_cortex_obj(
            cortex=args.cortex,
            local=args.local,
            http=args.http,
            no_verify=not args.no_verify,
            username=username,
            password=password,
        )
    except ValueError as err:
        return str(err)

    storm_scripts, data_files = collect_files(args.folders)

    logfd = None
    if args.logfile is not None:
        logfd = s_common.genfile(args.logfile)
        logfd.seek(0, 2)

    import_call = functools.partial(
        import_data,
        core_obj,
        storm_scripts,
        data_files,
        stormopts,
        args.csv_header,
        args.debug,
        print_skips,
        args.cli,
        logfd,
        args,
        args.splices,
    )

    if isinstance(core_obj, s_telepath.Proxy):
        async with s_telepath.withTeleEnv():
            await import_call()
    else:
        await import_call()

    if logfd is not None:
        logfd.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))

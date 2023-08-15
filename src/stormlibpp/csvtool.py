"""An HTTP version of Synapse's own CSV-based tool of the same name.

All CLI options should remain the same, with the exception of new options to
support HTTP based communication.

Currently only importing is supported!
"""

import asyncio
import csv
import getpass
import json
import sys

import synapse.exc as s_exc
import synapse.cortex as s_cortex
import synapse.common as s_common

import synapse.lib.cmd as s_cmd
import synapse.lib.base as s_base
import synapse.lib.cmdr as s_cmdr
import synapse.lib.output as s_output


from .httpcore import HttpCortex


class CsvTool:
    """Run Storm code on each row in the CSV(s) passed to this object."""

    def __init__(self, args, outp, text, stormopts) -> None:
        self.cli_args = args
        self.outp = outp
        self.storm_code = text
        self.stormopts = stormopts

        self.logfd = None
        if self.cli_args.logfile is not None:
            self.logfd = s_common.genfile(args.logfile)
            self.logfd.seek(0, 2)

        if not self.cli_args.user and not self.cli_args.password:
            # TODO - Make this a custom exception.
            raise ValueError("Must provide username and password for HTTP auth!")
        else:
            self.username = self.cli_args.user
            self.password = self.cli_args.password

    async def doImport(self):
        if self.args.test:
            async with s_cortex.getTempCortex() as core:
                nodecount = await self.addCsvData(core)
        else:
            async with HttpCortex(
                self.cli_args.cortex,
                self.username,
                self.password,
                ssl_verify=not self.cli_args.no_verify,
            ) as core:
                nodecount = await self.addCsvData(core)

        if self.logfd is not None:
            self.logfd.close()

        self.outp.printf("%d nodes." % (nodecount,))
        return 0

    def iterrows(self):
        """Iterate over the rows of all CSV files in ``self.args``."""

        for path in self.args.csvfiles:
            with open(path, "r", encoding="utf8") as fd:
                if self.args.csv_header:
                    fd.readline()

                def genr():
                    for row in csv.reader(fd):
                        yield row

                for rows in s_common.chunks(genr(), 1000):
                    yield rows

    async def addCsvData(self, core):
        nodecount = 0

        self.stormopts["editformat"] = "splices"
        vars = self.stormopts.setdefault("vars", {})

        for rows in self.iterrows():
            vars["rows"] = rows

            async for mesg in core.storm(self.storm_code, opts=self.stormopts):
                if mesg[0] == "node":
                    nodecount += 1

                elif mesg[0] == "err" and not self.cli_args.debug:
                    self.outp.printf(repr(mesg))

                elif mesg[0] == "print":
                    self.outp.printf(mesg[1].get("mesg"))

                if self.cli_args.debug:
                    self.outp.printf(repr(mesg))

                if self.logfd is not None:
                    byts = json.dumps(mesg).encode("utf8")
                    self.logfd.write(byts + b"\n")

        if self.cli_args.cli:
            # TODO - Make sure that this method can handle an HttpCortex
            await s_cmdr.runItemCmdr(core, self.outp, True)

        return nodecount


async def main(argv, outp=s_output.stdout):
    try:
        args = get_args(argv, outp)
    except s_exc.ParserExit as e:
        return e.get("status")

    with open(args.stormfile, "r", encoding="utf8") as fd:
        text = fd.read()

    stormopts = {}
    if args.optsfile:
        stormopts = s_common.yamlload(args.optsfile)

    if args.view:
        if not s_common.isguid(args.view):
            outp.printf(f"View is not a guid {args.view}")
            return 1
        stormopts["view"] = args.view

    if args.user:
        args.username = args.user
    else:
        gp_user = getpass.getuser()
        user_in = input(f"Username [{gp_user}]: ")
        args.username = user_in  if user_in else gp_user

    # TODO - Get password from config or envvar
    args.password = getpass.getpass()

    csvt = CsvTool(args, outp, text, stormopts)

    if args.export:
        raise NotImplementedError("StormLib++'s csvtool doesn't support exports!")
        # return await runCsvExport(opts, outp, text, stormopts)
    else:
        return await csvt.doImport()


def get_args(argv, outp):
    args = s_cmd.Parser("stormlibpp.csvtool", description=__doc__, outp=outp)
    args.add_argument(
        "--logfile", help="Set a log file to get JSON lines from the server events."
    )
    args.add_argument(
        "--csv-header",
        default=False,
        action="store_true",
        help="Skip the first line from each CSV file.",
    )
    args.add_argument(
        "--cli",
        default=False,
        action="store_true",
        help="Drop into a cli session after loading data.",
    )
    args.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Enable verbose debug output.",
    )
    muxp = args.add_mutually_exclusive_group(required=True)
    muxp.add_argument(
        "--cortex",
        "-c",
        type=str,
        help="The telepath URL for the cortex ( or alias from ~/.syn/aliases ).",
    )
    muxp.add_argument(
        "--test",
        "-t",
        default=False,
        action="store_true",
        help="Perform a local CSV ingest against a temporary cortex.",
    )
    args.add_argument(
        "--export",
        default=False,
        action="store_true",
        help="Export CSV data to file from storm using $lib.csv.emit(...) events.",
    )
    args.add_argument(
        "--view", default=None, action="store", help="Optional view to work in."
    )
    args.add_argument(
        "--optsfile",
        default=None,
        action="store",
        help="Path to an opts file (.yaml) on disk.",
    )
    args.add_argument(
        "-u",
        "--user",
        default=None,
        help=(
            "The username to login to the Cortex with. "
            "The value from getpass.getuser() is used if not given."
        ),
    )
    args.add_argument(
        "-n",
        "--no-verify",
        action="store_true",
        help="Whether to verify the HTTPS certificate of the Cortex.",
    )
    args.add_argument(
        "stormfile", help="A Storm script describing how to create nodes from rows."
    )
    args.add_argument("csvfiles", nargs="+", help="CSV files to load.")
    return args.parse_args(argv)


if __name__ == "__main__":
    sys.exit(asyncio.run(s_base.main(main(sys.argv[1:]))))

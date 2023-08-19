"""An HTTP based Storm CLI.

This CLI relies on Synapse's out of the box CLI objects. It just replaces the
CLI's Cortex with an ``HttpCortex``, making it capable of executing Storm code via
HTTP. However, currently ``HttpCortex`` only supports the ``storm`` and ``callStorm``
methods, so the builtin commands that do not rely on Storm (Axon-related commands)
do not work. ``HttpCortex`` raises a `synapse.exc.SynErr`` when these unsupported
CLI commands are used, so the commands fail cleanly from the user's perspective.

The script, like ``HttpCortex``, requires a user and password to communicate
with the Synapse Cortex. A user can be passed via the command-line, otherwise
``getpass`` is used to select the current user. A password is always prompted for.
Future versions will allow for further user/pass customization options.

The ``--no-verify`` option tells the script to not check the Cortex's HTTPS cert.
This is needed to connect to any test Cortex or a Cortex that otherwise doesn't
use a trusted CA to sign HTTPS certificates.
"""


import asyncio
import argparse
import getpass
import sys

import synapse.lib.output as s_output
import synapse.tools.storm as s_storm

from .httpcore import HttpCortex


def get_args(argv: list[str]):
    """Build an argument parser for this script and parse the passed in args."""

    args = argparse.ArgumentParser(prog="stormlibpp.hstorm")
    args.add_argument("cortex", help="An HTTP URL for the Cortex.")
    args.add_argument("onecmd", nargs="?", help="A Storm command to run and exit.")
    args.add_argument(
        "-v", "--view", default=None, help="The iden of the Synapse View to use."
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

    return args.parse_args(argv)


async def main(argv: list[str]):
    """The main functionality of the HTTP Storm CLI.

    Parameters
    ----------
    argv : list[str]
        The unparsed CLI arguments for this script.
    """

    args = get_args(argv)
    outp = s_output.stdout

    if args.user:
        user = args.user
    else:
        user = getpass.getuser()
        # TODO - Dynamically capture user
        # user_in = input(f"Username [{gp_user}]: ")

        # if user_in:
        #     user = user_in
        # else:
        #     user = gp_user

    # TODO - Get password from config or envvar
    password = getpass.getpass()

    async with HttpCortex(args.cortex, user, password, ssl_verify=not args.no_verify) as hcore:

        async with await s_storm.StormCli.anit(hcore, outp=outp, opts=args) as cli:

            if args.onecmd:
                await cli.runCmdLine(args.onecmd)
                return

            cli.colorsenabled = True
            cli.printf(s_storm.welcome)

            await cli.addSignalHandlers()
            await cli.runCmdLoop()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))

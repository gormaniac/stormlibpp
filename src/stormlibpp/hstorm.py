"""An HTTP based Storm CLI.

This CLI relies on Synapse's out of the box CLI objects. It just replaces the
CLI's Cortex with an ``HttpCortex``, making it capable of executing Storm code via
HTTP. However, currently ``HttpCortex`` only supports the ``storm`` and ``callStorm``
methods, so the builtin commands that do not rely on Storm (Axon-related commands)
do not work. ``HttpCortex`` raises a `synapse.exc.SynErr`` when these unsupported
CLI commands are used, so the commands fail cleanly from the user's perspective.

The script, like ``HttpCortex``, requires a user and password to communicate
with the Synapse Cortex. A user can be passed via the command-line, the ``CORTEX_USER``
environment variable, or will be prompted for (``getpass`` is used as a default).
The ``CORTEX_PASS`` environment variable may be used to give ``hstorm`` a password
at runtime, otherwise one will be prompted for.

The ``--no-verify`` option tells the script to not check the Cortex's HTTPS cert.
This is needed to connect to any test Cortex or a Cortex that otherwise doesn't
use a trusted CA to sign HTTPS certificates.
"""


import asyncio
import argparse
import sys

from ._args import USER_PARSER
from .httpcore import HttpCortex
from .output import OUTP
from .stormcli import start_storm_cli
from .utils import get_cortex_creds


def get_args(argv: list[str]):
    """Build an argument parser for this script and parse the passed in args."""

    args = argparse.ArgumentParser(
        prog="stormlibpp.hstorm",
        parents=[
            USER_PARSER,
        ],
    )
    args.add_argument("cortex", help="An HTTP URL for the Cortex.")
    args.add_argument("onecmd", nargs="?", help="A Storm command to run and exit.")
    args.add_argument(
        "-v", "--view", default=None, help="The iden of the Synapse View to use."
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

    username, password = get_cortex_creds(args.user)

    async with HttpCortex(
        args.cortex, username, password, ssl_verify=not args.no_verify
    ) as hcore:
        await start_storm_cli(hcore, outp=OUTP, opts=args, onecmd=args.onecmd)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))

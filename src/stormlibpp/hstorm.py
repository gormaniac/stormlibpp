"""An HTTP based Storm CLI."""


import asyncio
import argparse
import getpass
import sys

import synapse.lib.output as s_output
import synapse.tools.storm as s_storm

from .httpcore import HttpCortex


def get_args(argv: list[str]):
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

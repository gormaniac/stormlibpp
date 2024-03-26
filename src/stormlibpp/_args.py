"""CLI arguments shared by more than one script."""


import argparse


TOKEN_PARSER = argparse.ArgumentParser(add_help=False)
TOKEN_PARSER.add_argument(
    "--token",
    action="store_true",
    help=(
        "Use token-based authentication when connecting over HTTP. Reads the"
        " CORTEX_TOKEN environment variable for the token value. The token is"
        " prompted for if the environment variable is empty."
    ),
)

USER_PARSER = argparse.ArgumentParser(add_help=False)
USER_PARSER.add_argument(
    "--user",
    help=(
        "The Cortex user to authenticate with. The CORTEX_USER env var may be used"
        " instead of this argument, however; this argument overrides the env var."
        " If neither --user or CORTEX_USER are used, a prompt will appear to either"
        " input a value or accept the default (return of getpass.getpass()). Only"
        " works when connecting to a Cortex over HTTP."
    ),
)

VERIFY_PARSER = argparse.ArgumentParser(add_help=False)
VERIFY_PARSER.add_argument(
    "-n",
    "--no-verify",
    help="Skips verification of the Cortex's SSL certificate when using the HTTP API.",
    action="store_true",
)

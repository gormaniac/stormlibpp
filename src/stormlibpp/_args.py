"""CLI arguments shared by more than one script."""


import argparse

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

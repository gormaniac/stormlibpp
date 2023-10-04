"""Miscellaneous functions that are helpful for working with Storm/Synapse."""


import getpass
import os

import synapse.exc as s_exc
import synapse.lib.parser as s_parser

from . import errors


def absjoin(*paths: str) -> str:
    """Join paths with os.path.join and then pass it to os.path.abspath.

    Parameters
    ----------
    paths : list[str]
        The path strings to join together, as would be passed to ``os.path.join``.

    Returns
    -------
    str
        The absolute path derived from the joined ``paths``.
    """

    return os.path.abspath(os.path.join(*paths))


def chk_storm_syntax(storm: str) -> None:
    """Check if the given Storm code has valid syntax, raise exception if not.

    Raises
    ------
    StormSyntaxError
        If a Storm syntax error was found in the given Storm code.
    """

    try:
        s_parser.parseQuery(storm)
    except s_exc.BadSyntax as err:
        # TODO - Make sure this gives the caller verbose error info
        # and add it to the StormSyntaxError if not.
        raise errors.StormSyntaxError("Storm Syntax Error!", err) from err


def normver(ver: str | tuple) -> tuple[str, tuple]:
    """Take either a version str "x.x.x" or tuple (x, x, x) and return both.

    Raises
    ------
    TypeError
        If ``ver`` is not a str or tuple.
    """

    if isinstance(ver, str):
        verstr = ver
        vertup = tuple(int(part) for part in ver.split("."))
    elif isinstance(ver, tuple):
        vertup = ver
        verstr = ".".join([str(part) for part in ver])
    else:
        raise TypeError("Can only use a str or tuple as a Storm pkg version")

    return (verstr, vertup)


def get_cortex_creds(_user):
    if _user:
        username = _user
    elif envusr := os.environ.get("CORTEX_USER"):
        username = envusr
    else:
        gpusr = getpass.getuser()
        inusr = input(f"Username [{gpusr}]: ")
        username = inusr if inusr else gpusr

    if envpw := os.environ.get("CORTEX_PASS"):
        password = envpw
    else:
        password = getpass.getpass()

    return username, password

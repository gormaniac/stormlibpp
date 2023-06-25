"""Miscellaneous functions that are helpful for working with Storm/Synapse."""


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
        raise errors.StormSyntaxError() from err


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

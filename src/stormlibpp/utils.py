"""Miscellaneous functions that are helpful for working with Storm/Synapse."""


import csv
import getpass
import json
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


def csv_genr(fd: str) -> list:
    """Read a CSV from fd and yield each row."""

    for row in csv.reader(fd):
        yield row


def endswith(text: str, items: list[str]) -> bool:
    """Check if text ends with any of items."""

    for item in items:
        if text.endswith(item):
            return True
    return False


def get_cortex_creds(_user: str | None = None) -> tuple[str, str]:
    """Get credentials to use when connecting to a Cortex over HTTP.
    
    If ``_user`` is set, it overrides any other options to get a username.
    Otherwise use the value of the ``CORTEX_USER`` environment variable. If that
    is also empty, prompt for a username. A default option is given to the user
    at the prompt, it is the return of ``getpass.getuser()``.

    The password is read from the ``CORTEX_PASS`` environment variable and the
    user is prompted if this is empty.
    """

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


def json_genr(fd):
    """Read a JSON file from fd, and yield each top-level item within it."""

    # TODO - Support nested key to start with
    data = json.load(fd)

    if isinstance(data, dict):
        for key, row in data.items():
            yield [key, row]
    else:
        count = 0
        for row in data:
            yield [count, row]
            count += 1


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


def txt_genr(fd):
    """Read a raw text file from fd and yield each line."""

    for row in fd.readlines():
        yield row.strip()

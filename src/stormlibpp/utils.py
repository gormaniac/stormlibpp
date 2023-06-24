"""Miscellaneous functions that are helpful for working with Storm/Synapse."""


import os


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


def absjoin(*paths: str) -> str:
    """Join paths with os.path.join and then pass it to os.path.abspath.

    Parameters
    ----------
    *paths : str
        The path strings to join together, as would be passed to ``os.path.join``.

    Returns
    -------
    str
        The absolute path derived from the joined ``paths``.
    """

    return os.path.abspath(os.path.join(*paths))

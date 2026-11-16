"""
Python objects for working with Synapse Telepath endpoints.


"""


import contextlib

from collections.abc import Iterator
from typing import Any, TypedDict

import synapse.telepath as s_telepath


class TelepathRetn(TypedDict):
    """A standard return value from a Telepath API endpoint.

    Also typically returned by Cell methods that eventually
    get called by a Telepath endpoint method.

    Can be subclassed to override type of ``data``.

    Using this standard class to return values to Storm helps error handling in
    Storm code and type hints in Storm Service code. Subclassing to set ``data``'s
    type also improves a Storm developer's understanding of the Python object 
    available in Storm.

    This return convention is suggested throughout the Synapse Service documentation.

    A ``status`` of ``False`` means and error occurred. ``mesg`` must be set
    if ``status`` is ``False``. ``data`` may or may not be set.

    A ``status`` of ``True`` means everything worked well. In this case ``mesg``
    may be empty, but ``data`` must have a value.
    """

    status: bool
    mesg: str
    data: Any


class BoolRetn(TelepathRetn):
    """A TelepathRetn where ``data`` is a boolean value."""

    data: bool


class ListRetn(TelepathRetn):
    """A TelepathRetn where ``data`` is a list value."""

    data: list


class DictRetn(TelepathRetn):
    """A TelepathRetn where ``data`` is a dict value."""

    data: dict


class StrRetn(TelepathRetn):
    """A TelepathRetn where ``data`` is a str value."""

    data: str


def genDefaultTelepathRetn(obj=TelepathRetn, /, default_data=None) -> TelepathRetn:
    """Generate a default TelepathRetn return object, or the given subclass.

    Default values have a ``status`` of ``True``, an empty ``mesg``, and
    ``data`` is set to the ``default_data`` arg - which defaults to ``None``.
    """

    return obj(status=True, mesg="", data=default_data)


@contextlib.contextmanager
def tpath_proxy_contextmanager(cortex_url: str) -> Iterator[s_telepath.Proxy]:
    """Context manager that yields a telepath proxy object connected to cortex_url.

    A shortand for::

        async with await s_telepath.openurl(opts.cortex) as proxy:
            # do something with proxy

    A helper for ``get_cortex_obj()`` to put a Telepath-based Cortex connection
    into a ``functools.partial()`` call. Allowing us to open different Cortex
    connections based on various user objects (local vs http vs telepath).

    Parameters
    ----------
    cortex_url : str
        The Telepath URL (a Cortex in this case) to proxy to.

    Yields
    -------
    Iterator[s_telepath.Proxy]
        A telepath proxy object connected to the given cortex_url.
    """

    yield s_telepath.openurl(cortex_url)

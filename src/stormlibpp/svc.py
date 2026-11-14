"""Building blocks for Storm services (Synapse Advanced Power-Ups).

The Storm side of a service can only report an error it gets back, so a service's Telepath
API should never raise: every call returns a ``TelepathRetn`` and an error is a
``status=False`` return with a message. This module provides that contract once, so each
service doesn't hand-roll (and drift on) its own wrappers:

- ``RetnApi`` is a mixin for a service's ``CellApi``. It generates Telepath methods that
  call the cell and wrap the result, and makes sure no public method it defines can raise.
- ``retn()``, ``retnGenr()`` and ``errRetn()`` are the same wrapping as plain functions.
- ``SvcError`` is the base for errors whose message is meant for the Storm user.
- ``safeJoin()``, ``checkName()`` and ``checkGuid()`` validate values from Storm that end up
  in a file path, so a value like ``../..`` can't escape the service's storage.

A typical service API::

    class MySvcApi(RetnApi, s_cell.CellApi, s_stormsvc.StormSvc):
        RETN_METHS = ("lookup", "search")    # MySvc.lookup() etc., wrapped
        GENR_METHS = ("export",)             # MySvc.export() async generator, wrapped
        RETN_ERRORS = (MySvcApiError,)       # Errors returned with their own message

        def _retnRedact(self, mesg: str) -> str:
            return mesg.replace(self.cell.apikey, "<redacted>")

        async def setApiKey(self, apikey):   # Hand-written methods are guarded too
            await self.cell.setApiKey(apikey)
            return BoolRetn(status=True, mesg="Set the API key.", data=True)
"""

import functools
import inspect
import logging
import pathlib
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable

import synapse.common as s_common
import synapse.exc as s_exc
import synapse.lib.cell as s_cell

from .telepath import TelepathRetn

logger = logging.getLogger(__name__)


class SvcError(Exception):
    """An error whose message is meant for the Storm user.

    ``RetnApi`` and ``errRetn()`` return ``mesg`` as-is, without a traceback in the logs.
    Subclass it for a service's own errors, or list other error types in ``RETN_ERRORS``.
    """

    def __init__(self, mesg: str):
        super().__init__(mesg)
        self.mesg = mesg


# Errors that mean the input from Storm was bad, ex. a string where an int was expected.
INPUT_ERRORS: tuple[type[Exception], ...] = (ValueError, TypeError, s_exc.BadArg)


def _mesg(err: Exception) -> str:
    """The user facing message of an error."""

    if isinstance(err, s_exc.SynErr):
        return err.get("mesg") or str(err)
    mesg = getattr(err, "mesg", None)
    return mesg if isinstance(mesg, str) and mesg else str(err)


def errRetn(
    err: Exception,
    *,
    errors: Iterable[type[Exception]] = (SvcError,),
    redact: Callable[[str], str] | None = None,
    name: str = "",
) -> TelepathRetn:
    """A ``status=False`` TelepathRetn for an error.

    - An error that is one of ``errors``, or a Synapse ``AuthDeny`` (ex. from ``adminapi()``),
      returns its own message (``err.mesg`` when set).
    - A bad input error (``INPUT_ERRORS``) returns ``Invalid input: <error>``.
    - Anything else is unexpected: it's logged with its traceback, and returns
      ``Unexpected error: <type>: <error>``.

    ``redact`` is applied to every message, ex. to strip an API key that an HTTP library
    put in an error. ``name`` names the failed call in the log message.
    """

    errors = tuple(errors)
    if (errors and isinstance(err, errors)) or isinstance(err, s_exc.AuthDeny):
        mesg = _mesg(err)
    elif isinstance(err, INPUT_ERRORS):
        mesg = f"Invalid input: {_mesg(err)}"
    else:
        logger.error("Unexpected error in %s.", name or "a service call", exc_info=err)
        mesg = f"Unexpected error: {type(err).__name__}: {_mesg(err)}"
    if redact is not None:
        mesg = redact(mesg)
    return TelepathRetn(status=False, mesg=mesg, data=None)


async def retn(coro: Awaitable, **kwargs) -> TelepathRetn:
    """Await ``coro`` and wrap its result, or its error, in a TelepathRetn.

    Takes ``errRetn()``'s keyword arguments.
    """

    try:
        data = await coro
    except Exception as err:
        return errRetn(err, **kwargs)
    return TelepathRetn(status=True, mesg="", data=data)


async def retnGenr(genr: AsyncIterator, **kwargs) -> AsyncIterator[TelepathRetn]:
    """Wrap each item of an async generator in a TelepathRetn.

    An error ends the generator after yielding one ``status=False`` item. Takes
    ``errRetn()``'s keyword arguments.
    """

    try:
        async for item in genr:
            yield TelepathRetn(status=True, mesg="", data=item)
    except Exception as err:
        yield errRetn(err, **kwargs)


def _kind(func) -> str | None:
    """``"genr"`` or ``"coro"`` for an async method, looking through decorators like adminapi()."""

    if not callable(func):
        return None
    inner = inspect.unwrap(func)
    if inspect.isasyncgenfunction(inner):
        return "genr"
    if inspect.iscoroutinefunction(inner):
        return "coro"
    return None


def _guard(func):
    """Make an API method that already returns TelepathRetns return an error instead of raising.

    ``func`` may be wrapped by a sync decorator that raises before the coroutine exists, ex.
    Synapse's ``adminapi()``, so the call itself is inside the ``try`` too.
    """

    if _kind(func) == "genr":

        @functools.wraps(func)
        async def genr(self, *args, **kwargs):
            try:
                async for item in func(self, *args, **kwargs):
                    yield item
            except Exception as err:
                yield self._retnErr(err, func.__name__)

        genr._retn_guarded = True
        return genr

    @functools.wraps(func)
    async def meth(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as err:
            return self._retnErr(err, func.__name__)

    meth._retn_guarded = True
    return meth


def _retnMeth(cls, name: str):
    async def meth(self, *args, **kwargs) -> TelepathRetn:
        try:
            data = await getattr(self.cell, name)(*args, **kwargs)
        except Exception as err:
            return self._retnErr(err, name)
        return TelepathRetn(status=True, mesg="", data=data)

    meth.__name__ = name
    meth.__qualname__ = f"{cls.__qualname__}.{name}"
    meth.__doc__ = f"Call the cell's {name}() and return a TelepathRetn."
    meth._retn_guarded = True
    return meth


def _genrMeth(cls, name: str):
    async def meth(self, *args, **kwargs) -> AsyncIterator[TelepathRetn]:
        try:
            async for item in getattr(self.cell, name)(*args, **kwargs):
                yield TelepathRetn(status=True, mesg="", data=item)
        except Exception as err:
            yield self._retnErr(err, name)

    meth.__name__ = name
    meth.__qualname__ = f"{cls.__qualname__}.{name}"
    meth.__doc__ = (
        f"Yield the items of the cell's {name}(), each wrapped in a TelepathRetn."
    )
    meth._retn_guarded = True
    return meth


# Methods every CellApi already has, which RetnApi never wraps.
_CELLAPI_NAMES = frozenset(dir(s_cell.CellApi))


class RetnApi:
    """A mixin for a Storm service's ``CellApi`` that never raises to Storm.

    Put it first in the bases, ex. ``class Api(RetnApi, s_cell.CellApi, s_stormsvc.StormSvc)``.

    Subclasses set:

    ``RETN_METHS``
        Names of the cell's coroutine methods to expose. Each gets an API method that calls
        ``self.cell.<name>(*args, **kwargs)`` and returns its result as a TelepathRetn.
    ``GENR_METHS``
        Names of the cell's async generator methods to expose. Each item is wrapped.
    ``RETN_ERRORS``
        Error types whose message is returned to Storm as-is (default: ``SvcError``).

    Every public coroutine or async generator method a subclass defines itself is also
    guarded: if it raises, it returns (or yields) a ``status=False`` TelepathRetn instead.
    These methods are expected to build their own TelepathRetn on success.

    Override ``_retnRedact()`` to scrub secrets from every error message.

    A name in ``RETN_METHS``/``GENR_METHS`` that the subclass also defines is left alone,
    so a method can be hand-written when it needs more than a plain call (ex. a permission
    check).
    """

    RETN_METHS: tuple[str, ...] = ()
    GENR_METHS: tuple[str, ...] = ()
    RETN_ERRORS: tuple[type[Exception], ...] = (SvcError,)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for name, valu in list(vars(cls).items()):
            if name.startswith("_") or name in _CELLAPI_NAMES:
                continue
            if getattr(valu, "_retn_guarded", False):
                continue
            if _kind(valu) is not None:
                setattr(cls, name, _guard(valu))

        both = set(cls.RETN_METHS) & set(cls.GENR_METHS)
        if both:
            raise TypeError(
                f"{cls.__name__} lists {sorted(both)} in RETN_METHS and GENR_METHS."
            )

        for name in cls.RETN_METHS:
            if name not in vars(cls):
                setattr(cls, name, _retnMeth(cls, name))
        for name in cls.GENR_METHS:
            if name not in vars(cls):
                setattr(cls, name, _genrMeth(cls, name))

    def _retnRedact(self, mesg: str) -> str:
        """Scrub secrets from an error message before it's returned. Returns it as-is by default."""

        return mesg

    def _retnErr(self, err: Exception, name: str = "") -> TelepathRetn:
        """The ``status=False`` TelepathRetn for an error raised by the ``name`` API call."""

        return errRetn(
            err,
            errors=self.RETN_ERRORS,
            redact=self._retnRedact,
            name=f"{type(self).__name__}.{name}" if name else type(self).__name__,
        )


# A name that is safe to use as a single path component: no separators, no leading dot
# (which also rules out "." and ".."), and no control characters.
_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]{0,127}$")


def checkName(name, what: str = "name") -> str:
    """Return ``name`` if it's safe to use as a single file or directory name.

    Allows letters, digits, ``_``, ``.`` and ``-``, at most 128 characters, and no leading
    ``.``. Raises ``SvcError`` otherwise. ``what`` names the value in the error message.
    """

    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise SvcError(
            f"Invalid {what} {name!r}: use letters, digits, '_', '.' and '-', "
            "and don't start with '.'."
        )
    return name


def checkGuid(valu, what: str = "guid") -> str:
    """Return ``valu`` if it's a Synapse guid (32 lowercase hex characters).

    Raises ``SvcError`` otherwise. ``what`` names the value in the error message.
    """

    if not isinstance(valu, str) or not s_common.isguid(valu):
        raise SvcError(f"Invalid {what} {valu!r}: expected a 32 character hex guid.")
    return valu


def safeJoin(root: str | pathlib.Path, *parts: str) -> pathlib.Path:
    """Join ``parts`` onto ``root``, and refuse a result that isn't strictly inside ``root``.

    Each part must pass ``checkName()``, and the resolved path (following symlinks) must be
    below the resolved ``root``. Raises ``SvcError`` otherwise.
    """

    if not parts:
        raise SvcError("No path given.")
    for part in parts:
        checkName(part, "path component")

    base = pathlib.Path(root).resolve()
    path = base.joinpath(*parts).resolve()
    if path == base or base not in path.parents:
        raise SvcError(f"Path {'/'.join(parts)!r} is outside of the service's storage.")
    return path

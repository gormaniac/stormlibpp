"""Implements some methods from synapse.cortex.Cortex but with HTTP."""


import aiohttp
import json

from .errors import (
    HttpCortexError, HttpCortexLoginError, HttpCortexNotImplementedError,
)


StormMsgType = str
"""The type of a Storm message.

See `Storm Message Types`_.

.. _Storm Message Types: https://synapse.docs.vertex.link/en/latest/synapse/devguides/storm_api.html#message-types
"""

StormMsg = tuple[StormMsgType, dict]
"""A message yielded by a Cortex ``storm`` call.

See `Storm Message Types`_.

.. _Storm Message Types: https://synapse.docs.vertex.link/en/latest/synapse/devguides/storm_api.html#message-types
"""


class HttpCortex:
    """A class with some methods from synapse.cortex.Cortex but over HTTP.

    For now, it only supports the `storm` and `callStorm` methods. These methods
    take the same arguments and return the same types of values as their Cortex
    equivalents.

    Communicating with Synapse over HTTP requires a user on the Cortex that has
    a password set. HttpCortex needs to authenticate to the Cortex before making
    requests (i.e. using any of this objects methods). Because of this, HttpCortex
    implements a ``login`` method, and the object constructor expects a username
    and password.

    HttpCortex relies on an ``aiohttp.ClientSession`` underneath to make HTTP
    requests. This session needs to be closed to avoid errors at the end of
    program execution. HttpCortex exposes a ``close`` method that must be called
    when this object is no longer needed.

    HttpCortex is an async context manager. It calls the ``login`` and ``close``
    methods for you upon entrance and exit of the object.

    Parameters
    ----------
    url : str, optional
        The URL of the Synapse Cortex to connect to,
        by default `"https://localhost:4443"`.
    usr : str, optional
        The username to authenticate with, by default `""`.
    pwd : str, optional
        The password to authenticate with, by default `""`.
    default_opts : dict, optional
        The default Storm options to pass with every request made by this instance.
        Set this to an empty dict to disable. By default `{"repr": True}`.
    ssl_verify : bool, optional
        Whether to verify the Cortex's SSL certificate, by default `True`.
    """

    def __init__(
        self,
        url: str = "https://localhost:4443",
        usr: str = "",
        pwd: str = "",
        default_opts: dict = {"repr": True},
        ssl_verify: bool = True,
    ) -> None:
        self.url = url
        self.ssl_verify = ssl_verify
        self.default_opts = default_opts

        self.usr = usr
        self.pwd = pwd

        self.timeout = aiohttp.ClientTimeout(60.0, 10.0)
        self.sess = aiohttp.ClientSession(
            self.url, timeout=self.timeout, raise_for_status=True
        )

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.stop()

    def _prep_payload(self, text: str, opts: dict | None = None):
        if not opts:
            opts = self.default_opts
        return {"query": text, "opts": opts}

    async def callStorm(self, text: str, opts: dict | None = None):
        """Execute a Storm query and return the value passed to a Storm return() call.

        Parameters
        ----------
        text : str
            The Storm code to execute.
        opts : dict | None, optional
            Storm options to use when executing this Storm code, by default None.

        Returns
        -------
        dict
            The response from the Cortex's HTTP API. It contains 2 keys::

                result
                status

        Raises
        ------
        HttpCortexError
            If an exception is raised when making an HTTP request to the Cortex.
            This will likely either be from an HTTP error, a connection error,
            or an error decoding the JSON response.
        """

        url = "/api/v1/storm/call"

        data = self._prep_payload(text, opts=opts)

        try:
            async with self.sess.get(url, json=data, ssl=self.ssl_verify) as resp:
                data = await resp.json()
                return data
        except Exception as err:
            raise HttpCortexError(
                f"Unable to call storm on {self.url}: {err}", err
            ) from err

    async def login(self):
        """Login to the Cortex with the user/pass supplied at instantiation.

        Sets the cookie returned by the Cortex in the underlying ``ClientSession``.
        Ignores the expiration date because there was errors adding the
        ``SimpleCookie`` to the session's ``CookieJar``. Instead we use the
        raw cookie value, without options set by the server.

        Cortex cookies expire after 2 weeks. So this object shouldn't live
        longer than that without calling this method again.
        """

        info = {"user": self.usr, "passwd": self.pwd}
        url = "/api/v1/login"

        try:
            async with self.sess.post(url, json=info, ssl=self.ssl_verify) as resp:
                item = await resp.json()
        except Exception as err:
            raise HttpCortexLoginError(
                f"Error making login request to {self.url}: {err}", err
            ) from err

        if item.get("status") != "ok":
            code = item.get("code")
            mesg = item.get("mesg")
            raise HttpCortexLoginError(f"Login error ({code}): {mesg}")

        session_cookie = resp.cookies.get("sess")

        if session_cookie is None:
            raise HttpCortexLoginError(
                "Successfully authenticated but Synapse did not send session cookie"
            )

        self.sess.cookie_jar.update_cookies({"sess": session_cookie.value})

    async def stop(self):
        """Stop this instance by closing its HTTP session."""

        await self.sess.close()

    async def storm(self, text: str, opts: dict | None = None) -> StormMsg:
        """Evaulate a Storm query and yield the streamed Storm messages.

        Parameters
        ----------
        text : str
            The Storm code to execute.
        opts : dict | None, optional
            Storm options to use when executing this Storm code, by default None.

        Yields
        -------
        StormMsg
            Each message streamed by the Cortex.

        Raises
        ------
        HttpCortexError
            If an exception is raised when making an HTTP request to the Cortex.
            This will likely either be from an HTTP error, a connection error,
            or an error decoding the JSON response.
        """

        url = "/api/v1/storm"

        data = self._prep_payload(text, opts=opts)

        try:
            async with self.sess.get(url, json=data, ssl=self.ssl_verify) as resp:
                async for byts, _ in resp.content.iter_chunks():
                    if not byts:
                        break

                    yield json.loads(byts)
        except Exception as err:
            raise HttpCortexError(
                f"Unable to execute storm on {self.url}: {err}", err
            ) from err

    # TODO - Implement these methods so we can fully support Storm CLI features.
    async def exportStorm(self, *args, **kwargs):
        raise HttpCortexNotImplementedError("HttpCortex doesn't implement exportStorm!")

    async def getAxonBytes(self, *args, **kwargs):
        raise HttpCortexNotImplementedError(
            "HttpCortex doesn't implement getAxonBytes!"
        )

    async def getAxonUpload(self, *args, **kwargs):
        raise HttpCortexNotImplementedError(
            "HttpCortex doesn't implement getAxonUpload!"
        )

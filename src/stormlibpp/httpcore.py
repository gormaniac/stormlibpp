"""Implements some methods from synapse.cortex.Cortex but with HTTP.

This is useful when replicating Telepath based tools that need to be used with
HTTP. For example, the ``hstorm`` CLI replaces a ``Cortex`` object with an
``HttpCortex`` so it can run Storm commands over HTTP.
"""


import aiohttp
import json

import synapse.lib.msgpack as s_msgpack

from .errors import (
    HttpCortexError,
    HttpCortexJsonError,
    HttpCortexLoginError,
    HttpCortexNotImplementedError,
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

    Examples::

        # Use HttpCortex as an async context manager so login/cleanup is handled
        async with HttpCortex("<HTTP URL>", "<username>", "<password>") as hcore:
            async for msg in hcore.storm("[inet:ipv4=1.1.1.1]"):
                if msg[0] == "node":
                    pprint.pprint(msg[1])

        # Or handle login and object cleanup yourself
        hcore = HttpCortex("<HTTP URL>", "<username>", "<password>")
        await hcore.login()
        async for msg in hcore.storm("[inet:ipv4=1.1.1.1]"):
            print(msg)
            # Do other things with each "msg"
        await hcore.close()

        # callStorm can be used to get a single value instead of streaming results
        async with HttpCortex(...) as hcore:
            retn = await hcore.callStorm("$var = 'some val' return($var)")
            if retn["status"]:
                print(retn["result"])

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

        self.sess = aiohttp.ClientSession(
            self.url, raise_for_status=True, read_timeout=0
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

    async def storm(
        self, text: str, opts: dict | None = None, tuplify: bool = True
    ) -> StormMsg:
        """Evaulate a Storm query and yield the streamed Storm messages.

        Parameters
        ----------
        text : str
            The Storm code to execute.
        opts : dict | None, optional
            Storm options to use when executing this Storm code, by default None.
        tuplify : bool, optional
            Whether to pass streamed Storm messages to the ``synapse.lib.msgpack.deepcopy``
            function for conversion to the "packed tuple" format that most Cortex
            methods use. This results in a slight performance hit but it plays nice
            with all of the existing Synapse code, most importantly the CLI. Setting
            this option to False, will remove the performance concerns but it may
            break other tooling that are expecting "packed tuple" input values.
            ``synapse.common.tuplify`` was another candidate over ``deepcopy``, but
            ``deepcopy`` is faster.
            By default True.

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
                buf = b""
                async for byts, chunkend in resp.content.iter_chunks():
                    # If there's no byts in the response, we've read everything.
                    if not byts:
                        break

                    # Add the response chunk to the buffer.
                    buf += byts

                    # If we're not at the end of a chunk, keep filling the buffer.
                    if not chunkend:
                        continue

                    # If we're here, we're at the end of a chunk and ready to load it.
                    try:
                        data = json.loads(buf)
                    except json.JSONDecodeError as err:
                        # TODO - Add a retry count here or something to not get stuck in loop?
                        # HACK - This is the only way I found to fix a bug - may require reworking.
                        # Since we're chunking the response, occasionally we get part of a JSON
                        # doc instead of all of it, which will cause this error. Try reading more
                        # chunks until there's a readable JSON doc.
                        # This happens most often when very large nodes are returned by a Cortex.
                        err_str = str(err)
                        if (
                            "Unterminated string starting at" in err_str
                            or err_str.startswith("Expecting")
                        ):
                            continue
                        else:
                            raise err

                    # Reset the buffer so it can be reused for the next group of chunks.
                    buf = b""

                    # Yield each deserialized JSON response.
                    if tuplify:
                        yield s_msgpack.deepcopy(data)
                    else:
                        yield data

        except json.JSONDecodeError as err:
            raise HttpCortexJsonError(
                f"Malformed JSON response from {self.url}: {err}\nDoc:\n{err.doc}", err
            ) from err

        except Exception as err:
            if isinstance(err, KeyboardInterrupt) or isinstance(err, SystemExit):
                raise err
            raise HttpCortexError(
                f"Unable to execute storm on {self.url}: {err}", err
            ) from err

    # TODO - Implement these methods so we can fully support Storm CLI features.
    async def exportStorm(self, *args, **kwargs):
        """Not implemented - here to support an HTTP Storm CLI."""
        raise HttpCortexNotImplementedError("HttpCortex doesn't implement exportStorm!")

    async def getAxonBytes(self, *args, **kwargs):
        """Not implemented - here to support an HTTP Storm CLI."""
        raise HttpCortexNotImplementedError(
            "HttpCortex doesn't implement getAxonBytes!"
        )

    async def getAxonUpload(self, *args, **kwargs):
        """Not implemented - here to support an HTTP Storm CLI."""
        raise HttpCortexNotImplementedError(
            "HttpCortex doesn't implement getAxonUpload!"
        )

"""Implements some methods from synapse.cortex.Cortex but with HTTP."""


import aiohttp
import json

from .errors import HttpCortexError, HttpCortexLoginError


class HttpCortex:
    """A class with some methods from synapse.cortex.Cortex but over HTTP."""

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
        await self.start()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.stop()

    def _prep_payload(self, text: str, opts: dict | None = None):
        if not opts:
            opts = self.default_opts
        return {"query": text, "opts": opts}

    async def callStorm(self, text: str, opts: dict | None = None):
        """Execute a Storm query and return the value passed to a Storm return() call."""

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

    async def start(self):
        """Start this instance by initializing the HTTP session and logging in."""

        await self.login()

    async def stop(self):
        await self.sess.close()

    async def storm(self, text: str, opts: dict | None = None):
        """Evaulate a Storm query and yield the streamed Storm messages."""

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

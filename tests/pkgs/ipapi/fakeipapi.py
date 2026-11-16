"""A fake ip-api.com for the slib.ipapi tests, so they never call the real API.

Point slib.ipapi at it with the slib:ipapi:url global. It serves GET /json/<ip> and POST /batch,
records every request, and answers from ``results`` (an ip -> result dict), or with the queued
``replies`` first.
"""

import aiohttp.web

# A successful ip-api.com result for 8.8.8.8, as ip-api.com returns it.
RAW_DATA = {
    "query": "8.8.8.8",
    "status": "success",
    "country": "United States",
    "countryCode": "US",
    "region": "VA",
    "regionName": "Virginia",
    "city": "Ashburn",
    "lat": 39.03,
    "lon": -77.5,
    "isp": "Google LLC",
    "org": "Google Public DNS",
    "as": "AS15169 Google LLC",
    "asname": "GOOGLE",
    "reverse": "dns.google",
    "mobile": False,
    "proxy": False,
    "hosting": True,
}


class FakeIpApi:
    """A fake ip-api.com, used as an async context manager."""

    def __init__(self):
        # The result for each IP, ex. self.results["8.8.8.8"] = {...}. IPs without one get
        # RAW_DATA (with their own "query"), unless default is changed.
        self.results = {}
        self.default = RAW_DATA
        # (status, headers, body) replies to send before answering normally, in order.
        self.replies = []
        # The headers sent with normal answers.
        self.headers = {"X-Rl": "44", "X-Ttl": "60"}
        # Every request: {"method", "path", "query", "body"}.
        self.requests = []
        self.url = None

    def result(self, ipaddr: str) -> dict:
        return dict(self.results.get(ipaddr, self.default), query=ipaddr)

    def _reply(self):
        status, headers, body = self.replies.pop(0)
        if isinstance(body, str):
            return aiohttp.web.Response(status=status, headers=headers, text=body)
        return aiohttp.web.json_response(body, status=status, headers=headers)

    async def _json(self, request):
        self.requests.append({"method": "GET", "path": request.path, "query": dict(request.query), "body": None})
        if self.replies:
            return self._reply()
        return aiohttp.web.json_response(self.result(request.match_info["ip"]), headers=self.headers)

    async def _batch(self, request):
        body = await request.json()
        self.requests.append({"method": "POST", "path": request.path, "query": dict(request.query), "body": body})
        if self.replies:
            return self._reply()
        return aiohttp.web.json_response([self.result(ip) for ip in body], headers=self.headers)

    async def __aenter__(self):
        app = aiohttp.web.Application()
        app.router.add_get("/json/{ip:.+}", self._json)
        app.router.add_post("/batch", self._batch)
        self._runner = aiohttp.web.AppRunner(app)
        await self._runner.setup()
        site = aiohttp.web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        return self

    async def __aexit__(self, *args):
        await self._runner.cleanup()

    def ips(self) -> list:
        """The IPs queried with /json, in order."""
        return [r["path"].split("/json/", 1)[1] for r in self.requests if r["method"] == "GET"]

    def batches(self) -> list:
        """The IP lists sent to /batch, in order."""
        return [r["body"] for r in self.requests if r["method"] == "POST"]

"""Record the VCR cassettes the pdns and pssl package tests replay.

Every cassette is a real CIRCL Passive DNS/SSL response. Re-run this to refresh them:

    CIRCL_USER=<user> CIRCL_PASS=<pass> pipenv run python3 scripts/pkgs/record_circl.py

Pass cassette names to only record those (ex. ``pdns/domain pssl/cfetch``), the default is all
of them. Existing cassettes are overwritten. The Authorization header is never saved.

The ``unauthorized`` cassettes aren't recorded here, they're CIRCL's 401 response with no
credentials, written by hand.
"""

import argparse
import asyncio
import os
import sys

import aiohttp
import vcr

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASSETTES = {
    "pdns": os.path.join(ROOT, "tests/pkgs/pdns/cassettes"),
    "pssl": os.path.join(ROOT, "tests/pkgs/pssl/cassettes"),
}

PDNS = "https://www.circl.lu/pdns/query"
PSSL = "https://www.circl.lu/v2pssl"

# A cassette name, and the (url, request headers) of each request in it. A request may be a
# callable that takes the previous response and returns (url, headers) - for pagination.


def nextPage(url, headers):
    """Request the next page of a paginated pdns query, using the last response's cursor."""

    def _next(prev):
        hdrs = dict(headers)
        hdrs["dribble-paginate-cursor"] = prev.headers["X-Dribble-Cursor"]
        return url, hdrs

    return _next


WIXPAGE = {"dribble-paginate-count": "25", "dribble-filter-rrtype": "CNAME"}

# The certificates seen on 172.228.24.7 (pssl/query_ip.yaml), for a query then fetch flow.
CERTS_172_228_24_7 = (
    "37221925980c05deefac014f9a72b4765e716341",
    "3209cc3ce4f1c22ab64b2e4284100b0022ad2739",
    "041d0d04b5629698f0abb5348986e4bc38c3a0d5",
    "4d34ea92764b3a3149119952f41930ca11348361",
    "6ad2b04e2196e48bf685752890e811cd2ed60606",
    "c43b30bf08bfb0b92c070f42f51b6980c8ada064",
    "30d1fd4a296ab1a8831cd56b4110a227f557bfff",
    "79068f16776372aa6b12b83dd2b7288298727f54",
)

RECORDINGS = {
    # Passive DNS (application/x-ndjson, one COF record a line)
    "pdns/domain": [(f"{PDNS}/circl.lu", {})],
    "pdns/domain_noactive": [(f"{PDNS}/circl.lu", {"dribble-disable-active-query": "1"})],
    "pdns/fqdn_cname": [(f"{PDNS}/www.circl.lu", {})],
    "pdns/ipv4": [(f"{PDNS}/185.194.93.14", {})],
    "pdns/ipv6": [(f"{PDNS}/2a00:5980:93::14", {})],
    "pdns/rrtype": [(f"{PDNS}/circl.lu", {"dribble-filter-rrtype": "NS"})],
    "pdns/empty": [(f"{PDNS}/nonexistent-zzqx-example-12345.com", {})],
    # More than 1000 records of one rrtype - X-Dribble-Errors has a "maxset" error.
    "pdns/maxset": [(f"{PDNS}/cdn1.wixdns.net", {})],
    # Two pages, the 2nd uses the X-Dribble-Cursor of the 1st.
    "pdns/paginate": [
        (f"{PDNS}/cdn1.wixdns.net", WIXPAGE),
        nextPage(f"{PDNS}/cdn1.wixdns.net", WIXPAGE),
    ],
    # Passive SSL (application/json, errors are text/html 400s)
    "pssl/query_ip": [(f"{PSSL}/query/172.228.24.7", {})],
    "pssl/query_cidr": [(f"{PSSL}/query/172.228.24.0/28", {})],
    "pssl/query_empty": [(f"{PSSL}/query/185.194.93.14", {})],
    "pssl/query_cidr_too_big": [(f"{PSSL}/query/172.228.24.0/20", {})],
    "pssl/query_ipv6": [(f"{PSSL}/query/2a00:5980:93::14", {})],
    "pssl/cquery": [(f"{PSSL}/cquery/c46fed822dadac3f31f9bb4d1a78a1d9eae4567b", {})],
    "pssl/cquery_empty": [(f"{PSSL}/cquery/0000000000000000000000000000000000000000", {})],
    "pssl/cfetch": [(f"{PSSL}/cfetch/7c552ab044c76d1df4f5ddf358807bfdcd07fa57", {})],
    "pssl/cfetch_missing": [(f"{PSSL}/cfetch/0000000000000000000000000000000000000000", {})],
    "pssl/cfetch_badhash": [(f"{PSSL}/cfetch/notasha1", {})],
    "pssl/query_fetch": [(f"{PSSL}/query/172.228.24.7", {})]
    + [(f"{PSSL}/cfetch/{sha1}", {}) for sha1 in CERTS_172_228_24_7],
}


def cassettePath(name):
    pkg, base = name.split("/", 1)
    return os.path.join(CASSETTES[pkg], f"{base}.yaml")


async def record(name, auth):
    path = cassettePath(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.unlink(path)

    myvcr = vcr.VCR(
        record_mode="all",
        filter_headers=["authorization"],
        decode_compressed_response=True,
    )

    # trust_env so HTTPS_PROXY is used, if it's set.
    async with aiohttp.ClientSession(auth=auth, trust_env=True) as sess:
        with myvcr.use_cassette(path):
            prev = None
            for req in RECORDINGS[name]:
                url, headers = req(prev) if callable(req) else req
                async with sess.get(url, headers=headers) as resp:
                    await resp.read()
                    print(f"{name}: {resp.status} {url}")
                    if resp.status == 401:
                        sys.exit("CIRCL returned a 401, check CIRCL_USER and CIRCL_PASS.")
                    prev = resp


async def main(argv):
    pars = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    pars.add_argument("names", nargs="*", help=f"Cassettes to record (default: all): {', '.join(sorted(RECORDINGS))}")
    opts = pars.parse_args(argv)
    for name in opts.names:
        if name not in RECORDINGS:
            pars.error(f"unknown cassette: {name}")

    auth = None
    if os.environ.get("CIRCL_USER"):
        auth = aiohttp.BasicAuth(os.environ["CIRCL_USER"], os.environ.get("CIRCL_PASS", ""))

    for name in opts.names or sorted(RECORDINGS):
        await record(name, auth)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))

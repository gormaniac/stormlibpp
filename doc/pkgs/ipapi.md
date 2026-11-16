# ipapi

A Synapse Rapid Power-Up that enriches IPs using the free ip-api.com JSON API. It models each
IP's ASN and owner org, its `geo:place` and `:latlong`, a `geo:telem`, and its `:loc`, and tags
hosting, proxy and mobile IPs (`#rep.ipapi.infra.*` by default).

No API token is required. ip-api.com's free endpoint is HTTP only, and allows 45 requests a
minute per source IP. slib.ipapi follows ip-api.com's rate limit headers: when the limit is
used up, every query on the Cortex waits until the window resets, and a rate limited query
waits and retries.

Requires the `slib.utils` package (StormLib++'s `utils` package) to be loaded.

This package used to be the `slib.ipapi` Storm Service in the stormsvcs repo. Its commands,
perms and settings are the same. To upgrade from the service, remove it with `service.del`
and load this package.

## Examples
```
// Lift some inet:ipv4 nodes and query ip-api.com for information.
inet:ipv4 | limit 5 | slib.ipapi.query

// Use a string argument to query for a specific IP address.
slib.ipapi.query --query 8.8.8.8

// Use a custom tag prefix for the hosting/proxy/mobile tags, or turn the tags off.
slib.ipapi.admin.settag myorg.ipapi
slib.ipapi.admin.disabletag
```

## Perms

- `slib.ipapi.user` - Run `slib.ipapi.query`.
- `slib.ipapi.admin` - Run the `slib.ipapi.admin.*` commands.

# ipinfo

A Synapse Rapid Power-Up that enriches IPs from ipinfo.io

Since this uses only the Lite API, this is basically nothing but a glorified ASN enricher. There's no lat/long in this API so we can't even add `geo:nloc`s.

Requires an ipinfo.io token set as either a user var or a global var (`slib:ipinfo:token`).

## Examples
```
// Lift some inet:ipv4 nodes and query ipinfo.io for information.
inet:ipv4 | limit 5 | slib.ipinfo

// Use a string argument to query for a specific IP address.
slib.ipinfo --query 8.8.8.8
```

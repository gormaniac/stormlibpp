# dnsstorm
A Synapse Rapid Power-Up that brings DNS over HTTPS capabilities to a Cortex using Clourdflare.

Adds a `dns.request` Storm command to a Cortex that takes inbound `inet:fqdn` or `inet:ipv4` nodes and yields `inet:dns:answer` nodes. Querying by string value is also supported instead of using existing nodes.

The following DNS request types are supported:
```
A
AAAA
CNAME
MX
NS
PTR
TXT
```

## Examples
```
// Lift some inet:fqdn nodes and query their AAAA records
inet:fqdn | limit 5 | dns.request --type AAAA

// Make a DNS query using string input and then pivot to the inet:ipv4
// nodes corresponding to the DNS A records in the query's response
dns.request --query google.com | :a -> inet:dns:a :ipv4 -> inet:ipv4

// Lift an inet:ipv4 and make a reverse DNS query
inet:ipv4=1.1.1.1 | dns.request --type PTR
```

# Circl Passive DNS

An interface to the passive DNS data published by [circl.lu](https://www.circl.lu/services/passive-dns/).

`slib.pdns` is a Synapse Rapid Power-Up that looks up FQDNs and IPs in CIRCL Passive DNS and models the DNS records CIRCL has seen.

CIRCL Passive DNS needs an account. CIRCL gives access to trusted partners. Request it from CIRCL's [contact page](https://www.circl.lu/contact/) and say who you are and what you'll use the data for. The API uses HTTP Basic auth. An admin saves the credentials once with `slib.pdns.admin.key`, and every user's lookups use them. Users can't read the credentials.

## Examples
```
// Save the CIRCL Passive DNS credentials (admin only).
slib.pdns.admin.key myuser mypassword

// Look up the passive DNS records of some inet:fqdn nodes.
inet:fqdn=circl.lu | slib.pdns.lookup

// Look up a value without any inbound nodes, and yield the DNS records.
slib.pdns.lookup --query 185.194.93.14 --yield

// Only look up NS records, and skip CIRCL's active resolver.
inet:fqdn=circl.lu | slib.pdns.lookup --rrtype NS --no-active
```

## Commands

- `slib.pdns.lookup` - Look up `inet:fqdn`, `inet:ipv4` and `inet:ipv6` nodes, or a `--query` string. Options: `--rrtype`, `--no-active`, `--page-size`, `--yield`.
- `slib.pdns.admin.key` - Save (`<username> <password>`) or remove (`--clear`) the CIRCL credentials.

## Perms

- `slib.pdns.user` - Run `slib.pdns.lookup`.
- `slib.pdns.admin` - Run `slib.pdns.admin.key`.

## API Notes

- CIRCL doesn't support CIDR block queries.
- CIRCL's active resolver is on by default. `--no-active` sends `dribble-disable-active-query`.
- CIRCL returns at most 1000 records of one rrtype. When it caps a result, the `X-Dribble-Errors` response header has a `maxset` error. Use pages (`dribble-paginate-count`, then the `X-Dribble-Cursor` of each response) to get all of the records.
- In CIRCL's responses, `rrname` is the record's value and `rdata` is the name that owns the record. The COF spec has these the other way round. Ex. `{"rrtype": "A", "rrname": "185.194.93.14", "rdata": "circl.lu"}` is `circl.lu A 185.194.93.14`.
- Real responses for the tests are in `tests/pkgs/pdns/cassettes/`. Re-record them with `scripts/pkgs/record_circl.py`.

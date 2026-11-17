# Circl Passive SSL

An interface to the passive SSL data published by [circl.lu](https://www.circl.lu/services/passive-ssl/).

`slib.pssl` is a Synapse Rapid Power-Up that looks up IPs, CIDR blocks and certificates in CIRCL Passive SSL. CIRCL Passive SSL is a history of the X.509 certificates seen on IP addresses.

CIRCL Passive SSL needs an account. CIRCL gives access to partners, including security researchers and incident analysts. Request it from CIRCL's [contact page](https://www.circl.lu/contact/). The API uses HTTP Basic auth. An admin saves the credentials once with `slib.pssl.admin.key`, and every user's lookups use them. Users can't read the credentials.

Requires the `slib.utils` package (StormLib++'s `utils` package) to be loaded. `slib.pssl` uses its X.509 parser.

## Examples
```
// Save the CIRCL Passive SSL credentials (admin only).
slib.pssl.admin.key myuser mypassword

// Look up the certificates seen on some IPs.
inet:ipv4=172.228.24.7 | slib.pssl.lookup

// Look up a CIDR block, and fetch every certificate seen in it.
slib.pssl.lookup --query 172.228.24.0/28 --fetch --yield

// Look up the IPs a certificate was seen on.
crypto:x509:cert:sha1=c46fed822dadac3f31f9bb4d1a78a1d9eae4567b | slib.pssl.lookup
```

## Commands

- `slib.pssl.lookup` - Look up `inet:ipv4`, `inet:cidr4`, `crypto:x509:cert` (by `:sha1`) and `hash:sha1` nodes, or a `--query` string. Options: `--fetch`, `--yield`.
- `slib.pssl.admin.key` - Save (`<username> <password>`) or remove (`--clear`) the CIRCL credentials.

## Perms

- `slib.pssl.user` - Run `slib.pssl.lookup`.
- `slib.pssl.admin` - Run `slib.pssl.admin.key`.

## API Notes

The API has three endpoints under `https://www.circl.lu/v2pssl/`:

- `query/<ip or cidr>` - The certificates (SHA1s and subjects) seen on each IP. It supports IPv4 only, in blocks from /23 to /32. An IP with no certificates isn't in the result, so a lookup that finds nothing returns `{}`.
- `cquery/<sha1>` - The IPs a certificate was seen on. An unknown SHA1 returns `"hits": 0`.
- `cfetch/<sha1>` - The certificate's PEM, CIRCL's parsed info, and ICSI Notary first and last seen times.

Errors are HTTP 400s with a plain text message, ex. `Maximum CIDR block size reached >/23`, `IPv6 is not (yet) supported` or `Not existing certificate`.

Real responses for the tests are in `tests/pkgs/pssl/cassettes/`. Re-record them with `scripts/pkgs/record_circl.py`.

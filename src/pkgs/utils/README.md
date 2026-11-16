# StormLib++ `utils` Storm Module

A Synapse Rapid Power-Up that brings useful library code into a Synapse Cortex. It is used by other Power-Ups in the StormLib++ project.

## Functions

- `getUserOrSystemOpt`
    - Pass an option string and get it from either the user vars or global vars, returns `null` if not found. Example: 
        ```
        $utils = $lib.import(slib.utils)
        $token = $utils.getUserOrSystemOpt("slib:ipinfo:token")
        ```

## `slib.utils.inet`

Network modeling shared by StormLib++ packages (`slib.ipapi` and `ipinfo`).

- `asnNum(valu)` - The ASN number in an int or a string like `15169`, `AS15169` or
  `AS15169 Google LLC`. Returns `null` if there isn't one.
- `asnNode(asn, orgname=(null), names=(null), orgtype=(null))` - Make the `inet:asn` and return
  it. With `orgname`, its `:owner` is the `ou:org` with that name (`$lib.gen.orgByName`), which
  also gets `names` added to its `:names` (existing names are kept) and `orgtype`. Makes nothing and returns `null` if `asn` has no ASN number.
    ```
    $inet = $lib.import(slib.utils.inet)
    yield $inet.asnNode("AS15169 Google LLC", orgname="Google LLC", orgtype=company.isp)
    ```
## `slib.utils.x509`

A pure Storm X.509 certificate parser (RFC 5280), for packages that need certificate details
without a Storm service.

```
$x509 = $lib.import(slib.utils.x509)

// DER bytes, a PEM string, or a base64 string.
$cert = $x509.parse($valu)
$lib.print(`{$cert.subject.dn} issued by {$cert.issuer.dn}, expires {$lib.time.format($cert.notafter, "%Y-%m-%d")}`)

// crypto:x509:cert:identities:* values from the SANs and subject CNs.
$ids = $x509.identities($cert.sans, $cert.subject.attrs.cn)
```

### Functions

- `parse(valu)` - Parse a certificate, or a bare TBSCertificate (a CT log precertificate entry).
  `valu` is DER bytes, a PEM string (`CERTIFICATE`, `X509 CERTIFICATE` or `TRUSTED CERTIFICATE`
  blocks), or a base64 string. Raises `BadCert` if the DER is too malformed to read.
- `load(valu)` - The DER bytes of a PEM or base64 string (bytes are returned as they are).
- `isTbs(byts)` - Whether DER bytes are a bare TBSCertificate instead of a certificate.
- `identities(sans, cns)` - Split SANs and subject CNs into `fqdns`, `emails`, `ipv4s`, `ipv6s`
  and `urls`, sorted and de-duplicated. Wildcard DNS names use their base domain.

### What `parse()` returns

Only Storm primitives: bytes are lowercase hex and times are epoch milliseconds.

| Key | Value |
|---|---|
| `sha256`, `sha1`, `md5`, `size` | The certificate's fingerprints and DER size. `null` for a TBSCertificate. |
| `tbs` | A TBSCertificate's SHA-256 (it has no fingerprints). `null` for a certificate. |
| `version` | The raw version: `0` is v1, `2` is v3. |
| `serial` | Minimal two's complement hex. Positive serials have no leading `00`. |
| `subject`, `issuer` | `{"dn", "attrs", "rdns", "der"}`. `dn` is the RFC 4514 string, written exactly like Python cryptography's `rfc4514_string()`. `attrs` maps short keys (`cn`, `o`, `ou`, `c`, `st`, `l`, `email`, `dc`, ...) or dotted OIDs to lists of values. |
| `notbefore`, `notafter` | Epoch millis. |
| `sigalgo` | `{"oid", "name", "hash"}`, plus `pss` (RSASSA-PSS parameters) or `params`. |
| `signature` | Hex. `null` for a TBSCertificate. |
| `pubkey` | `{"algo", "size", "oid", "spki", "sha256", "sha1", "key"}`, plus `rsa` (`mod`, `exp`), `curve` and `point` (EC), `pss` or `params`. `sha256`/`sha1` are the SPKI hashes. |
| `selfsigned` | The subject and issuer match, and the AKI (if any) equals the SKI. |
| `sans`, `ca`, `pathlen`, `keyusage`, `extkeyusage`, `ski`, `aki`, `crls`, `ocsp`, `caissuers`, `policies`, `precert` | The commonly used extension values. SANs are `[type, value]` pairs using the `crypto:x509:san` types. |
| `ians`, `akiissuer`, `akiserial`, `crldps`, `freshestcrl`, `aia`, `sia`, `policyinfo`, `nameconstraints`, `policyconstraints`, `policymappings`, `inhibitanypolicy`, `privatekeyusage`, `tlsfeatures`, `scts`, `ocspnocheck`, `issueruid`, `subjectuid` | Set when the certificate has them. |
| `extensions` | Every extension: `{"oid", "name", "critical", "value", "parsed"}`, and `error` if it couldn't be parsed. |
| `unhandled` | OIDs of critical extensions the parser doesn't understand (or couldn't parse). |
| `warnings` | Deviations from DER and RFC 5280 that didn't stop parsing. |

### Edge cases

Recoverable problems become `warnings` instead of errors, so certificates from CT logs and old
CAs still parse: non-minimal lengths, INTEGERs and OID arcs, the high tag number form for low
tags, BOOLEANs that aren't `0x00`/`0xff`, DEFAULT values that are encoded (v1 version, critical
FALSE, cA FALSE), negative and over-long serials, UTCTime without seconds, UTC offsets, local
times, fractional seconds, leap seconds, GeneralizedTime validity dates before 2050, notBefore
after notAfter, extensions outside v3, duplicate extensions (the first is used), trailing data,
non-zero unused bits, strings that don't decode, mismatched signature algorithms, non-contiguous
name constraint netmasks and odd sized iPAddress values. An extension that fails to parse gets an
`error` and the rest of the certificate is still parsed.

Some things always raise `BadCert`: indefinite (BER) lengths, constructed (BER) primitives,
truncated DER, BIT STRINGs with more than 7 unused bits, invalid dates, and a missing or
malformed TBSCertificate field.

Times follow RFC 5280: UTCTime years 50-99 are 19xx and 00-49 are 20xx, and
`99991231235959Z` (no well-defined expiration) is year 9999. IPv6 addresses are written per
RFC 5952, IPv4-mapped addresses as `::ffff:a.b.c.d`. TeletexString is decoded as Latin-1,
BMPString as UTF-16 and UniversalString as UTF-32.

The parser reads certificates, it doesn't validate them: it doesn't check signatures, chains,
name constraints, the DER ordering of SET OF values or the character set of PrintableString.

### Performance

Storm is interpreted, so parsing takes roughly 100 ms per certificate on a typical machine
(measured on Synapse 2.256). OIDs and names are cached within a query, so parsing many
certificates from the same issuers in one query is a little faster.

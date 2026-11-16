import base64
import datetime
import hashlib
import ipaddress
import json
import os

import synapse.exc as s_exc
import synapse.tests.utils as s_test
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, padding, rsa, x25519
from cryptography.x509.name import _ASN1Type
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from ... import DIRNAME
from . import x509ref as r

DATA = os.path.join(DIRNAME, "tests/pkgs/utils/data")

PARSE = "return($lib.import(slib.utils.x509).parse($valu))"

# Keys are slow to make, so share them.
RSAKEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ECKEY = ec.generate_private_key(ec.SECP256R1())


def pems(path):
    text = open(path).read()
    return [
        base64.b64decode("".join(blk.split("-----END CERTIFICATE-----")[0].split()))
        for blk in text.split("-----BEGIN CERTIFICATE-----")[1:]
    ]


def millis(*args):
    return int(datetime.datetime(*args, tzinfo=datetime.UTC).timestamp() * 1000)


def spki(key):
    return key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def mkcert(
    subject=None,
    issuer=None,
    key=None,
    signkey=None,
    exts=(),
    algo=hashes.SHA256(),
    pad=None,
    notbefore=datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC),
    notafter=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    serial=0x1234,
):
    key = key or ECKEY
    signkey = signkey or RSAKEY
    subject = subject or x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.example.com")])
    issuer = issuer or x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test CA")])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(serial)
        .not_valid_before(notbefore)
        .not_valid_after(notafter)
    )
    for ext, critical in exts:
        builder = builder.add_extension(ext, critical=critical)
    if isinstance(signkey, (ed25519.Ed25519PrivateKey, ed448.Ed448PrivateKey)):
        algo = None
    kwargs = {"rsa_padding": pad} if pad is not None else {}
    cert = builder.sign(signkey, algo, **kwargs)
    return cert.public_bytes(serialization.Encoding.DER)


def wrapTbs(tbs):
    """Wrap a TBSCertificate in a Certificate with an empty signature, so cryptography can read it.

    The signature algorithm is copied from the TBSCertificate's own signature field.
    """
    pos = 2 if tbs[1] < 0x80 else 2 + (tbs[1] & 0x7F)
    body = tbs[pos:]
    idx = 0
    parts = []
    while idx < len(body) and len(parts) < 3:
        size = body[idx + 1]
        hlen = 2
        if size & 0x80:
            n = size & 0x7F
            size = int.from_bytes(body[idx + 2 : idx + 2 + n], "big")
            hlen += n
        parts.append(body[idx : idx + hlen + size])
        idx += hlen + size
    sigalg = parts[2] if parts[0][0] == 0xA0 else parts[1]
    return r.seq(tbs, sigalg, r.der(0x03, b"\x00"))


class X509Test(s_test.StormPkgTest):

    pkgprotos = (os.path.join(DIRNAME, "src/pkgs/utils/utils.yaml"),)

    async def parseAll(self, core, valus):
        """Parse many values in one query: the result, or {"err": ...} for each."""
        return await core.callStorm(
            """
            $x = $lib.import(slib.utils.x509)
            $retn = ([])
            for $valu in $valus {
                try { $retn.append($x.parse($valu)) }
                catch * as err { $retn.append(({"err": $err.name, "mesg": $err.mesg})) }
            }
            return($retn)
            """,
            opts={"vars": {"valus": valus}},
        )

    async def parse(self, core, valu):
        return await core.callStorm(PARSE, opts={"vars": {"valu": valu}})

    async def test_x509_real_certs(self):
        """Real root certificates parse exactly like cryptography parses them."""

        ders = pems(os.path.join(DATA, "x509_roots.pem"))
        self.ge(len(ders), 10)
        async with self.getTestCore() as core:
            for der, parsed in zip(ders, await self.parseAll(core, ders)):
                self.notin("err", parsed)
                self.eq(r.ref(der), r.project(parsed))
                self.eq([], list(parsed["unhandled"]))

    async def test_x509_ct_entries(self):
        """bgp.he.net's CT entries: certificates and precertificate TBSCertificates."""

        with open(os.path.join(DATA, "x509_ct.json")) as fd:
            entries = json.load(fd)["certs"]

        async with self.getTestCore() as core:
            results = await self.parseAll(core, entries)
            ntbs = 0
            for b64, parsed in zip(entries, results):
                self.notin("err", parsed)
                der = base64.b64decode(b64)
                isTbs = await core.callStorm(
                    "return($lib.import(slib.utils.x509).isTbs($b))", opts={"vars": {"b": der}}
                )
                if isTbs:
                    ntbs += 1
                    self.eq(parsed["tbs"], hashlib.sha256(der).hexdigest())
                    self.none(parsed["sha256"])
                    self.none(parsed["signature"])
                    exp = r.ref(wrapTbs(der))
                    got = r.project(parsed)
                    for key in ("sha256", "sha1", "md5", "size", "signature"):
                        exp.pop(key)
                        got.pop(key)
                    self.eq(exp, got)
                else:
                    self.none(parsed["tbs"])
                    self.eq(r.ref(der), r.project(parsed))
            self.ge(ntbs, 1)

    async def test_x509_inputs(self):
        """parse() takes DER bytes, PEM, or base64, and rejects anything else."""

        der = mkcert()
        b64 = base64.b64encode(der).decode()
        pem = x509.load_der_x509_certificate(der).public_bytes(serialization.Encoding.PEM).decode()
        trusted = pem.replace("BEGIN CERTIFICATE", "BEGIN TRUSTED CERTIFICATE").replace(
            "END CERTIFICATE", "END TRUSTED CERTIFICATE"
        )
        sha = hashlib.sha256(der).hexdigest()

        async with self.getTestCore() as core:
            results = await self.parseAll(
                core, [der, b64, pem, f"junk before\n{pem}\njunk after", trusted, f"  {b64}\n"]
            )
            for parsed in results:
                self.eq(sha, parsed["sha256"])

            bad = await self.parseAll(
                core,
                [b"", b"\x00\x01\x02", "not base64 !!!", "-----BEGIN CERTIFICATE-----\n", 1234,
                 b"\x30\x80\x02\x01\x01\x00\x00", der[:-10]],
            )
            for parsed in bad:
                self.eq("BadCert", parsed.get("err"), msg=parsed)
            self.isin("Indefinite length", bad[5]["mesg"])
            self.isin("Truncated", bad[6]["mesg"])

            self.eq(der, await core.callStorm(
                "return($lib.import(slib.utils.x509).load($v))", opts={"vars": {"v": pem}}
            ))

    async def test_x509_keys_and_signatures(self):
        """Every key type and signature algorithm, including RSA-PSS parameters."""

        certs = {
            "ed25519": mkcert(key=ed25519.Ed25519PrivateKey.generate(), signkey=ed25519.Ed25519PrivateKey.generate()),
            "ed448": mkcert(key=ed448.Ed448PrivateKey.generate(), signkey=ed448.Ed448PrivateKey.generate()),
            "x25519": mkcert(key=x25519.X25519PrivateKey.generate()),
            "dsa": mkcert(key=dsa.generate_private_key(2048), signkey=dsa.generate_private_key(2048)),
            "secp256k1": mkcert(key=ec.generate_private_key(ec.SECP256K1()), signkey=ECKEY),
            "secp521r1": mkcert(key=ec.generate_private_key(ec.SECP521R1()), algo=hashes.SHA512()),
            "brainpool": mkcert(key=ec.generate_private_key(ec.BrainpoolP384R1()), algo=hashes.SHA384()),
            "rsa4096": mkcert(key=rsa.generate_private_key(65537, 4096), algo=hashes.SHA224()),
            "sha3": mkcert(algo=hashes.SHA3_256()),
            "pss": mkcert(
                algo=hashes.SHA384(),
                pad=padding.PSS(mgf=padding.MGF1(hashes.SHA384()), salt_length=32),
            ),
        }

        async with self.getTestCore() as core:
            res = dict(zip(certs, await self.parseAll(core, list(certs.values()))))

            for name, der in certs.items():
                self.eq(r.ref(der), r.project(res[name]), msg=name)

            self.eq("ed25519", res["ed25519"]["sigalgo"]["name"])
            self.none(res["ed25519"]["sigalgo"]["hash"])
            self.eq(("ed448", 456), (res["ed448"]["pubkey"]["algo"], res["ed448"]["pubkey"]["size"]))
            self.eq(("x25519", 256), (res["x25519"]["pubkey"]["algo"], res["x25519"]["pubkey"]["size"]))
            self.eq("secp256k1", res["secp256k1"]["pubkey"]["curve"])
            self.eq(("secp521r1", 521), (res["secp521r1"]["pubkey"]["curve"], res["secp521r1"]["pubkey"]["size"]))
            self.eq("brainpoolP384r1", res["brainpool"]["pubkey"]["curve"])
            self.eq(4096, res["rsa4096"]["pubkey"]["size"])
            self.eq(65537, res["rsa4096"]["pubkey"]["rsa"]["exp"])
            self.eq("sha3-256", res["sha3"]["sigalgo"]["hash"])

            pss = res["pss"]["sigalgo"]
            self.eq(("rsassaPss", "sha384"), (pss["name"], pss["hash"]))
            self.eq({"hash": "sha384", "mgf": "mgf1", "mgfhash": "sha384", "salt": 32, "trailer": 1}, pss["pss"])

            # An explicit (specifiedCurve) EC key, an unknown key algorithm, and RSASSA-PSS defaults.
            ecpoint = b"\x04" + b"\x11" * 64
            prime = (2**256 - 2**224 + 2**192 + 2**96 - 1)
            specified = r.seq(
                r.integer(1),
                r.seq(r.oid("1.2.840.10045.1.1"), r.integer(prime)),
                r.seq(r.der(0x04, b"\x01"), r.der(0x04, b"\x02")),
                r.der(0x04, ecpoint),
                r.integer(5),
            )
            keys = [
                r.seq(r.seq(r.oid("1.2.840.10045.2.1"), specified), r.der(0x03, b"\x00" + ecpoint)),
                r.seq(r.seq(r.oid("1.2.3.4.5"), r.der(0x02, b"\x07")), r.der(0x03, b"\x00\xab\xcd")),
                r.seq(r.seq(r.oid("1.2.840.10045.2.1")), r.der(0x03, b"\x00" + ecpoint)),
            ]
            psssig = r.seq(r.oid("1.2.840.113549.1.1.10"), r.seq())
            crafted = [r.certder(r.tbsder(k)) for k in keys]
            crafted.append(r.certder(r.tbsder(keys[1], sigalg=psssig), sigalg=psssig))
            res = await self.parseAll(core, crafted)

            self.eq(("ec", "explicit", 256), (res[0]["pubkey"]["algo"], res[0]["pubkey"]["curve"], res[0]["pubkey"]["size"]))
            self.eq(("1.2.3.4.5", "020107"), (res[1]["pubkey"]["algo"], res[1]["pubkey"]["params"]))
            self.eq("abcd", res[1]["pubkey"]["key"])
            self.eq(("ec", "implicit"), (res[2]["pubkey"]["algo"], res[2]["pubkey"]["curve"]))
            self.eq({"hash": "sha1", "mgf": "mgf1", "mgfhash": "sha1", "salt": 20, "trailer": 1}, res[3]["sigalgo"]["pss"])

    async def test_x509_names(self):
        """Distinguished names: RFC 4514 escaping, multi-valued RDNs and every string type."""

        tricky = [
            "comma, here", "plus+sign", 'quote"d', "back\\slash", "semi;colon", "<angle>",
            "#hash first", " leading space", "trailing space ", " ", "nul\x00byte", "ünïcødé ✓",
        ]
        subjects = [
            x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, valu)]) for valu in tricky
        ]
        subjects.append(x509.Name([
            x509.RelativeDistinguishedName([
                x509.NameAttribute(NameOID.COMMON_NAME, "multi"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "valued"),
            ]),
            x509.RelativeDistinguishedName([x509.NameAttribute(NameOID.COUNTRY_NAME, "US")]),
        ]))
        subjects.append(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "bmp ✓", _type=_ASN1Type.BMPString),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "universal ✓", _type=_ASN1Type.UniversalString),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "teletex", _type=_ASN1Type.T61String),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, "a@example.com"),
            x509.NameAttribute(NameOID.DOMAIN_COMPONENT, "example"),
            x509.NameAttribute(NameOID.USER_ID, "uid1"),
            x509.NameAttribute(NameOID.X500_UNIQUE_IDENTIFIER, b"\x01\x02", _type=_ASN1Type.BitString),
            x509.NameAttribute(NameOID.JURISDICTION_COUNTRY_NAME, "US"),
            x509.NameAttribute(x509.ObjectIdentifier("2.25.329800735698586629295641978511506172918"), "uuid arc"),
            x509.NameAttribute(x509.ObjectIdentifier("2.999.1"), "big first arc"),
        ]))
        certs = [mkcert(subject=s) for s in subjects]

        async with self.getTestCore() as core:
            results = await self.parseAll(core, certs)
            for subject, der, parsed in zip(subjects, certs, results):
                self.eq(subject.rfc4514_string(), parsed["subject"]["dn"])
                self.eq(r.ref(der), r.project(parsed))

            last = results[-1]["subject"]
            self.eq(["a@example.com"], last["attrs"]["email"])
            self.eq(["0102"], last["attrs"]["2.5.4.45"])
            self.eq(["uuid arc"], last["attrs"]["2.25.329800735698586629295641978511506172918"])
            self.eq(["big first arc"], last["attrs"]["2.999.1"])
            self.eq("x500UniqueIdentifier", last["rdns"][6][0]["name"])
            self.eq(2, len(results[-2]["subject"]["rdns"][0]))

            # Hand built names: an empty Name, an INTEGER value, bad UTF-8, latin-1 Teletex.
            names = [
                r.nameder(),
                r.nameder(r.der(0x31, r.seq(r.oid("2.5.4.5"), r.integer(5)))),
                r.nameder(r.attr("2.5.4.3", b"bad \xff utf8")),
                r.nameder(r.attr("2.5.4.3", b"caf\xe9", tag=0x14)),
            ]
            crafted = [r.certder(r.tbsder(spki(ECKEY), subject=n)) for n in names]
            res = await self.parseAll(core, crafted)
            self.eq("", res[0]["subject"]["dn"])
            self.eq("2.5.4.5=#020105", res[1]["subject"]["dn"])
            self.true(any("isn't a string" in w for w in res[1]["warnings"]))
            self.eq("CN=bad � utf8", res[2]["subject"]["dn"])
            self.true(any("isn't valid utf8" in w for w in res[2]["warnings"]))
            self.eq("CN=café", res[3]["subject"]["dn"])

    async def test_x509_extensions(self):
        """Every extension the parser understands, in detail."""

        sct = (
            b"\x00"  # v1
            + b"\xaa" * 32  # log id
            + (1700000000123).to_bytes(8, "big")
            + b"\x00\x00"  # no extensions
            + b"\x04\x03"  # sha256, ecdsa
            + b"\x00\x04" + b"\xde\xad\xbe\xef"
        )
        sctlist = r.der(0x04, (len(sct) + 2).to_bytes(2, "big") + len(sct).to_bytes(2, "big") + sct)
        dirname = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "dir")])
        exts = [
            (x509.SubjectAlternativeName([
                x509.DNSName("example.com"), x509.DNSName("*.example.com"),
                x509.RFC822Name("a@example.com"), x509.UniformResourceIdentifier("https://example.com/"),
                x509.IPAddress(ipaddress.ip_address("192.0.2.1")),
                x509.IPAddress(ipaddress.ip_address("2001:db8::1")),
                x509.IPAddress(ipaddress.ip_address("::1")),
                x509.IPAddress(ipaddress.ip_address("2001:db8:0:1:1:1:1:1")),
                x509.IPAddress(ipaddress.ip_address("2001:0:0:1::1")),
                x509.IPAddress(ipaddress.ip_address("::ffff:192.0.2.9")),
                x509.DirectoryName(dirname),
                x509.RegisteredID(x509.ObjectIdentifier("1.2.3.4")),
                x509.OtherName(x509.ObjectIdentifier("1.3.6.1.4.1.311.20.2.3"), b"\x0c\x03a@b"),
            ]), False),
            (x509.IssuerAlternativeName([x509.DNSName("issuer.example.com")]), False),
            (x509.BasicConstraints(ca=True, path_length=0), True),
            (x509.KeyUsage(True, True, True, True, True, True, True, True, True), True),
            (x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH,
                                    x509.ObjectIdentifier("1.2.3.99")]), False),
            (x509.SubjectKeyIdentifier(b"\x01" * 20), False),
            (x509.AuthorityKeyIdentifier(b"\x02" * 20, [x509.DirectoryName(dirname)], 0xABCD), False),
            (x509.CRLDistributionPoints([
                x509.DistributionPoint([x509.UniformResourceIdentifier("http://crl.example.com/a.crl")],
                                       None, frozenset([x509.ReasonFlags.key_compromise]), [x509.DirectoryName(dirname)]),
                x509.DistributionPoint(None, x509.RelativeDistinguishedName([x509.NameAttribute(NameOID.COMMON_NAME, "rel")]), None, None),
            ]), False),
            (x509.FreshestCRL([x509.DistributionPoint([x509.UniformResourceIdentifier("http://delta.example.com")], None, None, None)]), False),
            (x509.AuthorityInformationAccess([
                x509.AccessDescription(x509.AuthorityInformationAccessOID.OCSP, x509.UniformResourceIdentifier("http://ocsp.example.com")),
                x509.AccessDescription(x509.AuthorityInformationAccessOID.CA_ISSUERS, x509.UniformResourceIdentifier("http://ca.example.com/ca.crt")),
            ]), False),
            (x509.SubjectInformationAccess([
                x509.AccessDescription(x509.oid.SubjectInformationAccessOID.CA_REPOSITORY, x509.UniformResourceIdentifier("http://repo.example.com")),
            ]), False),
            (x509.CertificatePolicies([
                x509.PolicyInformation(x509.ObjectIdentifier("2.23.140.1.2.1"), [
                    "https://cps.example.com",
                    x509.UserNotice(x509.NoticeReference("Example Org", [1, 2]), "Explicit text"),
                ]),
                x509.PolicyInformation(x509.ObjectIdentifier("2.5.29.32.0"), None),
            ]), False),
            (x509.NameConstraints(
                permitted_subtrees=[x509.DNSName("example.com"), x509.IPAddress(ipaddress.ip_network("10.0.0.0/8")),
                                    x509.IPAddress(ipaddress.ip_network("2001:db8::/32"))],
                excluded_subtrees=[x509.RFC822Name("bad.example.com")]), True),
            (x509.PolicyConstraints(require_explicit_policy=0, inhibit_policy_mapping=1), True),
            (x509.InhibitAnyPolicy(3), True),
            (x509.TLSFeature([x509.TLSFeatureType.status_request]), False),
            (x509.PrecertPoison(), True),
            (x509.OCSPNoCheck(), False),
            (x509.PrivateKeyUsagePeriod(datetime.datetime(2025, 1, 1), datetime.datetime(2025, 6, 1)), False),
            (x509.UnrecognizedExtension(x509.ObjectIdentifier("1.3.6.1.4.1.11129.2.4.2"), sctlist), False),
            (x509.UnrecognizedExtension(x509.ObjectIdentifier("2.5.29.33"), r.seq(r.seq(r.oid("1.2.3"), r.oid("1.2.4")))), True),
            (x509.UnrecognizedExtension(x509.ObjectIdentifier("1.2.3.4.5.6"), b"\x05\x00"), True),
        ]
        der = mkcert(exts=exts)

        async with self.getTestCore() as core:
            res = await self.parse(core, der)
            self.eq(r.ref(der), r.project(res))
            self.eq([], list(res["warnings"]))

            self.eq([
                ["dns", "example.com"], ["dns", "*.example.com"], ["email", "a@example.com"],
                ["uri", "https://example.com/"], ["ip", "192.0.2.1"], ["ip", "2001:db8::1"], ["ip", "::1"],
                ["ip", "2001:db8:0:1:1:1:1:1"], ["ip", "2001:0:0:1::1"], ["ip", "::ffff:192.0.2.9"],
                ["dirname", "CN=dir"], ["registeredid", "1.2.3.4"],
                ["othername", "1.3.6.1.4.1.311.20.2.3:0c03614062"],
            ], [list(s) for s in res["sans"]])
            self.eq([["dns", "issuer.example.com"]], [list(s) for s in res["ians"]])
            self.eq((True, 0), (res["ca"], res["pathlen"]))
            self.eq(["digital_signature", "content_commitment", "key_encipherment", "data_encipherment",
                     "key_agreement", "key_cert_sign", "crl_sign", "encipher_only", "decipher_only"], list(res["keyusage"]))
            self.eq([("1.3.6.1.5.5.7.3.1", "serverAuth"), ("1.3.6.1.5.5.7.3.2", "clientAuth"), ("1.2.3.99", "1.2.3.99")],
                    [(e["oid"], e["name"]) for e in res["extkeyusage"]])
            self.eq(("01" * 20, "02" * 20, "abcd"), (res["ski"], res["aki"], res["akiserial"]))
            self.eq([["dirname", "CN=dir"]], [list(g) for g in res["akiissuer"]])

            dps = res["crldps"]
            self.eq([["uri", "http://crl.example.com/a.crl"]], [list(g) for g in dps[0]["full"]])
            self.eq(["key_compromise"], list(dps[0]["reasons"]))
            self.eq([["dirname", "CN=dir"]], [list(g) for g in dps[0]["issuer"]])
            self.eq("CN=rel", dps[1]["relative"])
            self.eq(["http://crl.example.com/a.crl"], list(res["crls"]))
            self.eq(["http://delta.example.com"], [g[1] for g in res["freshestcrl"][0]["full"]])

            self.eq(["http://ocsp.example.com"], list(res["ocsp"]))
            self.eq(["http://ca.example.com/ca.crt"], list(res["caissuers"]))
            self.eq("caRepository", res["sia"][0]["name"])

            self.eq(["2.23.140.1.2.1", "2.5.29.32.0"], list(res["policies"]))
            pol = res["policyinfo"][0]
            self.eq(("domain-validated", ["https://cps.example.com"]), (pol["name"], list(pol["cps"])))
            self.eq({"org": "Example Org", "numbers": (1, 2), "text": "Explicit text"}, pol["notices"][0])

            nc = res["nameconstraints"]
            self.eq([["dns", "example.com"], ["ip", "10.0.0.0/8"], ["ip", "2001:db8::/32"]],
                    [list(t["name"]) for t in nc["permitted"]])
            self.eq([["email", "bad.example.com"]], [list(t["name"]) for t in nc["excluded"]])

            self.eq({"requireexplicit": 0, "inhibitmapping": 1}, res["policyconstraints"])
            self.eq(3, res["inhibitanypolicy"])
            self.eq([5], list(res["tlsfeatures"]))
            self.true(res["precert"])
            self.true(res["ocspnocheck"])
            self.eq({"notbefore": millis(2025, 1, 1), "notafter": millis(2025, 6, 1)}, res["privatekeyusage"])
            self.eq([("1.2.3", "1.2.4")], [tuple(m) for m in res["policymappings"]])

            sct = res["scts"][0]
            self.eq((0, "aa" * 32, 1700000000123, 4, 3, "deadbeef"),
                    (sct["version"], sct["logid"], sct["timestamp"], sct["hashalg"], sct["sigalg"], sct["signature"]))

            self.eq(["1.2.3.4.5.6"], list(res["unhandled"]))
            exts = {e["oid"]: e for e in res["extensions"]}
            self.eq(len(exts), len(res["extensions"]))
            self.false(exts["1.2.3.4.5.6"]["parsed"])
            self.true(exts["1.2.3.4.5.6"]["critical"])
            self.eq("0500", exts["1.2.3.4.5.6"]["value"])
            self.true(exts["2.5.29.17"]["parsed"])

    async def test_x509_der_edge_cases(self):
        """Hand built DER: deviations that warn, and malformed DER that raises."""

        key = spki(ECKEY)
        sigalg = r.SHA256RSA
        kuext = r.ext("2.5.29.15", r.der(0x03, b"\x07\x80"), critical=True)
        badku = r.ext("2.5.29.15", b"\xff\xff", critical=True)
        sanext = r.ext("2.5.29.17", r.seq(r.der(0x82, b"one.example.com")))
        sanext2 = r.ext("2.5.29.17", r.seq(r.der(0x82, b"two.example.com")))
        tbs = r.tbsder

        cases = {
            "v1": r.certder(tbs(key, version=None)),
            "v1explicit": r.certder(tbs(key, version=r.der(0xA0, r.integer(0)))),
            "v2uids": r.certder(tbs(key, version=r.der(0xA0, r.integer(1)),
                                    extra=r.der(0x81, b"\x00\x0a") + r.der(0x82, b"\x00\x0b"))),
            "negserial": r.certder(tbs(key, serial=r.integer(-128))),
            "longserial": r.certder(tbs(key, serial=r.integer(2**170))),
            "padserial": r.certder(tbs(key, serial=r.der(0x02, b"\x00\x00\x01"))),
            "utc2049": r.certder(tbs(key, validity=r.seq(r.utctime("491231235959Z"), r.utctime("500101000000Z")))),
            "gen2050": r.certder(tbs(key, validity=r.seq(r.utctime("250101000000Z"), r.gentime("99991231235959Z")))),
            "gen2049": r.certder(tbs(key, validity=r.seq(r.gentime("20490101000000Z"), r.gentime("20500101000000Z")))),
            "nosecs": r.certder(tbs(key, validity=r.seq(r.utctime("2501010000Z"), r.utctime("260101000000Z")))),
            "offset": r.certder(tbs(key, validity=r.seq(r.utctime("250101000000+0130"), r.utctime("260101000000Z")))),
            "fraction": r.certder(tbs(key, validity=r.seq(r.utctime("250101000000Z"), r.gentime("20501231235959.123Z")))),
            "leapsec": r.certder(tbs(key, validity=r.seq(r.utctime("250101000000Z"), r.gentime("20501231235960Z")))),
            "localtime": r.certder(tbs(key, validity=r.seq(r.utctime("250101000000Z"), r.gentime("20510101000000")))),
            "badday": r.certder(tbs(key, validity=r.seq(r.utctime("250230000000Z"), r.utctime("260101000000Z")))),
            "backwards": r.certder(tbs(key, validity=r.seq(r.utctime("260101000000Z"), r.utctime("250101000000Z")))),
            "trailing": r.certder(tbs(key)) + b"\x00\x00",
            "longlen": r.certder(tbs(key, serial=b"\x02\x81\x01\x05")),
            "hightag": r.certder(tbs(key, exts=None, extra=b"\xbf\x03" + r.der(0x30, r.seq(kuext))[1:])),
            "dupext": r.certder(tbs(key, exts=[sanext, sanext2])),
            "badext": r.certder(tbs(key, exts=[badku, sanext])),
            "unknowncrit": r.certder(tbs(key, exts=[r.ext("1.2.3.4", b"\x05\x00", critical=True)])),
            "boolnotff": r.certder(tbs(key, exts=[r.seq(r.oid("2.5.29.15"), r.der(0x01, b"\x01"), r.der(0x04, r.der(0x03, b"\x07\x80")))])),
            "explicitfalse": r.certder(tbs(key, exts=[r.seq(r.oid("2.5.29.15"), r.der(0x01, b"\x00"), r.der(0x04, r.der(0x03, b"\x07\x80")))])),
            "extsv1": r.certder(tbs(key, version=None, exts=[kuext])),
            "badoid": r.certder(tbs(key, exts=[r.seq(r.der(0x06, b"\x2a\x80\x03"), r.der(0x04, b"\x05\x00"))])),
            "sigmismatch": r.certder(tbs(key), sigalg=r.seq(r.oid("1.2.840.113549.1.1.5"), r.der(0x05, b""))),
            "badunused": r.certder(tbs(key), sig=b"\x09\x00"),
            "ipmask": r.certder(tbs(key, exts=[r.ext("2.5.29.30", r.seq(r.der(0xA0, r.seq(r.der(0x87, b"\x0a\x00\x00\x00\xff\x00\xff\x00")))), critical=True)])),
            "x400": r.certder(tbs(key, exts=[r.ext("2.5.29.17", r.seq(r.der(0xA3, r.seq())))])),
            "ipv6len": r.certder(tbs(key, exts=[r.ext("2.5.29.17", r.seq(r.der(0x87, b"\x01\x02\x03")))])),
            "berstring": r.certder(tbs(key, exts=[r.seq(r.oid("2.5.29.14"), r.der(0x24, r.der(0x04, r.der(0x04, b"\x01"))))])),
            "badgname": r.certder(tbs(key, exts=[r.ext("2.5.29.17", r.seq(r.der(0x89, b"\x01")))])),
        }

        async with self.getTestCore() as core:
            res = dict(zip(cases, await self.parseAll(core, list(cases.values()))))

            def warned(name, text):
                self.true(any(text in w for w in res[name]["warnings"]), msg=(name, res[name].get("warnings"), res[name].get("mesg")))

            self.eq((0, []), (res["v1"]["version"], list(res["v1"]["warnings"])))
            self.eq(0, res["v1explicit"]["version"])
            warned("v1explicit", "DEFAULT v1")
            self.eq((1, "0a", "0b"), (res["v2uids"]["version"], res["v2uids"]["issueruid"], res["v2uids"]["subjectuid"]))

            self.eq("80", res["negserial"]["serial"])
            warned("negserial", "Negative serial")
            warned("longserial", "longer than 20 octets")
            self.eq("01", res["padserial"]["serial"])
            warned("padserial", "Non-minimal INTEGER")

            self.eq((millis(2049, 12, 31, 23, 59, 59), millis(1950, 1, 1)),
                    (res["utc2049"]["notbefore"], res["utc2049"]["notafter"]))
            self.eq(millis(9999, 12, 31, 23, 59, 59), res["gen2050"]["notafter"])
            self.eq([], list(res["gen2050"]["warnings"]))
            warned("gen2049", "before 2050")
            self.eq(millis(2025, 1, 1), res["nosecs"]["notbefore"])
            warned("nosecs", "without seconds")
            self.eq(millis(2024, 12, 31, 22, 30), res["offset"]["notbefore"])
            warned("offset", "UTC offset")
            self.eq(millis(2050, 12, 31, 23, 59, 59) + 123, res["fraction"]["notafter"])
            warned("fraction", "fractional seconds")
            self.eq(millis(2051, 1, 1), res["leapsec"]["notafter"])
            warned("leapsec", "Leap second")
            self.eq(millis(2051, 1, 1), res["localtime"]["notafter"])
            warned("localtime", "Local time")
            self.eq("BadCert", res["badday"]["err"])
            warned("backwards", "notBefore is after notAfter")

            warned("trailing", "trailing data")
            self.eq("05", res["longlen"]["serial"])
            warned("longlen", "Non-minimal length")
            self.eq(["digital_signature"], list(res["hightag"]["keyusage"]))
            warned("hightag", "High tag number form")

            self.eq([["dns", "one.example.com"]], [list(s) for s in res["dupext"]["sans"]])
            self.eq(2, len(res["dupext"]["extensions"]))
            warned("dupext", "Duplicate extension 2.5.29.17")

            self.eq([["dns", "one.example.com"]], [list(s) for s in res["badext"]["sans"]])
            warned("badext", "Unable to parse extension 2.5.29.15")
            self.isin("error", res["badext"]["extensions"][0])
            self.eq(["2.5.29.15"], list(res["badext"]["unhandled"]))

            self.eq(["1.2.3.4"], list(res["unknowncrit"]["unhandled"]))
            warned("boolnotff", "isn't 0x00 or 0xff")
            self.true(res["boolnotff"]["extensions"][0]["critical"])
            warned("explicitfalse", "DEFAULT FALSE")
            warned("extsv1", "isn't v3")
            warned("badoid", "Non-minimal OBJECT IDENTIFIER")
            self.eq("1.2.3", res["badoid"]["extensions"][0]["oid"])
            warned("sigmismatch", "doesn't match")
            self.eq("BadCert", res["badunused"]["err"])

            self.eq(["ip", "10.0.0.0/255.0.255.0"], list(res["ipmask"]["nameconstraints"]["permitted"][0]["name"]))
            warned("ipmask", "Non-contiguous netmask")
            self.eq([["x400address", "3000"]], [list(s) for s in res["x400"]["sans"]])
            self.eq([["ip", "010203"]], [list(s) for s in res["ipv6len"]["sans"]])
            warned("ipv6len", "is 3 bytes")
            self.eq("BadCert", res["berstring"]["err"])
            self.isin("Constructed (BER)", res["berstring"]["mesg"])
            warned("badgname", "Unknown GeneralName")

    async def test_x509_selfsigned(self):
        """selfsigned needs a matching subject/issuer, and AKI (if any) equal to SKI."""

        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "root")])
        ski = x509.SubjectKeyIdentifier(b"\x01" * 20)
        certs = [
            mkcert(subject=name, issuer=name, signkey=ECKEY),
            mkcert(subject=name, issuer=name, exts=[(ski, False), (x509.AuthorityKeyIdentifier(b"\x01" * 20, None, None), False)]),
            mkcert(subject=name, issuer=name, exts=[(ski, False), (x509.AuthorityKeyIdentifier(b"\x02" * 20, None, None), False)]),
            mkcert(subject=name),
        ]
        async with self.getTestCore() as core:
            res = await self.parseAll(core, certs)
            self.eq([True, True, False, False], [p["selfsigned"] for p in res])

    async def test_x509_identities(self):
        """identities() splits SANs and CNs into crypto:x509:cert:identities:* values."""

        sans = [
            ["dns", "*.Example.com."], ["dns", "example.com"], ["dns", "bad*.example.com"], ["dns", "nodot"],
            ["email", "A@Example.com"], ["ip", "192.0.2.1"], ["ip", "2001:DB8:0::1"], ["ip", "not an ip"],
            ["uri", "https://example.com/x"], ["dirname", "CN=x"],
        ]
        cns = ["admin@example.org", "198.51.100.7", "www.example.net", "Some Org Name"]
        async with self.getTestCore() as core:
            res = await core.callStorm(
                "return($lib.import(slib.utils.x509).identities($sans, $cns))",
                opts={"vars": {"sans": sans, "cns": cns}},
            )
            self.eq({
                "fqdns": ("example.com", "www.example.net"),
                "emails": ("a@example.com", "admin@example.org"),
                "ipv4s": ("192.0.2.1", "198.51.100.7"),
                "ipv6s": ("2001:db8::1",),
                "urls": ("https://example.com/x",),
            }, res)

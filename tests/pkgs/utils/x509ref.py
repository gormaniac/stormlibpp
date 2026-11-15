"""A reference X.509 parser built on cryptography, and a small DER encoder, for the x509 tests.

``ref()`` returns the subset of ``slib.utils.x509.parse()`` that cryptography can also produce, in
the same shape, so the Storm parser can be checked field by field against a mature parser.
"""

import binascii
import datetime
import hashlib
import ipaddress

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa, x448, x25519
from cryptography.x509.oid import ExtensionOID, NameOID

ATTRKEYS = {
    NameOID.COMMON_NAME.dotted_string: "cn",
    NameOID.ORGANIZATION_NAME.dotted_string: "o",
    NameOID.ORGANIZATIONAL_UNIT_NAME.dotted_string: "ou",
    NameOID.COUNTRY_NAME.dotted_string: "c",
    NameOID.STATE_OR_PROVINCE_NAME.dotted_string: "st",
    NameOID.LOCALITY_NAME.dotted_string: "l",
    NameOID.STREET_ADDRESS.dotted_string: "street",
    NameOID.POSTAL_CODE.dotted_string: "postalcode",
    NameOID.EMAIL_ADDRESS.dotted_string: "email",
    NameOID.SERIAL_NUMBER.dotted_string: "serialnumber",
    NameOID.DOMAIN_COMPONENT.dotted_string: "dc",
    NameOID.BUSINESS_CATEGORY.dotted_string: "businesscategory",
    NameOID.JURISDICTION_COUNTRY_NAME.dotted_string: "jurisdiction:c",
    NameOID.JURISDICTION_STATE_OR_PROVINCE_NAME.dotted_string: "jurisdiction:st",
    NameOID.JURISDICTION_LOCALITY_NAME.dotted_string: "jurisdiction:l",
    NameOID.ORGANIZATION_IDENTIFIER.dotted_string: "organizationidentifier",
    NameOID.GIVEN_NAME.dotted_string: "givenname",
    NameOID.SURNAME.dotted_string: "surname",
    NameOID.TITLE.dotted_string: "title",
    NameOID.USER_ID.dotted_string: "uid",
}

KEYUSAGE = (
    "digital_signature", "content_commitment", "key_encipherment", "data_encipherment",
    "key_agreement", "key_cert_sign", "crl_sign",
)


def hexb(valu):
    return None if valu is None else binascii.hexlify(valu).decode()


def millis(valu):
    return int(valu.replace(tzinfo=datetime.UTC).timestamp() * 1000) if valu.tzinfo is None else int(valu.timestamp() * 1000)


def serialHex(serial):
    if serial < 0:
        size = (serial.bit_length() + 7) // 8 + 1
        text = binascii.hexlify(serial.to_bytes(size, "big", signed=True)).decode()
        # Minimal two's complement.
        while len(text) > 2 and text[:2] == "ff" and int(text[2:4], 16) >= 0x80:
            text = text[2:]
        return text
    text = format(serial, "x")
    return text if len(text) % 2 == 0 else "0" + text


def name(valu):
    attrs = {}
    for attr in valu:
        key = ATTRKEYS.get(attr.oid.dotted_string, attr.oid.dotted_string)
        attrs.setdefault(key, []).append(attr.value if isinstance(attr.value, str) else hexb(attr.value))
    return {"dn": valu.rfc4514_string(), "attrs": attrs}


def gname(valu):
    if isinstance(valu, x509.DNSName):
        return ["dns", valu.value]
    if isinstance(valu, x509.RFC822Name):
        return ["email", valu.value]
    if isinstance(valu, x509.UniformResourceIdentifier):
        return ["uri", valu.value]
    if isinstance(valu, x509.IPAddress):
        addr = valu.value
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
            return ["ip", f"::ffff:{addr.ipv4_mapped}"]
        return ["ip", str(addr)]
    if isinstance(valu, x509.DirectoryName):
        return ["dirname", valu.value.rfc4514_string()]
    if isinstance(valu, x509.RegisteredID):
        return ["registeredid", valu.value.dotted_string]
    if isinstance(valu, x509.OtherName):
        return ["othername", f"{valu.type_id.dotted_string}:{hexb(valu.value)}"]
    raise ValueError(valu)


def pubkey(cert):
    spki = cert.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    key = cert.public_key()
    retn = {"spki": hexb(spki), "sha256": hashlib.sha256(spki).hexdigest(), "sha1": hashlib.sha1(spki).hexdigest()}
    if isinstance(key, rsa.RSAPublicKey):
        nums = key.public_numbers()
        retn.update(algo="rsa", size=key.key_size, rsa={"mod": format(nums.n, "x"), "exp": nums.e})
    elif isinstance(key, ec.EllipticCurvePublicKey):
        retn.update(algo="ec", size=key.key_size, curve=key.curve.name)
    elif isinstance(key, dsa.DSAPublicKey):
        retn.update(algo="dsa", size=key.key_size)
    elif isinstance(key, ed25519.Ed25519PublicKey):
        retn.update(algo="ed25519", size=256)
    elif isinstance(key, ed448.Ed448PublicKey):
        retn.update(algo="ed448", size=456)
    elif isinstance(key, x25519.X25519PublicKey):
        retn.update(algo="x25519", size=256)
    elif isinstance(key, x448.X448PublicKey):
        retn.update(algo="x448", size=448)
    return retn


def ref(der):
    """The subset of slib.utils.x509.parse() cryptography can produce for a certificate."""

    cert = x509.load_der_x509_certificate(der)
    try:
        hashalg = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else None
    except Exception:
        hashalg = None

    retn = {
        "sha256": hashlib.sha256(der).hexdigest(),
        "sha1": hashlib.sha1(der).hexdigest(),
        "md5": hashlib.md5(der).hexdigest(),
        "size": len(der),
        "version": cert.version.value,
        "serial": serialHex(cert.serial_number),
        "subject": name(cert.subject),
        "issuer": name(cert.issuer),
        "notbefore": millis(cert.not_valid_before_utc),
        "notafter": millis(cert.not_valid_after_utc),
        "sigalgo": {"oid": cert.signature_algorithm_oid.dotted_string, "hash": hashalg},
        "signature": hexb(cert.signature),
        "pubkey": pubkey(cert),
        "sans": [], "ca": None, "pathlen": None, "keyusage": [], "extkeyusage": [],
        "ski": None, "aki": None, "crls": [], "ocsp": [], "caissuers": [], "policies": [],
        "precert": False,
    }

    for ext in cert.extensions:
        valu = ext.value
        oid = ext.oid
        if oid.dotted_string == "1.3.6.1.4.1.11129.2.4.3":
            retn["precert"] = True
        elif oid == ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
            retn["sans"] = [gname(g) for g in valu]
        elif oid == ExtensionOID.BASIC_CONSTRAINTS:
            retn["ca"] = valu.ca
            retn["pathlen"] = valu.path_length
        elif oid == ExtensionOID.KEY_USAGE:
            usage = [n for n in KEYUSAGE if getattr(valu, n)]
            if valu.key_agreement:
                usage += [n for n in ("encipher_only", "decipher_only") if getattr(valu, n)]
            retn["keyusage"] = usage
        elif oid == ExtensionOID.EXTENDED_KEY_USAGE:
            retn["extkeyusage"] = [o.dotted_string for o in valu]
        elif oid == ExtensionOID.SUBJECT_KEY_IDENTIFIER:
            retn["ski"] = hexb(valu.digest)
        elif oid == ExtensionOID.AUTHORITY_KEY_IDENTIFIER:
            retn["aki"] = hexb(valu.key_identifier)
        elif oid == ExtensionOID.CRL_DISTRIBUTION_POINTS:
            for point in valu:
                for g in point.full_name or ():
                    if isinstance(g, x509.UniformResourceIdentifier):
                        retn["crls"].append(g.value)
        elif oid == ExtensionOID.AUTHORITY_INFORMATION_ACCESS:
            for desc in valu:
                if isinstance(desc.access_location, x509.UniformResourceIdentifier):
                    if desc.access_method == x509.AuthorityInformationAccessOID.OCSP:
                        retn["ocsp"].append(desc.access_location.value)
                    elif desc.access_method == x509.AuthorityInformationAccessOID.CA_ISSUERS:
                        retn["caissuers"].append(desc.access_location.value)
        elif oid == ExtensionOID.CERTIFICATE_POLICIES:
            retn["policies"] = [p.policy_identifier.dotted_string for p in valu]

    retn["selfsigned"] = retn["subject"]["dn"] == retn["issuer"]["dn"] and (
        retn["aki"] is None or retn["aki"] == retn["ski"]
    )
    return retn


def project(parsed):
    """Reduce slib.utils.x509.parse() output to the fields ref() returns."""

    def tolist(valu):
        if isinstance(valu, (list, tuple)):
            return [tolist(v) for v in valu]
        if isinstance(valu, dict):
            return {k: tolist(v) for k, v in valu.items()}
        return valu

    parsed = tolist(parsed)
    retn = {k: parsed[k] for k in (
        "sha256", "sha1", "md5", "size", "version", "serial", "notbefore", "notafter",
        "signature", "sans", "ca", "pathlen", "ski", "aki", "crls", "ocsp", "caissuers",
        "policies", "precert", "selfsigned",
    )}
    retn["subject"] = {"dn": parsed["subject"]["dn"], "attrs": parsed["subject"]["attrs"]}
    retn["issuer"] = {"dn": parsed["issuer"]["dn"], "attrs": parsed["issuer"]["attrs"]}
    retn["sigalgo"] = {"oid": parsed["sigalgo"]["oid"], "hash": parsed["sigalgo"]["hash"]}
    usage = parsed["keyusage"]
    if "key_agreement" not in usage:
        usage = [u for u in usage if u not in ("encipher_only", "decipher_only")]
    retn["keyusage"] = usage
    retn["extkeyusage"] = [e["oid"] for e in parsed["extkeyusage"]]
    key = parsed["pubkey"]
    retn["pubkey"] = {k: key[k] for k in ("spki", "sha256", "sha1", "algo", "size") if k in key}
    for k in ("rsa", "curve"):
        if k in key:
            retn["pubkey"][k] = key[k]
    return retn


# A minimal DER encoder, for hand built certificates with edge cases cryptography won't make.

def der(tag, content):
    """Encode one TLV. tag is the full identifier octet(s) as bytes or an int."""

    if isinstance(tag, int):
        tag = bytes((tag,))
    size = len(content)
    if size < 0x80:
        head = bytes((size,))
    else:
        body = size.to_bytes((size.bit_length() + 7) // 8, "big")
        head = bytes((0x80 | len(body),)) + body
    return tag + head + content


def seq(*parts):
    return der(0x30, b"".join(parts))


def oid(dotted):
    arcs = [int(a) for a in dotted.split(".")]
    out = bytearray()
    for i, arc in enumerate([arcs[0] * 40 + arcs[1]] + arcs[2:]):
        chunk = [arc & 0x7F]
        arc >>= 7
        while arc:
            chunk.append(0x80 | (arc & 0x7F))
            arc >>= 7
        out += bytes(reversed(chunk))
    return der(0x06, bytes(out))


def integer(valu):
    size = (valu.bit_length() + 8) // 8
    return der(0x02, valu.to_bytes(size, "big", signed=True))


def attr(oidstr, valu, tag=0x0C):
    return der(0x31, seq(oid(oidstr), der(tag, valu)))


def nameder(*rdns):
    return seq(*rdns)


def utctime(text):
    return der(0x17, text.encode())


def gentime(text):
    return der(0x18, text.encode())


def ext(oidstr, valu, critical=False):
    parts = [oid(oidstr)]
    if critical:
        parts.append(der(0x01, b"\xff"))
    parts.append(der(0x04, valu))
    return seq(*parts)


SHA256RSA = seq(oid("1.2.840.113549.1.1.11"), der(0x05, b""))


def tbsder(spki, serial=integer(1), version=der(0xA0, integer(2)), sigalg=SHA256RSA,
           issuer=None, validity=None, subject=None, exts=None, extra=b""):
    issuer = issuer if issuer is not None else nameder(attr("2.5.4.3", b"Test CA"))
    subject = subject if subject is not None else nameder(attr("2.5.4.3", b"test.example.com"))
    validity = validity if validity is not None else seq(utctime("250101000000Z"), utctime("260101000000Z"))
    parts = [version or b"", serial, sigalg, issuer, validity, subject, spki, extra]
    if exts is not None:
        parts.append(der(0xA3, seq(*exts)))
    return seq(*parts)


def certder(tbs, sigalg=SHA256RSA, sig=b"\x00" + b"\x5a" * 32):
    return seq(tbs, sigalg, der(0x03, sig))

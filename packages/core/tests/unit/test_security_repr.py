"""A1 del audit 2026-05-12: CertBundle no debe filtrar la private key via repr()."""

from __future__ import annotations

import datetime as dt

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sunat_py.security.cert_loader import CertBundle


def _make_bundle() -> CertBundle:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TEST RUC 20000000001")])
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + dt.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return CertBundle(private_key=key, certificate=cert, cert_pem=cert_pem, key_pem=key_pem)


def test_certbundle_repr_no_leaks_private_key():
    bundle = _make_bundle()
    text = repr(bundle)
    assert "PRIVATE KEY" not in text
    assert "private_key=" not in text
    assert "key_pem=" not in text


def test_certbundle_repr_keeps_useful_fields():
    bundle = _make_bundle()
    assert bundle.common_name == "TEST RUC 20000000001"
    assert bundle.serial_hex
    # certificate y cert_pem siguen siendo parte del repr porque la cert es publica
    text = repr(bundle)
    assert "certificate=" in text
    assert "cert_pem=" in text

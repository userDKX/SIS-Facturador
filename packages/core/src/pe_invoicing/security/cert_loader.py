"""Carga de certificado digital PKCS12 (.pfx).

El SDK no toma opinion sobre donde vive el .pfx: puede ser env var en
base64 (tipico en serverless), un archivo local, una entrada de vault,
etc. El caller pasa los bytes ya leidos.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate
from cryptography.x509.oid import NameOID


@dataclass(frozen=True)
class CertBundle:
    private_key: RSAPrivateKey
    certificate: Certificate
    cert_pem: bytes
    key_pem: bytes

    @property
    def common_name(self) -> str:
        attrs = self.certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        return str(attrs[0].value) if attrs else ""

    @property
    def serial_hex(self) -> str:
        return format(self.certificate.serial_number, "X")


def load_cert_from_pfx(pfx_bytes: bytes, password: str | None = None) -> CertBundle:
    """Carga un cert PKCS12 desde bytes crudos.

    SUNAT solo acepta certificados con private key RSA (no DSA, no EC).
    Si el PFX trae cualquier otro tipo, esta funcion levanta ValueError.
    """
    pwd_bytes = password.encode("utf-8") if password else None
    private_key, certificate, _additional = pkcs12.load_key_and_certificates(pfx_bytes, pwd_bytes)

    if private_key is None or certificate is None:
        raise ValueError("El PFX no contiene private key o certificate validos")

    if not isinstance(private_key, RSAPrivateKey):
        raise ValueError("La private key del PFX no es RSA (SUNAT requiere RSA)")

    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return CertBundle(
        private_key=private_key,
        certificate=certificate,
        cert_pem=cert_pem,
        key_pem=key_pem,
    )


def load_cert_from_base64(pfx_base64: str, password: str | None = None) -> CertBundle:
    """Carga un cert PKCS12 desde su representacion base64.

    Util cuando el cert vive en una env var (Vercel, Heroku, K8s Secret).
    """
    if not pfx_base64:
        raise ValueError("pfx_base64 esta vacio")
    return load_cert_from_pfx(base64.b64decode(pfx_base64), password)

import base64
from dataclasses import dataclass
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate
from cryptography.x509.oid import NameOID

from app.config import settings


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


@lru_cache
def load_cert() -> CertBundle:
    if not settings.CERT_PFX_BASE64:
        raise ValueError("CERT_PFX_BASE64 no esta configurado")

    pfx_bytes = base64.b64decode(settings.CERT_PFX_BASE64)
    password = settings.CERT_PASSWORD.encode("utf-8") if settings.CERT_PASSWORD else None

    private_key, certificate, _additional = pkcs12.load_key_and_certificates(pfx_bytes, password)

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

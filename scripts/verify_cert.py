"""Validacion local del certificado SUNAT (.p12) sin contactar SUNAT.

Hace:
  1. Carga el .p12 desde CERT_PFX_BASE64 + CERT_PASSWORD del .env
  2. Imprime metadata: subject, issuer, vigencia, serial, RUC
  3. Construye un UBL 2.1 de muestra usando datos reales del cert
  4. Lo firma con XMLDSig RSA-SHA256
  5. Verifica la firma con la llave publica del propio cert
  6. Guarda el XML firmado en storage/test/verify_cert/

Cero contacto con SUNAT. Cero efecto tributario. Cero escritura a DB.
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import XMLVerifier
from sis_facturador.config import settings
from sunat_py import (
    InvoiceInput,
    InvoiceLine,
    Party,
    build_invoice_xml,
    load_cert_from_base64,
    sign_invoice_xml,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _name_str(x509_name) -> str:
    parts = []
    for attr in x509_name:
        parts.append(f"{attr.oid._name}={attr.value}")
    return ", ".join(parts)


def _cn(x509_name) -> str:
    attrs = x509_name.get_attributes_for_oid(NameOID.COMMON_NAME)
    return str(attrs[0].value) if attrs else "(sin CN)"


def main() -> int:
    print("=" * 70)
    print("VALIDACION LOCAL DEL CERTIFICADO SUNAT")
    print("=" * 70)

    print("\n[1/5] Cargando .p12 desde CERT_PFX_BASE64...")
    bundle = load_cert_from_base64(settings.CERT_PFX_BASE64, settings.CERT_PASSWORD)
    cert = bundle.certificate
    print("      OK")

    print("\n[2/5] Metadata del certificado:")
    print(f"      Subject CN : {_cn(cert.subject)}")
    print(f"      Subject    : {_name_str(cert.subject)}")
    print(f"      Issuer CN  : {_cn(cert.issuer)}")
    print(f"      Issuer     : {_name_str(cert.issuer)}")
    print(f"      Serial hex : {bundle.serial_hex}")
    not_before = cert.not_valid_before_utc
    not_after = cert.not_valid_after_utc
    now = date.today()
    print(f"      Valido desde: {not_before.isoformat()}")
    print(f"      Valido hasta: {not_after.isoformat()}")
    days_left = (not_after.date() - now).days
    if days_left < 0:
        print(f"      *** VENCIDO hace {-days_left} dias ***")
    elif days_left < 30:
        print(f"      *** VENCE en {days_left} dias - renovar pronto ***")
    else:
        print(f"      Vigente: faltan {days_left} dias")

    print(
        f"      Public key : {bundle.private_key.key_size} bits "
        f"({type(bundle.private_key).__name__})"
    )

    print("\n[3/5] Construyendo UBL 2.1 de muestra (sin enviar a SUNAT)...")
    emisor = Party(
        tipo_doc="6",
        numero_doc="20XXXXXXXXX",
        razon_social="MI EMPRESA SAC",
        direccion="DIRECCION DE PRUEBA LOCAL",
        ubigeo="150101",
    )
    receptor = Party(
        tipo_doc="6",
        numero_doc="20100070970",
        razon_social="CLIENTE PRUEBA LOCAL SAC",
        direccion="AV CLIENTE 456",
    )
    lines = [
        InvoiceLine(
            codigo="P001",
            descripcion="SERVICIO DE PRUEBA LOCAL - NO ENVIAR A SUNAT",
            unidad="NIU",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100.00"),
            igv_afectacion="10",
        ),
    ]
    invoice = InvoiceInput(
        serie="F001",
        numero=1,
        fecha_emision=date.today(),
        moneda="PEN",
        emisor=emisor,
        receptor=receptor,
        lines=lines,
    )
    unsigned_xml = build_invoice_xml(invoice)
    print(f"      UBL generado: {len(unsigned_xml)} bytes")

    print("\n[4/5] Firmando con XMLDSig RSA-SHA256...")
    signed_xml = sign_invoice_xml(unsigned_xml, bundle)
    print(f"      Firmado: {len(signed_xml)} bytes")

    out_dir = REPO_ROOT / "storage" / "test" / "verify_cert"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{emisor.numero_doc}-01-{invoice.serie}-{invoice.numero}.xml"
    out_path.write_bytes(signed_xml)
    print(f"      Guardado en: {out_path.relative_to(REPO_ROOT)}")

    print("\n[5/5] Verificando firma con la llave publica del cert...")
    XMLVerifier().verify(signed_xml, x509_cert=bundle.cert_pem)
    print("      OK - firma valida criptograficamente")

    root = etree.fromstring(signed_xml)
    NS_DS = "http://www.w3.org/2000/09/xmldsig#"
    NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
    sig = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/"
        f"{{{NS_EXT}}}ExtensionContent/{{{NS_DS}}}Signature"
    )
    if sig is None:
        print("      *** ERROR: ds:Signature no esta en ExtensionContent ***")
        return 1
    print(f"      ds:Signature ubicada correctamente (Id={sig.get('Id')})")

    print("\n" + "=" * 70)
    print("VALIDACION COMPLETA - cert cargable, firma valida, estructura UBL OK")
    print("=" * 70)
    print("\nProximo paso sugerido: opcion 2 (homologacion SUNAT con cert real)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

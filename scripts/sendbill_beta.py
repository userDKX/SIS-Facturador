"""Homologacion: envia un XML firmado real al endpoint beta de SUNAT.

Hace:
  1. Carga el cert real (CERT_PFX_BASE64)
  2. Construye un UBL 2.1 con el RUC real del cert
  3. Firma + empaca ZIP
  4. Envia a https://e-beta.sunat.gob.pe (sin efecto tributario)
  5. Parsea el CDR y reporta resultado
  6. Guarda XML firmado y CDR en storage/test/beta/

Requiere en .env:
  MODE=beta
  SUNAT_RUC=<ruc real del cert>
  SUNAT_USER=<usuario secundario SOL>
  SUNAT_PASSWORD=<clave SOL>
  CERT_PFX_BASE64=<...>
  CERT_PASSWORD=<...>
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.config import settings
from app.security.cert_loader import load_cert
from app.signer.xmldsig import sign_invoice_xml
from app.sunat.client import SunatError, send_bill
from app.sunat.packager import pack_invoice
from app.ubl.builder import build_invoice_xml
from app.ubl.models import InvoiceInput, InvoiceLine, Party

EMISOR_RAZON = "TRANSP M & L EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA"
RECEPTOR_RUC = "20100070970"
RECEPTOR_RAZON = "CLIENTE PRUEBA HOMOLOGACION SAC"


def main() -> int:
    print("=" * 70)
    print(f"HOMOLOGACION SUNAT BETA - MODE={settings.MODE}")
    print("=" * 70)

    if settings.MODE != "beta":
        print(f"ERROR: MODE debe ser 'beta', no '{settings.MODE}'. Aborto.")
        return 2

    if settings.SUNAT_USER.upper() == "MODDATOS":
        print("ERROR: SUNAT_USER=MODDATOS no funciona con un cert real.")
        print("       Necesitas usuario secundario SOL del RUC propietario del cert.")
        return 2

    print(f"\nEndpoint : {settings.sunat_wsdl}")
    print(f"WS-User  : {settings.sunat_username}")
    print(f"RUC      : {settings.SUNAT_RUC}")

    print("\n[1/5] Cargando cert...")
    bundle = load_cert()
    print(f"      OK - {bundle.common_name[:60]}...")

    serie = "F001"
    numero = 1
    emisor = Party(
        tipo_doc="6",
        numero_doc=settings.SUNAT_RUC,
        razon_social=EMISOR_RAZON,
        direccion="DIRECCION HOMOLOGACION",
        ubigeo="150101",
    )
    receptor = Party(
        tipo_doc="6",
        numero_doc=RECEPTOR_RUC,
        razon_social=RECEPTOR_RAZON,
        direccion="AV PRUEBA 123",
    )
    invoice = InvoiceInput(
        serie=serie,
        numero=numero,
        fecha_emision=date.today(),
        moneda="PEN",
        emisor=emisor,
        receptor=receptor,
        lines=[
            InvoiceLine(
                codigo="P001",
                descripcion="ITEM HOMOLOGACION BETA",
                unidad="NIU",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("100.00"),
                igv_afectacion="10",
            ),
        ],
    )

    filename_base = f"{settings.SUNAT_RUC}-01-{serie}-{numero}"
    out_dir = REPO_ROOT / "storage" / "test" / "beta"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n[2/5] Construyendo + firmando UBL...")
    unsigned = build_invoice_xml(invoice)
    signed = sign_invoice_xml(unsigned, bundle)
    (out_dir / f"{filename_base}.xml").write_bytes(signed)
    print(f"      Firmado: {len(signed)} bytes")

    print("\n[3/5] Empaquetando ZIP...")
    zip_bytes = pack_invoice(signed, filename_base)
    (out_dir / f"{filename_base}.zip").write_bytes(zip_bytes)
    print(f"      ZIP: {len(zip_bytes)} bytes")

    print("\n[4/5] Enviando a SUNAT beta (sendBill)...")
    try:
        result = send_bill(zip_bytes, f"{filename_base}.zip")
    except SunatError as e:
        print(f"      *** ERROR DE TRANSPORTE/FAULT: {e.code} - {e.message}")
        return 3

    print(f"      Status      : {result.status}")
    print(f"      Code        : {result.code}")
    print(f"      Description : {result.description}")

    if result.cdr_xml:
        cdr_path = out_dir / f"R-{filename_base}.xml"
        cdr_path.write_bytes(result.cdr_xml)
        print(f"      CDR guardado: {cdr_path.relative_to(REPO_ROOT)}")

    print("\n[5/5] Veredicto:")
    if result.status == "accepted":
        print("      ACEPTADO sin observaciones (cert + integracion + SOL: TODO OK)")
        return 0
    if result.status == "accepted_with_obs":
        print("      ACEPTADO con observaciones - revisar description")
        return 0
    print("      RECHAZADO - revisar description (codigo SUNAT en code)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

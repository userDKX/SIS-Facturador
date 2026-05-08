"""EMISION REAL: envia una boleta de venta productiva a SUNAT.

A diferencia de la factura (tipo 01 / serie F), la boleta (tipo 03 / serie B)
acepta DNI, CE, pasaporte o "sin documento" como receptor. Igual queda
registrada en RVIE — solo anulable con NC posterior.

Uso:
    python scripts/sendbill_prod_boleta.py --confirm-real
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

if "--confirm-real" not in sys.argv:
    print("=" * 70)
    print("ABORTADO - falta flag --confirm-real")
    print("=" * 70)
    print()
    print("Este script EMITE una boleta productiva real a SUNAT.")
    print("Para correrlo agrega el flag explicito:")
    print()
    print("  python scripts/sendbill_prod_boleta.py --confirm-real")
    sys.exit(1)

os.environ["MODE"] = "prod"

from sis_facturador.config import get_settings

get_settings.cache_clear()

from pe_invoicing import (
    InvoiceInput,
    InvoiceLine,
    Party,
    SunatError,
    build_invoice_xml,
    build_zeep_client,
    load_cert_from_base64,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
)
from sis_facturador.config import settings

REPO_ROOT = Path(__file__).resolve().parent.parent

EMISOR_RAZON = "TRANSP M & L EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA"
EMISOR_DIRECCION = "CAL.ICA MZA. A LOTE. 8 ICA - NASCA - VISTA ALEGRE"

RECEPTOR_TIPO_DOC = "1"  # DNI
RECEPTOR_NUMERO_DOC = "61624121"
RECEPTOR_NOMBRE = "ANTONY MENCILLA"

ITEM_DESCRIPCION = "SERVICIO BASICO"
PRECIO_UNITARIO = Decimal("2.54")
CANTIDAD = Decimal("1")

TIPO_DOC = "03"  # Boleta de venta
SERIE = "B001"
NUMERO = 1


def main() -> int:
    print("=" * 70)
    print(f"EMISION PROD - BOLETA - MODE={settings.MODE}")
    print("=" * 70)

    if settings.MODE != "prod":
        print(f"ERROR: MODE no quedo en 'prod' (es '{settings.MODE}'). Aborto.")
        return 2

    print(f"\nEndpoint   : {settings.sunat_wsdl}")
    print(f"WS-User    : {settings.sunat_username}")
    print(f"RUC emisor : {settings.SUNAT_RUC}")
    print("\n--- Comprobante a emitir ---")
    print(f"  Tipo          : {TIPO_DOC} (boleta)")
    print(f"  Serie/numero  : {SERIE}-{NUMERO}")
    print(f"  Receptor      : DNI {RECEPTOR_NUMERO_DOC} - {RECEPTOR_NOMBRE}")
    print(f"  Item          : {ITEM_DESCRIPCION}")
    print(f"  Cantidad x P.U: {CANTIDAD} x S/ {PRECIO_UNITARIO}")
    igv = (PRECIO_UNITARIO * CANTIDAD * Decimal("0.18")).quantize(Decimal("0.01"))
    total = (PRECIO_UNITARIO * CANTIDAD + igv).quantize(Decimal("0.01"))
    print(f"  Base imponible: S/ {(PRECIO_UNITARIO * CANTIDAD).quantize(Decimal('0.01'))}")
    print(f"  IGV (18%)     : S/ {igv}")
    print(f"  TOTAL         : S/ {total}")

    print("\n[1/5] Cargando cert...")
    bundle = load_cert_from_base64(settings.CERT_PFX_BASE64, settings.CERT_PASSWORD)
    print("      OK")

    emisor = Party(
        tipo_doc="6",
        numero_doc=settings.SUNAT_RUC,
        razon_social=EMISOR_RAZON,
        direccion=EMISOR_DIRECCION,
        ubigeo="150101",
    )
    receptor = Party(
        tipo_doc=RECEPTOR_TIPO_DOC,
        numero_doc=RECEPTOR_NUMERO_DOC,
        razon_social=RECEPTOR_NOMBRE,
        direccion="",
    )
    invoice = InvoiceInput(
        serie=SERIE,
        numero=NUMERO,
        fecha_emision=date.today(),
        moneda="PEN",
        emisor=emisor,
        receptor=receptor,
        lines=[
            InvoiceLine(
                codigo="SERV01",
                descripcion=ITEM_DESCRIPCION,
                unidad="ZZ",
                cantidad=CANTIDAD,
                precio_unitario=PRECIO_UNITARIO,
                igv_afectacion="10",
            ),
        ],
        tipo_documento=TIPO_DOC,
    )

    filename_base = f"{settings.SUNAT_RUC}-{TIPO_DOC}-{SERIE}-{NUMERO}"
    out_dir = REPO_ROOT / "storage" / "prod"
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

    print("\n[4/5] Enviando a SUNAT PRODUCCION (sendBill)...")
    client = build_zeep_client(
        mode=settings.MODE,
        ruc=settings.SUNAT_RUC,
        username=settings.SUNAT_USER,
        password=settings.SUNAT_PASSWORD,
    )
    try:
        result = send_bill(client, zip_bytes, f"{filename_base}.zip")
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
        print("      *** ACEPTADA POR SUNAT - efecto tributario activo ***")
        print(f"      Boleta {SERIE}-{NUMERO} registrada en SUNAT.")
        return 0
    if result.status == "accepted_with_obs":
        print("      ACEPTADA con observaciones - efecto tributario activo")
        return 0
    print("      RECHAZADA - revisar codigo y mensaje")
    return 1


if __name__ == "__main__":
    sys.exit(main())

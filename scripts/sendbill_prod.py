"""EMISION REAL: envia una factura productiva a SUNAT (e-factura.sunat.gob.pe).

ATENCION: a diferencia de beta, esta emision tiene EFECTO TRIBUTARIO.
Una factura aceptada por prod queda registrada en el RVIE/RCE del contribuyente
y NO se borra. Solo puede anularse con Nota de Credito posterior.

Requiere flag --confirm-real para correr. Sin ese flag, aborta.

Uso:
    python scripts/sendbill_prod.py --confirm-real

Lee del .env la config base; sobrescribe MODE=prod localmente para que el
cliente cargue el WSDL de produccion. El .env puede quedarse en MODE=beta
como default seguro.
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
    print("Este script EMITE una factura productiva real a SUNAT.")
    print("Para correrlo agrega el flag explicito:")
    print()
    print("  python scripts/sendbill_prod.py --confirm-real")
    print()
    print("Una factura aceptada en prod NO se puede borrar - solo anular")
    print("con Nota de Credito posterior. Asegurate de los datos antes.")
    sys.exit(1)

os.environ["MODE"] = "prod"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings

get_settings.cache_clear()

from app.config import settings
from app.security.cert_loader import load_cert
from app.signer.xmldsig import sign_invoice_xml
from app.sunat.client import SunatError, send_bill
from app.sunat.packager import pack_invoice
from app.ubl.builder import build_invoice_xml
from app.ubl.models import InvoiceInput, InvoiceLine, Party

EMISOR_RAZON = "TRANSP M & L EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA"
EMISOR_DIRECCION = "CAL.ICA MZA. A LOTE. 8 ICA - NASCA - VISTA ALEGRE"

RECEPTOR_TIPO_DOC = "6"  # RUC
RECEPTOR_NUMERO_DOC = "20495184120"
RECEPTOR_NOMBRE = "TRANSP M & L EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA"
ITEM_DESCRIPCION = "SERVICIO BASICO"
PRECIO_UNITARIO = Decimal("1.00")
CANTIDAD = Decimal("1")

SERIE = "F001"
NUMERO = 1


def main() -> int:
    print("=" * 70)
    print(f"EMISION PROD - MODE={settings.MODE}")
    print("=" * 70)

    if settings.MODE != "prod":
        print(f"ERROR: MODE no quedo en 'prod' (es '{settings.MODE}'). Aborto.")
        return 2

    print(f"\nEndpoint   : {settings.sunat_wsdl}")
    print(f"WS-User    : {settings.sunat_username}")
    print(f"RUC emisor : {settings.SUNAT_RUC}")
    print("\n--- Comprobante a emitir ---")
    print(f"  Serie/numero  : {SERIE}-{NUMERO}")
    tipo_label = {"6": "RUC", "1": "DNI", "4": "CE", "7": "Pasaporte"}.get(
        RECEPTOR_TIPO_DOC, RECEPTOR_TIPO_DOC
    )
    print(f"  Receptor      : {tipo_label} {RECEPTOR_NUMERO_DOC} - {RECEPTOR_NOMBRE}")
    print(f"  Item          : {ITEM_DESCRIPCION}")
    print(f"  Cantidad x P.U: {CANTIDAD} x S/ {PRECIO_UNITARIO}")
    igv = (PRECIO_UNITARIO * CANTIDAD * Decimal("0.18")).quantize(Decimal("0.01"))
    total = (PRECIO_UNITARIO * CANTIDAD + igv).quantize(Decimal("0.01"))
    print(f"  Base imponible: S/ {(PRECIO_UNITARIO * CANTIDAD).quantize(Decimal('0.01'))}")
    print(f"  IGV (18%)     : S/ {igv}")
    print(f"  TOTAL         : S/ {total}")

    print("\n[1/5] Cargando cert...")
    bundle = load_cert()
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
    )

    filename_base = f"{settings.SUNAT_RUC}-01-{SERIE}-{NUMERO}"
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
        print("      *** ACEPTADA POR SUNAT - efecto tributario activo ***")
        print(f"      Comprobante {SERIE}-{NUMERO} registrado en SUNAT.")
        return 0
    if result.status == "accepted_with_obs":
        print("      ACEPTADA con observaciones - efecto tributario activo")
        return 0
    print("      RECHAZADA - revisar codigo y mensaje")
    return 1


if __name__ == "__main__":
    sys.exit(main())

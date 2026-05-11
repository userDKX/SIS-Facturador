"""Ejemplo standalone: emite una comunicacion de baja (RA) usando solo el SDK.

Diferencia clave respecto a factura/NC/ND: la comunicacion de baja va por
`sendSummary` (asincrono). SUNAT devuelve un ticket y procesa el documento
en segundos/minutos. Este script hace polling automatico con get_status.

Uso:
    export CERT_PFX_BASE64="..."   # tu .pfx en base64
    export CERT_PASSWORD="..."     # password del .pfx
    export SUNAT_RUC="20XXXXXXXXX"
    export SUNAT_USER="USERSOL"    # secundario, sin RUC adelante
    export SUNAT_PASSWORD="..."
    export SUNAT_MODE="prod"       # "beta" o "prod" (default: prod)
    python -m examples.emit_voided

Anula el comprobante indicado en ITEM_TIPO/ITEM_SERIE/ITEM_NUMERO.
Ajusta esos valores y FECHA_REF antes de correr.

Restricciones SUNAT:
  - FECHA_REF debe ser la fecha de emision del CPE original.
  - SUNAT solo acepta bajas dentro de los 7 dias posteriores al CPE.
  - Un RA agrupa solo CPE emitidos en la misma fecha.
"""

from __future__ import annotations

import os
import sys
from datetime import date

from sunat_py import (
    Party,
    SunatError,
    VoidedDocumentsInput,
    VoidedItem,
    build_voided_xml,
    build_zeep_client,
    get_status,
    load_cert_from_base64,
    pack_invoice,
    send_summary,
    sign_invoice_xml,
    today_lima,
)

# Comprobante a anular
FECHA_REF = date(2026, 5, 11)  # fecha de emision del CPE original
ITEM_TIPO = "01"               # "01" factura, "03" boleta — RA no acepta "03"
ITEM_SERIE = "F001"
ITEM_NUMERO = 2
ITEM_MOTIVO = "ERROR EN EMISION"

# Correlativo del RA para esta fecha (incrementar si ya enviaste otro RA hoy)
RA_CORRELATIVO = 1


def main() -> int:
    pfx_b64 = os.environ.get("CERT_PFX_BASE64", "")
    pfx_password = os.environ.get("CERT_PASSWORD", "")
    ruc = os.environ.get("SUNAT_RUC", "")
    sunat_user = os.environ.get("SUNAT_USER", "")
    sunat_password = os.environ.get("SUNAT_PASSWORD", "")
    mode = os.environ.get("SUNAT_MODE", "prod")

    if not all([pfx_b64, ruc, sunat_user, sunat_password]):
        print("Faltan variables de entorno (CERT_PFX_BASE64, SUNAT_RUC, SUNAT_USER, SUNAT_PASSWORD)")
        return 1
    if mode not in ("beta", "prod"):
        print(f"SUNAT_MODE debe ser 'beta' o 'prod', recibido: {mode!r}")
        return 1

    cert = load_cert_from_base64(pfx_b64, pfx_password)
    print(f"Cert cargado: CN={cert.common_name}, serial={cert.serial_hex}")

    emisor = Party(
        tipo_doc="6",
        numero_doc=ruc,
        razon_social="TRANSP M & L EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA",
        direccion="CAL.ICA MZA. A LOTE. 8 ICA - NASCA - VISTA ALEGRE",
        ubigeo="150101",
    )

    ra = VoidedDocumentsInput(
        correlativo=RA_CORRELATIVO,
        fecha_referencia=FECHA_REF,
        fecha_emision=today_lima(),
        emisor=emisor,
        items=[
            VoidedItem(
                tipo_doc=ITEM_TIPO,
                serie=ITEM_SERIE,
                numero=ITEM_NUMERO,
                motivo=ITEM_MOTIVO,
            ),
        ],
    )

    unsigned = build_voided_xml(ra)
    signed = sign_invoice_xml(unsigned, cert)

    filename_base = f"{ruc}-{ra.id_ra}"
    zip_bytes = pack_invoice(signed, filename_base)
    print(f"Documento: {filename_base}")

    client = build_zeep_client(mode=mode, ruc=ruc, username=sunat_user, password=sunat_password)  # type: ignore[arg-type]
    try:
        ticket = send_summary(client, zip_bytes, f"{filename_base}.zip")
    except SunatError as exc:
        print(f"SUNAT error al enviar: {exc}")
        return 2

    print(f"Ticket:  {ticket}")
    print("Consultando CDR (polling)...")

    def log_attempt(attempt: int, status_code: str) -> None:
        print(f"  intento {attempt + 1}: statusCode={status_code}")

    try:
        result = get_status(client, ticket, retries=15, interval=5.0, on_attempt=log_attempt)
    except SunatError as exc:
        print(f"SUNAT error al consultar ticket: {exc}")
        return 2

    print(f"Status: {result.status}")
    print(f"Code:   {result.code}")
    print(f"Desc:   {result.description}")

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, f"{filename_base}.xml"), "wb") as f:
        f.write(signed)
    if result.cdr_xml:
        with open(os.path.join(out_dir, f"R-{filename_base}.xml"), "wb") as f:
            f.write(result.cdr_xml)
        print(f"CDR guardado: R-{filename_base}.xml")

    return 0 if result.status in ("accepted", "accepted_with_obs") else 3


if __name__ == "__main__":
    sys.exit(main())

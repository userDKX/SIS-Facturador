"""Ejemplo standalone: emite una nota de debito (tipo 08) usando solo el SDK.

Uso:
    export CERT_PFX_BASE64="..."   # tu .pfx en base64
    export CERT_PASSWORD="..."     # password del .pfx
    export SUNAT_RUC="20XXXXXXXXX"
    export SUNAT_USER="USERSOL"    # secundario, sin RUC adelante
    export SUNAT_PASSWORD="..."
    export SUNAT_MODE="prod"       # "beta" o "prod" (default: prod)
    python -m examples.emit_debitnote

Aumenta el monto de la factura F001-1 (referencia) emitiendo la ND FD01-1
con motivo "01" (intereses por mora). Ajusta DOC_SERIE, DOC_NUMERO y ND_SERIE
segun el comprobante original que quieras modificar.
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

from sunat_py import (
    DebitNoteInput,
    InvoiceLine,
    Party,
    ReferenciaDoc,
    SunatError,
    build_debitnote_xml,
    build_zeep_client,
    load_cert_from_base64,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
    today_lima,
)

# Documento original que esta ND modifica
DOC_TIPO = "01"  # "01" factura, "03" boleta
DOC_SERIE = "F001"
DOC_NUMERO = 1

# Serie de la ND: mismo prefijo que el doc original (F→FD, B→BD)
ND_SERIE = "FD01"
ND_NUMERO = 1


def main() -> int:
    pfx_b64 = os.environ.get("CERT_PFX_BASE64", "")
    pfx_password = os.environ.get("CERT_PASSWORD", "")
    ruc = os.environ.get("SUNAT_RUC", "")
    sunat_user = os.environ.get("SUNAT_USER", "")
    sunat_password = os.environ.get("SUNAT_PASSWORD", "")
    mode = os.environ.get("SUNAT_MODE", "prod")

    if not all([pfx_b64, ruc, sunat_user, sunat_password]):
        print(
            "Faltan variables de entorno (CERT_PFX_BASE64, SUNAT_RUC, SUNAT_USER, SUNAT_PASSWORD)"
        )
        return 1
    if mode not in ("beta", "prod"):
        print(f"SUNAT_MODE debe ser 'beta' o 'prod', recibido: {mode!r}")
        return 1

    cert = load_cert_from_base64(pfx_b64, pfx_password)
    print(f"Cert cargado: CN={cert.common_name}, serial={cert.serial_hex}")

    emisor = Party(
        tipo_doc="6",
        numero_doc=ruc,
        razon_social="MI EMPRESA SAC",
        direccion="AV PRINCIPAL 123 LIMA",
        ubigeo="150101",
    )
    receptor = Party(
        tipo_doc="6",
        numero_doc=ruc,
        razon_social="MI EMPRESA SAC",
        direccion="",
    )

    nd = DebitNoteInput(
        serie=ND_SERIE,
        numero=ND_NUMERO,
        fecha_emision=today_lima(),
        moneda="PEN",
        motivo_codigo="01",  # cat. 10: 01=intereses por mora
        motivo_descripcion="INTERES POR MORA",
        referencia=ReferenciaDoc(tipo_doc=DOC_TIPO, serie=DOC_SERIE, numero=DOC_NUMERO),
        emisor=emisor,
        receptor=receptor,
        lines=[
            InvoiceLine(
                codigo="MORA01",
                descripcion="INTERES POR MORA",
                unidad="ZZ",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("0.50"),
                igv_afectacion="10",
            ),
        ],
    )

    unsigned = build_debitnote_xml(nd)
    signed = sign_invoice_xml(unsigned, cert)

    filename_base = f"{ruc}-08-{nd.serie}-{nd.numero}"
    zip_bytes = pack_invoice(signed, filename_base)

    client = build_zeep_client(mode=mode, ruc=ruc, username=sunat_user, password=sunat_password)  # type: ignore[arg-type]
    try:
        result = send_bill(client, zip_bytes, f"{filename_base}.zip")
    except SunatError as exc:
        print(f"SUNAT error: {exc}")
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

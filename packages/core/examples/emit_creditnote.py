"""Ejemplo standalone: emite una nota de credito (tipo 07) usando solo el SDK.

Uso:
    export CERT_PFX_BASE64="..."   # tu .pfx en base64
    export CERT_PASSWORD="..."     # password del .pfx
    export SUNAT_RUC="20XXXXXXXXX"
    export SUNAT_USER="USERSOL"    # secundario, sin RUC adelante
    export SUNAT_PASSWORD="..."
    python -m examples.emit_creditnote

Anula la factura F001-1 (referencia) emitiendo la NC FC01-1 con motivo
"01" (anulacion de la operacion).
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal

from pe_invoicing import (
    CreditNoteInput,
    InvoiceLine,
    Party,
    ReferenciaDoc,
    SunatError,
    build_creditnote_xml,
    build_zeep_client,
    load_cert_from_base64,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
)


def main() -> int:
    pfx_b64 = os.environ.get("CERT_PFX_BASE64", "")
    pfx_password = os.environ.get("CERT_PASSWORD", "")
    ruc = os.environ.get("SUNAT_RUC", "")
    sunat_user = os.environ.get("SUNAT_USER", "")
    sunat_password = os.environ.get("SUNAT_PASSWORD", "")

    if not all([pfx_b64, ruc, sunat_user, sunat_password]):
        print("Faltan variables de entorno (CERT_PFX_BASE64, SUNAT_RUC, SUNAT_USER, SUNAT_PASSWORD)")
        return 1

    cert = load_cert_from_base64(pfx_b64, pfx_password)
    print(f"Cert cargado: CN={cert.common_name}, serial={cert.serial_hex}")

    emisor = Party(
        tipo_doc="6",
        numero_doc=ruc,
        razon_social="MI EMPRESA",
        direccion="AV. EJEMPLO 123, LIMA",
    )
    receptor = Party(
        tipo_doc="6",
        numero_doc="20512345678",
        razon_social="CLIENTE EJEMPLO S.A.C.",
        direccion="AV. CLIENTE 456, LIMA",
    )

    nc = CreditNoteInput(
        serie="FC01",
        numero=1,
        fecha_emision=date.today(),
        moneda="PEN",
        motivo_codigo="01",
        motivo_descripcion="ANULACION DE LA OPERACION",
        referencia=ReferenciaDoc(tipo_doc="01", serie="F001", numero=1),
        emisor=emisor,
        receptor=receptor,
        lines=[
            InvoiceLine(
                codigo="SERV01",
                descripcion="Servicio de consultoria",
                unidad="ZZ",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("100"),
                igv_afectacion="10",
            ),
        ],
    )

    unsigned = build_creditnote_xml(nc)
    signed = sign_invoice_xml(unsigned, cert)

    filename_base = f"{ruc}-07-{nc.serie}-{nc.numero}"
    zip_bytes = pack_invoice(signed, filename_base)

    client = build_zeep_client(mode="beta", ruc=ruc, username=sunat_user, password=sunat_password)
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

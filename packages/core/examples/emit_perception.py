"""Ejemplo standalone: emite un comprobante de percepcion (tipo 40).

Solo agentes de percepcion designados por SUNAT pueden emitir tipo 40.
Verifica que el RUC del emisor este registrado en el padron antes de
correr — sino la emision sera rechazada con codigo 1071.

Pipeline:
  build -> sign -> pack ZIP -> sendBill (sincrono) -> CDR

Uso:
    export CERT_PFX_BASE64="..."
    export CERT_PASSWORD="..."
    export SUNAT_RUC="20XXXXXXXXX"
    export SUNAT_USER="USERSOL"
    export SUNAT_PASSWORD="..."
    export SUNAT_MODE="prod"        # "beta" o "prod"
    python -m examples.emit_perception

Notas SUNAT:
  - Serie alfanumerica de 4 chars empezando con P (P001, P002, ...).
  - Tasa tipica para regimen general (02): 2%. Para combustibles (01): 1%.
  - El comprobante de percepcion SUMA al cliente (no resta como retencion).
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal

from sunat_py import (
    Party,
    SunatError,
    build_zeep_client,
    load_cert_from_base64,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
    today_lima,
)
from sunat_py.ubl.builder import build_perception_xml
from sunat_py.ubl.models import PerceptionDocReference, PerceptionInput

# Datos del comprobante de percepcion
PER_SERIE = "P001"
PER_NUMERO = 1
REGIMEN = "02"  # 01 combustibles, 02 venta interna, 03 importacion
TASA = Decimal("2.00")  # debe corresponder al regimen declarado

# Datos del cliente (sobre el que se percibe)
CLIENTE_TIPO_DOC = "6"  # 6=RUC, 1=DNI, 4=CE
CLIENTE_NUMERO_DOC = "20100070970"
CLIENTE_RAZON_SOCIAL = "CLIENTE EJEMPLO SAC"
CLIENTE_DIRECCION = "AV CLIENTE 456 LIMA"

# Cobros sobre los que se percibe
COBROS = [
    {
        "factura_serie": "F001",
        "factura_numero": 1,
        "fecha_factura": date(2026, 5, 1),
        "moneda": "PEN",
        "total_factura": Decimal("1180.00"),
        "fecha_cobro": date(2026, 5, 11),
        "importe_cobrado": Decimal("1180.00"),
    },
]


def main() -> int:
    pfx_b64 = os.environ.get("CERT_PFX_BASE64", "")
    pfx_password = os.environ.get("CERT_PASSWORD", "")
    ruc = os.environ.get("SUNAT_RUC", "")
    sunat_user = os.environ.get("SUNAT_USER", "")
    sunat_password = os.environ.get("SUNAT_PASSWORD", "")
    mode = os.environ.get("SUNAT_MODE", "prod")

    if not all([pfx_b64, ruc, sunat_user, sunat_password]):
        print(
            "Faltan variables de entorno (CERT_PFX_BASE64, SUNAT_RUC, "
            "SUNAT_USER, SUNAT_PASSWORD)"
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
        razon_social="AGENTE DE PERCEPCION EIRL",
        direccion="AV AGENTE 123 LIMA",
        ubigeo="150101",
    )
    receptor = Party(
        tipo_doc=CLIENTE_TIPO_DOC,  # type: ignore[arg-type]
        numero_doc=CLIENTE_NUMERO_DOC,
        razon_social=CLIENTE_RAZON_SOCIAL,
        direccion=CLIENTE_DIRECCION,
    )

    items = []
    total_percibido = Decimal("0")
    total_cobrado = Decimal("0")
    for c in COBROS:
        importe_percepcion = (c["importe_cobrado"] * TASA / Decimal("100")).quantize(
            Decimal("0.01")
        )
        importe_total_cobrado = c["importe_cobrado"] + importe_percepcion
        items.append(
            PerceptionDocReference(
                serie=c["factura_serie"],  # type: ignore[arg-type]
                numero=c["factura_numero"],  # type: ignore[arg-type]
                fecha_emision=c["fecha_factura"],  # type: ignore[arg-type]
                moneda=c["moneda"],  # type: ignore[arg-type]
                total=c["total_factura"],  # type: ignore[arg-type]
                fecha_pago=c["fecha_cobro"],  # type: ignore[arg-type]
                importe_sin_percepcion=c["importe_cobrado"],  # type: ignore[arg-type]
                importe_percepcion=importe_percepcion,
                fecha_percepcion=c["fecha_cobro"],  # type: ignore[arg-type]
                importe_total_cobrado=importe_total_cobrado,
            )
        )
        total_percibido += importe_percepcion
        total_cobrado += importe_total_cobrado

    perception = PerceptionInput(
        serie=PER_SERIE,
        numero=PER_NUMERO,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen=REGIMEN,  # type: ignore[arg-type]
        tasa=TASA,
        total_percibido=total_percibido,
        total_cobrado=total_cobrado,
        items=items,
    )

    unsigned = build_perception_xml(perception)
    signed = sign_invoice_xml(unsigned, cert)

    filename_base = f"{ruc}-40-{PER_SERIE}-{PER_NUMERO}"
    zip_bytes = pack_invoice(signed, filename_base)
    print(f"Documento: {filename_base}")

    client = build_zeep_client(
        mode=mode,  # type: ignore[arg-type]
        ruc=ruc,
        username=sunat_user,
        password=sunat_password,
        service="otroscpe",
    )
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

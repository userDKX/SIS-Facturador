"""Ejemplo standalone: emite un comprobante de retencion (tipo 20).

A diferencia de factura/NC/ND, la retencion solo puede emitirla un
agente de retencion designado por SUNAT. Antes de correr este script,
verifica que el RUC del emisor este registrado como agente de retencion
en el padron SUNAT — sino la emision sera rechazada con codigo 1071.

Pipeline:
  build -> sign -> pack ZIP -> sendBill (sincrono) -> CDR

Uso:
    export CERT_PFX_BASE64="..."   # tu .pfx en base64
    export CERT_PASSWORD="..."     # password del .pfx
    export SUNAT_RUC="20XXXXXXXXX"
    export SUNAT_USER="USERSOL"    # secundario, sin RUC adelante
    export SUNAT_PASSWORD="..."
    export SUNAT_MODE="prod"       # "beta" o "prod" (default: prod)
    python -m examples.emit_retention

Ajusta los datos del receptor (proveedor retenido) y de los pagos
referenciados antes de correr.

Notas SUNAT:
  - La serie es alfanumerica de 4 chars empezando con R (R001, R002...).
  - La tasa actual es 3% desde 01/03/2014. Antes era 6%.
  - El receptor puede ser RUC, DNI, CE o pasaporte (cualquier proveedor).
  - Solo se puede retener sobre facturas (tipo 01), no boletas.
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
from sunat_py.ubl.builder import build_retention_xml
from sunat_py.ubl.models import RetentionDocReference, RetentionInput

# Datos del comprobante de retencion
RET_SERIE = "R001"
RET_NUMERO = 1
TASA = Decimal("3.00")  # 3% desde 2014; usar 6.00 solo para emisiones historicas

# Datos del proveedor retenido (puede ser RUC, DNI, CE)
PROVEEDOR_TIPO_DOC = "6"  # 6=RUC, 1=DNI, 4=CE, 7=pasaporte
PROVEEDOR_NUMERO_DOC = "20100070970"
PROVEEDOR_RAZON_SOCIAL = "PROVEEDOR EJEMPLO SAC"
PROVEEDOR_DIRECCION = "AV PROVEEDOR 456 LIMA"

# Pagos sobre los que se retiene (uno por cada pago, no por factura)
PAGOS = [
    {
        "factura_serie": "F001",
        "factura_numero": 1,
        "fecha_factura": date(2026, 5, 1),
        "moneda": "PEN",
        "total_factura": Decimal("1180.00"),
        "fecha_pago": date(2026, 5, 11),
        "importe_pagado": Decimal("1180.00"),
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
        razon_social="AGENTE DE RETENCION EIRL",
        direccion="AV AGENTE 123 LIMA",
        ubigeo="150101",
    )
    receptor = Party(
        tipo_doc=PROVEEDOR_TIPO_DOC,  # type: ignore[arg-type]
        numero_doc=PROVEEDOR_NUMERO_DOC,
        razon_social=PROVEEDOR_RAZON_SOCIAL,
        direccion=PROVEEDOR_DIRECCION,
    )

    items = []
    total_retenido = Decimal("0")
    total_pagado = Decimal("0")
    for p in PAGOS:
        importe_retencion = (p["importe_pagado"] * TASA / Decimal("100")).quantize(
            Decimal("0.01")
        )
        importe_neto_pagado = p["importe_pagado"] - importe_retencion
        items.append(
            RetentionDocReference(
                serie=p["factura_serie"],  # type: ignore[arg-type]
                numero=p["factura_numero"],  # type: ignore[arg-type]
                fecha_emision=p["fecha_factura"],  # type: ignore[arg-type]
                moneda=p["moneda"],  # type: ignore[arg-type]
                total=p["total_factura"],  # type: ignore[arg-type]
                fecha_pago=p["fecha_pago"],  # type: ignore[arg-type]
                importe_sin_retencion=p["importe_pagado"],  # type: ignore[arg-type]
                importe_retencion=importe_retencion,
                fecha_retencion=p["fecha_pago"],  # type: ignore[arg-type]
                importe_neto_pagado=importe_neto_pagado,
            )
        )
        total_retenido += importe_retencion
        total_pagado += importe_neto_pagado

    retention = RetentionInput(
        serie=RET_SERIE,
        numero=RET_NUMERO,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="01",
        tasa=TASA,
        total_retenido=total_retenido,
        total_pagado=total_pagado,
        items=items,
    )

    unsigned = build_retention_xml(retention)
    signed = sign_invoice_xml(unsigned, cert)

    filename_base = f"{ruc}-20-{RET_SERIE}-{RET_NUMERO}"
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

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from sis_facturador.schemas.invoice import PartyIn


class RetentionItemIn(BaseModel):
    """Pago retenido sobre una factura.

    Cada item es un pago, no una factura completa: si una factura tiene
    varios pagos parciales, va como varios items con distinto
    `correlativo_pago` apuntando al mismo `(ref_serie, ref_numero)`.

    `ref_tipo_doc`: SUNAT solo admite "01" (factura) en retencion del IGV.
    `ref_moneda`: si distinta de PEN, debe venir `tipo_cambio` y
        `tipo_cambio_fecha` (error 2799).
    """

    ref_tipo_doc: Literal["01"] = "01"
    ref_serie: Annotated[
        str, Field(min_length=4, max_length=4, pattern=r"^[FE][A-Z0-9]{3}$")
    ]
    ref_numero: Annotated[int, Field(gt=0)]
    ref_fecha_emision: date
    ref_moneda: str = "PEN"
    ref_total: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]

    fecha_pago: date
    correlativo_pago: Annotated[int, Field(ge=1)] = 1
    importe_sin_retencion: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
    importe_retencion: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
    fecha_retencion: date
    importe_neto_pagado: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]

    tipo_cambio: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=4)] | None = (
        None
    )
    tipo_cambio_fecha: date | None = None


_RETENTION_EXAMPLE = {
    "serie": "R001",
    "numero": 1,
    "fecha_emision": "2026-05-11",
    "regimen": "01",
    "tasa": "3.00",
    "total_retenido": "35.40",
    "total_pagado": "1144.60",
    "receptor": {
        "tipo_doc": "6",
        "numero_doc": "20512345678",
        "razon_social": "PROVEEDOR EJEMPLO S.A.C.",
        "direccion": "AV PROVEEDOR 456 LIMA",
    },
    "items": [
        {
            "ref_tipo_doc": "01",
            "ref_serie": "F001",
            "ref_numero": 1,
            "ref_fecha_emision": "2026-05-01",
            "ref_moneda": "PEN",
            "ref_total": "1180.00",
            "fecha_pago": "2026-05-11",
            "correlativo_pago": 1,
            "importe_sin_retencion": "1180.00",
            "importe_retencion": "35.40",
            "fecha_retencion": "2026-05-11",
            "importe_neto_pagado": "1144.60",
        },
    ],
}


class RetentionCreate(BaseModel):
    """Payload para emitir un comprobante de retencion (tipo 20).

    El RUC del emisor (agente de retencion) sale de la config del servicio
    (`SUNAT_RUC`) — no se pasa en el payload. Solo agentes designados por
    SUNAT pueden emitir tipo 20; verificar en
    <http://www.sunat.gob.pe/padronesnotificaciones/>.

    `regimen`: catalogo SUNAT 23, siempre "01".
    `tasa`: 3.00 desde 01/03/2014. 6.00 solo para emisiones historicas.

    Las sumas deben cuadrar:
      * `total_retenido` == sum(items[].importe_retencion)
      * `total_pagado`   == sum(items[].importe_neto_pagado)
      * por cada item: `importe_neto_pagado == importe_sin_retencion - importe_retencion`

    Si alguna no cuadra, devuelve 422 antes de tocar SUNAT.
    """

    model_config = ConfigDict(
        json_schema_extra={"examples": [_RETENTION_EXAMPLE]},
    )

    serie: Annotated[str, Field(min_length=4, max_length=4, pattern=r"^R[A-Z0-9]{3}$")]
    numero: Annotated[int, Field(gt=0)]
    fecha_emision: date
    regimen: Literal["01"] = "01"
    tasa: Annotated[Decimal, Field(gt=0, max_digits=5, decimal_places=2)]
    total_retenido: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
    total_pagado: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
    nota: Annotated[str | None, Field(max_length=500)] = None
    receptor: PartyIn
    items: Annotated[list[RetentionItemIn], Field(min_length=1)]


class RetentionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ref_tipo_doc: str
    ref_serie: str
    ref_numero: int
    ref_fecha_emision: date
    ref_moneda: str
    ref_total: Decimal
    fecha_pago: date
    correlativo_pago: int
    importe_sin_retencion: Decimal
    importe_retencion: Decimal
    fecha_retencion: date
    importe_neto_pagado: Decimal
    tipo_cambio: Decimal | None
    tipo_cambio_fecha: date | None


class RetentionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ruc_emisor": "20XXXXXXXXX",
                "tipo_doc": "20",
                "serie": "R001",
                "numero": 1,
                "fecha_emision": "2026-05-11",
                "moneda": "PEN",
                "regimen": "01",
                "tasa": "3.00",
                "total_retenido": "35.40",
                "total_pagado": "1144.60",
                "receptor_tipo_doc": "6",
                "receptor_numero_doc": "20512345678",
                "receptor_razon_social": "PROVEEDOR EJEMPLO S.A.C.",
                "status": "accepted",
                "sunat_code": "0",
                "sunat_description": "El Comprobante de Retencion numero R001-1, ha sido aceptado",
                "xml_signed_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/xml/20XXXXXXXXX-20-R001-1.xml",
                "cdr_xml_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/cdr/R-20XXXXXXXXX-20-R001-1.xml",
                "error_message": None,
                "items": [],
            }
        },
    )

    id: int
    ruc_emisor: str
    tipo_doc: str
    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    regimen: str
    tasa: Decimal
    total_retenido: Decimal
    total_pagado: Decimal
    nota: str | None
    receptor_tipo_doc: str
    receptor_numero_doc: str
    receptor_razon_social: str
    status: str
    sunat_code: str | None
    sunat_description: str | None
    xml_signed_url: str | None
    cdr_xml_url: str | None
    error_message: str | None
    items: list[RetentionItemResponse]

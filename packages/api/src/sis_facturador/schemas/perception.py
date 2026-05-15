from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from sis_facturador.schemas.invoice import PartyIn


class PerceptionItemIn(BaseModel):
    """Cobro percibido sobre una factura/boleta/NC/ND/ticket.

    Cada item es un cobro al cliente. Si una factura se cobra en varios
    pagos, va como varios items con distinto `correlativo_pago`.

    `ref_tipo_doc`: SUNAT admite 01 factura, 03 boleta, 07 NC, 08 ND,
        12 ticket. Lo tipico para venta interna (regimen 02) es 01 o 03.
    `ref_moneda`: si != PEN, requiere `tipo_cambio` y `tipo_cambio_fecha`.
    """

    ref_tipo_doc: Literal["01", "03", "07", "08", "12"] = "01"
    ref_serie: Annotated[str, Field(min_length=4, max_length=4)]
    ref_numero: Annotated[int, Field(gt=0)]
    ref_fecha_emision: date
    ref_moneda: str = "PEN"
    ref_total: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]

    fecha_pago: date
    correlativo_pago: Annotated[int, Field(ge=1)] = 1
    importe_sin_percepcion: Annotated[
        Decimal, Field(gt=0, max_digits=14, decimal_places=2)
    ]
    importe_percepcion: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
    fecha_percepcion: date
    importe_total_cobrado: Annotated[
        Decimal, Field(gt=0, max_digits=14, decimal_places=2)
    ]

    tipo_cambio: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=4)] | None = (
        None
    )
    tipo_cambio_fecha: date | None = None


_PERCEPTION_EXAMPLE = {
    "serie": "P001",
    "numero": 1,
    "fecha_emision": "2026-05-11",
    "regimen": "02",
    "tasa": "2.00",
    "total_percibido": "23.60",
    "total_cobrado": "1203.60",
    "receptor": {
        "tipo_doc": "6",
        "numero_doc": "20512345678",
        "razon_social": "CLIENTE EJEMPLO S.A.C.",
        "direccion": "AV CLIENTE 456 LIMA",
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
            "importe_sin_percepcion": "1180.00",
            "importe_percepcion": "23.60",
            "fecha_percepcion": "2026-05-11",
            "importe_total_cobrado": "1203.60",
        },
    ],
}


class PerceptionCreate(BaseModel):
    """Payload para emitir un comprobante de percepcion (tipo 40).

    El RUC del emisor (agente de percepcion) sale de la config del
    servicio (`SUNAT_RUC`). Solo agentes designados por SUNAT pueden
    emitir tipo 40 (<http://www.sunat.gob.pe/padronesnotificaciones/>).

    `regimen`: catalogo SUNAT 22 — 01 combustible, 02 venta interna, 03
    importacion.
    `tasa`: porcentaje declarado (corresponder al regimen).

    Las sumas deben cuadrar:
      * `total_percibido` == sum(items[].importe_percepcion)
      * `total_cobrado`   == sum(items[].importe_total_cobrado)
      * por cada item: `importe_total_cobrado == importe_sin_percepcion + importe_percepcion`
        (suma a diferencia de retencion, que resta).
    """

    model_config = ConfigDict(
        json_schema_extra={"examples": [_PERCEPTION_EXAMPLE]},
    )

    serie: Annotated[str, Field(min_length=4, max_length=4, pattern=r"^P[A-Z0-9]{3}$")]
    numero: Annotated[int, Field(gt=0)]
    fecha_emision: date
    regimen: Literal["01", "02", "03"]
    tasa: Annotated[Decimal, Field(gt=0, max_digits=5, decimal_places=2)]
    total_percibido: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
    total_cobrado: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
    nota: Annotated[str | None, Field(max_length=500)] = None
    receptor: PartyIn
    items: Annotated[list[PerceptionItemIn], Field(min_length=1)]


class PerceptionItemResponse(BaseModel):
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
    importe_sin_percepcion: Decimal
    importe_percepcion: Decimal
    fecha_percepcion: date
    importe_total_cobrado: Decimal
    tipo_cambio: Decimal | None
    tipo_cambio_fecha: date | None


class PerceptionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ruc_emisor": "20XXXXXXXXX",
                "tipo_doc": "40",
                "serie": "P001",
                "numero": 1,
                "fecha_emision": "2026-05-11",
                "moneda": "PEN",
                "regimen": "02",
                "tasa": "2.00",
                "total_percibido": "23.60",
                "total_cobrado": "1203.60",
                "status": "accepted",
                "sunat_code": "0",
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
    total_percibido: Decimal
    total_cobrado: Decimal
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
    items: list[PerceptionItemResponse]

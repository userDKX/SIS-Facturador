from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sis_facturador.schemas.invoice import LineIn, PartyIn

MotivoNC = Literal[
    "01",  # Anulacion de la operacion
    "02",  # Anulacion por error en el RUC
    "03",  # Correccion por error en la descripcion
    "04",  # Descuento global
    "05",  # Descuento por item
    "06",  # Devolucion total
    "07",  # Devolucion por item
    "08",  # Bonificacion
    "09",  # Disminucion en el valor
    "10",  # Otros conceptos
    "13",  # Ajuste - montos y/o fechas de pago
]


class ReferenciaIn(BaseModel):
    """Comprobante original que la nota de crédito modifica.

    tipo_doc (Catálogo SUNAT 01):
      * "01" Factura
      * "03" Boleta de venta
    """

    tipo_doc: Literal["01", "03"]
    serie: Annotated[str, Field(min_length=4, max_length=4, pattern=r"^[FB][A-Z0-9]{3}$")]
    numero: Annotated[int, Field(gt=0)]


_NC_FACTURA_EXAMPLE = {
    "serie": "FC01",
    "numero": 1,
    "fecha_emision": "2026-05-10",
    "moneda": "PEN",
    "motivo_codigo": "01",
    "motivo_descripcion": "ANULACION DE LA OPERACION",
    "referencia": {
        "tipo_doc": "01",
        "serie": "F001",
        "numero": 1,
    },
    "receptor": {
        "tipo_doc": "6",
        "numero_doc": "20512345678",
        "razon_social": "EMPRESA EJEMPLO S.A.C.",
        "direccion": "AV. JAVIER PRADO 1234, SAN ISIDRO, LIMA",
    },
    "lines": [
        {
            "codigo": "PROD001",
            "descripcion": "Servicio de consultoría",
            "unidad": "ZZ",
            "cantidad": "1.00",
            "precio_unitario": "100.00",
            "igv_afectacion": "10",
        },
    ],
}

_NC_BOLETA_EXAMPLE = {
    "serie": "BC01",
    "numero": 1,
    "fecha_emision": "2026-05-10",
    "moneda": "PEN",
    "motivo_codigo": "06",
    "motivo_descripcion": "DEVOLUCION TOTAL",
    "referencia": {
        "tipo_doc": "03",
        "serie": "B001",
        "numero": 1,
    },
    "receptor": {
        "tipo_doc": "1",
        "numero_doc": "12345678",
        "razon_social": "JUAN PEREZ MENDOZA",
        "direccion": "",
    },
    "lines": [
        {
            "codigo": "ART01",
            "descripcion": "Polo manga corta talla M",
            "unidad": "NIU",
            "cantidad": "2.00",
            "precio_unitario": "25.00",
            "igv_afectacion": "10",
        },
    ],
}


class CreditNoteCreate(BaseModel):
    """Payload para emitir una nota de crédito (tipo 07).

    La serie debe coincidir con el prefijo del comprobante referenciado:
      * NC de factura (`referencia.tipo_doc="01"`) → serie con prefijo F
      * NC de boleta  (`referencia.tipo_doc="03"`) → serie con prefijo B

    Si no coincide, devuelve 422 antes de tocar SUNAT.

    `motivo_codigo` es del catálogo SUNAT 09 (tipo de NC).
    `motivo_descripcion` es texto libre que SUNAT muestra en consultas.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [_NC_FACTURA_EXAMPLE, _NC_BOLETA_EXAMPLE],
        }
    )

    serie: Annotated[str, Field(min_length=4, max_length=4, pattern=r"^[FB][A-Z0-9]{3}$")]
    numero: Annotated[int, Field(gt=0)]
    fecha_emision: date
    moneda: str = "PEN"
    motivo_codigo: MotivoNC
    motivo_descripcion: Annotated[str, Field(min_length=3, max_length=250)]
    referencia: ReferenciaIn
    receptor: PartyIn
    lines: Annotated[list[LineIn], Field(min_length=1)]

    @model_validator(mode="after")
    def _serie_matches_referencia(self) -> "CreditNoteCreate":
        expected_prefix = "F" if self.referencia.tipo_doc == "01" else "B"
        if not self.serie.startswith(expected_prefix):
            raise ValueError(
                f"La serie '{self.serie}' no corresponde al tipo del comprobante "
                f"referenciado ('{self.referencia.tipo_doc}'). NC de factura usa "
                f"serie F###; NC de boleta usa serie B###."
            )
        return self


class CreditNoteResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "invoice_id": 5,
                "ruc_emisor": "20495184120",
                "tipo_doc": "07",
                "serie": "FC01",
                "numero": 1,
                "fecha_emision": "2026-05-10",
                "moneda": "PEN",
                "motivo_codigo": "01",
                "motivo_descripcion": "ANULACION DE LA OPERACION",
                "ref_tipo_doc": "01",
                "ref_serie": "F001",
                "ref_numero": 1,
                "subtotal": "100.00",
                "igv": "18.00",
                "total": "118.00",
                "status": "accepted",
                "sunat_code": "0",
                "sunat_description": "La Nota de Credito numero FC01-1, ha sido aceptada",
                "xml_signed_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/xml/20495184120-07-FC01-1.xml",
                "cdr_xml_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/cdr/R-20495184120-07-FC01-1.xml",
                "error_message": None,
            }
        },
    )

    id: int
    invoice_id: int | None
    ruc_emisor: str
    tipo_doc: str
    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    motivo_codigo: str
    motivo_descripcion: str
    ref_tipo_doc: str
    ref_serie: str
    ref_numero: int
    subtotal: Decimal
    igv: Decimal
    total: Decimal
    status: str
    sunat_code: str | None
    sunat_description: str | None
    xml_signed_url: str | None
    cdr_xml_url: str | None
    error_message: str | None

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PartyIn(BaseModel):
    """Receptor del comprobante.

    tipo_doc (Catálogo SUNAT 06):
      * "6" RUC
      * "1" DNI
      * "4" Carnet de extranjería
      * "7" Pasaporte
      * "0" Sin documento (solo boletas, hasta cierto monto)

    Ojo: la factura tipo 01 solo acepta tipo_doc="6" (RUC). La boleta tipo 03
    acepta los demás. Si mandas DNI en una factura, SUNAT te rechaza con
    código 2800.
    """

    tipo_doc: Annotated[str, Field(min_length=1, max_length=1)]
    numero_doc: Annotated[str, Field(min_length=1, max_length=15)]
    razon_social: Annotated[str, Field(min_length=1, max_length=250)]
    direccion: str = ""


class LineIn(BaseModel):
    """Línea de detalle del comprobante.

    igv_afectacion (Catálogo SUNAT 07):
      * "10" Gravado - operación onerosa (default)
      * "20" Exonerado
      * "30" Inafecto
    """

    codigo: Annotated[str, Field(min_length=1, max_length=30)]
    descripcion: Annotated[str, Field(min_length=1, max_length=500)]
    unidad: Annotated[str, Field(min_length=1, max_length=10)]
    cantidad: Annotated[Decimal, Field(gt=0)]
    precio_unitario: Annotated[Decimal, Field(ge=0)]
    igv_afectacion: str = "10"


_FACTURA_EXAMPLE = {
    "tipo_documento": "01",
    "serie": "F001",
    "numero": 123,
    "fecha_emision": "2026-05-08",
    "moneda": "PEN",
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

_BOLETA_EXAMPLE = {
    "tipo_documento": "03",
    "serie": "B001",
    "numero": 456,
    "fecha_emision": "2026-05-08",
    "moneda": "PEN",
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


class InvoiceCreate(BaseModel):
    """Payload para emitir una Factura (tipo 01) o Boleta (tipo 03).

    La serie debe matchear el tipo de comprobante:
      * Factura tipo "01" → serie con prefijo F (ej. F001, F002)
      * Boleta  tipo "03" → serie con prefijo B (ej. B001, B002)

    Si el prefijo no coincide con el tipo, devuelve 422 antes de tocar SUNAT.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [_FACTURA_EXAMPLE, _BOLETA_EXAMPLE],
        }
    )

    tipo_documento: Literal["01", "03"] = "01"
    serie: Annotated[str, Field(min_length=4, max_length=4, pattern=r"^[FB]\d{3}$")]
    numero: Annotated[int, Field(gt=0)]
    fecha_emision: date
    moneda: str = "PEN"
    receptor: PartyIn
    lines: Annotated[list[LineIn], Field(min_length=1)]

    @model_validator(mode="after")
    def _validate_serie_matches_tipo(self) -> "InvoiceCreate":
        expected_prefix = "F" if self.tipo_documento == "01" else "B"
        if not self.serie.startswith(expected_prefix):
            raise ValueError(
                f"La serie '{self.serie}' no corresponde al tipo_documento "
                f"'{self.tipo_documento}'. Factura (01) usa serie F###; "
                f"boleta (03) usa serie B###."
            )
        return self


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ruc_emisor": "20XXXXXXXXX",
                "tipo_doc": "01",
                "serie": "F001",
                "numero": 123,
                "fecha_emision": "2026-05-08",
                "moneda": "PEN",
                "subtotal": "100.00",
                "igv": "18.00",
                "total": "118.00",
                "status": "accepted",
                "sunat_code": "0",
                "sunat_description": "La Factura numero F001-123, ha sido aceptada",
                "xml_signed_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/xml/20XXXXXXXXX-01-F001-123.xml",
                "cdr_xml_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/cdr/R-20XXXXXXXXX-01-F001-123.xml",
                "error_message": None,
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
    subtotal: Decimal
    igv: Decimal
    total: Decimal
    status: str
    sunat_code: str | None
    sunat_description: str | None
    xml_signed_url: str | None
    cdr_xml_url: str | None
    error_message: str | None

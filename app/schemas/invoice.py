from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class PartyIn(BaseModel):
    """Receptor del comprobante.

    tipo_doc: catalogo SUNAT 06 -- "6" RUC, "1" DNI, "4" Carnet, "7" Pasaporte, "0" sin doc.
    """

    tipo_doc: Annotated[str, Field(min_length=1, max_length=1)]
    numero_doc: Annotated[str, Field(min_length=1, max_length=15)]
    razon_social: Annotated[str, Field(min_length=1, max_length=250)]
    direccion: str = ""


class LineIn(BaseModel):
    codigo: Annotated[str, Field(min_length=1, max_length=30)]
    descripcion: Annotated[str, Field(min_length=1, max_length=500)]
    unidad: Annotated[str, Field(min_length=1, max_length=10)]
    cantidad: Annotated[Decimal, Field(gt=0)]
    precio_unitario: Annotated[Decimal, Field(ge=0)]
    igv_afectacion: str = "10"


class InvoiceCreate(BaseModel):
    serie: Annotated[str, Field(min_length=4, max_length=4, pattern=r"^F\d{3}$")]
    numero: Annotated[int, Field(gt=0)]
    fecha_emision: date
    moneda: str = "PEN"
    receptor: PartyIn
    lines: Annotated[list[LineIn], Field(min_length=1)]


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

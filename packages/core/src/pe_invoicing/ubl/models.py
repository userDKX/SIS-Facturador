from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Party:
    """Emisor o receptor del comprobante.

    tipo_doc: catalogo SUNAT 06 (Identificador de documento)
        "6" = RUC
        "1" = DNI
        "4" = Carnet de extranjeria
        "7" = Pasaporte
        "0" = Sin documento
    """

    tipo_doc: str
    numero_doc: str
    razon_social: str
    direccion: str = ""
    ubigeo: str = "0000"


@dataclass(frozen=True)
class InvoiceLine:
    """Linea de detalle de la factura.

    igv_afectacion: catalogo SUNAT 07 (Tipo de afectacion del IGV)
        "10" = Gravado - Operacion onerosa (default)
        "20" = Exonerado - Operacion onerosa
        "30" = Inafecto - Operacion onerosa
    """

    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio_unitario: Decimal
    igv_afectacion: str = "10"


@dataclass(frozen=True)
class InvoiceTotals:
    subtotal: Decimal
    igv: Decimal
    total: Decimal


@dataclass(frozen=True)
class InvoiceInput:
    """Comprobante de venta (factura o boleta).

    tipo_documento: catalogo SUNAT 01 (Tipo de Documento)
        "01" = Factura (serie F###)
        "03" = Boleta de venta (serie B###)
    """

    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    emisor: Party
    receptor: Party
    lines: list[InvoiceLine]
    tipo_documento: str = "01"
